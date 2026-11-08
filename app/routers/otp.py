"""Verificación de correo por código (OTP) para el registro.

Flujo:
  1. POST /api/v1/otp/email/request  { email }        -> genera y "envía" un código.
  2. POST /api/v1/otp/email/verify   { email, code }  -> valida el código.

Si no hay SMTP configurado, el código se devuelve en la respuesta (modo demo)
y también se imprime en los logs del servidor. En producción, configura las
variables SMTP_* para enviar un correo real.
"""
import json
import logging
import random
import smtplib
import time
import urllib.error
import urllib.request
from email.message import EmailMessage

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from ..config import settings

router = APIRouter(prefix="/api/v1/otp", tags=["verificación"])

# Almacén en memoria: email -> (código, expira_en, intentos). Suficiente para la demo.
_CODES: dict[str, dict] = {}
_MAX_ATTEMPTS = 5


class EmailIn(BaseModel):
    email: EmailStr


class VerifyIn(BaseModel):
    email: EmailStr
    code: str


class RequestOut(BaseModel):
    sent: bool
    channel: str          # "email" (enviado real) | "dev" (devuelto aquí)
    dev_code: str | None = None  # solo en modo demo


class VerifyOut(BaseModel):
    verified: bool


def _email_html(code: str) -> str:
    """Plantilla HTML del correo de verificación (colores Ayni/Shalom)."""
    mins = settings.otp_ttl_seconds // 60
    return f"""\
<!doctype html>
<html lang="es"><body style="margin:0;background:#f4f6fb;font-family:Segoe UI,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6fb;padding:28px 0;">
    <tr><td align="center">
      <table role="presentation" width="440" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.06);">
        <tr><td style="background:#1e2a5a;padding:22px 28px;color:#fff;font-size:22px;font-weight:800;">
          Ayni
          <span style="display:block;font-size:12px;font-weight:400;opacity:.8;margin-top:2px;">
            Hoy por ti, mañana por mí
          </span>
        </td></tr>
        <tr><td style="padding:30px 28px 10px;color:#1c2333;">
          <h1 style="margin:0 0 8px;font-size:20px;color:#1e2a5a;">Tu código de verificación</h1>
          <p style="margin:0 0 20px;font-size:14px;color:#5b6170;line-height:1.5;">
            Usa este código para confirmar tu correo y crear tu cuenta en Ayni.
          </p>
          <div style="text-align:center;margin:10px 0 18px;">
            <span style="display:inline-block;background:#f4f6fb;border:1px dashed #1e2a5a;border-radius:12px;
                         padding:14px 26px;font-size:34px;font-weight:800;letter-spacing:10px;color:#1e2a5a;">
              {code}
            </span>
          </div>
          <p style="margin:0 0 24px;font-size:13px;color:#8a909c;text-align:center;">
            Vence en {mins} minutos. Si no lo solicitaste, ignora este mensaje.
          </p>
        </td></tr>
        <tr><td style="background:#f4f6fb;padding:16px 28px;color:#8a909c;font-size:12px;text-align:center;">
          © Ayni · Plataforma de colaboración vecinal
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def _send_resend(to: str, code: str) -> bool:
    """Envía el código con la API de Resend. True si se envió."""
    if not settings.resend_api_token:
        return False
    payload = json.dumps({
        "from": settings.resend_from,
        "to": [to],
        "subject": "Tu código de verificación Ayni",
        "html": _email_html(code),
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.resend_api_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        return True
    except urllib.error.HTTPError as e:
        logging.warning("Resend respondió %s: %s", e.code, e.read().decode("utf-8", "ignore"))
        return False
    except Exception as e:  # noqa: BLE001
        logging.warning("No se pudo enviar por Resend: %s", e)
        return False


def _send_email(to: str, code: str) -> bool:
    """Envía el código por SMTP. Devuelve True si se envió de verdad."""
    if not (settings.smtp_host and settings.smtp_user and settings.smtp_password):
        return False
    msg = EmailMessage()
    msg["Subject"] = "Tu código de verificación Ayni"
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.set_content(
        f"Hola,\n\nTu código de verificación de Ayni es: {code}\n"
        f"Vence en {settings.otp_ttl_seconds // 60} minutos.\n\n"
        "Si no solicitaste este código, ignora este mensaje."
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
            s.starttls()
            s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        return True
    except Exception as e:  # noqa: BLE001
        logging.warning("No se pudo enviar el correo OTP: %s", e)
        return False


@router.post("/email/request", response_model=RequestOut)
def request_code(payload: EmailIn):
    email = payload.email.lower()
    code = f"{random.randint(0, 999999):06d}"
    _CODES[email] = {
        "code": code,
        "expires": time.time() + settings.otp_ttl_seconds,
        "attempts": 0,
    }

    logging.info("Código OTP para %s: %s", email, code)  # visible en logs del server
    # Preferir Resend; si no, SMTP.
    sent_real = _send_resend(email, code) or _send_email(email, code)

    # Mientras OTP_DEV_RETURN_CODE=true, devolvemos el código igual (respaldo en
    # pantalla), porque sin dominio verificado Resend puede no entregar el correo
    # aunque la API responda OK. Pon OTP_DEV_RETURN_CODE=false cuando el dominio
    # esté verificado y quieras ocultarlo.
    dev_code = code if settings.otp_dev_return_code else None
    return RequestOut(
        sent=True,
        channel="email" if sent_real else "dev",
        dev_code=dev_code,
    )


@router.post("/email/verify", response_model=VerifyOut)
def verify_code(payload: VerifyIn):
    email = payload.email.lower()
    entry = _CODES.get(email)
    if not entry:
        raise HTTPException(status_code=400, detail="Solicita un código primero.")
    if time.time() > entry["expires"]:
        _CODES.pop(email, None)
        raise HTTPException(status_code=400, detail="El código venció. Solicita uno nuevo.")
    if entry["attempts"] >= _MAX_ATTEMPTS:
        _CODES.pop(email, None)
        raise HTTPException(status_code=429, detail="Demasiados intentos. Solicita un código nuevo.")

    entry["attempts"] += 1
    if payload.code.strip() != entry["code"]:
        raise HTTPException(status_code=400, detail="Código incorrecto.")

    _CODES.pop(email, None)  # un solo uso
    return VerifyOut(verified=True)

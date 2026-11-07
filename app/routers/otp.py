"""Verificación de correo por código (OTP) para el registro.

Flujo:
  1. POST /api/v1/otp/email/request  { email }        -> genera y "envía" un código.
  2. POST /api/v1/otp/email/verify   { email, code }  -> valida el código.

Si no hay SMTP configurado, el código se devuelve en la respuesta (modo demo)
y también se imprime en los logs del servidor. En producción, configura las
variables SMTP_* para enviar un correo real.
"""
import logging
import random
import smtplib
import time
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
    sent_real = _send_email(email, code)
    if sent_real:
        return RequestOut(sent=True, channel="email")

    # Sin SMTP: modo demo (devolvemos el código para poder probar).
    return RequestOut(
        sent=True,
        channel="dev",
        dev_code=code if settings.otp_dev_return_code else None,
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

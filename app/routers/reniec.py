"""Consulta de DNI (RENIEC) para autocompletar nombres en el registro.

No existe una API pública oficial gratuita de RENIEC; se usa un proveedor tercero
(apis.net.pe, apiperu.dev, decolecta, etc.) mediante un token configurado en
`RENIEC_API_TOKEN`. Si no hay token, se responde con datos de prueba (mock) para
que la demo del registro funcione igual.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/api/v1/reniec", tags=["reniec"])


class DniResult(BaseModel):
    dni: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str
    nombre_completo: str
    source: str  # "reniec" (API real) | "mock" (sin token)


# Datos de prueba para la demo (incluye el DNI demo de María del seed).
_MOCK_DNIS = {
    "72345678": ("María", "Quispe", "Huamán"),
    "10000001": ("José", "Huamán", "Ccopa"),
    "10000002": ("Rosa", "Ccopa", "Flores"),
    "10000003": ("Pedro", "Flores", "Quispe"),
}


def _mock_person(dni: str) -> DniResult:
    nombres, ap_pat, ap_mat = _MOCK_DNIS.get(
        dni, ("Vecino", "Demo", f"N{dni[-4:]}" if len(dni) >= 4 else "Ayni")
    )
    full = f"{nombres} {ap_pat} {ap_mat}".strip()
    return DniResult(
        dni=dni,
        nombres=nombres,
        apellido_paterno=ap_pat,
        apellido_materno=ap_mat,
        nombre_completo=full,
        source="mock",
    )


def _extract(data: dict) -> tuple[str, str, str]:
    """Normaliza la respuesta de distintos proveedores a (nombres, ap_pat, ap_mat)."""
    def pick(*keys):
        for k in keys:
            v = data.get(k)
            if v:
                return str(v).strip()
        return ""

    nombres = pick("nombres", "first_name", "name", "nombre")
    ap_pat = pick("apellidoPaterno", "apellido_paterno", "last_name_father", "apellidoPaterno")
    ap_mat = pick("apellidoMaterno", "apellido_materno", "last_name_mother")
    # Algunos proveedores solo devuelven nombre completo.
    if not (nombres or ap_pat) and data.get("nombreCompleto"):
        partes = str(data["nombreCompleto"]).split()
        if len(partes) >= 3:
            ap_pat, ap_mat, nombres = partes[0], partes[1], " ".join(partes[2:])
        else:
            nombres = str(data["nombreCompleto"])
    return nombres, ap_pat, ap_mat


@router.get("/dni/{dni}", response_model=DniResult)
def consultar_dni(dni: str):
    dni = dni.strip()
    if not dni.isdigit() or len(dni) != 8:
        raise HTTPException(status_code=422, detail="El DNI debe tener 8 dígitos numéricos.")

    # Sin token → modo demo (mock).
    if not settings.reniec_api_token:
        return _mock_person(dni)

    # Con token → consulta al proveedor real.
    url = f"{settings.reniec_api_url}?{urllib.parse.urlencode({'numero': dni})}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {settings.reniec_api_token}",
            "Accept": "application/json",
            "User-Agent": "AyniApp/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise HTTPException(status_code=404, detail="No se encontró una persona con ese DNI.")
        raise HTTPException(status_code=502, detail=f"El servicio de RENIEC respondió {e.code}.")
    except Exception:
        raise HTTPException(status_code=502, detail="No se pudo consultar RENIEC en este momento.")

    nombres, ap_pat, ap_mat = _extract(data)
    if not (nombres or ap_pat):
        raise HTTPException(status_code=404, detail="No se encontró una persona con ese DNI.")

    full = f"{nombres} {ap_pat} {ap_mat}".strip()
    return DniResult(
        dni=dni,
        nombres=nombres,
        apellido_paterno=ap_pat,
        apellido_materno=ap_mat,
        nombre_completo=full,
        source="reniec",
    )

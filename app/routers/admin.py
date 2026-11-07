"""Panel de administración / moderación.

Flujo: un vecino reporta un contenido (servicio, producto, aviso, solicitud o
usuario) → el moderador/admin ve el reporte CON su contexto → decide:
  - dismiss        : descartar el reporte (no procede)
  - takedown       : cerrar/ocultar la publicación reportada
  - suspend_user   : suspender al dueño del contenido (no podrá iniciar sesión)

Todo aquí exige rol 'moderador' o 'admin'.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_roles

router = APIRouter(prefix="/api/v1/admin", tags=["administración"])


# ---------- helpers ----------
def _target_context(db: Session, target_type: str, target_id: str) -> Optional[dict]:
    """Devuelve un resumen del contenido reportado para que el admin lo evalúe."""
    if target_type == "service":
        o = db.get(models.Service, target_id)
        if o:
            return {"type": "service", "id": o.id, "title": o.title,
                    "detail": o.description, "status": o.status, "owner_id": o.provider_id}
    elif target_type == "product":
        o = db.get(models.Product, target_id)
        if o:
            return {"type": "product", "id": o.id, "title": o.title,
                    "detail": o.description, "status": o.status, "owner_id": o.owner_id}
    elif target_type == "post":
        o = db.get(models.CommunityPost, target_id)
        if o:
            return {"type": "post", "id": o.id, "title": o.title,
                    "detail": o.body, "status": o.verification_status, "owner_id": o.author_id}
    elif target_type == "help_request":
        o = db.get(models.HelpRequest, target_id)
        if o:
            return {"type": "help_request", "id": o.id, "title": o.request_type,
                    "detail": o.description, "status": o.status, "owner_id": o.author_id}
    elif target_type == "user":
        o = db.get(models.User, target_id)
        if o:
            return {"type": "user", "id": o.id, "title": o.display_name,
                    "detail": None, "status": o.status, "owner_id": o.id}
    return None


def _hide_target(db: Session, target_type: str, target_id: str) -> bool:
    """Cierra/oculta la publicación reportada."""
    if target_type == "service":
        o = db.get(models.Service, target_id)
        if o:
            o.status = "deleted"
            return True
    elif target_type == "product":
        o = db.get(models.Product, target_id)
        if o:
            o.status = "deleted"
            return True
    elif target_type == "post":
        o = db.get(models.CommunityPost, target_id)
        if o:
            o.verification_status = "expired"
            return True
    elif target_type == "help_request":
        o = db.get(models.HelpRequest, target_id)
        if o:
            o.status = "cancelled"
            return True
    return False


# ---------- schemas locales ----------
class ReportWithContext(BaseModel):
    report: schemas.ReportOut
    reporter_name: Optional[str] = None
    target: Optional[dict] = None


class ModerationAction(BaseModel):
    action: str = Field(pattern="^(dismiss|takedown|suspend_user)$")
    note: Optional[str] = None


class ModerationResult(BaseModel):
    report_id: str
    action: str
    result: str


# ---------- endpoints ----------
@router.get("/reports", response_model=list[ReportWithContext])
def list_reports_with_context(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("moderador", "admin")),
):
    """Lista los reportes con el contexto del contenido reportado (para el panel)."""
    q = db.query(models.Report)
    if status:
        q = q.filter(models.Report.status == status)
    out = []
    for r in q.order_by(models.Report.created_at.desc()).limit(200).all():
        reporter = db.get(models.User, r.reporter_id)
        out.append(ReportWithContext(
            report=schemas.ReportOut.model_validate(r),
            reporter_name=reporter.display_name if reporter else None,
            target=_target_context(db, r.target_type, r.target_id),
        ))
    return out


@router.post("/reports/{report_id}/action", response_model=ModerationResult)
def moderate_report(
    report_id: str,
    payload: ModerationAction,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("moderador", "admin")),
):
    """El admin decide qué hacer con un reporte."""
    report = db.get(models.Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    ctx = _target_context(db, report.target_type, report.target_id)

    if payload.action == "takedown":
        if report.target_type == "user":
            raise HTTPException(status_code=400, detail="Para un usuario usa 'suspend_user'")
        if not _hide_target(db, report.target_type, report.target_id):
            raise HTTPException(status_code=404, detail="El contenido reportado ya no existe")
        report.status = "reviewed"
        result = "Publicación cerrada/ocultada"

    elif payload.action == "suspend_user":
        owner_id = ctx["owner_id"] if ctx else None
        if not owner_id:
            raise HTTPException(status_code=404, detail="No se encontró al usuario")
        user = db.get(models.User, owner_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if user.role == "admin":
            raise HTTPException(status_code=400, detail="No se puede suspender a un administrador")
        user.status = "suspended"
        report.status = "reviewed"
        result = f"Usuario '{user.display_name}' suspendido"

    else:  # dismiss
        report.status = "dismissed"
        result = "Reporte descartado"

    db.commit()
    return ModerationResult(report_id=report.id, action=payload.action, result=result)


@router.post("/users/{user_id}/reactivate", response_model=ModerationResult)
def reactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("moderador", "admin")),
):
    """Revierte una suspensión (vuelve a activar la cuenta)."""
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.status = "active"
    db.commit()
    return ModerationResult(report_id="-", action="reactivate", result=f"Usuario '{user.display_name}' reactivado")

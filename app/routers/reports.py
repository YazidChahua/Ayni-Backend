"""Reportes de moderación."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles


class ReportStatusUpdate(BaseModel):
    status: str = Field(pattern="^(pending|reviewed|dismissed)$")

router = APIRouter(prefix="/api/v1/reports", tags=["moderación"])


@router.post("", response_model=schemas.ReportOut, status_code=201)
def create_report(
    payload: schemas.ReportCreate,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    report = models.Report(reporter_id=current.id, **payload.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("", response_model=list[schemas.ReportOut])
def list_reports(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("moderador", "admin")),
):
    return db.query(models.Report).order_by(models.Report.created_at.desc()).all()


@router.patch("/{report_id}", response_model=schemas.ReportOut)
def resolve_report(
    report_id: str,
    payload: ReportStatusUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("moderador", "admin")),
):
    report = db.get(models.Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    report.status = payload.status
    db.commit()
    db.refresh(report)
    return report

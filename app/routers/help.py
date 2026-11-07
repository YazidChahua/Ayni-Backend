"""Solidaridad / cadena de favores: solicitudes de ayuda vecinal."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/v1/help-requests", tags=["solidaridad"])


@router.get("", response_model=list[schemas.HelpRequestOut])
def list_help_requests(
    neighborhood_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    urgency: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(models.HelpRequest)
    if neighborhood_id is not None:
        q = q.filter(models.HelpRequest.neighborhood_id == neighborhood_id)
    if status:
        q = q.filter(models.HelpRequest.status == status)
    if urgency:
        q = q.filter(models.HelpRequest.urgency == urgency)
    return q.order_by(models.HelpRequest.created_at.desc()).limit(100).all()


@router.post("", response_model=schemas.HelpRequestOut, status_code=201)
def create_help_request(
    payload: schemas.HelpRequestCreate,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    hr = models.HelpRequest(author_id=current.id, **payload.model_dump())
    db.add(hr)
    db.commit()
    db.refresh(hr)
    return hr


@router.patch("/{request_id}/status", response_model=schemas.HelpRequestOut)
def update_status(
    request_id: str,
    payload: schemas.HelpRequestStatusUpdate,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    hr = db.get(models.HelpRequest, request_id)
    if not hr:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if hr.author_id != current.id:
        raise HTTPException(status_code=403, detail="Solo quien publicó puede cambiar el estado")
    hr.status = payload.status
    db.commit()
    db.refresh(hr)
    return hr

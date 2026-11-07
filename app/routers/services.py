"""Servicios ofrecidos por los vecinos/proveedores."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..reputation import user_public

router = APIRouter(prefix="/api/v1/services", tags=["servicios"])


def _serialize(db: Session, svc: models.Service) -> schemas.ServiceOut:
    out = schemas.ServiceOut.model_validate(svc)
    if svc.provider:
        out.provider = schemas.UserPublic(**user_public(db, svc.provider))
    return out


@router.get("", response_model=list[schemas.ServiceOut])
def list_services(
    category_id: Optional[int] = Query(default=None),
    neighborhood_id: Optional[int] = Query(default=None),
    district_id: Optional[int] = Query(default=None),
    q: Optional[str] = Query(default=None, description="Texto a buscar en título/descripción"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(models.Service).filter(models.Service.status == "published")
    if category_id is not None:
        query = query.filter(models.Service.category_id == category_id)
    if neighborhood_id is not None:
        query = query.filter(models.Service.neighborhood_id == neighborhood_id)
    if district_id is not None:
        sub = db.query(models.Neighborhood.id).filter(models.Neighborhood.district_id == district_id)
        query = query.filter(models.Service.neighborhood_id.in_(sub))
    if q:
        like = f"%{q}%"
        query = query.filter(
            models.Service.title.ilike(like) | models.Service.description.ilike(like)
        )
    rows = query.order_by(models.Service.created_at.desc()).limit(limit).offset(offset).all()
    return [_serialize(db, s) for s in rows]


@router.post("", response_model=schemas.ServiceOut, status_code=201)
def create_service(
    payload: schemas.ServiceCreate,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    if not db.get(models.ServiceCategory, payload.category_id):
        raise HTTPException(status_code=422, detail="Categoría inválida")
    svc = models.Service(provider_id=current.id, **payload.model_dump())
    db.add(svc)
    db.commit()
    db.refresh(svc)
    return _serialize(db, svc)


@router.get("/{service_id}", response_model=schemas.ServiceOut)
def get_service(service_id: str, db: Session = Depends(get_db)):
    svc = db.get(models.Service, service_id)
    if not svc or svc.status == "deleted":
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return _serialize(db, svc)


@router.patch("/{service_id}", response_model=schemas.ServiceOut)
def update_service(
    service_id: str,
    payload: schemas.ServiceUpdate,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    svc = db.get(models.Service, service_id)
    if not svc or svc.status == "deleted":
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    if svc.provider_id != current.id:
        raise HTTPException(status_code=403, detail="Solo el proveedor puede editar su servicio")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(svc, field, value)
    db.commit()
    db.refresh(svc)
    return _serialize(db, svc)


@router.delete("/{service_id}", status_code=204)
def delete_service(
    service_id: str,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    svc = db.get(models.Service, service_id)
    if not svc:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    if svc.provider_id != current.id:
        raise HTTPException(status_code=403, detail="Solo el proveedor puede eliminar su servicio")
    svc.status = "deleted"
    db.commit()

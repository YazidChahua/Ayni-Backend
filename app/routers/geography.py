"""Catálogo territorial: distritos y barrios."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/v1", tags=["geografía"])


@router.get("/districts", response_model=list[schemas.DistrictOut])
def list_districts(db: Session = Depends(get_db)):
    return db.query(models.District).order_by(models.District.name).all()


@router.get("/neighborhoods", response_model=list[schemas.NeighborhoodOut])
def list_neighborhoods(
    district_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(models.Neighborhood)
    if district_id is not None:
        q = q.filter(models.Neighborhood.district_id == district_id)
    return q.order_by(models.Neighborhood.name).all()

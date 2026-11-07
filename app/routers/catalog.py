"""Categorías de servicios."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/v1", tags=["catálogo"])


@router.get("/service-categories", response_model=list[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(models.ServiceCategory).order_by(models.ServiceCategory.name).all()

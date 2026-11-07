"""Productos e intercambios (trueque) del marketplace vecinal."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/v1/products", tags=["productos"])


@router.get("", response_model=list[schemas.ProductOut])
def list_products(
    neighborhood_id: Optional[int] = Query(default=None),
    exchange_only: bool = Query(default=False, description="Solo productos que aceptan trueque"),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(models.Product).filter(models.Product.status == "published")
    if neighborhood_id is not None:
        query = query.filter(models.Product.neighborhood_id == neighborhood_id)
    if exchange_only:
        query = query.filter(models.Product.exchange_enabled == 1)
    if q:
        like = f"%{q}%"
        query = query.filter(
            models.Product.title.ilike(like) | models.Product.description.ilike(like)
        )
    return query.order_by(models.Product.created_at.desc()).limit(limit).offset(offset).all()


@router.post("", response_model=schemas.ProductOut, status_code=201)
def create_product(
    payload: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    data = payload.model_dump()
    data["exchange_enabled"] = 1 if data["exchange_enabled"] else 0
    product = models.Product(owner_id=current.id, **data)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: str, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product or product.status == "deleted":
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product


@router.patch("/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: str,
    payload: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    product = db.get(models.Product, product_id)
    if not product or product.status == "deleted":
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if product.owner_id != current.id:
        raise HTTPException(status_code=403, detail="Solo el dueño puede editar el producto")
    data = payload.model_dump(exclude_unset=True)
    if "exchange_enabled" in data:
        data["exchange_enabled"] = 1 if data["exchange_enabled"] else 0
    for field, value in data.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if product.owner_id != current.id:
        raise HTTPException(status_code=403, detail="Solo el dueño puede eliminar el producto")
    product.status = "deleted"
    db.commit()

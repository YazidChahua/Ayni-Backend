"""Muro comunitario: avisos, cortes de agua/luz, actividades."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/v1/community", tags=["comunidad"])


@router.get("/posts", response_model=list[schemas.CommunityPostOut])
def list_posts(
    neighborhood_id: Optional[int] = Query(default=None),
    category: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(models.CommunityPost)
    if neighborhood_id is not None:
        q = q.filter(models.CommunityPost.neighborhood_id == neighborhood_id)
    if category:
        q = q.filter(models.CommunityPost.category == category)
    return q.order_by(models.CommunityPost.created_at.desc()).limit(100).all()


@router.post("/posts", response_model=schemas.CommunityPostOut, status_code=201)
def create_post(
    payload: schemas.CommunityPostCreate,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    post = models.CommunityPost(author_id=current.id, **payload.model_dump())
    db.add(post)
    db.commit()
    db.refresh(post)
    return post

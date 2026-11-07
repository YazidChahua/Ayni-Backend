"""Perfil del usuario autenticado y perfiles públicos."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..reputation import user_public

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=schemas.UserOut)
def get_me(current: models.User = Depends(get_current_user)):
    return current


@router.patch("/me", response_model=schemas.UserOut)
def update_me(
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    if payload.display_name is not None:
        current.display_name = payload.display_name

    if current.profile is None:
        current.profile = models.UserProfile(user_id=current.id)

    if payload.bio is not None:
        current.profile.bio = payload.bio
    if payload.neighborhood_id is not None:
        current.profile.neighborhood_id = payload.neighborhood_id
    if payload.public_area_label is not None:
        current.profile.public_area_label = payload.public_area_label
    if payload.photo_url is not None:
        current.profile.photo_url = payload.photo_url

    db.commit()
    db.refresh(current)
    return current


@router.get("/{user_id}", response_model=schemas.UserPublic)
def get_public_profile(user_id: str, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user_public(db, user)

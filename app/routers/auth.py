"""Registro e inicio de sesión."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=schemas.Token, status_code=201)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    if not payload.email and not payload.phone:
        raise HTTPException(status_code=422, detail="Debes indicar email o teléfono")

    # Evitar duplicados por email o teléfono.
    exists = (
        db.query(models.User)
        .filter(
            or_(
                models.User.email == payload.email if payload.email else False,
                models.User.phone == payload.phone if payload.phone else False,
            )
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese email o teléfono")

    role = payload.role if payload.role in {"vecino", "proveedor"} else "vecino"
    user = models.User(
        display_name=payload.display_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=role,
    )
    user.profile = models.UserProfile(neighborhood_id=payload.neighborhood_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.Token(access_token=create_access_token(user.id))


@router.post("/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login estándar OAuth2. 'username' puede ser el email o el teléfono."""
    ident = form.username.strip()
    user = (
        db.query(models.User)
        .filter(or_(models.User.email == ident, models.User.phone == ident))
        .first()
    )
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email/teléfono o contraseña incorrectos")
    return schemas.Token(access_token=create_access_token(user.id))

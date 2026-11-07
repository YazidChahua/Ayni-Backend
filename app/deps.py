"""Dependencias compartidas: obtener el usuario autenticado desde el token."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
    except Exception:
        raise cred_exc
    if not user_id:
        raise cred_exc
    user = db.get(models.User, user_id)
    if user is None or user.status != "active":
        raise cred_exc
    return user


def require_roles(*roles: str):
    """Fábrica de dependencia para proteger endpoints por rol."""

    def checker(user: models.User = Depends(get_current_user)) -> models.User:
        if roles and user.role not in roles:
            raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
        return user

    return checker

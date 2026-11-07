"""Cálculo de reputación: promedio y cantidad de reseñas por usuario."""
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models


def rating_for(db: Session, user_id: str) -> tuple[float, int]:
    row = (
        db.query(func.avg(models.Review.rating), func.count(models.Review.id))
        .filter(models.Review.reviewee_id == user_id)
        .one()
    )
    avg = round(float(row[0]), 2) if row[0] is not None else 0.0
    count = int(row[1] or 0)
    return avg, count


def user_public(db: Session, user: models.User) -> dict:
    avg, count = rating_for(db, user.id)
    label = user.profile.public_area_label if user.profile else None
    return {
        "id": user.id,
        "display_name": user.display_name,
        "role": user.role,
        "public_area_label": label,
        "rating_avg": avg,
        "rating_count": count,
    }

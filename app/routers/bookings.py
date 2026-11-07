"""Contrataciones (bookings) y reseñas asociadas."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/v1/bookings", tags=["contrataciones"])


@router.post("", response_model=schemas.BookingOut, status_code=201)
def create_booking(
    payload: schemas.BookingCreate,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    svc = db.get(models.Service, payload.service_id)
    if not svc or svc.status == "deleted":
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    if svc.provider_id == current.id:
        raise HTTPException(status_code=400, detail="No puedes contratar tu propio servicio")

    booking = models.Booking(
        service_id=svc.id,
        client_id=current.id,
        provider_id=svc.provider_id,
        note=payload.note,
        scheduled_at=payload.scheduled_at,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("", response_model=list[schemas.BookingOut])
def my_bookings(
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Booking)
        .filter(or_(models.Booking.client_id == current.id, models.Booking.provider_id == current.id))
        .order_by(models.Booking.created_at.desc())
        .all()
    )


@router.patch("/{booking_id}/status", response_model=schemas.BookingOut)
def update_status(
    booking_id: str,
    payload: schemas.BookingStatusUpdate,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    booking = db.get(models.Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Contratación no encontrada")
    if current.id not in (booking.client_id, booking.provider_id):
        raise HTTPException(status_code=403, detail="No participas en esta contratación")

    new = payload.status
    # Reglas: el cliente cancela; el proveedor acepta/rechaza/completa.
    # IMPORTANTE: solo el PROVEEDOR puede marcar "completada". Así el cliente no
    # puede autocompletarse el servicio para dejarse una reseña falsa.
    if new in {"accepted", "rejected", "completed"} and current.id != booking.provider_id:
        raise HTTPException(
            status_code=403,
            detail="Solo el proveedor puede aceptar, rechazar o completar la contratación",
        )
    if new == "cancelled" and current.id != booking.client_id:
        raise HTTPException(status_code=403, detail="Solo el cliente puede cancelar")
    # No se puede completar algo que no fue aceptado antes.
    if new == "completed" and booking.status != "accepted":
        raise HTTPException(
            status_code=400,
            detail="La contratación debe estar 'accepted' antes de completarse",
        )

    booking.status = new
    if new == "completed":
        booking.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/reviews", response_model=schemas.ReviewOut, status_code=201)
def create_review(
    booking_id: str,
    payload: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    booking = db.get(models.Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Contratación no encontrada")
    if current.id != booking.client_id:
        raise HTTPException(status_code=403, detail="Solo el cliente puede calificar")
    if booking.status != "completed":
        raise HTTPException(status_code=400, detail="Solo se califica una contratación completada")
    if db.query(models.Review).filter(models.Review.booking_id == booking.id).first():
        raise HTTPException(status_code=409, detail="Esta contratación ya fue calificada")

    review = models.Review(
        booking_id=booking.id,
        reviewer_id=current.id,
        reviewee_id=booking.provider_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review

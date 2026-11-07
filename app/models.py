"""Modelos de base de datos (SQLAlchemy) para Ayni.

Diseño basado en el Anexo A del documento técnico, adaptado para que funcione
sin cambios en SQLite (desarrollo) y PostgreSQL (producción en Render).

Decisiones para el MVP del hackathon:
- IDs como String(36) (UUID en texto): mismo comportamiento en SQLite y Postgres.
- Geolocalización simple con lat/lng (Float) + neighborhood_id. PostGIS queda
  para una fase posterior (ver README).
- Estados y tipos como texto con valores controlados en los schemas.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class District(Base):
    __tablename__ = "districts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    region = Column(String(120))

    neighborhoods = relationship("Neighborhood", back_populates="district")


class Neighborhood(Base):
    __tablename__ = "neighborhoods"
    id = Column(Integer, primary_key=True, autoincrement=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    name = Column(String(120), nullable=False)
    lat = Column(Float)  # centro aproximado de la zona
    lng = Column(Float)
    __table_args__ = (UniqueConstraint("district_id", "name", name="uq_neighborhood"),)

    district = relationship("District", back_populates="neighborhoods")


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    display_name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True)
    phone = Column(String(30), unique=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), nullable=False, default="vecino")  # vecino, proveedor, moderador, admin
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    neighborhood_id = Column(Integer, ForeignKey("neighborhoods.id"))
    bio = Column(Text)
    public_area_label = Column(String(160))
    photo_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship("User", back_populates="profile")
    neighborhood = relationship("Neighborhood")


class ServiceCategory(Base):
    __tablename__ = "service_categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    icon = Column(String(60))
    parent_id = Column(Integer, ForeignKey("service_categories.id"))


class Service(Base):
    __tablename__ = "services"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    provider_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("service_categories.id"), nullable=False)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=False)
    price_type = Column(String(20), nullable=False, default="quote")  # quote, fixed, hourly, free
    price_amount = Column(Numeric(10, 2))
    neighborhood_id = Column(Integer, ForeignKey("neighborhoods.id"))
    lat = Column(Float)
    lng = Column(Float)
    status = Column(String(20), nullable=False, default="published")  # published, paused, deleted
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    provider = relationship("User")
    category = relationship("ServiceCategory")
    neighborhood = relationship("Neighborhood")


class Product(Base):
    __tablename__ = "products"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=False)
    price_amount = Column(Numeric(10, 2))
    exchange_enabled = Column(Integer, nullable=False, default=0)  # 0/1: acepta trueque
    neighborhood_id = Column(Integer, ForeignKey("neighborhoods.id"))
    status = Column(String(20), nullable=False, default="published")  # published, paused, deleted
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    owner = relationship("User")
    neighborhood = relationship("Neighborhood")


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    service_id = Column(String(36), ForeignKey("services.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    provider_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    # requested, accepted, rejected, completed, cancelled
    status = Column(String(24), nullable=False, default="requested")
    note = Column(Text)
    scheduled_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (CheckConstraint("client_id <> provider_id", name="ck_booking_distinct_parties"),)

    service = relationship("Service")


class Review(Base):
    __tablename__ = "reviews"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    booking_id = Column(String(36), ForeignKey("bookings.id"), nullable=False, unique=True)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    reviewee_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    rating = Column(SmallInteger, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_rating_range"),
        CheckConstraint("reviewer_id <> reviewee_id", name="ck_review_distinct"),
    )


class CommunityPost(Base):
    __tablename__ = "community_posts"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    # client_uuid: id generado por el móvil para sincronización idempotente (offline).
    client_uuid = Column(String(36), unique=True)
    author_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    neighborhood_id = Column(Integer, ForeignKey("neighborhoods.id"))
    category = Column(String(40), nullable=False)  # aviso, corte_agua, corte_luz, actividad, junta
    title = Column(String(160), nullable=False)
    body = Column(Text, nullable=False)
    verification_status = Column(String(24), nullable=False, default="unverified")  # unverified, corroborated, official, expired
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    author = relationship("User")
    neighborhood = relationship("Neighborhood")


class HelpRequest(Base):
    __tablename__ = "help_requests"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    # client_uuid: id generado por el móvil para sincronización idempotente (offline).
    client_uuid = Column(String(36), unique=True)
    author_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    neighborhood_id = Column(Integer, ForeignKey("neighborhoods.id"))
    request_type = Column(String(40), nullable=False)  # alimentos, herramientas, transporte, apoyo, otro
    description = Column(Text, nullable=False)
    urgency = Column(String(20), nullable=False, default="normal")  # normal, alta, emergencia
    status = Column(String(24), nullable=False, default="open")  # open, coordinating, resolved, cancelled
    lat = Column(Float)
    lng = Column(Float)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    author = relationship("User")
    neighborhood = relationship("Neighborhood")


class Report(Base):
    __tablename__ = "reports"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    reporter_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    target_type = Column(String(30), nullable=False)  # user, service, post, help_request
    target_id = Column(String(36), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending, reviewed, dismissed
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

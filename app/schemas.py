"""Schemas de Pydantic: definen qué entra y qué sale de la API."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth / Users ----------
class UserRegister(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(default="vecino")
    neighborhood_id: Optional[int] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileOut(ORMModel):
    neighborhood_id: Optional[int] = None
    bio: Optional[str] = None
    public_area_label: Optional[str] = None
    photo_url: Optional[str] = None


class UserOut(ORMModel):
    id: str
    display_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: str
    status: str
    created_at: datetime
    profile: Optional[ProfileOut] = None


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    bio: Optional[str] = None
    neighborhood_id: Optional[int] = None
    public_area_label: Optional[str] = Field(default=None, max_length=160)
    photo_url: Optional[str] = Field(default=None, max_length=500)


class UserPublic(ORMModel):
    """Perfil público con reputación (sin datos sensibles)."""
    id: str
    display_name: str
    role: str
    public_area_label: Optional[str] = None
    rating_avg: float = 0.0
    rating_count: int = 0


# ---------- Geografía ----------
class DistrictOut(ORMModel):
    id: int
    name: str
    region: Optional[str] = None


class NeighborhoodOut(ORMModel):
    id: int
    district_id: int
    name: str
    lat: Optional[float] = None
    lng: Optional[float] = None


# ---------- Categorías ----------
class CategoryOut(ORMModel):
    id: int
    name: str
    icon: Optional[str] = None
    parent_id: Optional[int] = None


# ---------- Servicios ----------
class ServiceCreate(BaseModel):
    category_id: int
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=3)
    price_type: str = Field(default="quote", pattern="^(quote|fixed|hourly|free)$")
    price_amount: Optional[Decimal] = None
    neighborhood_id: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class ServiceUpdate(BaseModel):
    category_id: Optional[int] = None
    title: Optional[str] = Field(default=None, min_length=3, max_length=160)
    description: Optional[str] = None
    price_type: Optional[str] = Field(default=None, pattern="^(quote|fixed|hourly|free)$")
    price_amount: Optional[Decimal] = None
    neighborhood_id: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    status: Optional[str] = Field(default=None, pattern="^(published|paused|deleted)$")


class ServiceOut(ORMModel):
    id: str
    provider_id: str
    category_id: int
    title: str
    description: str
    price_type: str
    price_amount: Optional[Decimal] = None
    neighborhood_id: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    status: str
    created_at: datetime
    provider: Optional[UserPublic] = None
    category: Optional[CategoryOut] = None


# ---------- Contrataciones (bookings) ----------
class BookingCreate(BaseModel):
    service_id: str
    note: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class BookingStatusUpdate(BaseModel):
    status: str = Field(pattern="^(requested|accepted|rejected|completed|cancelled)$")


class BookingOut(ORMModel):
    id: str
    service_id: str
    client_id: str
    provider_id: str
    status: str
    note: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


# ---------- Reseñas ----------
class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class ReviewOut(ORMModel):
    id: str
    booking_id: str
    reviewer_id: str
    reviewee_id: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime


# ---------- Productos / intercambios ----------
class ProductCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=3)
    price_amount: Optional[Decimal] = None
    exchange_enabled: bool = False
    neighborhood_id: Optional[int] = None


class ProductUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=160)
    description: Optional[str] = None
    price_amount: Optional[Decimal] = None
    exchange_enabled: Optional[bool] = None
    neighborhood_id: Optional[int] = None
    status: Optional[str] = Field(default=None, pattern="^(published|paused|deleted)$")


class ProductOut(ORMModel):
    id: str
    owner_id: str
    title: str
    description: str
    price_amount: Optional[Decimal] = None
    exchange_enabled: bool
    neighborhood_id: Optional[int] = None
    status: str
    created_at: datetime


# ---------- Comunidad ----------
class CommunityPostCreate(BaseModel):
    category: str = Field(max_length=40)
    title: str = Field(min_length=3, max_length=160)
    body: str = Field(min_length=3)
    neighborhood_id: Optional[int] = None
    expires_at: Optional[datetime] = None


class CommunityPostOut(ORMModel):
    id: str
    author_id: str
    neighborhood_id: Optional[int] = None
    category: str
    title: str
    body: str
    verification_status: str
    expires_at: Optional[datetime] = None
    created_at: datetime


# ---------- Solidaridad (help requests) ----------
class HelpRequestCreate(BaseModel):
    request_type: str = Field(max_length=40)
    description: str = Field(min_length=3)
    urgency: str = Field(default="normal", pattern="^(normal|alta|emergencia)$")
    neighborhood_id: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    expires_at: Optional[datetime] = None


class HelpRequestStatusUpdate(BaseModel):
    status: str = Field(pattern="^(open|coordinating|resolved|cancelled)$")


class HelpRequestOut(ORMModel):
    id: str
    author_id: str
    neighborhood_id: Optional[int] = None
    request_type: str
    description: str
    urgency: str
    status: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    expires_at: Optional[datetime] = None
    created_at: datetime


# ---------- Reportes ----------
class ReportCreate(BaseModel):
    target_type: str = Field(pattern="^(user|service|post|help_request)$")
    target_id: str
    reason: str = Field(min_length=3)


class ReportOut(ORMModel):
    id: str
    reporter_id: str
    target_type: str
    target_id: str
    reason: str
    status: str
    created_at: datetime


# ---------- Sincronización offline ----------
class SyncBatchItem(BaseModel):
    """Una operación creada por el móvil sin conexión."""
    entity: str = Field(pattern="^(help_request|community_post)$")
    client_uuid: str = Field(description="UUID generado por el móvil para evitar duplicados")
    data: dict


class SyncBatchResultItem(BaseModel):
    client_uuid: str
    server_id: Optional[str] = None
    status: str  # created, duplicate, error
    detail: Optional[str] = None


class SyncBatchResult(BaseModel):
    results: list[SyncBatchResultItem]


class SyncChanges(BaseModel):
    server_time: datetime
    help_requests: list[HelpRequestOut]
    community_posts: list[CommunityPostOut]
    services: list[ServiceOut]


# ---------- Mapa ----------
class MapServiceOut(BaseModel):
    id: str
    title: str
    category_id: int
    lat: Optional[float] = None
    lng: Optional[float] = None
    neighborhood_id: Optional[int] = None
    provider_name: str
    rating_avg: float = 0.0
    distance_km: Optional[float] = None

"""Mapa de servicios: puntos para pintar en el mapa (OpenStreetMap/Leaflet)."""
import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..reputation import rating_for

router = APIRouter(prefix="/api/v1/map", tags=["mapa"])


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia en km entre dos coordenadas (fórmula de Haversine)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 2)


@router.get("/services", response_model=list[schemas.MapServiceOut])
def map_services(
    neighborhood_id: Optional[int] = Query(default=None),
    category_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(models.Service).filter(models.Service.status == "published")
    if neighborhood_id is not None:
        q = q.filter(models.Service.neighborhood_id == neighborhood_id)
    if category_id is not None:
        q = q.filter(models.Service.category_id == category_id)

    result = []
    for s in q.limit(200).all():
        avg, _ = rating_for(db, s.provider_id)
        result.append(
            schemas.MapServiceOut(
                id=s.id,
                title=s.title,
                category_id=s.category_id,
                lat=s.lat,
                lng=s.lng,
                neighborhood_id=s.neighborhood_id,
                provider_name=s.provider.display_name if s.provider else "",
                rating_avg=avg,
            )
        )
    return result


@router.get("/services/near", response_model=list[schemas.MapServiceOut])
def services_near_me(
    lat: float = Query(..., description="Latitud del usuario"),
    lng: float = Query(..., description="Longitud del usuario"),
    radius_km: float = Query(default=5.0, gt=0, le=50),
    category_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Servicios dentro de un radio (km) ordenados por cercanía."""
    q = db.query(models.Service).filter(
        models.Service.status == "published",
        models.Service.lat.isnot(None),
        models.Service.lng.isnot(None),
    )
    if category_id is not None:
        q = q.filter(models.Service.category_id == category_id)

    out = []
    for s in q.limit(500).all():
        dist = _haversine_km(lat, lng, s.lat, s.lng)
        if dist <= radius_km:
            avg, _ = rating_for(db, s.provider_id)
            out.append(
                schemas.MapServiceOut(
                    id=s.id,
                    title=s.title,
                    category_id=s.category_id,
                    lat=s.lat,
                    lng=s.lng,
                    neighborhood_id=s.neighborhood_id,
                    provider_name=s.provider.display_name if s.provider else "",
                    rating_avg=avg,
                    distance_km=dist,
                )
            )
    out.sort(key=lambda x: x.distance_km if x.distance_km is not None else 1e9)
    return out

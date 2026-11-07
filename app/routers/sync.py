"""Sincronización offline (RF-12).

Soporta el escenario del documento: el móvil crea solicitudes/avisos sin
conexión y, al recuperar internet, los envía. La idempotencia se garantiza con
`client_uuid` (si ya se sincronizó, no se duplica).
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/v1/sync", tags=["sincronización"])


@router.get("/changes", response_model=schemas.SyncChanges)
def get_changes(
    since: Optional[datetime] = Query(
        default=None, description="Fecha ISO-8601. Devuelve lo creado después de este momento."
    ),
    db: Session = Depends(get_db),
):
    """Descarga los cambios del servidor para refrescar la caché local del móvil."""
    hr = db.query(models.HelpRequest)
    cp = db.query(models.CommunityPost)
    sv = db.query(models.Service).filter(models.Service.status == "published")
    if since is not None:
        hr = hr.filter(models.HelpRequest.created_at > since)
        cp = cp.filter(models.CommunityPost.created_at > since)
        sv = sv.filter(models.Service.created_at > since)

    return schemas.SyncChanges(
        server_time=datetime.now(timezone.utc),
        help_requests=hr.order_by(models.HelpRequest.created_at).limit(200).all(),
        community_posts=cp.order_by(models.CommunityPost.created_at).limit(200).all(),
        services=sv.order_by(models.Service.created_at).limit(200).all(),
    )


@router.post("/batch", response_model=schemas.SyncBatchResult)
def push_batch(
    items: list[schemas.SyncBatchItem],
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    """Sube operaciones creadas offline. Idempotente por client_uuid."""
    results: list[schemas.SyncBatchResultItem] = []

    for item in items:
        try:
            if item.entity == "help_request":
                model_cls = models.HelpRequest
                allowed = {"request_type", "description", "urgency", "neighborhood_id", "lat", "lng"}
            else:  # community_post
                model_cls = models.CommunityPost
                allowed = {"category", "title", "body", "neighborhood_id"}

            # ¿Ya se sincronizó antes? → no duplicar.
            existing = (
                db.query(model_cls).filter(model_cls.client_uuid == item.client_uuid).first()
            )
            if existing:
                results.append(schemas.SyncBatchResultItem(
                    client_uuid=item.client_uuid, server_id=existing.id, status="duplicate"
                ))
                continue

            fields = {k: v for k, v in item.data.items() if k in allowed}
            obj = model_cls(client_uuid=item.client_uuid, author_id=current.id, **fields)
            db.add(obj)
            db.commit()
            db.refresh(obj)
            results.append(schemas.SyncBatchResultItem(
                client_uuid=item.client_uuid, server_id=obj.id, status="created"
            ))
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            results.append(schemas.SyncBatchResultItem(
                client_uuid=item.client_uuid, status="error", detail=str(exc)[:200]
            ))

    return schemas.SyncBatchResult(results=results)

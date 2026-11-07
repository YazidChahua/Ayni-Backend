"""Punto de entrada de la API Ayni (FastAPI)."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, SessionLocal, engine
from .routers import (
    admin,
    auth,
    bookings,
    catalog,
    community,
    geography,
    help,
    map,
    products,
    reports,
    services,
    sync,
    users,
)
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Aviso de seguridad: si no se cambió el JWT_SECRET, cualquiera podría falsificar tokens.
    if settings.jwt_secret == "dev-secret-change-me":
        logging.warning(
            "⚠️  JWT_SECRET usa el valor por defecto. Define uno seguro en producción "
            "(Render → Environment → JWT_SECRET)."
        )
    # Crea las tablas si no existen (sin migraciones, ideal para hackathon).
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            seed(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="Ayni API",
    description="API de la plataforma de colaboración vecinal Ayni — Hackathon UTP · El Comercio 2026.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    # Usamos token por header (Authorization: Bearer), no cookies, así que no
    # necesitamos credenciales. Además "*" + credentials=True el navegador lo rechaza.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(geography.router)
app.include_router(catalog.router)
app.include_router(services.router)
app.include_router(products.router)
app.include_router(bookings.router)
app.include_router(community.router)
app.include_router(help.router)
app.include_router(map.router)
app.include_router(sync.router)
app.include_router(reports.router)
app.include_router(admin.router)


@app.get("/", tags=["health"])
def root():
    return {"app": "Ayni API", "status": "ok", "docs": "/docs"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}

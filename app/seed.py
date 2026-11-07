"""Siembra datos de demostración para el pitch del hackathon.

Es idempotente: si ya hay distritos, no vuelve a cargar. Ejecuta con:
    python -m app.seed
o déjalo automático con SEED_ON_STARTUP=true (por defecto).
"""
from sqlalchemy.orm import Session

from . import models
from .database import Base, SessionLocal, engine
from .security import hash_password

DISTRICTS = {
    "Lima": [
        ("Cercado de Lima", -12.0464, -77.0428),
        ("Barrios Altos", -12.0500, -77.0200),
    ],
    "San Juan de Lurigancho": [
        ("Zárate", -12.0280, -76.9980),
        ("Canto Grande", -11.9800, -76.9950),
    ],
    "Villa El Salvador": [
        ("Sector 1", -12.2130, -76.9360),
        ("Sector 3", -12.2300, -76.9400),
    ],
    "Comas": [
        ("La Pascana", -11.9500, -77.0600),
        ("El Retablo", -11.9400, -77.0500),
    ],
}

CATEGORIES = [
    ("Gasfitería", "wrench"),
    ("Carpintería", "hammer"),
    ("Electricidad", "zap"),
    ("Cerrajería", "key"),
    ("Paseo de mascotas", "dog"),
    ("Clases particulares", "book"),
    ("Limpieza", "broom"),
    ("Albañilería", "brick"),
    ("Jardinería", "leaf"),
    ("Cocina / catering", "chef"),
]


def seed(db: Session) -> None:
    if db.query(models.District).first():
        return  # ya sembrado

    # Distritos y barrios
    nbhd_by_name = {}
    for dname, barrios in DISTRICTS.items():
        district = models.District(name=dname, region="Lima")
        db.add(district)
        db.flush()
        for bname, lat, lng in barrios:
            n = models.Neighborhood(district_id=district.id, name=bname, lat=lat, lng=lng)
            db.add(n)
            db.flush()
            nbhd_by_name[bname] = n.id

    # Categorías
    cats = {}
    for name, icon in CATEGORIES:
        c = models.ServiceCategory(name=name, icon=icon)
        db.add(c)
        db.flush()
        cats[name] = c.id

    # Usuarios demo (contraseña para todos: ayni1234)
    pw = hash_password("ayni1234")
    demo_users = [
        ("María Quispe", "maria@ayni.pe", "proveedor", "Zárate", "Electricista con 8 años de experiencia."),
        ("José Huamán", "jose@ayni.pe", "proveedor", "La Pascana", "Gasfitero certificado, atención rápida."),
        ("Rosa Ccopa", "rosa@ayni.pe", "proveedor", "Sector 1", "Clases de matemática y física."),
        ("Pedro Flores", "pedro@ayni.pe", "vecino", "Cercado de Lima", "Vecino del barrio."),
    ]
    users = {}
    for name, email, role, barrio, bio in demo_users:
        u = models.User(display_name=name, email=email, password_hash=pw, role=role)
        u.profile = models.UserProfile(
            neighborhood_id=nbhd_by_name.get(barrio),
            bio=bio,
            public_area_label=barrio,
        )
        db.add(u)
        db.flush()
        users[email] = u

    # Servicios demo
    demo_services = [
        ("maria@ayni.pe", "Electricidad", "Instalaciones eléctricas y reparaciones",
         "Instalación de tomacorrientes, tableros y solución de cortocircuitos.", "hourly", 40, "Zárate"),
        ("jose@ayni.pe", "Gasfitería", "Reparación de fugas y desagües",
         "Cambio de caños, destape de desagües y mantenimiento de baños.", "quote", None, "La Pascana"),
        ("rosa@ayni.pe", "Clases particulares", "Clases de matemática (primaria y secundaria)",
         "Refuerzo escolar personalizado, presencial o virtual.", "hourly", 25, "Sector 1"),
    ]
    for email, cat, title, desc, ptype, price, barrio in demo_services:
        n_id = nbhd_by_name.get(barrio)
        nb = db.get(models.Neighborhood, n_id) if n_id else None
        svc = models.Service(
            provider_id=users[email].id,
            category_id=cats[cat],
            title=title,
            description=desc,
            price_type=ptype,
            price_amount=price,
            neighborhood_id=n_id,
            lat=nb.lat if nb else None,
            lng=nb.lng if nb else None,
        )
        db.add(svc)

    # Un producto / intercambio de ejemplo
    db.add(models.Product(
        owner_id=users["jose@ayni.pe"].id,
        title="Taladro percutor (se presta o cambia)",
        description="Taladro en buen estado. Acepto trueque por herramientas de jardinería.",
        price_amount=None,
        exchange_enabled=1,
        neighborhood_id=nbhd_by_name.get("La Pascana"),
    ))

    # Un aviso comunitario y una solicitud de ayuda de ejemplo
    db.add(models.CommunityPost(
        author_id=users["pedro@ayni.pe"].id,
        neighborhood_id=nbhd_by_name.get("Cercado de Lima"),
        category="corte_agua",
        title="Corte de agua programado",
        body="Sedapal informa corte de agua el sábado de 8am a 4pm en la zona.",
        verification_status="corroborated",
    ))
    db.add(models.HelpRequest(
        author_id=users["pedro@ayni.pe"].id,
        neighborhood_id=nbhd_by_name.get("Cercado de Lima"),
        request_type="herramientas",
        description="Necesito prestada una escalera por unas horas este fin de semana.",
        urgency="normal",
    ))

    db.commit()


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
        print("Datos de demo sembrados. Usuarios: maria@ayni.pe / jose@ayni.pe / rosa@ayni.pe / pedro@ayni.pe (clave: ayni1234)")
    finally:
        db.close()


if __name__ == "__main__":
    run()

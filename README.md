# Ayni API — Backend (FastAPI)

Backend de **Ayni**, la plataforma de colaboración vecinal del Hackathon UTP · El Comercio 2026.
Monolito modular en **FastAPI + SQLAlchemy**, con **SQLite** en local y **PostgreSQL** en producción (Render).

## Qué incluye (MVP)

- Registro / login con **JWT**.
- Perfil vecinal con barrio y reputación.
- **Servicios** (economía local): publicar, buscar, filtrar (categoría, barrio, distrito), editar, pausar.
- **Productos / intercambios** (trueque vecinal).
- **Contrataciones** (bookings) + **reseñas** (solo tras servicio completado).
- **Reputación**: promedio de calificaciones por proveedor.
- **Comunidad**: avisos, cortes de agua/luz, actividades.
- **Solidaridad**: solicitudes de ayuda vecinal.
- **Mapa**: servicios por zona aproximada y **"cerca de mí"** (búsqueda por distancia en km).
- **Sincronización offline** (RF-12): subida idempotente de operaciones creadas sin internet + descarga de cambios.
- **Reportes** y resolución (moderación).
- Datos de **demo** sembrados automáticamente para el pitch.

> Todo probado con una batería de 23 pruebas automáticas (registro, login, contratación,
> reglas de negocio, reputación, productos, mapa cercano y sincronización idempotente).

---

## 1. Correr en local (Windows / VS Code)

Abre la carpeta `ayni-backend` en **VS Code** y una terminal (Ctrl + Ñ):

```powershell
# 1. Crear entorno virtual (si no existe)
python -m venv .venv

# 2. Activarlo
.venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Levantar el servidor
uvicorn app.main:app --reload
```

Abre en el navegador:

- **http://127.0.0.1:8000/docs** → documentación interactiva (Swagger). Desde aquí se prueban todos los endpoints.
- **http://127.0.0.1:8000/health** → estado del servicio.

> Usuarios de demo (clave `ayni1234`): `maria@ayni.pe`, `jose@ayni.pe`, `rosa@ayni.pe`, `pedro@ayni.pe`.

### Extensiones recomendadas de VS Code
- **Python** (Microsoft)
- **Pylance**
- (opcional) **Thunder Client** o **REST Client** para probar la API.

---

## 2. Subir a GitHub

```powershell
git init
git add .
git commit -m "Backend Ayni inicial (FastAPI)"
git branch -M main
# Crea un repo vacío en github.com (sin README) y copia su URL:
git remote add origin https://github.com/<tu-usuario>/ayni-backend.git
git push -u origin main
```

> Si tienes GitHub CLI: `gh repo create ayni-backend --public --source=. --push`.

---

## 3. Desplegar: API en Render + Base de datos en Supabase

La base de datos vive en **Supabase** (PostgreSQL gratis, no expira, con editor visual y PostGIS).
La API (este repo) corre en **Render**.

### 3.1 Crear la base en Supabase
1. https://supabase.com → **New project** (región *South America / São Paulo*). Guarda la contraseña.
2. (Opcional, para geo avanzada) **Database → Extensions → activa `postgis`**.
3. **Project Settings → Database → Connection string → URI**. Copia la del **pooler (puerto 6543)**
   y reemplaza `[YOUR-PASSWORD]` por tu contraseña. Esa es tu `DATABASE_URL`.

### 3.2 Desplegar la API en Render
1. https://render.com → **New +** → **Web Service** → conecta tu repo `ayni-backend`.
2. Configura:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. **Environment** (aquí van los secretos, NO en GitHub):
   - `DATABASE_URL` = *(la URI de Supabase del paso 3.1)*
   - `JWT_SECRET` = *(una clave larga y secreta)*
   - `CORS_ORIGINS` = `*`
4. **Create Web Service** → espera ~3 min → `https://ayni-api.onrender.com/docs`.

> También puedes usar el `render.yaml` (New + → Blueprint): Render te pedirá el `DATABASE_URL`
> al desplegar porque está marcado como secreto (`sync: false`), así nunca se sube al repo.

> **Nota del plan Free:** Render "duerme" el servicio tras inactividad; la 1.ª petición tarda
> ~30-50 s. Para el pitch, entra a `/docs` un minuto antes para "despertarlo".

---

## 4. Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./ayni.db` | Conexión a la BD. Render la inyecta. |
| `JWT_SECRET` | `dev-secret-change-me` | Clave para firmar tokens. **Cambiar en prod.** |
| `CORS_ORIGINS` | `*` | Orígenes permitidos (coma separada o `*`). |
| `SEED_ON_STARTUP` | `true` | Sembrar datos de demo al iniciar. |

Copia `.env.example` → `.env` para desarrollo local.

---

## 5. Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/auth/register` | Crear cuenta |
| POST | `/api/v1/auth/login` | Iniciar sesión (devuelve token) |
| GET | `/api/v1/users/me` | Mi perfil |
| PATCH | `/api/v1/users/me` | Editar mi perfil |
| GET | `/api/v1/districts` · `/neighborhoods` | Distritos y barrios |
| GET | `/api/v1/service-categories` | Categorías de oficios |
| GET/POST | `/api/v1/services` | Listar / publicar servicios (filtros: categoría, barrio, distrito, texto) |
| GET/PATCH/DELETE | `/api/v1/services/{id}` | Ver / editar / pausar |
| GET/POST | `/api/v1/products` | Productos e intercambios (trueque) |
| GET/PATCH/DELETE | `/api/v1/products/{id}` | Ver / editar / eliminar |
| POST | `/api/v1/bookings` | Contratar un servicio |
| PATCH | `/api/v1/bookings/{id}/status` | Cambiar estado |
| POST | `/api/v1/bookings/{id}/reviews` | Calificar |
| GET/POST | `/api/v1/community/posts` | Avisos comunitarios |
| GET/POST | `/api/v1/help-requests` | Solicitudes de ayuda |
| PATCH | `/api/v1/help-requests/{id}/status` | Cambiar estado de la solicitud |
| GET | `/api/v1/map/services` | Servicios para el mapa |
| GET | `/api/v1/map/services/near` | Servicios cerca de mí (lat, lng, radius_km) |
| GET | `/api/v1/sync/changes` | Descargar cambios (offline) |
| POST | `/api/v1/sync/batch` | Subir operaciones creadas offline (idempotente) |
| POST | `/api/v1/reports` | Reportar contenido |
| GET/PATCH | `/api/v1/reports` · `/{id}` | Ver / resolver reportes (moderador/admin) |

La lista completa y probable está en **`/docs`**.

---

## 6. Estructura del proyecto

```
ayni-backend/
├── app/
│   ├── main.py          # arranque FastAPI + routers + CORS
│   ├── config.py        # variables de entorno
│   ├── database.py      # conexión y sesión
│   ├── models.py        # tablas (SQLAlchemy)
│   ├── schemas.py       # validación (Pydantic)
│   ├── security.py      # hash de claves + JWT
│   ├── deps.py          # usuario autenticado / roles
│   ├── reputation.py    # cálculo de calificaciones
│   ├── seed.py          # datos de demo
│   └── routers/         # endpoints por módulo
│       ├── auth · users · geography · catalog
│       ├── services · products · bookings
│       ├── community · help · map
│       └── sync · reports
├── requirements.txt
├── render.yaml          # despliegue automático en Render
├── .env.example
└── README.md
```

## 7. Pendiente / fase 2 (fuera del MVP de 48h)
- Geolocalización avanzada con **PostGIS** (hoy: "cerca de mí" por Haversine, ya funciona;
  PostGIS sería una optimización con índices espaciales).
- Mensajería local (Bluetooth / mesh) — es trabajo del cliente móvil, no del backend.
- Migraciones con Alembic (hoy las tablas se crean solas al iniciar, ideal para hackathon).
- Subida de imágenes (hoy se guarda la URL de la foto, no el archivo).

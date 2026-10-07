import time
import logging
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response, status, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from database import SessionLocal, engine
from models import User, Base

# logger  
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crud_app")

# Prometheus
USER_CREATED = Counter("user_created", "Number of users created")
USER_UPDATED = Counter("user_updated", "Number of users updated")
USER_DELETED = Counter("user_deleted", "Number of users deleted")
USERS_TOTAL_GAUGE = Gauge("users_total", "Current total number of users registered in the database")

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP Requests handled by the API",
    ["method", "endpoint", "status_code"]
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP Request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

def init_db(max_retries: int = 15, delay: float = 2.0):
    """Wait for database to be ready and initialize tables."""
    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Successfully connected to PostgreSQL and initialized tables.")
            return
        except OperationalError as exc:
            logger.warning(
                f"PostgreSQL not ready yet (attempt {attempt}/{max_retries}): {exc}. Retrying in {delay}s..."
            )
            time.sleep(delay)
        except Exception as exc:
            logger.error(f"Unexpected error initializing database: {exc}")
            time.sleep(delay)
    logger.error("Could not initialize database after maximum retries.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa tablas de la base de datos al iniciar la aplicacion
    init_db()
    # Actualiza el inicial
    try:
        with SessionLocal() as db:
            USERS_TOTAL_GAUGE.set(db.query(User).count())
    except Exception:
        pass
    yield

app = FastAPI(
    title="User CRUD & Monitoring API",
    description="FastAPI CRUD service with PostgreSQL, Prometheus metrics, and Grafana monitoring.",
    version="1.0.0",
    lifespan=lifespan
)

#  Middleware para medir duracion de solicitudes y contar solicitudes para Prometheus
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    # Evita medir el endpoint de metricas para no generar ruido
    if request.url.path == "/metrics":
        return await call_next(request)

    method = request.method
    endpoint = request.url.path
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    status_code = str(response.status_code)

    HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

    return response

# Dependencia para obtener sesion de BD
def get_db():   
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Actualiza el gauge
def sync_users_gauge(db: Session):
    try:
        count = db.query(User).count()
        USERS_TOTAL_GAUGE.set(count)
    except Exception as e:
        logger.warning(f"Error updating users gauge: {e}")

@app.get("/", tags=["Health"])
def root():
    return {
        "service": "User CRUD Monitoring API",
        "status": "online",
        "docs": "/docs",
        "metrics": "/metrics"
    }

@app.get("/health", tags=["Health"])
def health(db: Session = Depends(get_db)):
    try:
        # Conexión
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connectivity issue: {str(e)}"
        )

# --- Endpoints  CRUS---

@app.get("/users", tags=["Users"])
def get_users(db: Session = Depends(get_db)):
    """Retrieve all users from the database."""
    users = db.query(User).all()
    sync_users_gauge(db)
    return users

@app.get("/users/{user_id}", tags=["Users"])
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    """Retrieve a single user by their ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user

@app.post("/users", status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user(name: str, age: int, db: Session = Depends(get_db)):
    """Create a new user with name and age (query parameters as specified in guide)."""
    user = User(name=name, age=age)
    db.add(user)
    db.commit()
    db.refresh(user)

    USER_CREATED.inc()
    sync_users_gauge(db)
    return user

@app.put("/users/{user_id}", tags=["Users"])
def update_user(
    user_id: int,
    name: Optional[str] = Query(None, description="New name for the user"),
    age: Optional[int] = Query(None, description="New age for the user"),
    db: Session = Depends(get_db)
):
    """Update an existing user's name or age."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    if name is not None:
        user.name = name
    if age is not None:
        user.age = age

    db.commit()
    db.refresh(user)

    USER_UPDATED.inc()
    sync_users_gauge(db)
    return user

@app.delete("/users/{user_id}", tags=["Users"])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete a user by their ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    db.delete(user)
    db.commit()

    USER_DELETED.inc()
    sync_users_gauge(db)
    return {"message": f"User {user_id} successfully deleted", "id": user_id}

# --- Metricas Prometheus   ---

@app.get("/metrics", tags=["Metrics"])
def metrics():
    """Expose Prometheus metrics for scraping."""
    return Response(generate_latest(), media_type="text/plain")

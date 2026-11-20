from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, doctor, notifications, patients
from app.config import settings
from app.database.session import SessionLocal, init_db
from app.services.maintenance import cleanup_legacy


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.require_secret()
    init_db()
    with SessionLocal() as db:
        cleanup_legacy(db)
    yield


app = FastAPI(title="GlucoCare AI", version="1.0.0", lifespan=lifespan,
              description="Diabetes patient monitoring & clinical decision-support API. Not a diagnostic device.")
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router)
app.include_router(doctor.router)
app.include_router(notifications.router)
app.include_router(patients.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "GlucoCare AI"}

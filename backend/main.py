import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

load_dotenv()

app = FastAPI(title="Pharmacie API")

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes.requete import router as requete_router
app.include_router(requete_router) 

from db import SessionLocal


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _database_health():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "up"}
    except Exception as exc:
        return {
            "status": "down",
            "error_type": exc.__class__.__name__,
        }
    finally:
        db.close()


def _health_payload():
    db = _database_health()
    status = "ok" if db["status"] == "up" else "degraded"
    return {
        "status": status,
        "timestamp": _utc_now_iso(),
        "api": {"status": "up"},
        "db": db,
    }


@app.get("/health")
def health():
    payload = _health_payload()
    status_code = 200 if payload["status"] == "ok" else 503
    return JSONResponse(status_code=status_code, content=payload)


@app.get("/api/health")
def health_alias():
    return health()

"""API inicial: operaciones del negocio pendientes de siguientes etapas."""

from fastapi import FastAPI
from fastapi import Depends
from typing import Annotated
from app.auth import Profile, current_profile
from app.catalog import router as catalog_router

app = FastAPI(title="Ferretería y Matizados Miguel", version="0.1.0")
app.include_router(catalog_router)


@app.get("/api/health", tags=["Estado"])
def health() -> dict[str, str]:
    """Comprueba el proceso API, no la conexión con PostgreSQL."""
    return {"status": "ok", "service": "ferreteria-api"}


@app.get('/api/auth/me', response_model=Profile, tags=['Acceso'])
def me(profile: Annotated[Profile, Depends(current_profile)]) -> Profile:
    return profile

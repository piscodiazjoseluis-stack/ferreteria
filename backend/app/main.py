"""API comercial de ventas, catálogo, compras y recepción."""

from fastapi import FastAPI
from fastapi import Depends
from typing import Annotated
from app.auth import Profile, current_profile
from app.catalog import router as catalog_router
from app.sales import router as sales_router
from app.purchasing import router as purchasing_router
from app.reporting import router as reporting_router

app = FastAPI(title="Ferretería y Matizados Miguel", version="0.2.0")
app.include_router(catalog_router)
app.include_router(sales_router)
app.include_router(purchasing_router)
app.include_router(reporting_router)


@app.get("/api/health", tags=["Estado"])
def health() -> dict[str, str]:
    """Comprueba el proceso API, no la conexión con PostgreSQL."""
    return {"status": "ok", "service": "ferreteria-api"}


@app.get('/api/auth/me', response_model=Profile, tags=['Acceso'])
def me(profile: Annotated[Profile, Depends(current_profile)]) -> Profile:
    return profile

"""API comercial de ventas, catÃ¡logo, compras y recepciÃ³n."""

from fastapi import FastAPI
from fastapi import Depends
from typing import Annotated
from app.auth import Profile, current_profile
from app.catalog import router as catalog_router
from app.sales import router as sales_router
from app.purchasing import router as purchasing_router
from app.reporting import router as reporting_router
from app.cash import router as cash_router
from app.reports import router as reports_router

from app.customers import router as customers_router
from app.mixing import router as mixing_router
from app.public import router as public_router
from app.documents import router as documents_router
from app.management import router as management_router

app = FastAPI(title="FerreterÃ­a y Matizados Miguel", version="1.0.0")
app.include_router(catalog_router)
app.include_router(sales_router)
app.include_router(purchasing_router)
app.include_router(reporting_router)
app.include_router(cash_router)
app.include_router(reports_router)
app.include_router(customers_router)
app.include_router(mixing_router)
app.include_router(public_router)
app.include_router(documents_router)
app.include_router(management_router)


@app.get("/api/health", tags=["Estado"])
def health() -> dict[str, str]:
    """Comprueba el proceso API, no la conexiÃ³n con PostgreSQL."""
    return {"status": "ok", "service": "ferreteria-api"}


@app.get('/api/auth/me', response_model=Profile, tags=['Acceso'])
def me(profile: Annotated[Profile, Depends(current_profile)]) -> Profile:
    return profile

from typing import Annotated, Literal
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import user_connection

bearer = HTTPBearer(auto_error=False)


class Profile(BaseModel):
    id: UUID
    nombre: str
    rol: Literal['gerente', 'vendedor']
    activo: bool


def verify_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> UUID:
    if credentials is None:
        raise HTTPException(401, 'Inicia sesión para continuar.', headers={'WWW-Authenticate': 'Bearer'})
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(503, 'Autenticación pendiente de configuración.')
    try:
        response = httpx.get(
            settings.supabase_url + '/auth/v1/user',
            headers={'apikey': settings.supabase_publishable_key,
                     'Authorization': f'Bearer {credentials.credentials}'},
            timeout=10,
        )
    except httpx.RequestError:
        raise HTTPException(503, 'No se pudo comprobar la sesión. Inténtalo de nuevo.') from None
    if response.status_code in (401, 403):
        raise HTTPException(401, 'Tu sesión no es válida. Vuelve a ingresar.')
    if response.status_code != 200:
        raise HTTPException(503, 'El servicio de autenticación no está disponible.')
    try:
        return UUID(response.json()['id'])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(503, 'No se pudo comprobar la identidad.') from None


def current_profile(user_id: Annotated[UUID, Depends(verify_identity)]) -> Profile:
    try:
        with user_connection(user_id) as connection:
            row = connection.execute(
                text('SELECT id,nombre,rol,activo FROM ferreteria.perfiles WHERE id=:id'),
                {'id': user_id},
            ).mappings().one_or_none()
    except SQLAlchemyError:
        raise HTTPException(503, 'No se pudo consultar el acceso. Inténtalo de nuevo.') from None
    if row is None or not row['activo']:
        raise HTTPException(403, 'Tu cuenta no tiene un perfil activo en Ferretería.')
    return Profile(**row)


def require_manager(profile: Annotated[Profile, Depends(current_profile)]) -> Profile:
    if profile.rol != 'gerente':
        raise HTTPException(403, 'Esta acción requiere el rol de gerente.')
    return profile

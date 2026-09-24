from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from uuid import UUID

from sqlalchemy import Connection, create_engine, text

from app.config import get_settings


@lru_cache
def get_engine():
    return create_engine(
        get_settings().database_url, pool_pre_ping=True,
        pool_size=3, max_overflow=2, pool_timeout=10,
        hide_parameters=True,
        connect_args={'connect_timeout': 10, 'options': '-c statement_timeout=10000'},
    )


@contextmanager
def user_connection(user_id: UUID) -> Iterator[Connection]:
    """Un contexto de usuario por transacción; nunca persiste en el pool."""
    with get_engine().begin() as connection:
        connection.execute(
            text("SELECT set_config('app.user_id', :user_id, true)"),
            {'user_id': str(user_id)},
        )
        yield connection

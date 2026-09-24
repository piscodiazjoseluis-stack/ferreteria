import os
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

load_dotenv(Path(__file__).resolve().parents[1] / '.env', encoding='utf-8-sig')
url = os.environ.get('MIGRATION_DATABASE_URL')
if not url:
    raise RuntimeError('Configura MIGRATION_DATABASE_URL con una conexión administrativa; DATABASE_URL es solo para la API.')

if context.is_offline_mode():
    context.configure(url=url, literal_binds=True, version_table_schema='ferreteria')
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
    with engine.connect() as connection:
        connection.exec_driver_sql('CREATE SCHEMA IF NOT EXISTS ferreteria')
        connection.commit()
        context.configure(connection=connection, version_table_schema='ferreteria')
        with context.begin_transaction():
            context.run_migrations()

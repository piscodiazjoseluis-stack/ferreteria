"""Modelo inicial; limpieza antigua aplicada una sola vez mediante Supabase MCP."""
from pathlib import Path
from alembic import op

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    source = (Path(__file__).parents[1] / 'sql' / '0001_initial.sql').read_text(encoding='utf-8')
    # En una instalación nueva no se ejecuta la limpieza del proyecto anterior.
    schema = source[source.index('CREATE SCHEMA ferreteria;'):]
    schema = schema.replace('CREATE SCHEMA ferreteria;', 'CREATE SCHEMA IF NOT EXISTS ferreteria;', 1)
    op.get_bind().exec_driver_sql(schema)


def downgrade():
    raise RuntimeError('No se elimina información comercial con downgrade; restaurar una copia o crear una migración correctiva.')

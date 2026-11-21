"""Clientes, crédito, matizado, catálogo y auditoría de la entrega final."""
from pathlib import Path
from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    source = Path(__file__).resolve().parents[3] / 'supabase/migrations/20261121165018_cierre_final.sql'
    op.get_bind().exec_driver_sql(source.read_text(encoding='utf-8'))


def downgrade():
    raise RuntimeError('Conservar el historial: aplicar una migración correctiva.')

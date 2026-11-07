"""Recepciones parciales, objetivos de reposición y caja diaria."""
from pathlib import Path
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    source = Path(__file__).resolve().parents[3] / 'supabase/migrations/20261107164429_operaciones_v3.sql'
    op.get_bind().exec_driver_sql(source.read_text(encoding='utf-8'))


def downgrade():
    raise RuntimeError('Conservar las operaciones confirmadas; usar una migración correctiva.')

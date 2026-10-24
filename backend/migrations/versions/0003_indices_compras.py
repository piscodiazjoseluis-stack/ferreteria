"""Índices de responsables y proveedor para consultas de compras."""
from pathlib import Path
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    source = (Path(__file__).parents[1] / 'sql' / '0003_indices_compras.sql').read_text(encoding='utf-8')
    op.get_bind().exec_driver_sql(source)


def downgrade():
    raise RuntimeError('Los índices se modifican con una migración correctiva.')

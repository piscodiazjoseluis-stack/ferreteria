from pathlib import Path
from alembic import op
revision='0007'
down_revision='0006'
branch_labels=None
depends_on=None

def upgrade():
    op.get_bind().exec_driver_sql((Path(__file__).resolve().parents[3]/'supabase/migrations/20261121175846_respaldo_comercial.sql').read_text(encoding='utf-8'))

def downgrade():
    raise RuntimeError('Usar migración correctiva y revocar la identidad de respaldo si corresponde.')

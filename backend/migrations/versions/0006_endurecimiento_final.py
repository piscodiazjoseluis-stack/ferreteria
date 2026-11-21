from pathlib import Path
from alembic import op
revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None

def upgrade():
    op.get_bind().exec_driver_sql((Path(__file__).resolve().parents[3]/'supabase/migrations/20261121172329_endurecimiento_final.sql').read_text(encoding='utf-8'))

def downgrade():
    raise RuntimeError('Usar migración correctiva.')

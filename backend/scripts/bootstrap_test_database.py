"""Disposable LOCAL database only. Never points at Supabase or reads .env."""
import sys
from pathlib import Path
import psycopg

ROOT=Path(__file__).resolve().parents[2]
DSN='postgresql://postgres@127.0.0.1:55432/ferreteria_final_test'

def bootstrap():
    with psycopg.connect('postgresql://postgres@127.0.0.1:55432/postgres',autocommit=True) as c:
        if '--reset' in sys.argv:
            c.execute('DROP DATABASE IF EXISTS ferreteria_final_test WITH (FORCE)')
        if c.execute("SELECT 1 FROM pg_database WHERE datname='ferreteria_final_test'").fetchone():
            raise RuntimeError('La base de prueba ya existe. No se elimina automÃ¡ticamente.')
        c.execute('CREATE DATABASE ferreteria_final_test')
    with psycopg.connect(DSN,autocommit=True) as c:
        for role in ('anon','authenticated'):
            if not c.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone(): c.execute('CREATE ROLE '+role+' NOLOGIN')
        c.execute('CREATE SCHEMA auth; CREATE TABLE auth.users(id uuid PRIMARY KEY)')
        for file in ['backend/migrations/sql/0001_initial.sql','backend/migrations/sql/0002_compras_almacen.sql','backend/migrations/sql/0003_indices_compras.sql','supabase/migrations/20261107164429_operaciones_v3.sql','supabase/migrations/20261121165018_cierre_final.sql','supabase/migrations/20261121172329_endurecimiento_final.sql','supabase/migrations/20261121175846_respaldo_comercial.sql']:
            source=(ROOT/file).read_text(encoding='utf-8')
            import re
            for role in ('ferreteria_api','ferreteria_public','ferreteria_backup'):
                if c.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone():
                    source=re.sub('CREATE ROLE '+role+'[^;]+;','',source)
            with c.transaction(): c.execute(source)
            print('MigraciÃ³n OK:',file)
        for n,role in enumerate(('gerente','vendedor','almacenero','cajero'),1):
            id=f'00000000-0000-4000-8000-{n:012}'
            c.execute('INSERT INTO auth.users VALUES(%s)',(id,))
            c.execute('INSERT INTO ferreteria.perfiles(id,nombre,rol) VALUES(%s,%s,%s)',(id,role.title()+' de prueba',role))
    print('Base local preparada; sin credenciales ni conexiÃ³n a producciÃ³n.')

if __name__=='__main__': bootstrap()

"""Verify the encrypted business backup in a NEW LOCAL PostgreSQL database.

Starts from migrations, substitutes Auth UUID stubs, disables user triggers only
during the new database's data import, then enables them and validates integrity.
Never connects to Supabase. Does not overwrite an existing database.
"""
import argparse
import json
import re
from pathlib import Path
import psycopg
from psycopg import sql
from backup_business import decrypt

ROOT=Path(__file__).resolve().parents[2]
def restore(encrypted,private_key,database='ferreteria_encrypted_restore'):
    if database!='ferreteria_encrypted_restore' and not re.fullmatch(r'ferreteria_restore_[a-z0-9_]{1,40}',database):
        raise ValueError('Solo se admite un nombre de base local de ensayo con prefijo ferreteria_restore_.')
    payload=decrypt(Path(encrypted).read_bytes(),Path(private_key).read_bytes())
    if payload.get('schema')!='ferreteria' or payload.get('format')!=1:raise ValueError('Formato de copia desconocido.')
    with psycopg.connect('postgresql://postgres@127.0.0.1:55432/postgres',autocommit=True) as c:
        c.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
    with psycopg.connect('postgresql://postgres@127.0.0.1:55432/'+database) as c:
        c.execute('CREATE SCHEMA auth; CREATE TABLE auth.users(id uuid PRIMARY KEY)')
        files=['backend/migrations/sql/0001_initial.sql','backend/migrations/sql/0002_compras_almacen.sql','backend/migrations/sql/0003_indices_compras.sql','supabase/migrations/20261107164429_operaciones_v3.sql','supabase/migrations/20261121165018_cierre_final.sql','supabase/migrations/20261121172329_endurecimiento_final.sql','supabase/migrations/20261121175846_respaldo_comercial.sql']
        for file in files:
            source=(ROOT/file).read_text(encoding='utf-8')
            for role in ('ferreteria_api','ferreteria_public','ferreteria_backup'):
                if c.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone():source=re.sub('CREATE ROLE '+role+'[^;]+;','',source)
            c.execute(source)
        c.execute('CREATE TABLE ferreteria.alembic_version(version_num varchar(32) PRIMARY KEY)')
        c.execute('DELETE FROM ferreteria.categorias')
        actual={r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='ferreteria'")}
        if set(payload['order'])!=actual:raise ValueError('La copia no coincide con la revisión instalada.')
        for table in actual:c.execute(sql.SQL('ALTER TABLE ferreteria.{} DISABLE TRIGGER USER').format(sql.Identifier(table)))
        for p in payload['data']['perfiles']:c.execute('INSERT INTO auth.users(id) VALUES(%s)',(p['id'],))
        counts={}
        for table in payload['order']:
            columns=[r[0] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='ferreteria' AND table_name=%s AND is_generated='NEVER' ORDER BY ordinal_position",(table,))]
            names=sql.SQL(',').join(map(sql.Identifier,columns))
            c.execute(sql.SQL('INSERT INTO ferreteria.{} ({}) OVERRIDING SYSTEM VALUE SELECT {} FROM jsonb_populate_recordset(NULL::ferreteria.{},%s::jsonb)').format(sql.Identifier(table),names,names,sql.Identifier(table)),(json.dumps(payload['data'][table]),))
            counts[table]=c.execute(sql.SQL('SELECT count(*) FROM ferreteria.{}').format(sql.Identifier(table))).fetchone()[0]
            assert counts[table]==len(payload['data'][table])
            for col in columns:
                seq=c.execute('SELECT pg_get_serial_sequence(%s,%s)',('ferreteria.'+table,col)).fetchone()[0]
                if seq:
                    c.execute(sql.SQL('SELECT setval(%s::regclass,coalesce((SELECT max({}) FROM ferreteria.{}),0)+1,false)').format(sql.Identifier(col),sql.Identifier(table)),(seq,))
        for table in actual:c.execute(sql.SQL('ALTER TABLE ferreteria.{} ENABLE TRIGGER USER').format(sql.Identifier(table)))
        c.execute('ALTER TABLE ferreteria.alembic_version ENABLE ROW LEVEL SECURITY; ALTER TABLE ferreteria.alembic_version FORCE ROW LEVEL SECURITY')
        assert not c.execute('''SELECT e.producto_id FROM ferreteria.existencias e LEFT JOIN ferreteria.movimientos_inventario m ON m.producto_id=e.producto_id GROUP BY e.producto_id,e.cantidad HAVING e.cantidad<>coalesce(sum(m.variacion),0)''').fetchall()
        next_sale=c.execute("SELECT nextval('ferreteria.ventas_numero_seq')").fetchone()[0]
        assert next_sale>c.execute('SELECT coalesce(max(numero),0) FROM ferreteria.ventas').fetchone()[0]
        c.commit()
    (ROOT/'.artifacts/encrypted-restore-validation.json').write_text(json.dumps({'source':Path(encrypted).name,'local_database':database,'tables':counts,'stock_reconciled':True,'sequences_valid':True,'auth':'UUID stubs, no passwords'}),encoding='utf-8')
    print('Restauración cifrada validada:',len(counts),'tablas; stock y secuencias correctos.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('encrypted');p.add_argument('private_key');p.add_argument('--database',default='ferreteria_encrypted_restore');a=p.parse_args();restore(a.encrypted,a.private_key,a.database)

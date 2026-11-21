"""Restore the private V3 business snapshot into a NEW LOCAL database only.

Auth users are represented by ID stubs, not backed up credentials. Never restores
over production. Validates business rows and the stock ledger.
"""
import json
import re
from pathlib import Path
import psycopg
from psycopg import sql

ROOT=Path(__file__).resolve().parents[2]
def restore():
    raw=json.loads((ROOT/'.artifacts/pre-final-remote-backup.json').read_text(encoding='utf-8'))
    wrapped=json.loads(raw['content'][0]['text'])['result']
    match=re.search(r'<untrusted-data-[^>]+>\n(.*?)\n</untrusted-data-',wrapped,re.S)
    data=json.loads(match[1])[0]['backup']
    with psycopg.connect('postgresql://postgres@127.0.0.1:55432/postgres',autocommit=True) as c:
        c.execute('CREATE DATABASE ferreteria_restore_test')
    with psycopg.connect('postgresql://postgres@127.0.0.1:55432/ferreteria_restore_test') as c:
        c.execute('CREATE SCHEMA auth; CREATE TABLE auth.users(id uuid PRIMARY KEY)')
        initial=(ROOT/'backend/migrations/sql/0001_initial.sql').read_text()
        initial=re.sub(r'CREATE ROLE ferreteria_api[^;]+;','',initial)
        c.execute(initial)
        for f in ['backend/migrations/sql/0002_compras_almacen.sql','backend/migrations/sql/0003_indices_compras.sql','supabase/migrations/20261107164429_operaciones_v3.sql']:
            c.execute((ROOT/f).read_text())
        c.execute('DELETE FROM ferreteria.categorias')
        for p in data['perfiles']:c.execute('INSERT INTO auth.users VALUES(%s)',(p['id'],))
        order=['perfiles','categorias','productos','existencias','proveedores','compras','detalle_compra','recepciones','detalle_recepcion','ventas','detalle_venta','movimientos_inventario','cajas','movimientos_caja']
        counts={}
        for t in order:
            columns=[r[0] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='ferreteria' AND table_name=%s AND is_generated='NEVER' ORDER BY ordinal_position",(t,))]
            names=sql.SQL(',').join(map(sql.Identifier,columns))
            query=sql.SQL('INSERT INTO ferreteria.{} ({}) OVERRIDING SYSTEM VALUE SELECT {} FROM jsonb_populate_recordset(NULL::ferreteria.{},%s::jsonb)').format(sql.Identifier(t),names,names,sql.Identifier(t))
            c.execute(query,(json.dumps(data[t]),))
            counts[t]=c.execute(sql.SQL('SELECT count(*) FROM ferreteria.{}').format(sql.Identifier(t))).fetchone()[0]
            assert counts[t]==len(data[t])
        assert not c.execute('''SELECT e.producto_id FROM ferreteria.existencias e LEFT JOIN ferreteria.movimientos_inventario m ON m.producto_id=e.producto_id GROUP BY e.producto_id,e.cantidad HAVING e.cantidad<>coalesce(sum(m.variacion),0)''').fetchall()
        c.commit()
    (ROOT/'.artifacts/restore-validation.json').write_text(json.dumps({'result':'passed','target':'new local database on port 55432','counts':counts,'auth':'IDs only, no credentials'}),encoding='utf-8')
    print('Restore passed:',counts)
if __name__=='__main__':restore()

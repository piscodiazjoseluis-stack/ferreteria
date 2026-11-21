"""Business-only backup, encrypted before it ever leaves the process.

Only public RSA key is stored in Git/CI. The private key belongs to the owner.
Excludes Supabase Auth secrets. Raises before saving any oversized backup.
"""
import base64
import json
import os
import zlib
from decimal import Decimal
from datetime import datetime,timezone
from pathlib import Path
import psycopg
from psycopg import sql
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def export_database(dsn):
    with psycopg.connect(dsn) as c:
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        c.execute("SET LOCAL statement_timeout='60s'")
        role=c.execute('SELECT current_user').fetchone()[0]
        if role!='ferreteria_backup':raise RuntimeError('Solo se admite el rol de respaldo de solo lectura.')
        names=[r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='ferreteria' ORDER BY tablename")]
        dependencies={name:set() for name in names}
        for child,parent in c.execute("SELECT a.relname,b.relname FROM pg_constraint f JOIN pg_class a ON a.oid=f.conrelid JOIN pg_namespace n ON n.oid=a.relnamespace JOIN pg_class b ON b.oid=f.confrelid WHERE f.contype='f' AND n.nspname='ferreteria'"):
            if parent in dependencies and child!=parent:dependencies[child].add(parent)
        ordered=[]
        while len(ordered)<len(names):
            ready=sorted(n for n in names if n not in ordered and dependencies[n].issubset(ordered))
            if not ready:raise RuntimeError('Dependencias cíclicas sin orden de restauración.')
            ordered.extend(ready)
        data={}
        for t in ordered:
            value=c.execute(sql.SQL('SELECT coalesce(jsonb_agg(to_jsonb(x)),\'[]\'::jsonb)::text FROM ferreteria.{} x').format(sql.Identifier(t))).fetchone()[0]
            data[t]=json.loads(value,parse_float=Decimal)
        return {'format':1,'schema':'ferreteria','created_utc':datetime.now(timezone.utc).isoformat(),'order':ordered,'data':data,'auth_credentials_included':False}

def encrypt(payload,public_pem):
    raw=zlib.compress(json.dumps(payload,ensure_ascii=False,separators=(',',':'),default=str).encode(),9)
    key=AESGCM.generate_key(bit_length=256);nonce=os.urandom(12)
    public=serialization.load_pem_public_key(public_pem)
    wrapped=public.encrypt(key,padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    aad=b'Ferreteria commercial backup v1'
    return json.dumps({'format':1,'wrapped_key':base64.b64encode(wrapped).decode(),'nonce':base64.b64encode(nonce).decode(),'data':base64.b64encode(AESGCM(key).encrypt(nonce,raw,aad)).decode()}).encode()

def decrypt(blob,private_pem):
    value=json.loads(blob)
    private=serialization.load_pem_private_key(private_pem,password=None)
    key=private.decrypt(base64.b64decode(value['wrapped_key']),padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    raw=AESGCM(key).decrypt(base64.b64decode(value['nonce']),base64.b64decode(value['data']),b'Ferreteria commercial backup v1')
    return json.loads(zlib.decompress(raw))

def main():
    root=Path(__file__).resolve().parents[2]
    data=export_database(os.environ['BACKUP_DATABASE_URL'])
    result=encrypt(data,(root/'backend/scripts/backup_public.pem').read_bytes())
    if len(result)>10000000:raise RuntimeError('Respaldo supera 10 MB cifrado. Revisar almacenamiento antes de ampliar el límite.')
    directory=root/'.backup-output';directory.mkdir(exist_ok=True)
    (directory/'ferreteria-business.enc').write_bytes(result)
    print('Respaldo comercial cifrado creado. No incluye credenciales Auth.')

if __name__=='__main__':main()

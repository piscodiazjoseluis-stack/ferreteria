"""LOCAL test harness. Not imported by app.main or Vercel. No real Auth simulated as tested."""
import os
from pathlib import Path
import sys
from uuid import UUID
from fastapi import Header, HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['DATABASE_URL']='postgresql+psycopg://postgres@127.0.0.1:55432/ferreteria_final_test'
from app.main import app
from app.auth import verify_identity
from app.database import get_engine
from sqlalchemy import event

@event.listens_for(get_engine(),'begin')
def limited_role(connection):
    connection.exec_driver_sql('SET LOCAL ROLE ferreteria_api')

def identity(authorization:str=Header(default='')):
    role=authorization.removeprefix('Bearer ')
    if role not in ('gerente','vendedor','almacenero','cajero'): raise HTTPException(401,'Token local de prueba no válido.')
    return UUID(f'00000000-0000-4000-8000-{("gerente","vendedor","almacenero","cajero").index(role)+1:012}')

app.dependency_overrides[verify_identity]=identity

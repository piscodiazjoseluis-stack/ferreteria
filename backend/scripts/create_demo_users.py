"""Provisiona cuentas ficticias sin enviar correos. Ejecutar una vez."""
import json
import secrets
from pathlib import Path

import httpx
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[2]
config = dotenv_values(root / 'backend/.env', encoding='utf-8-sig')
output = root / '.artifacts/demo-accounts.json'
if output.exists():
    raise SystemExit('Ya hay cuentas documentadas; no se crean duplicados ni se cambian contraseñas.')
admin = dotenv_values(root / '.artifacts/provision.env')
if not admin.get('SUPABASE_SECRET_KEY'):
    raise SystemExit('Falta .artifacts/provision.env con SUPABASE_SECRET_KEY para el aprovisionamiento inicial.')
accounts = []
with httpx.Client(timeout=20) as client:
    for role, name in [('gerente', 'Gerente de demostración'), ('vendedor', 'Vendedor de demostración')]:
        account = {'email': f'{role}@ferreteria.example.com', 'password': secrets.token_urlsafe(20), 'rol': role, 'nombre': name}
        response = client.post(
            config['SUPABASE_URL'] + '/auth/v1/admin/users',
            headers={'apikey': admin['SUPABASE_SECRET_KEY']},
            json={'email': account['email'], 'password': account['password'], 'email_confirm': True},
        )
        if response.status_code not in (200, 201):
            raise SystemExit(f'No se pudo crear {role}: HTTP {response.status_code}. Revisar antes de reintentar.')
        account['id'] = response.json()['id']
        accounts.append(account)
        output.write_text(json.dumps(accounts, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps({k: account[k] for k in ('id','rol','nombre')}))

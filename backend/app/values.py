"""Exact quantities, currency rounding and safe inline photographs."""
import base64
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated
from pydantic import Field
from fastapi import HTTPException

Quantity = Annotated[Decimal, Field(gt=0, le=2147483647, max_digits=13, decimal_places=3)]
NonnegativeQuantity = Annotated[Decimal, Field(ge=0, le=2147483647, max_digits=13, decimal_places=3)]


def money(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def check_unit(unit, quantity):
    if unit in ('unidad','caja','bolsa','paquete','galon','balde') and quantity != int(quantity):
        raise HTTPException(422, 'Esta unidad se registra en cantidades enteras.')


def photo(value: str):
    if not value:
        return value
    match = re.fullmatch(r'data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)', value)
    if not match or len(value)>280000:
        raise ValueError('Usa una imagen PNG, JPEG o WebP de hasta 200 KB.')
    try:
        data=base64.b64decode(match[2],validate=True)
        valid=(match[1]=='png' and data.startswith(b'\x89PNG\r\n\x1a\n')) or (match[1]=='jpeg' and data.startswith(b'\xff\xd8\xff')) or (match[1]=='webp' and data[:4]==b'RIFF' and data[8:12]==b'WEBP')
        if not valid or len(data)>200000: raise ValueError()
    except ValueError:
        raise ValueError('Archivo de imagen no válido.') from None
    return value

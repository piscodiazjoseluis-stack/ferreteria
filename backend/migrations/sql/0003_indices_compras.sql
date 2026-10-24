CREATE INDEX compras_proveedor_idx ON ferreteria.compras(proveedor_id);
CREATE INDEX compras_creado_por_idx ON ferreteria.compras(creado_por);
CREATE INDEX compras_recibido_por_idx ON ferreteria.compras(recibido_por) WHERE recibido_por IS NOT NULL;

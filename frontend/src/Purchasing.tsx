import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { Session } from '@supabase/supabase-js'
import { ArrowRight, Building2, ClipboardCheck, Package, Plus, RefreshCw, Truck, X } from 'lucide-react'
import { api, dateTime, money } from './lib/appData'
import type { Product, Profile, Purchase, Supplier } from './lib/appData'
import './Purchasing.css'

type LineDraft = { producto_id: string; cantidad: string; costo_unitario: string }
const newLine = (): LineDraft => ({ producto_id: '', cantidad: '1', costo_unitario: '' })

export function Purchasing({ session, profile, products, onReceived }: { session: Session; profile: Profile; products: Product[]; onReceived: () => Promise<void> }) {
  const manager = profile.rol === 'gerente'
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [orders, setOrders] = useState<Purchase[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [tab, setTab] = useState<'orders' | 'suppliers'>('orders')
  const [supplierOpen, setSupplierOpen] = useState(false)
  const [selectedSupplier, setSelectedSupplier] = useState<Supplier | null>(null)
  const [orderOpen, setOrderOpen] = useState(false)
  const [supplierDraft, setSupplierDraft] = useState({ nombre: '', documento: '', telefono: '', correo: '' })
  const [supplierId, setSupplierId] = useState('')
  const [observation, setObservation] = useState('')
  const [lines, setLines] = useState<LineDraft[]>([newLine()])
  const [selected, setSelected] = useState<Purchase | null>(null)
  const [counts, setCounts] = useState<Record<string, string>>({})

  const refresh = useCallback(async () => {
    try {
      const [s, p] = await Promise.all([api<Supplier[]>('/suppliers', session), api<Purchase[]>('/purchases', session)])
      setSuppliers(s); setOrders(p); setError('')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudieron cargar las compras.') }
    finally { setLoading(false) }
  }, [session])
  useEffect(() => { void Promise.resolve().then(refresh) }, [refresh])

  const pending = orders.filter(order => order.estado === 'pendiente')
  const estimate = useMemo(() => lines.reduce((sum, line) => sum + (Number(line.cantidad) || 0) * (Number(line.costo_unitario) || 0), 0), [lines])

  function openSupplier(supplier?: Supplier) {
    setSelectedSupplier(supplier || null)
    setSupplierDraft(supplier ? { nombre: supplier.nombre, documento: supplier.documento || '', telefono: supplier.telefono || '', correo: supplier.correo || '' } : { nombre: '', documento: '', telefono: '', correo: '' })
    setError(''); setSupplierOpen(true)
  }

  async function saveSupplier(event: FormEvent) {
    event.preventDefault(); if (busy) return
    setBusy(true); setError('')
    try {
      const saved = await api<Supplier>(selectedSupplier ? `/suppliers/${selectedSupplier.id}` : '/suppliers', session, { method: selectedSupplier ? 'PUT' : 'POST', body: JSON.stringify(selectedSupplier ? { ...supplierDraft, activo: selectedSupplier.activo } : supplierDraft) })
      setSupplierOpen(false); setSelectedSupplier(null); setSupplierDraft({ nombre: '', documento: '', telefono: '', correo: '' }); setSupplierId(saved.id)
      setNotice(`Proveedor ${saved.nombre} ${selectedSupplier ? 'actualizado' : 'registrado'}.`); await refresh()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo registrar el proveedor.') }
    finally { setBusy(false) }
  }

  async function saveOrder(event: FormEvent) {
    event.preventDefault(); if (busy) return
    if (new Set(lines.map(line => line.producto_id)).size !== lines.length) { setError('No repitas un producto en el pedido.'); return }
    setBusy(true); setError('')
    try {
      const created = await api<Purchase>('/purchases', session, { method: 'POST', body: JSON.stringify({ proveedor_id: supplierId, observacion: observation, items: lines.map(line => ({ producto_id: line.producto_id, cantidad: Number(line.cantidad), costo_unitario: Number(line.costo_unitario) })) }) })
      setOrderOpen(false); setLines([newLine()]); setObservation(''); setNotice(`Pedido #${created.numero} creado. Almacén puede recibirlo.`); await refresh()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo crear el pedido.') }
    finally { setBusy(false) }
  }

  async function openOrder(order: Purchase) {
    setError('')
    try {
      const detail = await api<Purchase>(`/purchases/${order.id}`, session)
      setSelected(detail); setCounts(Object.fromEntries((detail.items || []).map(line => [line.id, ''])))
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo consultar el pedido.') }
  }

  async function receiveOrder(event: FormEvent) {
    event.preventDefault(); if (!selected || busy) return
    setBusy(true); setError('')
    try {
      await api<Purchase>(`/purchases/${selected.id}/receive`, session, { method: 'POST', body: JSON.stringify({ items: (selected.items || []).map(line => ({ detalle_id: line.id, cantidad_fisica: Number(counts[line.id]) })) }) })
      setNotice(`Pedido #${selected.numero} recibido. Las existencias ya están actualizadas.`)
      setSelected(null); await refresh(); await onReceived()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo confirmar la recepción.') }
    finally { setBusy(false) }
  }

  async function cancelOrder() {
    if (!selected || busy) return
    setBusy(true); setError('')
    try {
      await api<Purchase>(`/purchases/${selected.id}/cancel`, session, { method: 'POST' })
      setNotice(`Pedido #${selected.numero} cancelado.`); setSelected(null); await refresh()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo cancelar el pedido.') }
    finally { setBusy(false) }
  }

  function updateLine(index: number, field: keyof LineDraft, value: string) {
    setLines(current => current.map((line, i) => i === index ? { ...line, [field]: value } : line))
  }

  return <div className="purchasing-module">
    <div className="purchase-intro"><span className="purchase-intro-icon">{manager ? <Truck size={24} /> : <ClipboardCheck size={24} />}</span><div><strong>{manager ? 'De la alerta de stock al pedido' : 'Recepción con conteo y trazabilidad'}</strong><p>{manager ? 'Solicita productos a un proveedor y sigue el estado hasta que almacén registre la recepción.' : 'Compara las cantidades físicas con el pedido y confirma la entrada real al inventario.'}</p></div><span className="purchase-intro-tag">{manager ? 'GERENCIA' : 'ALMACÉN'}</span></div>
    <div className="purchase-metrics"><div><small>Pedidos pendientes</small><strong>{pending.length}</strong><span>En espera de recepción</span></div><div><small>Pedidos recibidos</small><strong>{orders.filter(order => order.estado === 'recibida').length}</strong><span>Stock actualizado</span></div><div><small>Proveedores registrados</small><strong>{suppliers.length}</strong><span>Directorio de compras</span></div></div>
    <div className="purchase-toolbar"><div className="purchase-tabs"><button className={tab === 'orders' ? 'active' : ''} onClick={() => setTab('orders')}>Pedidos</button><button className={tab === 'suppliers' ? 'active' : ''} onClick={() => setTab('suppliers')}>Proveedores</button></div><div className="purchase-actions"><button className="secondary-button" disabled={loading} onClick={() => { setLoading(true); void refresh() }}><RefreshCw size={16} /> Actualizar</button>{manager && <button className="primary-button" onClick={() => { setError(''); setOrderOpen(true) }}><Plus size={17} /> Nuevo pedido</button>}</div></div>
    {notice && <div className="alert success" role="status">{notice}</div>}{error && !selected && !orderOpen && !supplierOpen && <div className="alert error" role="alert">{error}</div>}
    {tab === 'orders' ? <section className="panel table-panel"><div className="table-toolbar"><div><h2>Órdenes de compra</h2><p>{manager ? 'Pedidos emitidos a proveedores.' : 'Abre un pedido pendiente para contar y recibir.'}</p></div><span className="purchase-count">{orders.length} pedidos</span></div><div className="table-scroll"><table><thead><tr><th>PEDIDO</th><th>PROVEEDOR</th><th>FECHA</th><th>PRODUCTOS</th>{manager && <th>IMPORTE EST.</th>}<th>ESTADO</th><th>ACCIÓN</th></tr></thead><tbody>{orders.map(order => <tr key={order.id}><td><strong>#{order.numero}</strong></td><td>{order.proveedor}</td><td>{dateTime(order.creado_en)}</td><td>{order.lineas}</td>{manager && <td>{money(Number(order.total_estimado))}</td>}<td><span className={`purchase-state ${order.estado}`}>{order.estado}</span></td><td><button className="row-link" onClick={() => void openOrder(order)}>{!manager && order.estado === 'pendiente' ? 'Recibir' : 'Ver detalle'} <ArrowRight size={14} /></button></td></tr>)}</tbody></table></div>{!orders.length && <div className="purchase-empty"><Package size={26} /><strong>Aún no hay pedidos</strong><p>{manager ? 'Crea el primero para iniciar la reposición.' : 'Los pedidos creados por gerencia aparecerán aquí.'}</p></div>}</section> : <section className="panel table-panel"><div className="table-toolbar"><div><h2>Directorio de proveedores</h2><p>Contactos registrados para las compras.</p></div>{manager && <button className="primary-button" onClick={() => openSupplier()}><Plus size={17} /> Nuevo proveedor</button>}</div><div className="table-scroll"><table><thead><tr><th>PROVEEDOR</th><th>DOCUMENTO</th><th>TELÉFONO</th><th>CORREO</th><th>ESTADO</th>{manager && <th>ACCIÓN</th>}</tr></thead><tbody>{suppliers.map(supplier => <tr key={supplier.id}><td><strong>{supplier.nombre}</strong></td><td>{supplier.documento || '—'}</td><td>{supplier.telefono || '—'}</td><td>{supplier.correo || '—'}</td><td>{supplier.activo ? 'Activo' : 'Inactivo'}</td>{manager && <td><button className="row-link" onClick={() => openSupplier(supplier)}>Editar <ArrowRight size={14} /></button></td>}</tr>)}</tbody></table></div>{!suppliers.length && <div className="purchase-empty"><Building2 size={26} /><strong>Sin proveedores</strong><p>Gerencia puede registrar el primer proveedor.</p></div>}</section>}
    {supplierOpen && <div className="modal-backdrop"><div className="modal" role="dialog" aria-modal="true" aria-labelledby="supplier-title"><div className="modal-heading"><div><span className="eyebrow">COMPRAS</span><h2 id="supplier-title">{selectedSupplier ? 'Editar proveedor' : 'Nuevo proveedor'}</h2><p>Identifica la fuente de cada reposición.</p></div><button className="icon-button" onClick={() => setSupplierOpen(false)} aria-label="Cerrar"><X size={20} /></button></div><form className="modal-form" onSubmit={saveSupplier}><div className="form-grid"><label className="wide">Nombre o razón social<input required minLength={2} maxLength={160} value={supplierDraft.nombre} onChange={e => setSupplierDraft({ ...supplierDraft, nombre: e.target.value })} /></label><label>RUC o documento<input minLength={8} maxLength={20} value={supplierDraft.documento} onChange={e => setSupplierDraft({ ...supplierDraft, documento: e.target.value })} /></label><label>Teléfono<input minLength={6} maxLength={30} value={supplierDraft.telefono} onChange={e => setSupplierDraft({ ...supplierDraft, telefono: e.target.value })} /></label><label className="wide">Correo de contacto<input type="email" maxLength={160} value={supplierDraft.correo} onChange={e => setSupplierDraft({ ...supplierDraft, correo: e.target.value })} /></label></div>{selectedSupplier && <label className="check"><input type="checkbox" checked={selectedSupplier.activo} onChange={e => setSelectedSupplier({ ...selectedSupplier, activo: e.target.checked })} /> Proveedor activo</label>}{error && <div className="alert error" role="alert">{error}</div>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setSupplierOpen(false)}>Cancelar</button><button type="submit" className="primary-button" disabled={busy}>{busy ? 'Guardando…' : 'Guardar proveedor'}</button></div></form></div></div>}
    {orderOpen && <div className="modal-backdrop"><div className="modal purchase-modal" role="dialog" aria-modal="true" aria-labelledby="order-title"><div className="modal-heading"><div><span className="eyebrow">GERENCIA · ABASTECIMIENTO</span><h2 id="order-title">Nuevo pedido</h2><p>El stock aumentará cuando almacén confirme la recepción.</p></div><button className="icon-button" onClick={() => setOrderOpen(false)} aria-label="Cerrar"><X size={20} /></button></div><form className="modal-form" onSubmit={saveOrder}><label>Proveedor<select required value={supplierId} onChange={e => setSupplierId(e.target.value)}><option value="">Selecciona un proveedor</option>{suppliers.filter(s => s.activo).map(s => <option key={s.id} value={s.id}>{s.nombre}</option>)}</select></label>{!suppliers.length && <p className="purchase-help">Primero registra un proveedor en la pestaña Proveedores.</p>}<div className="purchase-lines-heading"><strong>Productos solicitados</strong><button type="button" onClick={() => setLines(current => [...current, newLine()])} disabled={lines.length >= 50}><Plus size={15} /> Añadir línea</button></div>{lines.map((line, index) => <div className="purchase-line-draft" key={index}><label>Producto<select required value={line.producto_id} onChange={e => updateLine(index, 'producto_id', e.target.value)}><option value="">Seleccionar</option>{products.filter(p => p.activo).map(p => <option key={p.id} value={p.id}>{p.codigo} · {p.nombre} · stock {p.stock}</option>)}</select></label><label>Cantidad<input required type="number" min="1" step="1" value={line.cantidad} onChange={e => updateLine(index, 'cantidad', e.target.value)} /></label><label>Costo unitario S/<input required type="number" min="0.01" step="0.01" value={line.costo_unitario} onChange={e => updateLine(index, 'costo_unitario', e.target.value)} /></label>{lines.length > 1 && <button type="button" className="line-remove" onClick={() => setLines(current => current.filter((_, i) => i !== index))} aria-label={`Quitar producto ${index + 1}`}><X size={17} /></button>}</div>)}<label>Nota del pedido<textarea maxLength={500} rows={2} value={observation} onChange={e => setObservation(e.target.value)} placeholder="Referencia o indicaciones para almacén" /></label><div className="purchase-estimate"><span>Total estimado</span><strong>{money(estimate)}</strong></div>{error && <div className="alert error" role="alert">{error}</div>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setOrderOpen(false)}>Cancelar</button><button type="submit" className="primary-button" disabled={busy || !suppliers.length}>{busy ? 'Creando…' : 'Crear pedido'}</button></div></form></div></div>}
    {selected && <div className="modal-backdrop"><div className="modal purchase-modal" role="dialog" aria-modal="true" aria-labelledby="detail-title"><div className="modal-heading"><div><span className="eyebrow">PEDIDO #{selected.numero}</span><h2 id="detail-title">{selected.estado === 'pendiente' ? manager ? 'Pedido por recibir' : 'Confirmar recepción' : selected.estado === 'recibida' ? 'Pedido recibido' : 'Pedido cancelado'}</h2><p>{selected.proveedor} · Pedido por {selected.creado_nombre || 'Gerencia'} · {dateTime(selected.creado_en)}{selected.recibido_nombre && selected.recibido_en ? ` · Recibido por ${selected.recibido_nombre} el ${dateTime(selected.recibido_en)}` : ''}</p></div><button className="icon-button" onClick={() => { setSelected(null); setError('') }} aria-label="Cerrar"><X size={20} /></button></div><form className="modal-form" onSubmit={receiveOrder}><div className="purchase-detail-head"><span>PRODUCTO</span><span>PEDIDO</span>{!manager && selected.estado === 'pendiente' && <span>CONTADO</span>}</div>{selected.items?.map(line => <div className="purchase-detail-line" key={line.id}><div><strong>{line.nombre_producto}</strong><small>{line.codigo_producto}{manager && ` · ${money(Number(line.costo_unitario))} c/u`}</small></div><b>{line.cantidad}</b>{!manager && selected.estado === 'pendiente' && <input required aria-label={`Cantidad física de ${line.nombre_producto}`} type="number" min="0" step="1" value={counts[line.id] || ''} onChange={e => setCounts({ ...counts, [line.id]: e.target.value })} />}</div>)}{manager && <div className="purchase-estimate"><span>Total estimado</span><strong>{money(Number(selected.total_estimado))}</strong></div>}{selected.observacion && <p className="purchase-help">Nota: {selected.observacion}</p>}{error && <div className="alert error" role="alert">{error}</div>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={() => { setSelected(null); setError('') }}>Cerrar</button>{manager && selected.estado === 'pendiente' && <button type="button" className="secondary-button" onClick={() => void cancelOrder()} disabled={busy}>Cancelar pedido</button>}{!manager && selected.estado === 'pendiente' && <button type="submit" className="primary-button" disabled={busy}>{busy ? 'Confirmando…' : 'Confirmar recepción'}</button>}</div></form></div></div>}
  </div>
}

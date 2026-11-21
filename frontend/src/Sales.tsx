import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { Session } from '@supabase/supabase-js'
import { ArrowRight, Check, ClipboardList, Minus, Plus, ReceiptText, Search, ShoppingBasket, X } from 'lucide-react'
import { api, dateTime, money } from './lib/appData'
import type { Product, Profile, SaleReceipt, SaleSummary, SalesSummaryStats } from './lib/appData'
import type { Customer } from './FinalModules'
import './Sales.css'

type Payment = 'efectivo' | 'yape' | 'plin' | 'transferencia' | 'tarjeta' | 'credito'
type Cart = Record<string, number>
const paymentLabels: Record<Payment, string> = { efectivo: 'Efectivo', yape: 'Yape', plin: 'Plin', transferencia: 'Transferencia', tarjeta: 'Tarjeta', credito: 'Crédito autorizado' }

export function Sales({ session, profile, products, onSaleSaved }: { session: Session; profile: Profile; products: Product[]; onSaleSaved: () => Promise<void> }) {
  const manager = profile.rol === 'gerente'
  const [view, setView] = useState<'new' | 'history'>(manager ? 'history' : 'new')
  const [cart, setCart] = useState<Cart>({})
  const [payment, setPayment] = useState<Payment>('efectivo')
  const [customer, setCustomer] = useState('')
  const [customers, setCustomers] = useState<Customer[]>([])
  const [voidReason, setVoidReason] = useState('')
  const [receiptError, setReceiptError] = useState('')
  const [search, setSearch] = useState('')
  const [sales, setSales] = useState<SaleSummary[]>([])
  const [summary, setSummary] = useState<SalesSummaryStats>({ total_ventas: 0, ventas_hoy: 0, importe_hoy: 0 })
  const [cashState, setCashState] = useState('cargando')
  const [salesLoaded, setSalesLoaded] = useState(false)
  const [receipt, setReceipt] = useState<SaleReceipt | null>(null)
  const [loadingReceipt, setLoadingReceipt] = useState(false)
  const [pendingKey, setPendingKey] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [historyError, setHistoryError] = useState('')

  const loadSales = useCallback(async () => {
    try {
      const [recent, totals, cash, clients] = await Promise.all([api<SaleSummary[]>('/sales', session), api<SalesSummaryStats>('/sales/summary', session), api<{ estado: string }>('/cash/status', session), api<Customer[]>('/customers', session)])
      setCustomers(clients); setSales(recent); setSummary(totals); setCashState(cash.estado); setHistoryError(''); setSalesLoaded(true)
    }
    catch (reason) { setHistoryError(reason instanceof Error ? reason.message : 'No se pudo cargar el historial.') }
  }, [session])
  useEffect(() => { void Promise.resolve().then(loadSales) }, [loadSales])

  const available = useMemo(() => products.filter(p => p.activo && p.tipo !== 'insumo' && p.stock > 0 && `${p.nombre} ${p.codigo} ${p.categoria}`.toLocaleLowerCase('es-PE').includes(search.toLocaleLowerCase('es-PE'))), [products, search])
  const lines = useMemo(() => Object.entries(cart).flatMap(([id, quantity]) => { const product = products.find(p => p.id === id); return product ? [{ product, quantity }] : [] }), [cart, products])
  const units = lines.reduce((sum, line) => sum + line.quantity, 0)
  const total = lines.reduce((sum, line) => sum + Math.round(Number(line.product.precio_venta) * line.quantity * 100) / 100, 0)

  function changeQuantity(id: string, next: number) {
    const product = products.find(p => p.id === id)
    if (!product) return
    setCart(previous => {
      const updated = { ...previous }
      if (next <= 0) delete updated[id]
      else updated[id] = Math.min(next, product.stock)
      return updated
    })
    setPendingKey(null); setError('')
  }

  async function saveSale(event: FormEvent) {
    event.preventDefault()
    if (busy || !lines.length) return
    const key = pendingKey || crypto.randomUUID()
    setPendingKey(key); setBusy(true); setError('')
    try {
      const saved = await api<SaleReceipt>('/sales', session, { method: 'POST', body: JSON.stringify({ clave_idempotencia: key, metodo_pago: payment, cliente_id: customer || null, items: lines.map(line => ({ producto_id: line.product.id, cantidad: line.quantity, precio_esperado: line.product.precio_venta })) }) })
      setReceipt(saved); setCart({}); setPendingKey(null); setPayment('efectivo'); setCustomer('')
      await Promise.all([onSaleSaved(), loadSales()])
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo confirmar la venta.')
      await onSaleSaved()
    } finally { setBusy(false) }
  }

  async function openReceipt(id: string) {
    setLoadingReceipt(true); setHistoryError(''); setReceiptError(''); setVoidReason('')
    try { setReceipt(await api<SaleReceipt>(`/sales/${id}`, session)) }
    catch (reason) { setHistoryError(reason instanceof Error ? reason.message : 'No se pudo abrir el comprobante.') }
    finally { setLoadingReceipt(false) }
  }

  async function downloadPdf() {
    if (!receipt) return
    setReceiptError('')
    try {
      const r = await fetch('/api/sales/' + receipt.id + '/pdf', { headers: { Authorization: 'Bearer ' + session.access_token } })
      if (!r.ok) throw new Error('No se pudo descargar el comprobante.')
      const url = URL.createObjectURL(await r.blob()); const a = document.createElement('a'); a.href = url; a.download = 'venta-' + receipt.numero + '.pdf'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (e) { setReceiptError(e instanceof Error ? e.message : 'No se pudo descargar.') }
  }
  async function voidSale() {
    if (!receipt || busy) return
    setBusy(true); setReceiptError('')
    try { setReceipt(await api<SaleReceipt>('/sales/' + receipt.id + '/void', session, { method: 'POST', body: JSON.stringify({ motivo: voidReason }) })); setVoidReason(''); await Promise.all([onSaleSaved(), loadSales()]) } catch (e) { setReceiptError(e instanceof Error ? e.message : 'No se pudo anular.') } finally { setBusy(false) }
  }
  return <div className="sales-module">
    <div className="sales-role-banner"><span className="sales-role-icon">{manager ? <ClipboardList size={23} /> : <ShoppingBasket size={23} />}</span><div><strong>{manager ? 'Supervisión de ventas' : 'Tu mostrador digital'}</strong><p>{manager ? 'Consulta todas las ventas, sus comprobantes y el inventario descontado automáticamente.' : 'Selecciona productos, confirma el cobro y consulta tus propias ventas. El precio lo establece el catálogo.'}</p></div><span className="sales-role-tag">{manager ? 'GERENCIA' : 'VENTAS'}</span></div>
    <div className="sales-metrics"><div><span>{manager ? 'Ventas de hoy · equipo' : 'Mis ventas de hoy'}</span><strong>{salesLoaded ? summary.ventas_hoy : '—'}</strong><small>Operaciones confirmadas</small></div><div><span>{manager ? 'Facturación de hoy' : 'Mi total de hoy'}</span><strong>{salesLoaded ? money(Number(summary.importe_hoy)) : '—'}</strong><small>Ventas registradas en el sistema</small></div><div><span>{manager ? 'Ventas registradas' : 'Mi historial'}</span><strong>{salesLoaded ? summary.total_ventas : '—'}</strong><small>{manager ? 'Visibles para gerencia' : 'Solo tus operaciones'}</small></div></div>
    <div className="sales-tabs" role="tablist" aria-label="Vistas de ventas"><button type="button" role="tab" aria-selected={view === 'new'} className={view === 'new' ? 'active' : ''} onClick={() => setView('new')}><Plus size={17} /> Nueva venta</button><button type="button" role="tab" aria-selected={view === 'history'} className={view === 'history' ? 'active' : ''} onClick={() => { setView('history'); void loadSales() }}><ReceiptText size={17} /> {manager ? 'Todas las ventas' : 'Mis ventas'}</button></div>
    {view === 'new' && cashState !== 'abierta' && <div className="alert error" role="status">{cashState === 'cerrada' ? 'La caja de hoy está cerrada. No se pueden registrar más ventas hoy.' : cashState === 'cargando' ? 'Comprobando caja…' : 'Gerencia debe abrir Caja diaria para comenzar a vender.'}<button className="link-button" onClick={() => void loadSales()}>Comprobar otra vez</button></div>}
    {view === 'new' ? <div className="pos-grid"><section className="panel pos-catalog"><div className="pos-heading"><div><span className="eyebrow">01 · SELECCIONAR</span><h2>Productos disponibles</h2><p>Precio y stock actualizados desde el catálogo.</p></div><span className="pos-count">{available.length} disponibles</span></div><label className="search pos-search"><Search size={18} /><input aria-label="Buscar para vender" placeholder="Buscar producto o código..." value={search} onChange={event => setSearch(event.target.value)} /></label><div className="pos-products">{available.map(product => <div className="pos-product" key={product.id}><div className="pos-product-icon"><ShoppingBasket size={19} /></div><div className="pos-product-info"><strong>{product.nombre}</strong><small>{product.codigo} · {product.stock} {product.unidad_venta} disponibles</small></div><div className="pos-product-action"><strong>{money(Number(product.precio_venta))}</strong><button type="button" onClick={() => changeQuantity(product.id, (cart[product.id] || 0) + 1)} disabled={(cart[product.id] || 0) >= product.stock} aria-label={`Agregar ${product.nombre}`}><Plus size={16} /> Agregar</button></div></div>)}{!available.length && <div className="pos-empty">No hay productos disponibles para esa búsqueda.</div>}</div></section>
      <form className="panel pos-cart" onSubmit={saveSale}><div className="pos-heading"><div><span className="eyebrow">02 · CONFIRMAR</span><h2>Venta actual</h2><p>Revisa cantidades antes de cobrar.</p></div><span className="pos-count">{units} {units === 1 ? 'unidad' : 'unidades'}</span></div><div className="cart-lines">{lines.length ? lines.map(({ product, quantity }) => <div className="cart-line" key={product.id}><div><strong>{product.nombre}</strong><small>{money(Number(product.precio_venta))} · {product.codigo}</small></div><div className="cart-line-controls"><button type="button" onClick={() => changeQuantity(product.id, quantity - 1)} aria-label={`Quitar uno de ${product.nombre}`}><Minus size={15} /></button><input aria-label={'Cantidad de ' + product.nombre} type="number" min="0.001" step={["ml","g","litro","kg"].includes(product.unidad_venta) ? "0.001" : "1"} max={product.stock} value={quantity} style={{width:75}} onChange={e => changeQuantity(product.id, Number(e.target.value))} /><button type="button" onClick={() => changeQuantity(product.id, quantity + 1)} disabled={quantity >= product.stock} aria-label={`Agregar uno de ${product.nombre}`}><Plus size={15} /></button></div><strong>{money(Number(product.precio_venta) * quantity)}</strong></div>) : <div className="cart-empty"><ShoppingBasket size={28} /><strong>Tu venta está vacía</strong><span>Agrega productos para comenzar.</span></div>}</div><div className="cart-footer"><label className="payment-label">Cliente<select value={customer} onChange={e => { setCustomer(e.target.value); setPendingKey(null) }}><option value="">Público general</option>{customers.filter(c => c.activo).map(c => <option key={c.id} value={c.id}>{c.nombre} · disponible {money(Math.max(0,Number(c.limite_credito)-Number(c.saldo)))}</option>)}</select></label><label className="payment-label">Medio de pago<select value={payment} onChange={event => { setPayment(event.target.value as Payment); setPendingKey(null); setError('') }}>{Object.entries(paymentLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><div className="cart-total"><span>Total a cobrar</span><strong>{money(total)}</strong></div><p>Al confirmar, el sistema guarda la venta y descuenta el stock en una sola operación.</p>{error && <div className="alert error" role="alert">{error}</div>}<button className="primary-button confirm-sale" type="submit" disabled={busy || !lines.length || cashState !== 'abierta' || (payment === 'credito' && !customer)}>{busy ? 'Confirmando venta…' : <>Confirmar venta <ArrowRight size={18} /></>}</button></div></form></div> : <section className="panel table-panel"><div className="table-toolbar"><div><h2>{manager ? 'Ventas del equipo' : 'Mis ventas registradas'}</h2><p>{manager ? 'Supervisa cada operación confirmada.' : 'Aquí aparecen únicamente las ventas que registraste.'}</p></div><button className="secondary-button" type="button" onClick={() => void loadSales()}>Actualizar</button></div>{historyError && <div className="alert error" role="alert">{historyError}</div>}<div className="table-scroll"><table><thead><tr><th>VENTA</th><th>FECHA</th>{manager && <th>RESPONSABLE</th>}<th>PRODUCTOS</th><th>PAGO</th><th>TOTAL</th><th>DETALLE</th></tr></thead><tbody>{sales.map(sale => <tr key={sale.id}><td><strong>#{sale.numero}{sale.anulada ? ' · Anulada' : ''}</strong></td><td>{dateTime(sale.fecha)}</td>{manager && <td>{sale.usuario}</td>}<td>{sale.lineas} {sale.lineas === 1 ? 'producto' : 'productos'} · {sale.unidades} uds.</td><td>{paymentLabels[sale.metodo_pago as Payment] || sale.metodo_pago}</td><td><strong>{money(Number(sale.total))}</strong></td><td><button type="button" className="row-link" disabled={loadingReceipt} onClick={() => void openReceipt(sale.id)}>Ver comprobante <ArrowRight size={14} /></button></td></tr>)}</tbody></table></div>{!sales.length && !historyError && <div className="pos-empty" role="status">{salesLoaded ? 'Todavía no hay ventas registradas.' : 'Cargando ventas…'}</div>}</section>}
    {receipt && <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) setReceipt(null) }}><div className="modal receipt-modal" role="dialog" aria-modal="true" aria-labelledby="receipt-title"><div className="modal-heading"><div><span className="eyebrow">VENTA CONFIRMADA</span><h2 id="receipt-title">Comprobante #{receipt.numero}</h2><p>{dateTime(receipt.fecha)} · {paymentLabels[receipt.metodo_pago as Payment]}</p></div><button type="button" className="icon-button" aria-label="Cerrar comprobante" onClick={() => setReceipt(null)}><X size={20} /></button></div><div className="receipt-success"><Check size={18} /> {receipt.anulada ? 'Venta anulada: existencias restituidas' : 'Venta guardada y existencias actualizadas'}</div><div className="receipt-lines">{receipt.items.map(item => <div key={item.producto_id}><div><strong>{item.nombre_producto}</strong><small>{item.codigo_producto} · {item.cantidad} × {money(Number(item.precio_unitario))}</small></div><strong>{money(Number(item.subtotal))}</strong></div>)}</div><div className="receipt-total"><span>Total cobrado</span><strong>{money(Number(receipt.total))}</strong></div><div className="operations-form">{receiptError && <p className="alert error" role="alert">{receiptError}</p>}<button type="button" className="secondary-button" onClick={() => void downloadPdf()}>Descargar comprobante PDF</button>{manager && !receipt.anulada && <><label>Motivo de anulación (solo día actual, sin abonos)<input minLength={3} maxLength={500} value={voidReason} onChange={e => setVoidReason(e.target.value)} /></label><p>La anulación devuelve existencias y excluye el cobro del día. La venta original se conserva.</p><button className="secondary-button" type="button" disabled={busy || voidReason.trim().length < 3} onClick={() => void voidSale()}>Confirmar anulación de esta venta</button></>}</div><div className="modal-actions"><button type="button" className="primary-button" onClick={() => { setReceipt(null); setView(manager ? 'history' : 'new') }}>Continuar</button></div></div></div>}
  </div>
}

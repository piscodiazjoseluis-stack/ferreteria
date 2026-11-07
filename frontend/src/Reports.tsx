import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { Session } from '@supabase/supabase-js'
import { Download, RefreshCw } from 'lucide-react'
import { api, dateTime, money } from './lib/appData'
import './Operations.css'

type Filters = { tipo: string; desde: string; hasta: string; buscar: string; responsable: string; estado: string; pago: string }
type Result = { columnas: string[]; filas: Record<string, string | number>[]; totales: { registros: number; unidades: number; importe?: number }; pagina: number; tamano: number }
const labels: Record<string, string> = { numero: 'Número', fecha: 'Fecha', responsable: 'Responsable', pago: 'Medio de pago', unidades: 'Unidades', total: 'Total', proveedor: 'Proveedor', estado: 'Estado / tipo', recibidas: 'Recibidas', total_estimado: 'Importe estimado', producto: 'Producto', codigo: 'Código', variacion: 'Variación', stock_anterior: 'Antes', stock_resultante: 'Después', motivo: 'Motivo' }
const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(new Date())
const initial: Filters = { tipo: 'ventas', desde: today.slice(0, 8) + '01', hasta: today, buscar: '', responsable: '', estado: '', pago: '' }

export function Reports({ session }: { session: Session }) {
  const [draft, setDraft] = useState(initial)
  const [filters, setFilters] = useState(initial)
  const [page, setPage] = useState(1)
  const [refresh, setRefresh] = useState(0)
  const [data, setData] = useState<Result | null>(null)
  const [busy, setBusy] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    const query = new URLSearchParams({ ...filters, pagina: String(page) })
    void Promise.resolve().then(() => { if (!controller.signal.aborted) { setBusy(true); setError('') } })
    api<Result>(`/reports?${query}`, session, { signal: controller.signal }).then(value => { if (!controller.signal.aborted) setData(value) })
      .catch(reason => { if (!controller.signal.aborted) { setError(reason instanceof Error ? reason.message : 'No se pudo consultar el reporte.'); setData(null) } })
      .finally(() => { if (!controller.signal.aborted) setBusy(false) })
    return () => controller.abort()
  }, [filters, page, refresh, session])
  function submit(event: FormEvent) { event.preventDefault(); setPage(1); setFilters({ ...draft }); setRefresh(n => n + 1) }
  async function download() {
    setExporting(true); setError('')
    try {
      const response = await fetch(`/api/reports?${new URLSearchParams({ ...filters, csv_export: 'true' })}`, { headers: { Authorization: `Bearer ${session.access_token}` } })
      if (!response.ok) { const e = await response.json(); throw new Error(typeof e.detail === 'string' ? e.detail : 'No se pudo exportar el reporte.') }
      const url = URL.createObjectURL(await response.blob())
      const link = document.createElement('a'); link.href = url; link.download = `reporte-${filters.tipo}-${filters.desde || 'inicio'}-${filters.hasta || 'actual'}.csv`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Error al descargar.') }
    finally { setExporting(false) }
  }
  function cell(key: string, value: string | number) {
    if (key === 'fecha') return dateTime(String(value))
    if (key === 'total' || key === 'total_estimado') return money(Number(value))
    return String(value ?? '—')
  }
  return <div className="operations-stack">
    <p className="operations-intro">Consulta ventas, compras y movimientos por período. Los totales abarcan todos los resultados del filtro, aunque haya varias páginas.</p>
    <form className="panel operations-form report-filters" onSubmit={submit}>
      <label>Información<select value={draft.tipo} onChange={e => setDraft({ ...draft, tipo: e.target.value, estado: '', pago: '' })}><option value="ventas">Ventas</option><option value="compras">Compras</option><option value="movimientos">Movimientos de inventario</option></select></label>
      <label>Desde<input type="date" value={draft.desde} onChange={e => setDraft({ ...draft, desde: e.target.value })} /></label>
      <label>Hasta<input type="date" min={draft.desde || undefined} value={draft.hasta} onChange={e => setDraft({ ...draft, hasta: e.target.value })} /></label>
      <label>Buscar<input maxLength={120} value={draft.buscar} placeholder={draft.tipo === 'compras' ? 'Producto, proveedor o número' : 'Producto o código'} onChange={e => setDraft({ ...draft, buscar: e.target.value })} /></label>
      <label>Responsable<input maxLength={120} value={draft.responsable} placeholder="Nombre del colaborador" onChange={e => setDraft({ ...draft, responsable: e.target.value })} /></label>
      {draft.tipo === 'ventas' ? <label>Medio de pago<select value={draft.pago} onChange={e => setDraft({ ...draft, pago: e.target.value })}><option value="">Todos</option>{['efectivo', 'yape', 'plin', 'transferencia', 'tarjeta'].map(p => <option key={p}>{p}</option>)}</select></label> : <label>Estado o movimiento<select value={draft.estado} onChange={e => setDraft({ ...draft, estado: e.target.value })}><option value="">Todos</option>{(draft.tipo === 'compras' ? ['pendiente', 'parcial', 'recibida', 'cancelada'] : ['saldo_inicial', 'entrada', 'ajuste', 'venta', 'compra']).map(s => <option key={s}>{s}</option>)}</select></label>}
      <button className="primary-button" disabled={busy} type="submit"><RefreshCw size={16} /> Consultar</button>
      <button className="secondary-button" disabled={busy || exporting || !data} type="button" onClick={() => void download()}><Download size={16} /> {exporting ? 'Descargando…' : 'Exportar CSV'}</button>
    </form>
    {error && <div className="alert error" role="alert">{error}</div>}
    {busy && <p role="status">Consultando registros…</p>}
    {data && !busy && <><div className="operations-metrics"><div><small>Registros del período</small><strong>{data.totales.registros}</strong></div><div><small>{filters.tipo === 'movimientos' ? 'Variación neta de unidades' : 'Unidades registradas'}</small><strong>{data.totales.unidades}</strong></div>{data.totales.importe !== undefined && <div><small>{filters.tipo === 'compras' ? 'Importe estimado de pedidos' : 'Importe vendido'}</small><strong>{money(Number(data.totales.importe))}</strong></div>}</div>
      <section className="panel table-panel"><div className="table-toolbar"><div><h2>Resultado de la consulta</h2><p>Fechas interpretadas en hora de Lima. CSV incluye todos los resultados, hasta 50 000 filas.</p></div></div><div className="table-scroll"><table><thead><tr>{data.columnas.map(k => <th key={k}>{labels[k] || k}</th>)}</tr></thead><tbody>{data.filas.map((row, i) => <tr key={i}>{data.columnas.map(k => <td key={k}>{cell(k, row[k])}</td>)}</tr>)}</tbody></table></div>{!data.filas.length && <p className="operations-empty">No hay registros para estos filtros.</p>}<div className="operations-pagination"><button className="secondary-button" disabled={page === 1} onClick={() => setPage(n => n - 1)}>Anterior</button><span>Página {page} de {Math.max(1, Math.ceil(data.totales.registros / data.tamano))}</span><button className="secondary-button" disabled={page * data.tamano >= data.totales.registros} onClick={() => setPage(n => n + 1)}>Siguiente</button></div></section>
    </>}
  </div>
}

import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { Session } from '@supabase/supabase-js'
import { RefreshCw, X } from 'lucide-react'
import { api, dateTime, money } from './lib/appData'
import './Operations.css'

type Totals = { pagos: Record<string, number>; ventas_total: number; operaciones: number; ingresos: number; retiros: number; efectivo_esperado: number }
type Box = { id: string; fecha: string; fondo: number; estado: string; contado: number | null; diferencia: number | null; motivo: string; abierto_nombre: string; cerrado_nombre: string; cerrado_en: string; totales: Totals; movimientos: { id: string; tipo: string; importe: number; motivo: string; usuario_nombre: string; fecha: string }[] }
type BoxSummary = Pick<Box, 'id' | 'fecha' | 'estado' | 'diferencia'>
const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(new Date())

export function Cash({ session }: { session: Session }) {
  const [day, setDay] = useState(today)
  const [box, setBox] = useState<Box | null>(null)
  const [history, setHistory] = useState<BoxSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [fund, setFund] = useState('')
  const [type, setType] = useState('ingreso')
  const [amount, setAmount] = useState('')
  const [reason, setReason] = useState('')
  const [count, setCount] = useState('')
  const [closingReason, setClosingReason] = useState('')
  const [confirm, setConfirm] = useState(false)
  const [movementKey, setMovementKey] = useState(() => crypto.randomUUID())
  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      const [b, h] = await Promise.all([api<Box | null>(`/cash/day/${day}`, session, { signal }), api<BoxSummary[]>('/cash', session, { signal })])
      if (!signal?.aborted) { setBox(b); setHistory(h); setError('') }
    } catch (r) { if (!signal?.aborted) setError(r instanceof Error ? r.message : 'No se pudo consultar la caja.') }
    finally { if (!signal?.aborted) setLoading(false) }
  }, [session, day])
  useEffect(() => {
    const controller = new AbortController()
    void Promise.resolve().then(() => { if (!controller.signal.aborted) { setLoading(true); setCount(''); setClosingReason(''); setNotice('') } })
    void Promise.resolve().then(() => load(controller.signal))
    return () => controller.abort()
  }, [load])
  async function mutate(path: string, payload: unknown, message: string) {
    setBusy(true); setError(''); setNotice('')
    try { const result = await api<Box>(path, session, { method: 'POST', body: JSON.stringify(payload) }); setBox(result); setNotice(message); await load(); return true }
    catch (r) { setError(r instanceof Error ? r.message : 'No se pudo completar la acción.'); return false }
    finally { setBusy(false) }
  }
  async function open(event: FormEvent) { event.preventDefault(); await mutate('/cash', { fondo: Number(fund) }, 'Caja abierta. El equipo ya puede registrar ventas.') }
  async function movement(event: FormEvent) {
    event.preventDefault(); if (!box) return
    if (await mutate(`/cash/${box.id}/movements`, { id: movementKey, tipo: type, importe: Number(amount), motivo: reason }, 'Movimiento de efectivo registrado.')) { setAmount(''); setReason(''); setMovementKey(crypto.randomUUID()) }
  }
  async function close() {
    if (!box) return
    if (await mutate(`/cash/${box.id}/close`, { contado: Number(count), motivo: closingReason }, 'Cierre confirmado y conservado en el historial.')) setConfirm(false)
  }
  const difference = Number(count) - Number(box?.totales.efectivo_esperado || 0)
  return <div className="operations-stack">
    <p className="operations-intro">Una caja para el negocio por cada día de Lima. Abre antes de vender, registra ingresos o retiros de efectivo y compara el conteo físico al cerrar. Los pagos digitales se muestran separados.</p>
    <div className="operations-toolbar"><label>Día consultado<input type="date" value={day} max={today} onChange={e => { if (e.target.value) setDay(e.target.value) }} /></label><button className="secondary-button" disabled={loading || busy} onClick={() => void load()}><RefreshCw size={16} /> Actualizar caja</button></div>
    {error && <div className="alert error" role="alert">{error}</div>}{notice && <div className="alert success" role="status">{notice}</div>}
    {loading ? <p role="status">Consultando caja…</p> : !box ? <section className="panel operations-form"><h2>Sin apertura registrada</h2>{day === today ? <form onSubmit={open} className="operations-form"><label>Fondo inicial en efectivo S/<input required type="number" min="0" max="9999999999.99" step="0.01" value={fund} onChange={e => setFund(e.target.value)} /></label><p className="form-message">Es el efectivo disponible al comenzar. No representa una venta.</p><button className="primary-button" disabled={busy}>Abrir caja de hoy</button></form> : <p>No hay caja registrada para este día.</p>}</section> : <>
      <div className="purchase-metrics"><div><small>Estado de la caja</small><strong>{box.estado === 'abierta' ? 'Abierta' : 'Cerrada'}</strong><span>Abrió {box.abierto_nombre}</span></div><div><small>Total vendido</small><strong>{money(Number(box.totales.ventas_total))}</strong><span>{box.totales.operaciones} ventas confirmadas</span></div><div><small>Efectivo esperado</small><strong>{money(Number(box.totales.efectivo_esperado))}</strong><span>Fondo + ventas en efectivo + ingresos − retiros</span></div></div>
      <div className="cash-grid"><section className="panel operations-form"><h2>Cobros y efectivo</h2><div className="cash-breakdown"><div><span>Fondo inicial</span><strong>{money(Number(box.fondo))}</strong></div>{Object.entries(box.totales.pagos).map(([key, value]) => <div key={key}><span>Ventas · {key}</span><strong>{money(Number(value))}</strong></div>)}<div><span>Otros ingresos de efectivo</span><strong>{money(Number(box.totales.ingresos))}</strong></div><div><span>Retiros de efectivo</span><strong>{money(Number(box.totales.retiros))}</strong></div></div></section>
        {box.estado === 'abierta' ? <div className="operations-stack"><form className="panel operations-form" onSubmit={movement}><h2>Movimiento de efectivo</h2><label>Tipo<select value={type} onChange={e => { setType(e.target.value); setMovementKey(crypto.randomUUID()) }}><option value="ingreso">Ingreso adicional</option><option value="retiro">Retiro</option></select></label><label>Importe S/<input required type="number" min="0.01" max="9999999999.99" step="0.01" value={amount} onChange={e => { setAmount(e.target.value); setMovementKey(crypto.randomUUID()) }} /></label><label>Motivo<textarea required minLength={3} maxLength={500} value={reason} onChange={e => { setReason(e.target.value); setMovementKey(crypto.randomUUID()) }} placeholder="Ej. Retiro para traslado de mercancía" /></label><button className="secondary-button" disabled={busy}>Registrar movimiento</button></form>
          <form className="panel operations-form" onSubmit={e => { e.preventDefault(); setConfirm(true) }}><h2>Preparar cierre</h2><label>Efectivo contado S/<input required type="number" min="0" max="9999999999.99" step="0.01" value={count} onChange={e => setCount(e.target.value)} /></label>{count !== '' && <strong className={`cash-difference ${difference ? 'cash-warning' : ''}`}>Diferencia: {money(difference)}</strong>}<label>Explicación {difference !== 0 && count !== '' ? '(obligatoria si hay diferencia)' : '(opcional)'}<textarea required={difference !== 0 && count !== ''} minLength={difference !== 0 ? 3 : undefined} maxLength={500} value={closingReason} onChange={e => setClosingReason(e.target.value)} /></label><p>El cierre conserva los importes y bloquea nuevas ventas en este día.</p><button className="primary-button" disabled={busy || count === ''}>Revisar cierre</button></form></div> : <section className="panel operations-form"><h2>Cierre confirmado</h2><div className="cash-breakdown"><div><span>Efectivo contado</span><strong>{money(Number(box.contado))}</strong></div><div><span>Diferencia</span><strong>{money(Number(box.diferencia))}</strong></div></div><p>{box.motivo || 'Cierre sin diferencia.'}</p><p>{box.cerrado_nombre} · {dateTime(box.cerrado_en)}</p><p>Este cierre se conserva sin cambios.</p></section>}
      </div><section className="panel table-panel"><div className="table-toolbar"><h2>Movimientos de efectivo</h2></div><div className="table-scroll"><table><thead><tr><th>FECHA</th><th>TIPO</th><th>IMPORTE</th><th>MOTIVO</th><th>RESPONSABLE</th></tr></thead><tbody>{box.movimientos.map(m => <tr key={m.id}><td>{dateTime(m.fecha)}</td><td>{m.tipo}</td><td>{money(Number(m.importe))}</td><td>{m.motivo}</td><td>{m.usuario_nombre}</td></tr>)}</tbody></table></div>{!box.movimientos.length && <p className="operations-empty">Sin ingresos adicionales ni retiros.</p>}</section>
    </>}
    <section className="panel table-panel"><div className="table-toolbar"><h2>Últimas cajas registradas</h2></div><div className="table-scroll"><table><thead><tr><th>DÍA</th><th>ESTADO</th><th>DIFERENCIA</th><th>CONSULTAR</th></tr></thead><tbody>{history.map(h => <tr key={h.id}><td>{h.fecha}</td><td>{h.estado}</td><td>{h.diferencia === null ? '—' : money(Number(h.diferencia))}</td><td><button className="row-link" onClick={() => setDay(h.fecha)}>Ver caja</button></td></tr>)}</tbody></table></div></section>
    {confirm && box && <div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="cash-close-title"><div className="modal-heading"><h2 id="cash-close-title">Confirmar cierre de caja</h2><button className="icon-button" aria-label="Cancelar cierre" disabled={busy} onClick={() => setConfirm(false)}><X /></button></div><div className="modal-form"><p className="cash-close-summary">Día {box.fecha}. Esperado: {money(Number(box.totales.efectivo_esperado))}. Contado: {money(Number(count))}. Diferencia preliminar: {money(difference)}.</p><p className="cash-close-summary">Al confirmar se recalculan las ventas. Después no se podrán agregar ventas ni movimientos a este día.</p>{error && <div className="alert error" role="alert">{error}</div>}<div className="modal-actions"><button className="secondary-button" disabled={busy} onClick={() => setConfirm(false)}>Seguir revisando</button><button className="primary-button" disabled={busy} onClick={() => void close()}>{busy ? 'Cerrando…' : 'Confirmar cierre definitivo'}</button></div></div></section></div>}
  </div>
}

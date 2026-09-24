import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from './lib/supabase'
import './App.css'

type Profile = { id: string; nombre: string; rol: 'gerente' | 'vendedor'; activo: boolean }

export default function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [checking, setChecking] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!supabase) return
    const { data } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next)
      setProfile(null)
      setChecking(Boolean(next))
      setError('')
    })
    return () => data.subscription.unsubscribe()
  }, [])

  useEffect(() => {
    if (!session) return
    const controller = new AbortController()
    fetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${session.access_token}` }, signal: controller.signal,
    }).then(async (response) => {
      const data: unknown = await response.json()
      if (!response.ok) {
        const detail = data && typeof data === 'object' && 'detail' in data ? String(data.detail) : 'No se pudo comprobar el acceso.'
        throw new Error(detail)
      }
      if (!data || typeof data !== 'object' || !('id' in data) || !('nombre' in data) ||
          !('rol' in data) || !('activo' in data) || data.activo !== true ||
          typeof data.id !== 'string' || typeof data.nombre !== 'string' ||
          !['gerente', 'vendedor'].includes(String(data.rol))) throw new Error('Respuesta de acceso no válida.')
      if (!controller.signal.aborted) setProfile(data as Profile)
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'No se pudo conectar con el servidor.')
    }).finally(() => {
      if (!controller.signal.aborted) setChecking(false)
    })
    return () => controller.abort()
  }, [session, attempt])

  async function login(event: FormEvent) {
    event.preventDefault()
    if (!supabase || busy) return
    setBusy(true); setError('')
    try {
      const { error: failure } = await supabase.auth.signInWithPassword({ email: email.trim(), password })
      if (failure) setError(failure.status === 400 ? 'Correo o contraseña incorrectos.' : 'No se pudo iniciar sesión. Inténtalo de nuevo.')
      else setPassword('')
    } catch { setError('No se pudo conectar con el servicio de acceso.') }
    finally { setBusy(false) }
  }

  async function logout() {
    if (!supabase || busy) return
    setBusy(true)
    try {
      const { error: failure } = await supabase.auth.signOut({ scope: 'local' })
      if (failure) setError('No se pudo cerrar la sesión. Inténtalo de nuevo.')
    } catch { setError('No se pudo cerrar la sesión. Inténtalo de nuevo.') }
    finally { setBusy(false) }
  }

  return (
    <main>
      <p className="eyebrow">FERRETERÍA Y MATIZADOS MIGUEL</p>
      <h1>{profile ? `Hola, ${profile.nombre}` : 'Acceso al sistema'}</h1>
      <p>Ventas e inventario de la ferretería.</p>
      {!supabase ? <p role="alert">Falta configurar la conexión de autenticación.</p> :
        checking ? <p role="status">Comprobando acceso…</p> :
        profile ? <section>
          <h2>Sesión iniciada</h2>
          <p>Rol: <strong>{profile.rol === 'gerente' ? 'Gerente' : 'Vendedor'}</strong></p>
          <p>Tu cuenta está activa y tiene acceso al sistema.</p>
          <p className="note">Los módulos de productos, inventario y ventas se incorporarán en las siguientes etapas.</p>
          <button onClick={logout} disabled={busy}>Cerrar sesión</button>
        </section> : session ? <section>
          <h2>No se pudo completar el acceso</h2>
          <button onClick={() => { setChecking(true); setError(''); setAttempt((value) => value + 1) }}>Reintentar</button>
          <button onClick={logout} disabled={busy}>Cerrar sesión</button>
        </section> : <form onSubmit={login}>
          <label htmlFor="email">Correo electrónico</label>
          <input id="email" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <label htmlFor="password">Contraseña</label>
          <input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          <button type="submit" disabled={busy}>{busy ? 'Ingresando…' : 'Ingresar'}</button>
        </form>}
      {error && <p role="alert" className="error">{error}</p>}
    </main>
  )
}

import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { Session } from '@supabase/supabase-js'
import { ArrowRight, Eye, EyeOff, LockKeyhole, ShieldCheck } from 'lucide-react'
import { Brand } from './Brand'
import { supabase } from './lib/supabase'

export function Auth({ onSession }: { onSession: (session: Session | null) => void }) {
  const [mode, setMode] = useState<'login' | 'forgot' | 'reset'>(window.location.search.includes('recuperar=1') ? 'reset' : 'login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    if (!supabase) return
    const { data } = supabase.auth.onAuthStateChange(event => {
      if (event === 'PASSWORD_RECOVERY') { setMode('reset'); setError('') }
    })
    return () => data.subscription.unsubscribe()
  }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!supabase || busy) return
    const enteredEmail = String(new FormData(event.currentTarget as HTMLFormElement).get('email') || email).trim()
    const enteredPassword = String(new FormData(event.currentTarget as HTMLFormElement).get('password') || password)
    setBusy(true); setError(''); setSuccess('')
    try {
      if (mode === 'login') {
        const { data, error: failure } = await supabase.auth.signInWithPassword({ email: enteredEmail, password: enteredPassword })
        if (failure || !data.session) throw new Error(failure?.status === 400 ? 'Correo o contraseña incorrectos.' : 'No se pudo iniciar sesión.')
        setPassword(''); onSession(data.session)
      } else if (mode === 'forgot') {
        const { error: failure } = await supabase.auth.resetPasswordForEmail(enteredEmail, { redirectTo: `${window.location.origin}/?recuperar=1` })
        if (failure) throw new Error(failure.message)
        setSuccess('Si ese correo tiene una cuenta, recibirás un enlace para restablecer la contraseña. Revisa también spam.')
      } else {
        if (enteredPassword.length < 8) throw new Error('La nueva contraseña debe tener al menos 8 caracteres.')
        if (enteredPassword !== confirm) throw new Error('Las contraseñas no coinciden.')
        const { error: failure } = await supabase.auth.updateUser({ password: enteredPassword })
        if (failure) throw new Error(failure.message)
        await supabase.auth.signOut()
        onSession(null); setPassword(''); setConfirm(''); setMode('login')
        setSuccess('Contraseña actualizada. Ingresa con tu nueva contraseña.')
        window.history.replaceState({}, '', '/')
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo conectar con el servicio de acceso.') }
    finally { setBusy(false) }
  }

  return <div className="auth-shell"><section className="auth-story"><Brand light /><div className="story-content"><div className="story-kicker"><i /> UNA FORMA MÁS CLARA DE TRABAJAR</div><h1>Del cuaderno y Excel<br /><em>al control en tiempo real.</em></h1><p>Ventas, compras e inventario conectados. Cada rol trabaja con información actualizada y movimientos verificables.</p><div className="story-bottom"><span>01 / 04</span><span>PRODUCTOS · VENTAS · COMPRAS · INVENTARIO</span></div></div><div className="story-orb one" /><div className="story-orb two" /></section><section className="auth-panel"><div className="auth-card"><div className="auth-icon"><LockKeyhole size={21} /></div><span className="eyebrow">ACCESO SEGURO</span><h2>{mode === 'login' ? 'Bienvenido de nuevo' : mode === 'forgot' ? 'Recupera tu acceso' : 'Nueva contraseña'}</h2><p>{mode === 'login' ? 'Ingresa tus datos para continuar con la gestión de la ferretería.' : mode === 'forgot' ? 'Te enviaremos un enlace a tu correo para restablecer la contraseña.' : 'Elige una contraseña segura para volver a ingresar.'}</p>{!supabase && <div className="alert error" role="alert">Falta configurar la autenticación.</div>}<form onSubmit={submit}>{mode !== 'reset' && <label>Correo electrónico<input type="email" name="email" autoComplete="username" placeholder="nombre@correo.com" required value={email} onChange={e => setEmail(e.target.value)} /></label>}{mode !== 'forgot' && <label>Contraseña<div className="password-field"><input type={show ? 'text' : 'password'} name="password" autoComplete={mode === 'reset' ? 'new-password' : 'current-password'} placeholder="••••••••" required value={password} onChange={e => setPassword(e.target.value)} /><button type="button" aria-label={show ? 'Ocultar contraseña' : 'Mostrar contraseña'} onClick={() => setShow(!show)}>{show ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></label>}{mode === 'reset' && <label>Confirmar contraseña<input type="password" autoComplete="new-password" required value={confirm} onChange={e => setConfirm(e.target.value)} /></label>}{mode === 'login' && <button type="button" className="link-button forgot" onClick={() => { setMode('forgot'); setError(''); setSuccess('') }}>¿Olvidaste tu contraseña?</button>}{error && <div className="alert error" role="alert">{error}</div>}{success && <div className="alert success" role="status">{success}</div>}<button className="primary-button auth-submit" type="submit" disabled={busy || !supabase}>{busy ? 'Un momento…' : mode === 'login' ? 'Ingresar al sistema' : mode === 'forgot' ? 'Enviar enlace de recuperación' : 'Guardar nueva contraseña'} <ArrowRight size={17} /></button></form>{mode === 'forgot' && <button className="link-button back" onClick={() => { setMode('login'); setError('') }}>Volver al inicio de sesión</button>}<div className="auth-safety"><ShieldCheck size={17} /> Acceso exclusivo para personal autorizado.</div></div><small className="copyright">© 2026 Ferretería y Matizados Miguel</small></section></div>
}

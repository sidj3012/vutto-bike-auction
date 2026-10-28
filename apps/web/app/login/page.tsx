'use client';
import { useState } from 'react';
import Link from 'next/link';
import { ArrowRight, LockKeyhole } from 'lucide-react';
import { api, User } from '@/lib/api';

export default function Login() {
  const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setError('');
    try { const user = await api<User>('/auth/login', { method:'POST', body: JSON.stringify({email,password}) }); const next = new URLSearchParams(window.location.search).get('next');
      const safeNext = next?.startsWith('/') && !next.startsWith('//') && !next.startsWith('/\\') ? next : '/';
      window.location.assign(user.role === 'admin' ? '/admin' : safeNext); }
    catch(e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  return <main className="auth-page"><div className="auth-panel"><div className="auth-symbol"><LockKeyhole size={26}/></div><span className="overline light">GOOD TO HAVE YOU BACK</span><h1>Welcome<br/>back<span className="brand-point">.</span></h1><p>Sign in to bid on your next motorcycle.</p><form onSubmit={submit} className="auth-form"><label>Email address<input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" required/></label><label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password" required/></label>{error && <div className="alert error" role="alert">{error}</div>}<button disabled={busy} className="button primary full">{busy?'Signing in…':'Sign in'} <ArrowRight size={18}/></button></form><p className="auth-switch">New around here? <Link href="/register">Create an account</Link></p></div></main>;
}

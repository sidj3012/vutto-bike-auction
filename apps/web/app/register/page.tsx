'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowRight, UserPlus } from 'lucide-react';
import { api } from '@/lib/api';

export default function Register() {
  const router = useRouter(); const [display_name, setName] = useState(''); const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setError('');
    try { await api('/auth/register', {method:'POST',body:JSON.stringify({display_name,email,password})}); router.push('/'); router.refresh(); }
    catch(e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  return <main className="auth-page"><div className="auth-panel"><div className="auth-symbol"><UserPlus size={26}/></div><span className="overline light">WELCOME TO THE GARAGE</span><h1>Find your<br/>ride<span className="brand-point">.</span></h1><p>Create a free account to join live auctions.</p><form onSubmit={submit} className="auth-form"><label>Your name<input value={display_name} onChange={e=>setName(e.target.value)} minLength={2} maxLength={60} placeholder="Full name" required autoComplete="name"/></label><label>Email address<input type="email" value={email} onChange={e=>setEmail(e.target.value)} required placeholder="you@example.com" autoComplete="email"/></label><label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} minLength={10} maxLength={128} required placeholder="At least 10 characters" autoComplete="new-password"/></label>{error && <div className="alert error" role="alert">{error}</div>}<button disabled={busy} className="button primary full">{busy?'Creating account…':'Create account'} <ArrowRight size={18}/></button></form><p className="auth-switch">Already registered? <Link href="/login">Sign in</Link></p></div></main>;
}

'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowRight, LogOut, ShieldCheck } from 'lucide-react';
import { api, User } from '@/lib/api';

export function Header() {
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => { api<User>('/auth/me').then(setUser).catch(() => setUser(null)); }, []);
  const logout = async () => {
    await api('/auth/logout', { method: 'POST' });
    setUser(null);
    window.location.assign('/');
  };
  return <header className="site-header">
    <div className="container header-inside">
      <Link href="/" className="brand"><span className="logo-mark">M.</span> MotoBid<span className="brand-point">.</span></Link>
      <nav aria-label="Main navigation"><Link href="/">Explore auctions</Link>{user?.role === 'admin' && <Link href="/admin">Admin studio</Link>}</nav>
      <div className="header-account">
        {user ? <><span className="hello"><ShieldCheck size={15}/>{user.display_name}</span><button className="icon-button" onClick={logout} title="Sign out" aria-label="Sign out"><LogOut size={18}/></button></>
          : <Link className="button small dark" href="/login">Sign in <ArrowRight size={15}/></Link>}
      </div>
    </div>
  </header>;
}

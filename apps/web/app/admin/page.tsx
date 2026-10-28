'use client';
import { FormEvent, useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowUpRight, Plus, ShieldCheck, Play, Square } from 'lucide-react';
import { api, Auction, User, rupees } from '@/lib/api';

const initial = {
  title: '', brand: '', model: '', year: '2023', mileage_km: '8000', description: '',
  starting_price: '150000', min_increment: '2500', starts_at: '', ends_at: ''
};
export default function Admin() {
  const [auctions, setAuctions] = useState<Auction[]>([]); const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const [form, setForm] = useState(initial); const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => { const rows = await api<Auction[]>('/admin/auctions'); setAuctions(rows); }, []);
  useEffect(()=>{ api<User>('/auth/me').then(u=>{setUser(u); if(u.role==='admin') void refresh().catch(e=>setError(e.message));}).catch(()=>setError('Please sign in as an administrator.')).finally(()=>setLoading(false)); },[refresh]);
  const act = async (id: string, action:'publish'|'close') => {
    setBusy(true); setError(''); setNotice('');
    try { await api(`/admin/auctions/${id}/${action}`, {method:'POST'}); setNotice(`Auction ${action==='publish'?'published':'closed'} successfully.`); await refresh(); }
    catch(e){setError((e as Error).message);} finally{setBusy(false);}
  };
  const create = async (event:FormEvent) => {
    event.preventDefault(); setBusy(true); setError(''); setNotice('');
    try {
      const data = {
        title:form.title, brand:form.brand, model:form.model, description:form.description,
        year:Number(form.year), mileage_km:Number(form.mileage_km),
        starting_price_paise:Math.round(Number(form.starting_price)*100),
        min_increment_paise:Math.round(Number(form.min_increment)*100),
        starts_at:new Date(form.starts_at).toISOString(), ends_at:new Date(form.ends_at).toISOString()
      };
      await api('/admin/auctions',{method:'POST',body:JSON.stringify(data)}); setForm(initial); setNotice('Draft created. Publish it when ready.'); await refresh();
    } catch(e){setError((e as Error).message);} finally{setBusy(false);}
  };
  return <main className="container admin-page"><div className="admin-heading"><div><span className="overline light">MOTOBID / OPERATIONS</span><h1>Auction studio<span className="brand-point">.</span></h1><p>Prepare listings. Control lifecycle. Keep the bidding fair.</p></div><span className="admin-verified"><ShieldCheck size={17}/> ADMIN ACCESS</span></div>
  {error && <div className="alert error" role="alert">{error}</div>}{notice && <div className="alert success" role="status">{notice}</div>}
  {loading?<div className="empty-state">Checking authorization…</div>:user?.role!=='admin'?<div className="empty-state"><h2>Administrator access required</h2><Link className="button primary" href="/login">Sign in</Link></div>:<div className="admin-grid"><div className="admin-list"><div className="subheading"><h2>Manage listings</h2><span>{auctions.length} auctions</span></div>{auctions.length?auctions.map(a=><div className="admin-listing" key={a.id}><div><div className="auction-meta">{a.year} · {a.brand.toUpperCase()}</div><h3>{a.title}</h3><small>{rupees(a.current_price_paise??a.starting_price_paise)} · {a.bid_count} bids</small><div><span className={`status-chip ${a.status}`}>{a.status.toUpperCase()}</span></div></div><div className="admin-actions">{a.status!=='draft' && <Link title="View listing" href={`/auctions/${a.id}`}><ArrowUpRight size={18}/></Link>}{a.status==='draft'&&<button disabled={busy} title="Publish" onClick={()=>act(a.id,'publish')}><Play size={17}/></button>}{['scheduled','active'].includes(a.status)&&<button disabled={busy} title="Close auction" onClick={()=>act(a.id,'close')}><Square size={17}/></button>}</div></div>):<div className="empty-state">No listings yet. Create your first draft.</div>}</div>
  <div className="admin-new"><div className="subheading"><h2><Plus size={20}/> Create a listing</h2></div><form onSubmit={create} className="admin-form"><label>Display title<input required minLength={5} value={form.title} onChange={e=>setForm({...form,title:e.target.value})} placeholder="e.g. Triumph Speed 400"/></label><div className="form-two"><label>Make / brand<input required value={form.brand} onChange={e=>setForm({...form,brand:e.target.value})} placeholder="Triumph"/></label><label>Model<input required value={form.model} onChange={e=>setForm({...form,model:e.target.value})} placeholder="Speed 400"/></label></div><div className="form-two"><label>Year<input required type="number" min={1950} max={2030} value={form.year} onChange={e=>setForm({...form,year:e.target.value})}/></label><label>Mileage (km)<input required type="number" min={0} value={form.mileage_km} onChange={e=>setForm({...form,mileage_km:e.target.value})}/></label></div><label>Description<textarea required minLength={15} maxLength={3000} rows={3} value={form.description} onChange={e=>setForm({...form,description:e.target.value})} placeholder="Condition, history, documents, service records…"/></label><div className="form-two"><label>Starting price (₹)<input required type="number" min={1} step={1} value={form.starting_price} onChange={e=>setForm({...form,starting_price:e.target.value})}/></label><label>Bid increment (₹)<input required type="number" min={1} step={1} value={form.min_increment} onChange={e=>setForm({...form,min_increment:e.target.value})}/></label></div><div className="form-two"><label>Starts at<input required type="datetime-local" value={form.starts_at} onChange={e=>setForm({...form,starts_at:e.target.value})}/></label><label>Ends at<input required type="datetime-local" value={form.ends_at} onChange={e=>setForm({...form,ends_at:e.target.value})}/></label></div><button disabled={busy} className="button primary full" type="submit">{busy?'Saving…':'Save as draft'} <Plus size={17}/></button></form></div></div>}
  </main>;
}

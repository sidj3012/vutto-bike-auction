'use client';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { ArrowLeft, CheckCircle2, Clock3, Gauge, Gavel, ShieldCheck, Radio } from 'lucide-react';
import { api, Auction, Bid, countdown, rupees } from '@/lib/api';
import { BikeArt } from '@/components/BikeArt';

export default function AuctionDetail() {
  const { id } = useParams<{ id: string }>();
  const [auction, setAuction] = useState<Auction | null>(null);
  const [bids, setBids] = useState<Bid[]>([]);
  const [now, setNow] = useState(Date.now());
  const [amount, setAmount] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [connected, setConnected] = useState(false);
  const refresh = useCallback(async () => {
    try {
      const [a, b] = await Promise.all([api<Auction>(`/auctions/${id}`), api<Bid[]>(`/auctions/${id}/bids`)]);
      setAuction(prev => prev && prev.version > a.version ? prev : a);
      setBids(b); setError('');
    } catch (e) { setError((e as Error).message); }
  }, [id]);
  useEffect(() => { void refresh(); const p = setInterval(refresh, 10000); const t = setInterval(()=>setNow(Date.now()),1000); return () => { clearInterval(p); clearInterval(t); }; }, [refresh]);
  useEffect(() => {
    let ws: WebSocket | undefined;
    let attempt = 0;
    let reconnect: ReturnType<typeof setTimeout> | undefined;
    let closed = false;
    const connect = async () => {
      let base: string;
      try {
        const conf = await fetch('/runtime-config', { cache: 'no-store' }).then(r => r.json());
        base = conf.ws_url;
      } catch { return; }
      if (closed) return;
      ws = new WebSocket(`${base}/ws/auctions/${id}`);
      ws.onopen = () => { setConnected(true); attempt = 0; };
      ws.onmessage = event => {
        try { const data = JSON.parse(event.data); if (data.type === 'auction_changed' || data.type === 'sync') void refresh(); }
        catch { /* ignore malformed stream data */ }
      };
      ws.onclose = () => { setConnected(false); if (!closed) { attempt++; reconnect = setTimeout(connect, Math.min(30000, 1000 * 2 ** Math.min(attempt, 5))); } };
      ws.onerror = () => { ws?.close(); };
    };
    connect(); return () => { closed = true; clearTimeout(reconnect); ws?.close(); };
  }, [id, refresh]);
  if (!auction) return <main className="container detail-page"><Link href="/" className="back-link"><ArrowLeft size={16}/> Back to auctions</Link><div className="empty-state">{error || 'Loading auction…'}</div></main>;
  const minimum = (auction.current_price_paise ?? (auction.starting_price_paise - auction.min_increment_paise)) + auction.min_increment_paise;
  const canBid = auction.status === 'active' && new Date(auction.starts_at).getTime() <= now && new Date(auction.ends_at).getTime() > now;
  const bid = async (e: React.FormEvent) => {
    e.preventDefault(); setNotice(''); setError('');
    const amountPaise = Math.round(Number(amount) * 100);
    if (!Number.isSafeInteger(amountPaise) || amountPaise < minimum) { setError(`Minimum bid is ${rupees(minimum)}.`); return; }
    setBusy(true);
    try {
      await api(`/auctions/${id}/bids`, { method: 'POST', body: JSON.stringify({ amount_paise: amountPaise, idempotency_key: crypto.randomUUID() }) });
      setNotice('Bid accepted! Your offer is now in the lead.'); setAmount(''); await refresh();
    } catch(e) { const msg = (e as Error).message; if (msg.includes('Sign in')) window.location.assign('/login'); else { setError(msg); await refresh(); } }
    finally { setBusy(false); }
  };
  return <main className="container detail-page"><Link href="/" className="back-link"><ArrowLeft size={16}/> All auctions</Link>
    <div className="detail-heading"><div><div className="overline light">{auction.brand.toUpperCase()} / {auction.year} / PRE-OWNED</div><h1>{auction.title}<span className="brand-point">.</span></h1><p>Inspect the details. Trust the process. Bid with confidence.</p></div><span className={`status-chip detail-chip ${auction.status}`}>{auction.status === 'active' ? '● LIVE AUCTION' : auction.status.toUpperCase()}</span></div>
    <div className="detail-grid"><div><div className="detail-art"><BikeArt variant={auction.year%3}/><span className="art-watermark">MOTOBID SELECT</span></div><div className="spec-cards"><div><Gauge size={22}/><span>MILEAGE</span><strong>{auction.mileage_km.toLocaleString('en-IN')} km</strong></div><div><Clock3 size={22}/><span>MODEL YEAR</span><strong>{auction.year}</strong></div><div><ShieldCheck size={22}/><span>TRANSPARENCY</span><strong>Live bid history</strong></div></div><div className="detail-description"><h2>Meet your next ride</h2><p>{auction.description}</p></div><div className="bid-history"><div className="history-title"><h2>Bid activity</h2><span>{auction.bid_count} total bids</span></div>{bids.length ? bids.map((b,i)=><div className="history-row" key={b.id}><span className="history-dot"><Gavel size={17}/></span><div><strong>{b.bidder_label}</strong><small>{new Date(b.created_at).toLocaleString('en-IN')}</small></div><strong>{rupees(b.amount_paise)}</strong>{i===0 && <span className="leading-pill">Highest</span>}</div>) : <p className="muted">Be the first to make an offer.</p>}</div></div>
    <aside className="bid-sidebar"><div className="bid-panel"><div className="bid-panel-head"><span>{auction.bid_count ? 'CURRENT HIGHEST BID' : 'STARTING PRICE'}</span><span className="live-indicator"><Radio size={14}/>{connected?'LIVE SYNC':'AUTO SYNC'}</span></div><div className="big-price">{rupees(auction.current_price_paise ?? auction.starting_price_paise)}</div><div className="timer-box"><span>{auction.status==='closed'?'AUCTION ENDED':auction.status==='scheduled'?'STARTS IN':'TIME REMAINING'}</span><strong>{auction.status==='closed'?'00:00:00':countdown(auction.status==='scheduled'?auction.starts_at:auction.ends_at,now)}</strong></div><div className="bid-facts"><div><span>Minimum next bid</span><strong>{rupees(minimum)}</strong></div><div><span>Total accepted bids</span><strong>{auction.bid_count}</strong></div></div>
      {canBid ? <form onSubmit={bid} className="bid-form"><label htmlFor="bid-amount">Your bid amount (₹)</label><div className="amount-input"><span>₹</span><input id="bid-amount" type="number" min={minimum/100} step="1" inputMode="numeric" placeholder={String(Math.ceil(minimum/100))} value={amount} onChange={e=>setAmount(e.target.value)} required/></div><button disabled={busy} type="submit" className="button primary full">{busy?'Placing bid…':'Place your bid'} <Gavel size={19}/></button></form>:<div className="inactive-msg">{auction.status==='scheduled'?'Bidding begins when the auction goes live.':'This auction is not accepting new bids.'}</div>}
      {notice && <div className="alert success" role="status"><CheckCircle2 size={18}/>{notice}</div>}{error && <div className="alert error" role="alert">{error}</div>}<div className="panel-assurance"><ShieldCheck size={19}/><span>Every bid is validated and securely recorded. You will never be charged by placing a demo bid.</span></div>
    </div></aside></div></main>;
}

'use client';
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowUpRight, ArrowRight, ShieldCheck, Clock3, Search, Gavel, Zap } from 'lucide-react';
import { api, Auction } from '@/lib/api';
import { AuctionCard } from '@/components/AuctionCard';
import { BikeArt } from '@/components/BikeArt';

export default function Home() {
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  useEffect(() => {
    const load = () => api<Auction[]>('/auctions').then(v => { setAuctions(v); setError(''); }).catch(e => setError(e.message)).finally(() => setLoading(false));
    load(); const timer = setInterval(load, 15000); return () => clearInterval(timer);
  }, []);
  const shown = useMemo(() => auctions
    .filter(a => filter === 'all' || a.status === filter)
    .filter(a => `${a.title} ${a.brand} ${a.model}`.toLowerCase().includes(query.toLowerCase()))
    .sort((a,b) => ({ active: 0, scheduled: 1, closed: 2, draft: 3 }[a.status] - { active: 0, scheduled: 1, closed: 2, draft: 3 }[b.status])), [auctions, filter, query]);
  const liveCount = auctions.filter(a => a.status === 'active').length;
  return <main>
    <section className="hero"><div className="container hero-grid">
      <div className="hero-copy"><span className="overline"><span className="pulse"/> THE NEW WAY TO BUY PRE-OWNED</span>
        <h1>Find your<br/>next <em>ride.</em><br/>Own the moment.</h1>
        <p>Handpicked motorcycles. Transparent live auctions. Your next adventure starts with one smart bid.</p>
        <div className="hero-actions"><a className="button primary" href="#auctions">Explore auctions <ArrowRight size={18}/></a><span className="hero-count"><b>{liveCount}</b> live auctions now</span></div>
        <div className="hero-trust"><span><ShieldCheck size={17}/> Verified listings</span><span><Zap size={17}/> Real-time bidding</span></div>
      </div>
      <div className="hero-display"><div className="hero-large-circle"/><BikeArt variant={0}/><div className="float-tag"><span className="mini-icon"><Gavel size={18}/></span><div><small>GOING, GOING...</small><strong>Your next bike awaits</strong></div></div><div className="hero-stamp">RIDE<br/>BEYOND<br/><span>ORDINARY ↗</span></div></div>
    </div></section>
    <section className="container catalogue" id="auctions"><div className="section-top"><div><span className="overline light">THE GARAGE / 001</span><h2>On the auction block<span className="brand-point">.</span></h2><p>Discover something worth riding for.</p></div><div className="listing-total">{auctions.length.toString().padStart(2, '0')} <span>AVAILABLE LISTINGS</span></div></div>
      <div className="catalogue-toolbar"><div className="filter-buttons" role="group" aria-label="Auction status">{[['all','All bikes'],['active','Live now'],['scheduled','Upcoming'],['closed','Ended']].map(([value,label])=><button key={value} className={filter===value?'selected':''} onClick={()=>setFilter(value)}>{label}</button>)}</div><label className="search-box"><Search size={18}/><input type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search make or model" aria-label="Search motorcycles"/></label></div>
      {error && <div className="alert error" role="alert">Could not load auctions: {error}</div>}
      {loading ? <div className="empty-state">Loading the garage…</div> : shown.length ? <div className="auction-grid">{shown.map((a,i)=><AuctionCard key={a.id} auction={a} index={i}/>)}</div> : <div className="empty-state"><Gavel size={28}/><h3>No bikes in this lane yet</h3><p>Try another filter, or check back when new auctions go live.</p></div>}
    </section>
    <section className="how-section"><div className="container"><span className="overline light">IT'S SIMPLE</span><h2>Three steps to the open road.</h2><div className="steps"><div><span className="step-num">01</span><Search size={25}/><h3>Find your match</h3><p>Explore curated bikes with key details and clear starting prices.</p></div><div><span className="step-num">02</span><Gavel size={25}/><h3>Make your move</h3><p>Place secure bids and see every accepted bid update live.</p></div><div><span className="step-num">03</span><Clock3 size={25}/><h3>Win the moment</h3><p>When the clock ends, the highest valid bidder takes the lead.</p></div></div></div></section>
  </main>;
}

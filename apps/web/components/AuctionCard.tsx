'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowUpRight, Gauge, Clock3, Gavel } from 'lucide-react';
import { Auction, countdown, rupees } from '@/lib/api';
import { BikeArt } from './BikeArt';

export function AuctionCard({ auction, index }: { auction: Auction; index: number }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  const live = auction.status === 'active' && new Date(auction.ends_at).getTime() > now;
  const upcoming = auction.status === 'scheduled' && new Date(auction.starts_at).getTime() > now;
  const current = auction.current_price_paise ?? auction.starting_price_paise;
  return <Link href={`/auctions/${auction.id}`} className="auction-card">
    <div className="auction-art"><BikeArt variant={index} /><span className={`status-chip ${auction.status}`}>{auction.status === 'active' ? '● LIVE NOW' : auction.status.toUpperCase()}</span></div>
    <div className="auction-body">
      <div className="auction-meta">{auction.brand.toUpperCase()} <span>•</span> {auction.year}</div>
      <div className="card-title-row"><h3>{auction.title}</h3><ArrowUpRight size={19}/></div>
      <div className="spec-row"><span><Gauge size={14}/>{auction.mileage_km.toLocaleString('en-IN')} km driven</span><span><Gavel size={14}/>{auction.bid_count} bids</span></div>
      {(live || upcoming) && <div className="card-countdown" aria-label={live ? "Time left" : "Starts in"}><Clock3 size={14}/><span>{live ? "Time left" : "Starts in"}: <strong>{countdown(live ? auction.ends_at : auction.starts_at, now)}</strong></span></div>}
      {auction.status === "closed" || (auction.status === "active" && !live) ? <div className="card-countdown">Auction ended</div> : null}
      <div className="card-bottom"><div><div className="eyebrow">{auction.bid_count ? 'CURRENT BID' : 'STARTING AT'}</div><strong>{rupees(current)}</strong></div><span className="view-circle"><ArrowUpRight size={20}/></span></div>
    </div>
  </Link>;
}

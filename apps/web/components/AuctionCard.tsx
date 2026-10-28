import Link from 'next/link';
import { ArrowUpRight, Gauge, CalendarDays, Gavel } from 'lucide-react';
import { Auction, rupees } from '@/lib/api';
import { BikeArt } from './BikeArt';

export function AuctionCard({ auction, index }: { auction: Auction; index: number }) {
  const current = auction.current_price_paise ?? auction.starting_price_paise;
  return <Link href={`/auctions/${auction.id}`} className="auction-card">
    <div className="auction-art"><BikeArt variant={index} /><span className={`status-chip ${auction.status}`}>{auction.status === 'active' ? '● LIVE NOW' : auction.status.toUpperCase()}</span></div>
    <div className="auction-body">
      <div className="auction-meta">{auction.brand.toUpperCase()} <span>•</span> {auction.year}</div>
      <div className="card-title-row"><h3>{auction.title}</h3><ArrowUpRight size={19}/></div>
      <div className="spec-row"><span><Gauge size={14}/>{auction.mileage_km.toLocaleString('en-IN')} km</span><span><Gavel size={14}/>{auction.bid_count} bids</span></div>
      <div className="card-bottom"><div><div className="eyebrow">{auction.bid_count ? 'CURRENT BID' : 'STARTING AT'}</div><strong>{rupees(current)}</strong></div><span className="view-circle"><ArrowUpRight size={20}/></span></div>
    </div>
  </Link>;
}

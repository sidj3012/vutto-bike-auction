import type { Metadata } from 'next';
import { Header } from '@/components/Header';
import './globals.css';

export const metadata: Metadata = {
  title: 'MotoBid — Ride your next story',
  description: 'Premium pre-owned motorcycles, transparent live bidding, real-time auctions.',
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Header />{children}<footer className="footer"><div className="container footer-inside"><span>MotoBid<span className="brand-point">.</span></span><span>Curated rides. Clear bids. Confident buyers.</span><span>Demo auction experience · INR</span></div></footer></body></html>;
}

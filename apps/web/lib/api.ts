export type User = { id: string; display_name: string; email: string; role: 'buyer' | 'admin' };
export type Auction = {
  id: string; title: string; brand: string; model: string; year: number;
  mileage_km: number; description: string; image_url: string | null;
  starting_price_paise: number; min_increment_paise: number;
  current_price_paise: number | null; bid_count: number;
  version: number; status: 'draft' | 'scheduled' | 'active' | 'closed';
  starts_at: string; ends_at: string; winner_id: string | null;
};
export type Bid = { id: string; auction_id: string; amount_paise: number; created_at: string; bidder_label: string };

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
  });
  if (!response.ok) {
    let message = `${response.status}: Request failed`;
    try {
      const data = await response.json();
      if (typeof data.detail === 'string') message = data.detail;
      else if (Array.isArray(data.detail)) message = data.detail.map((issue: { msg?: string; loc?: string[] }) => issue.msg ?? 'Invalid request').join('; ');
      else if (typeof data.message === 'string') message = data.message;
    } catch { /* fallback */ }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const rupees = (paise: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(paise / 100);

export function countdown(iso: string, now: number) {
  const seconds = Math.max(0, Math.ceil((new Date(iso).getTime() - now) / 1000));
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${d ? `${d}d ` : ''}${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

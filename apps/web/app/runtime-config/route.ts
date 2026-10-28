export const dynamic = 'force-dynamic';
export function GET() {
  return Response.json({ ws_url: process.env.PUBLIC_WS_URL || 'ws://localhost:8000' },
                       { headers: { 'Cache-Control': 'no-store' } });
}

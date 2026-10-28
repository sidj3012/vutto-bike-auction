/** Same-origin browser API gateway. Cookies stay HttpOnly on the web host. */
import { NextRequest } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type Ctx = { params: Promise<{ path: string[] }> };
async function proxy(request: NextRequest, { params }: Ctx) {
  const backend = process.env.API_BACKEND_URL;
  if (!backend) return Response.json({ detail: 'API_BACKEND_URL is not configured' }, { status: 503 });
  const { path } = await params;
  const destination = new URL(`${backend.replace(/\/$/, '')}/api/${path.map(encodeURIComponent).join('/')}`);
  destination.search = request.nextUrl.search;
  const headers = new Headers();
  for (const name of ['content-type', 'cookie', 'origin', 'x-request-id']) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  try {
    const upstream = await fetch(destination, {
      method: request.method,
      headers,
      body: ['GET', 'HEAD'].includes(request.method) ? undefined : await request.arrayBuffer(),
      cache: 'no-store',
      redirect: 'manual',
      signal: request.signal,
    });
    const outgoing = new Headers();
    for (const name of ['content-type', 'set-cookie', 'cache-control', 'x-request-id']) {
      const value = upstream.headers.get(name);
      if (value) outgoing.set(name, value);
    }
    outgoing.set('cache-control', 'no-store');
    return new Response(upstream.body, { status: upstream.status, headers: outgoing });
  } catch {
    return Response.json({ detail: 'Backend unavailable' }, { status: 502 });
  }
}
export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };

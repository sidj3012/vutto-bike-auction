import logging
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy import text
from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, generate_latest
import sentry_sdk
from app.config import settings
from app.db import engine
from app.routers import auth, auctions, admin, bidding, live

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
log = logging.getLogger('vutto')
if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
REQUESTS = Counter('vutto_http_requests_total', 'HTTP requests', ['method', 'route', 'status'])
LATENCY = Histogram('vutto_http_request_seconds', 'HTTP request latency', ['method', 'route'])

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    yield
    await app.state.redis.aclose()
    await engine.dispose()

app = FastAPI(title='Vutto Auction API', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.web_origin], allow_credentials=True,
                   allow_methods=['GET', 'POST'], allow_headers=['Content-Type', 'X-Request-ID'])

@app.middleware('http')
async def security_and_metrics(request: Request, call_next):
    start = time.perf_counter()
    request_id = request.headers.get('x-request-id') or str(uuid.uuid4())
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        # Enforce same-origin writes for session-cookie authenticated browser clients.
        if request.headers.get('origin') != settings.web_origin:
            return Response('Untrusted request origin', status_code=403)
    try:
        response = await call_next(request)
    except Exception:
        log.exception('request.failed id=%s method=%s path=%s', request_id, request.method, request.url.path)
        raise
    route = request.scope.get('route')
    path = route.path if route else '/unmatched'
    REQUESTS.labels(request.method, path, str(response.status_code)).inc()
    LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
    response.headers['X-Request-ID'] = request_id
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    log.info('request id=%s method=%s route=%s status=%s duration_ms=%d',
             request_id, request.method, path, response.status_code, (time.perf_counter()-start)*1000)
    return response

@app.get('/healthz')
async def healthz():
    return {'status': 'ok'}

@app.get('/readyz')
async def readyz():
    async with engine.connect() as connection:
        await connection.execute(text('SELECT 1'))
    await app.state.redis.ping()
    return {'status': 'ready'}

@app.get('/metrics', include_in_schema=False)
async def metrics(request: Request):
    if request.headers.get('x-metrics-token') != settings.metrics_token:
        raise HTTPException(403, 'Forbidden')
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

app.include_router(auth.router, prefix='/api/v1')
app.include_router(auctions.router, prefix='/api/v1')
app.include_router(admin.router, prefix='/api/v1')

app.include_router(bidding.router, prefix='/api/v1')
app.include_router(live.router)

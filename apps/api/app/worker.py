"""Independent worker: time-based transitions plus transactional outbox publisher.

Runs as a single replica for this demonstration. Row locks and idempotent transitions
are safe across replicas; high-scale deployments should enforce per-auction ordering.
"""
import asyncio
import json
import logging
import signal
from datetime import datetime, timezone
from sqlalchemy import select, func
from redis.asyncio import Redis
from app.config import settings
from app.db import SessionLocal, engine
from app.events import enqueue
from app.models import Auction, OutboxEvent

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
log = logging.getLogger('motobid.worker')

async def transition_auctions() -> int:
    count = 0
    # Select candidate rows with SKIP LOCKED, so concurrent workers do not
    # block one another or accidentally transition the same auction twice.
    async with SessionLocal.begin() as db:
        now = await db.scalar(select(func.clock_timestamp()))
        pending = (await db.scalars(select(Auction).where(
            Auction.status == 'scheduled', Auction.starts_at <= now)
            .order_by(Auction.starts_at).limit(100).with_for_update(skip_locked=True))).all()
        for auction in pending:
            auction.status = 'active'
            auction.version += 1
            enqueue(db, auction, 'started')
            count += 1
    async with SessionLocal.begin() as db:
        now = await db.scalar(select(func.clock_timestamp()))
        expired = (await db.scalars(select(Auction).where(
            Auction.status == 'active', Auction.ends_at <= now)
            .order_by(Auction.ends_at).limit(100).with_for_update(skip_locked=True))).all()
        for auction in expired:
            auction.status = 'closed'
            auction.winner_id = auction.highest_bidder_id
            auction.version += 1
            enqueue(db, auction, 'closed')
            count += 1
    return count

async def publish_outbox(redis: Redis) -> int:
    async with SessionLocal.begin() as db:
        events = (await db.scalars(select(OutboxEvent).where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.created_at, OutboxEvent.id).limit(100)
            .with_for_update(skip_locked=True))).all()
        for event in events:
            payload = json.dumps({'type': 'auction_changed', 'auction_id': str(event.auction_id),
                                  'version': event.version, 'action': event.action})
            await redis.publish(f'auction:{event.auction_id}', payload)
            event.published_at = datetime.now(timezone.utc)
        return len(events)

async def main():
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        while True:
            try:
                transitions = await transition_auctions()
                delivered = await publish_outbox(redis)
                if transitions or delivered:
                    log.info('cycle transitions=%s events_delivered=%s', transitions, delivered)
            except Exception:
                log.exception('cycle.failed will retry')
            await asyncio.sleep(1.0)
    finally:
        await redis.aclose()
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(main())

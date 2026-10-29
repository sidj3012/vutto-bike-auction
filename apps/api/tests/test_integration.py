"""Real PostgreSQL/Redis integration tests. Never run against production.

To run: set TEST_DATABASE_URL ending in `/auction_test` and DATABASE_URL to the
same database, plus Redis, APP_SECRET, WEB_ORIGIN and METRICS_TOKEN.
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone
import pytest

@pytest.mark.asyncio
async def test_concurrent_bid_locking_idempotency_and_expiry():
    test_url = os.getenv('TEST_DATABASE_URL', '')
    if not test_url:
        pytest.skip('Set TEST_DATABASE_URL to run integration tests')
    if not test_url.split('?')[0].endswith('/auction_test') or test_url != os.getenv('DATABASE_URL'):
        pytest.fail('Refusing to run: DATABASE_URL and TEST_DATABASE_URL must match and target auction_test')

    from httpx import AsyncClient, ASGITransport
    from sqlalchemy import select, func
    from redis.asyncio import Redis
    from app.main import app
    from app.db import engine, SessionLocal
    from app.models import Base, Auction, Bid, User, OutboxEvent
    from app.security import hash_password, make_session, SESSION_AGE_SECONDS, COOKIE_NAME
    from app.config import settings
    from app.worker import publish_outbox, transition_auctions

    async with engine.begin() as c:
        await c.run_sync(Base.metadata.drop_all)
        await c.run_sync(Base.metadata.create_all)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis = redis
    async with SessionLocal.begin() as db:
        first = User(email='first@example.test', display_name='First', password_hash=hash_password('LongPass123456'), role='buyer')
        second = User(email='second@example.test', display_name='Second', password_hash=hash_password('LongPass123456'), role='buyer')
        db.add_all([first, second]); await db.flush()
        auction = Auction(title='Test bike', brand='Test', model='Bike', year=2022, mileage_km=100,
                          description='Test auction description', starting_price_paise=10_000_000,
                          min_increment_paise=100_000, status='active', bid_count=0, version=1,
                          starts_at=datetime.now(timezone.utc)-timedelta(minutes=1),
                          ends_at=datetime.now(timezone.utc)+timedelta(hours=1))
        db.add(auction); await db.flush()
        aid = str(auction.id)
    first_token, first_jti = make_session(first)
    second_token, second_jti = make_session(second)
    await redis.set(f'session:{first_jti}', str(first.id), ex=SESSION_AGE_SECONDS)
    await redis.set(f'session:{second_jti}', str(second.id), ex=SESSION_AGE_SECONDS)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://api.test') as client:
            headers = {'Origin': settings.web_origin}
            async def place(token: str, key: str, price: int):
                return await client.post(f'/api/v1/auctions/{aid}/bids',
                    json={'amount_paise': price, 'idempotency_key': key},
                    cookies={COOKIE_NAME: token}, headers=headers)
            # Both contend for same price. A single acceptance is possible.
            a, b = await asyncio.gather(place(first_token, 'concurrent-1', 10_000_000),
                                        place(second_token, 'concurrent-2', 10_000_000))
            assert sorted([a.status_code, b.status_code]) == [201, 409], (a.text, b.text)
            accepted_token = first_token if a.status_code == 201 else second_token
            accepted_key = 'concurrent-1' if a.status_code == 201 else 'concurrent-2'
            replay = await place(accepted_token, accepted_key, 10_000_000)
            assert replay.status_code == 201
            assert replay.json()['id'] == (a if a.status_code == 201 else b).json()['id']
            conflict = await place(accepted_token, accepted_key, 12_000_000)
            assert conflict.status_code == 409
            async with SessionLocal() as db:
                assert await db.scalar(select(func.count(Bid.id))) == 1
                assert await db.scalar(select(func.count(OutboxEvent.id))) == 1
                item = await db.get(Auction, auction.id)
                assert item.version == 2 and item.current_price_paise == 10_000_000
            # No same-origin header => forbidden even with a valid cookie.
            csrf = await client.post(f'/api/v1/auctions/{aid}/bids',
                json={'amount_paise': 11_000_000, 'idempotency_key': 'no-origin-key'},
                cookies={COOKIE_NAME: first_token})
            assert csrf.status_code == 403
            # Publish outbox once; emitted event is recoverable after restart.
            channel = f'auction:{aid}'

            async with redis.pubsub() as pubsub:
                await pubsub.subscribe(channel)

                # Wait until Redis confirms that the subscription is active.
                confirmation = await pubsub.get_message(
                    ignore_subscribe_messages=False,
                    timeout=2,
                )
                assert confirmation is not None
                assert confirmation["type"] == "subscribe"

                # Publish only after the subscription is confirmed.
                assert await publish_outbox(redis) == 1

                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=2,
                )
                assert msg and 'auction_changed' in msg['data']
            # Expire auction, then assert that new bids are rejected.
            async with SessionLocal.begin() as db:
                item = await db.get(Auction, auction.id)
                item.ends_at = datetime.now(timezone.utc)-timedelta(seconds=1)
            assert await transition_auctions() == 1
            rejected = await place(first_token, 'expired-key', 12_000_000)
            assert rejected.status_code == 409
            async with SessionLocal() as db:
                item = await db.get(Auction, auction.id)
                assert item.status == 'closed' and item.winner_id is not None
    finally:
        await redis.delete(f'session:{first_jti}', f'session:{second_jti}')
        await redis.aclose()
        await engine.dispose()

import asyncio
import json
import logging
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from app.config import settings
from app.db import SessionLocal
from app.models import Auction

router = APIRouter(tags=['live'])
log = logging.getLogger(__name__)

@router.websocket('/ws/auctions/{auction_id}')
async def auction_ws(websocket: WebSocket, auction_id: uuid.UUID):
    # Read-only public stream: users bid via authenticated HTTP endpoint only.
    if websocket.headers.get('origin') != settings.web_origin:
        await websocket.close(code=1008)
        return
    redis = websocket.app.state.redis
    channel = f'auction:{auction_id}'
    async with redis.pubsub() as pubsub:
        # Subscribe BEFORE fetching snapshot to avoid missing a commit event
        # between snapshot and subscription. Versions let clients deduplicate.
        await pubsub.subscribe(channel)
        async with SessionLocal() as db:
            auction = await db.scalar(select(Auction).where(Auction.id == auction_id,
                                                              Auction.status != 'draft'))
            if auction is None:
                await websocket.close(code=1008)
                return
            version = auction.version
        await websocket.accept()
        await websocket.send_json({'type': 'sync', 'auction_id': str(auction_id), 'version': version})
        try:
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg['type'] == 'message':
                    await websocket.send_text(msg['data'])
                else:
                    # Periodic heartbeat detects broken connections and lets clients
                    # periodically reconcile even if pub/sub notifications are lost.
                    await websocket.send_json({'type': 'heartbeat'})
                    await asyncio.sleep(9)
        except (WebSocketDisconnect, RuntimeError, OSError):
            pass
        except Exception:
            log.exception('websocket.failed auction=%s', auction_id)
            try:
                await websocket.close(code=1011)
            except Exception:
                pass

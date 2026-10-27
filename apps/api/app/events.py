from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Auction, OutboxEvent

def enqueue(db: AsyncSession, auction: Auction, action: str):
    db.add(OutboxEvent(auction_id=auction.id, version=auction.version, action=action))

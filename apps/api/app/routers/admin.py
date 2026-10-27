import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from app.db import SessionLocal
from app.events import enqueue
from app.models import User, Auction
from app.schemas import AuctionCreate, AuctionOut
from app.security import require_admin

router = APIRouter(prefix='/admin', tags=['admin'])
log = logging.getLogger(__name__)

@router.get('/auctions', response_model=list[AuctionOut])
async def list_all(user: User = Depends(require_admin)):
    async with SessionLocal() as db:
        return (await db.scalars(select(Auction).order_by(desc(Auction.created_at)).limit(100))).all()

@router.post('/auctions', response_model=AuctionOut, status_code=201)
async def create_auction(data: AuctionCreate, user: User = Depends(require_admin)):
    auction = Auction(**data.model_dump(), status='draft', version=0, bid_count=0)
    async with SessionLocal.begin() as db:
        db.add(auction)
        await db.flush()
    log.info('auction.created auction=%s by=%s', auction.id, user.id)
    return auction

@router.post('/auctions/{auction_id}/publish', response_model=AuctionOut)
async def publish(auction_id: uuid.UUID, user: User = Depends(require_admin)):
    async with SessionLocal.begin() as db:
        auction = await db.scalar(select(Auction).where(Auction.id == auction_id).with_for_update())
        if auction is None:
            raise HTTPException(404, 'Auction not found')
        if auction.status != 'draft':
            raise HTTPException(409, 'Only draft auctions can be published')
        now = await db.scalar(select(func.clock_timestamp()))
        if auction.ends_at <= now:
            raise HTTPException(409, 'Auction end time has already passed')
        auction.status = 'active' if auction.starts_at <= now else 'scheduled'
        auction.version += 1
        enqueue(db, auction, 'published')
    log.info('auction.published auction=%s by=%s', auction.id, user.id)
    return auction

@router.post('/auctions/{auction_id}/close', response_model=AuctionOut)
async def close(auction_id: uuid.UUID, user: User = Depends(require_admin)):
    async with SessionLocal.begin() as db:
        auction = await db.scalar(select(Auction).where(Auction.id == auction_id).with_for_update())
        if auction is None:
            raise HTTPException(404, 'Auction not found')
        if auction.status not in ('scheduled', 'active'):
            raise HTTPException(409, 'Only scheduled/active auctions can be closed')
        auction.status = 'closed'
        auction.winner_id = auction.highest_bidder_id
        auction.version += 1
        enqueue(db, auction, 'closed')
    log.info('auction.closed auction=%s by=%s', auction.id, user.id)
    return auction

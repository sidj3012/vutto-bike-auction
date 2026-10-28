import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.models import Auction, Bid
from app.schemas import AuctionOut, BidOut

router = APIRouter(prefix='/auctions', tags=['auctions'])

@router.get('', response_model=list[AuctionOut])
async def list_auctions(status: str | None = None, limit: int = Query(30, ge=1, le=60),
                        offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db)):
    if status and status not in ('active', 'scheduled', 'closed'):
        raise HTTPException(422, 'Invalid status filter')
    query = select(Auction).where(Auction.status != 'draft')
    if status:
        query = query.where(Auction.status == status)
    query = query.order_by(desc(Auction.created_at), desc(Auction.id)).offset(offset).limit(limit)
    return (await db.scalars(query)).all()

@router.get('/{auction_id}', response_model=AuctionOut)
async def get_auction(auction_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    auction = await db.get(Auction, auction_id)
    if auction is None or auction.status == 'draft':
        raise HTTPException(404, 'Auction not found')
    return auction

@router.get('/{auction_id}/bids', response_model=list[BidOut])
async def bid_history(auction_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    auction = await db.get(Auction, auction_id)
    if auction is None or auction.status == 'draft':
        raise HTTPException(404, 'Auction not found')
    bids = (await db.scalars(select(Bid).where(Bid.auction_id == auction_id)
                             .order_by(desc(Bid.auction_version)).limit(20))).all()
    return [BidOut(id=b.id, auction_id=b.auction_id, amount_paise=b.amount_paise,
                   created_at=b.created_at, bidder_label=f'Bidder #{str(b.bidder_id)[:6]}') for b in bids]

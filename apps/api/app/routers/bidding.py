import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from app.db import SessionLocal
from app.events import enqueue
from app.logic import minimum_next_bid, validate_bid, BidRejected
from app.models import Auction, Bid, User
from app.schemas import BidIn, BidOut
from app.security import require_user, throttle

router = APIRouter(prefix='/auctions', tags=['bidding'])

@router.post('/{auction_id}/bids', response_model=BidOut, status_code=201)
async def submit_bid(auction_id: uuid.UUID, data: BidIn, request: Request,
                     user: User = Depends(require_user)):
    await throttle(request, 'bid', limit=60)
    # Lock the auction row before checking price/time/idempotency. The DB lock,
    # not the event bus or frontend, decides which concurrent request wins.
    try:
        async with SessionLocal.begin() as db:
            auction = await db.scalar(select(Auction).where(Auction.id == auction_id).with_for_update())
            if auction is None or auction.status == 'draft':
                raise HTTPException(404, 'Auction not found')
            existing = await db.scalar(select(Bid).where(
                Bid.auction_id == auction_id, Bid.bidder_id == user.id,
                Bid.idempotency_key == data.idempotency_key))
            if existing:
                if existing.amount_paise != data.amount_paise:
                    raise HTTPException(409, 'Idempotency key already used for another amount')
                return BidOut(id=existing.id, auction_id=existing.auction_id,
                              amount_paise=existing.amount_paise, created_at=existing.created_at,
                              bidder_label=f'Bidder #{str(user.id)[:6]}')
            now = await db.scalar(select(func.clock_timestamp()))
            minimum = minimum_next_bid(auction.starting_price_paise,
                                       auction.current_price_paise, auction.min_increment_paise)
            validate_bid(status=auction.status, starts=auction.starts_at, ends=auction.ends_at,
                         now=now, amount=data.amount_paise, minimum=minimum,
                         highest_bidder_id=str(auction.highest_bidder_id) if auction.highest_bidder_id else None,
                         bidder_id=str(user.id))
            bid = Bid(auction_id=auction.id, bidder_id=user.id,
                      amount_paise=data.amount_paise, idempotency_key=data.idempotency_key)
            db.add(bid)
            auction.current_price_paise = data.amount_paise
            auction.highest_bidder_id = user.id
            auction.bid_count += 1
            auction.version += 1
            enqueue(db, auction, 'bid_accepted')
            await db.flush()
            result = BidOut(id=bid.id, auction_id=bid.auction_id, amount_paise=bid.amount_paise,
                            created_at=bid.created_at, bidder_label=f'Bidder #{str(user.id)[:6]}')
    except BidRejected as exc:
        raise HTTPException(exc.status_code, exc.message)
    return result

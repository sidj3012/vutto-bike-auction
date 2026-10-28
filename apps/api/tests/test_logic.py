from datetime import datetime, timezone, timedelta
import pytest
from app.logic import minimum_next_bid, validate_bid, BidRejected

NOW = datetime.now(timezone.utc)

def test_first_bid_starts_at_reserve():
    assert minimum_next_bid(15_000_000, None, 250_000) == 15_000_000

def test_next_bid_requires_increment():
    assert minimum_next_bid(15_000_000, 16_000_000, 250_000) == 16_250_000

@pytest.mark.parametrize('status,seconds_to_end', [('draft',300), ('scheduled',300), ('closed',300), ('active',-1)])
def test_unavailable_auction_rejects(status, seconds_to_end):
    with pytest.raises(BidRejected, match='not accepting'):
        validate_bid(status=status, starts=NOW-timedelta(hours=2), ends=NOW+timedelta(seconds=seconds_to_end),
                     now=NOW, amount=20_000_000, minimum=10_000_000,
                     highest_bidder_id=None, bidder_id='b')

def test_bid_below_minimum_rejected():
    with pytest.raises(BidRejected, match='Minimum'):
        validate_bid(status='active', starts=NOW-timedelta(seconds=1), ends=NOW+timedelta(seconds=30),
                     now=NOW, amount=109, minimum=110, highest_bidder_id=None, bidder_id='b')

def test_highest_bidder_cannot_outbid_self():
    with pytest.raises(BidRejected, match='highest'):
        validate_bid(status='active', starts=NOW-timedelta(seconds=1), ends=NOW+timedelta(seconds=30),
                     now=NOW, amount=200, minimum=110, highest_bidder_id='a', bidder_id='a')

def test_valid_auction_accepts_bid_at_exact_minimum():
    validate_bid(status='active', starts=NOW, ends=NOW+timedelta(seconds=30), now=NOW,
                 amount=110, minimum=110, highest_bidder_id=None, bidder_id='a')

def test_end_time_is_exclusive():
    with pytest.raises(BidRejected):
        validate_bid(status='active', starts=NOW-timedelta(seconds=1), ends=NOW,
                     now=NOW, amount=200, minimum=100, highest_bidder_id=None, bidder_id='a')

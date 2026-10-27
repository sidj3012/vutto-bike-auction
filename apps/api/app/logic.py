"""Pure rules shared by services and fast unit tests."""
from dataclasses import dataclass
from datetime import datetime

class BidRejected(Exception):
    def __init__(self, message: str, status_code: int = 409):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

def minimum_next_bid(starting: int, current: int | None, increment: int) -> int:
    return starting if current is None else current + increment

def validate_bid(*, status: str, starts: datetime, ends: datetime, now: datetime,
                 amount: int, minimum: int, highest_bidder_id: str | None, bidder_id: str):
    if status != 'active' or not (starts <= now < ends):
        raise BidRejected('This auction is not accepting bids')
    if highest_bidder_id == bidder_id:
        raise BidRejected('You already hold the highest bid')
    if amount < minimum:
        raise BidRejected(f'Minimum acceptable bid is {minimum} paise')

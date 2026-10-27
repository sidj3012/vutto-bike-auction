from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

class RegisterIn(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=60)
    password: str = Field(min_length=10, max_length=128)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    display_name: str
    role: str

class AuctionCreate(BaseModel):
    title: str = Field(min_length=5, max_length=140)
    brand: str = Field(min_length=2, max_length=60)
    model: str = Field(min_length=1, max_length=80)
    year: int = Field(ge=1950, le=2030)
    mileage_km: int = Field(ge=0, le=2_000_000)
    description: str = Field(min_length=15, max_length=3000)
    image_url: str | None = Field(default=None, max_length=400, pattern=r'^https://')
    starting_price_paise: int = Field(gt=0, le=10_000_000_000)
    min_increment_paise: int = Field(gt=0, le=100_000_000)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode='after')
    def valid_times(self):
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError('Timezone-aware ISO 8601 timestamps required')
        if self.ends_at <= self.starts_at:
            raise ValueError('Auction must end after starting')
        return self

class AuctionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    brand: str
    model: str
    year: int
    mileage_km: int
    description: str
    image_url: str | None
    starting_price_paise: int
    min_increment_paise: int
    current_price_paise: int | None
    bid_count: int
    version: int
    status: str
    starts_at: datetime
    ends_at: datetime
    winner_id: UUID | None

class BidIn(BaseModel):
    amount_paise: int = Field(gt=0, le=10_000_000_000)
    idempotency_key: str = Field(min_length=8, max_length=90, pattern=r'^[A-Za-z0-9_-]+$')

class BidOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    auction_id: UUID
    amount_paise: int
    created_at: datetime
    bidder_label: str

import enum
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, CheckConstraint, UniqueConstraint, Index, BigInteger, Integer, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

class Base(DeclarativeBase):
    pass

class Role(str, enum.Enum):
    BUYER = 'buyer'
    ADMIN = 'admin'

class AuctionStatus(str, enum.Enum):
    DRAFT = 'draft'
    SCHEDULED = 'scheduled'
    ACTIVE = 'active'
    CLOSED = 'closed'

class User(Base):
    __tablename__ = 'users'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(60), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=Role.BUYER.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Auction(Base):
    __tablename__ = 'auctions'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    brand: Mapped[str] = mapped_column(String(60), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    mileage_km: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(400), nullable=True)
    starting_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    min_increment_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    current_price_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    highest_bidder_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    winner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    bid_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AuctionStatus.DRAFT.value)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint('starting_price_paise > 0'),
        CheckConstraint('min_increment_paise > 0'),
        CheckConstraint('mileage_km >= 0'),
        CheckConstraint('ends_at > starts_at'),
        Index('ix_auctions_status_ends', 'status', 'ends_at'),
        Index('ix_auctions_status_starts', 'status', 'starts_at'),
    )

class Bid(Base):
    __tablename__ = 'bids'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('auctions.id', ondelete='CASCADE'), nullable=False)
    bidder_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    auction_version: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(90), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint('auction_id', 'bidder_id', 'idempotency_key', name='uq_bid_idempotency'),
        CheckConstraint('amount_paise > 0'),
        CheckConstraint('auction_version > 0'),
        UniqueConstraint('auction_id', 'auction_version', name='uq_bid_auction_version'),
        Index('ix_bids_auction_time', 'auction_id', 'created_at'),
    )

class OutboxEvent(Base):
    __tablename__ = 'outbox_events'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('auctions.id', ondelete='CASCADE'), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (Index('ix_outbox_unpublished', 'published_at', 'created_at'),)

"""Initial production schema.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('display_name', sa.String(60), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table('auctions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(140), nullable=False),
        sa.Column('brand', sa.String(60), nullable=False),
        sa.Column('model', sa.String(80), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('mileage_km', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('image_url', sa.String(400)),
        sa.Column('starting_price_paise', sa.BigInteger(), nullable=False),
        sa.Column('min_increment_paise', sa.BigInteger(), nullable=False),
        sa.Column('current_price_paise', sa.BigInteger()),
        sa.Column('highest_bidder_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('winner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('bid_count', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('starting_price_paise > 0'),
        sa.CheckConstraint('min_increment_paise > 0'),
        sa.CheckConstraint('mileage_km >= 0'),
        sa.CheckConstraint('ends_at > starts_at'))
    op.create_index('ix_auctions_status_ends', 'auctions', ['status', 'ends_at'])
    op.create_index('ix_auctions_status_starts', 'auctions', ['status', 'starts_at'])
    op.create_table('bids',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('auction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('auctions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bidder_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('amount_paise', sa.BigInteger(), nullable=False),
        sa.Column('idempotency_key', sa.String(90), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('auction_id', 'bidder_id', 'idempotency_key', name='uq_bid_idempotency'),
        sa.CheckConstraint('amount_paise > 0'))
    op.create_index('ix_bids_auction_time', 'bids', ['auction_id', 'created_at'])
    op.create_table('outbox_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('auction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('auctions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True)))
    op.create_index('ix_outbox_unpublished', 'outbox_events', ['published_at', 'created_at'])

def downgrade():
    op.drop_table('outbox_events')
    op.drop_table('bids')
    op.drop_table('auctions')
    op.drop_table('users')

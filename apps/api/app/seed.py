"""Opt-in demo setup: creates an admin and three DRAFT examples; safe to rerun."""
import asyncio
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.db import SessionLocal
from app.models import User, Auction
from app.security import hash_password

BIKES = [
    ('Royal Enfield Classic 350', 'Royal Enfield', 'Classic 350', 2022, 13200, 17500000, 250000,
     'Beautifully maintained single-owner motorcycle. Recently serviced with clean documentation.'),
    ('KTM Duke 390', 'KTM', 'Duke 390', 2023, 8400, 23000000, 500000,
     'Powerful street machine with low kilometres driven, inspected brakes and excellent tyres.'),
    ('Honda CB350 RS', 'Honda', 'CB350 RS', 2021, 18100, 15500000, 250000,
     'Retro styling, reliable engine, complete service history and original spare key.'),
]

async def main():
    email = os.environ.get('ADMIN_EMAIL')
    password = os.environ.get('ADMIN_PASSWORD')
    if not email or not password or len(password) < 12:
        raise SystemExit('Set ADMIN_EMAIL and a strong ADMIN_PASSWORD (>= 12 chars) before seeding')
    async with SessionLocal.begin() as db:
        admin = await db.scalar(select(User).where(User.email == email.lower()))
        if admin is None:
            db.add(User(email=email.lower(), display_name='Auction Administrator',
                        password_hash=hash_password(password), role='admin'))
        existing = await db.scalar(select(Auction.id).limit(1))
        if existing is None:
            now = datetime.now(timezone.utc)
            for i, (title, brand, model, year, km, price, inc, desc) in enumerate(BIKES):
                db.add(Auction(title=title, brand=brand, model=model, year=year,
                    mileage_km=km, description=desc, starting_price_paise=price,
                    min_increment_paise=inc, starts_at=now + timedelta(minutes=2+i),
                    ends_at=now + timedelta(days=2+i), status='draft', version=0, bid_count=0))
    print('Seed completed. Publish draft auctions from /admin. (Existing admin passwords are unchanged.)')

if __name__ == '__main__':
    asyncio.run(main())

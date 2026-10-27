from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import Depends, HTTPException, Request
from jwt import encode, decode, InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from app.config import settings
from app.db import get_db
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession

password_hash = PasswordHash.recommended()
COOKIE_NAME = 'motobid_session'
SESSION_AGE_SECONDS = 60 * 60 * 24 * 7

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)

def make_session(user: User) -> str:
    now = datetime.now(timezone.utc)
    return encode({'sub': str(user.id), 'iat': now, 'exp': now + timedelta(seconds=SESSION_AGE_SECONDS)},
                  settings.app_secret, algorithm='HS256')

async def get_optional_user(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        claims = decode(token, settings.app_secret, algorithms=['HS256'])
        user_id = UUID(claims['sub'])
    except (InvalidTokenError, KeyError, ValueError, TypeError):
        return None
    return await db.scalar(select(User).where(User.id == user_id))

async def require_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(401, 'Sign in to continue')
    return user

async def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != 'admin':
        raise HTTPException(403, 'Administrator access required')
    return user

async def throttle(request: Request, action: str, limit: int, window: int = 60):
    # Per-network-peer rate limit. At a trusted reverse proxy, configure trusted forwarded headers.
    ip = request.client.host if request.client else 'unknown'
    key = f'rl:{action}:{ip}'
    redis = request.app.state.redis
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window)
    if count > limit:
        raise HTTPException(status_code=429, detail='Too many requests; try again shortly',
                            headers={'Retry-After': str(window)})

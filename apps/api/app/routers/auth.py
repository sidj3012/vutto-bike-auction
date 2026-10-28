from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.db import SessionLocal
from app.models import User
from app.schemas import RegisterIn, LoginIn, UserOut
from app.security import (COOKIE_NAME, SESSION_AGE_SECONDS, hash_password, verify_password,
                          make_session, session_claims, require_user, throttle)

router = APIRouter(prefix='/auth', tags=['auth'])

async def attach_session(request: Request, response: Response, user: User):
    token, jti = make_session(user)
    await request.app.state.redis.set(f'session:{jti}', str(user.id), ex=SESSION_AGE_SECONDS)
    response.set_cookie(COOKIE_NAME, token, max_age=SESSION_AGE_SECONDS,
                        httponly=True, secure=settings.cookie_secure, samesite='lax', path='/')

@router.post('/register', response_model=UserOut, status_code=201)
async def register(data: RegisterIn, request: Request, response: Response):
    await throttle(request, 'register', limit=6, identity=data.email)
    user = User(email=data.email.lower(), display_name=data.display_name.strip(),
                password_hash=hash_password(data.password), role='buyer')
    try:
        async with SessionLocal.begin() as db:
            db.add(user)
            await db.flush()
    except IntegrityError:
        raise HTTPException(409, 'This email is already registered')
    await attach_session(request, response, user)
    return user

@router.post('/login', response_model=UserOut)
async def login(data: LoginIn, request: Request, response: Response):
    await throttle(request, 'login', limit=12, identity=data.email)
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == data.email.lower()))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, 'Invalid email or password')
    await attach_session(request, response, user)
    return user

@router.post('/logout', status_code=204)
async def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        claims = session_claims(token)
        if claims:
            await request.app.state.redis.delete(f'session:{claims[1]}')
    response.delete_cookie(COOKIE_NAME, path='/', secure=settings.cookie_secure, samesite='lax')

@router.get('/me', response_model=UserOut)
async def me(user: User = Depends(require_user)):
    return user

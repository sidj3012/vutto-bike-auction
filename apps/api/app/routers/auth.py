from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.db import SessionLocal
from app.models import User
from app.schemas import RegisterIn, LoginIn, UserOut
from app.security import (COOKIE_NAME, SESSION_AGE_SECONDS, hash_password, verify_password,
                          make_session, require_user, throttle)

router = APIRouter(prefix='/auth', tags=['auth'])

def attach_session(response: Response, user: User):
    response.set_cookie(COOKIE_NAME, make_session(user), max_age=SESSION_AGE_SECONDS,
                        httponly=True, secure=settings.cookie_secure, samesite='lax', path='/')

@router.post('/register', response_model=UserOut, status_code=201)
async def register(data: RegisterIn, request: Request, response: Response):
    await throttle(request, 'register', limit=6)
    user = User(email=data.email.lower(), display_name=data.display_name.strip(),
                password_hash=hash_password(data.password), role='buyer')
    try:
        async with SessionLocal.begin() as db:
            db.add(user)
            await db.flush()
    except IntegrityError:
        raise HTTPException(409, 'This email is already registered')
    attach_session(response, user)
    return user

@router.post('/login', response_model=UserOut)
async def login(data: LoginIn, request: Request, response: Response):
    await throttle(request, 'login', limit=12)
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == data.email.lower()))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, 'Invalid email or password')
    attach_session(response, user)
    return user

@router.post('/logout', status_code=204)
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path='/', secure=settings.cookie_secure, samesite='lax')

@router.get('/me', response_model=UserOut)
async def me(user: User = Depends(require_user)):
    return user

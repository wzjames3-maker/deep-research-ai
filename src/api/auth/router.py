from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.base import get_db
from src.models.user import User
from src.middleware.rate_limiter import RateLimit, UserRateLimit
from src.middleware.auth import get_current_user
from src.api.auth.schemas import (
    RegisterRequest, RegisterResponse,
    LoginRequest, LoginResponse,
    MeResponse, RefreshResponse, TicketResponse,
)
from src.api.auth.service import register_user, login_user, refresh_user_token
from src.utils.ticket_store import create_ticket

router = APIRouter()
register_rate_limit = RateLimit(5)
login_rate_limit = RateLimit(10)
refresh_rate_limit = UserRateLimit(30)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=201,
    dependencies=[Depends(register_rate_limit)],
)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user, token = await register_user(db, request.username, request.password)
    return RegisterResponse(
        userId=user.id,
        username=user.username,
        token=token,
        expiresIn=86400,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=200,
    dependencies=[Depends(login_rate_limit)],
)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    user, token = await login_user(db, request.username, request.password, request.rememberMe)
    return LoginResponse(
        userId=user.id,
        username=user.username,
        token=token,
        expiresIn=604800 if request.rememberMe else 86400,
    )


@router.get("/me", response_model=MeResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return MeResponse(
        userId=current_user.id,
        username=current_user.username,
        status=current_user.status,
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    dependencies=[Depends(refresh_rate_limit)],
)
async def refresh(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    token, expires_in = await refresh_user_token(db, current_user)
    return RefreshResponse(token=token, expiresIn=expires_in)


@router.post("/ticket", response_model=TicketResponse)
async def get_ticket(current_user: User = Depends(get_current_user)):
    ticket = create_ticket(current_user.id)
    return TicketResponse(ticket=ticket, expiresIn=30)

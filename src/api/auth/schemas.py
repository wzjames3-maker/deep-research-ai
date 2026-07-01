import re
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=64)

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("password")
    @classmethod
    def password_has_letter_and_digit(cls, v: str) -> str:
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("密码必须包含至少1个字母")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含至少1个数字")
        return v


class RegisterResponse(BaseModel):
    userId: UUID
    username: str
    token: str
    expiresIn: int


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)
    rememberMe: bool = Field(default=False)


class LoginResponse(BaseModel):
    userId: UUID
    username: str
    token: str
    expiresIn: int


class MeResponse(BaseModel):
    userId: UUID
    username: str
    status: str


class RefreshResponse(BaseModel):
    token: str
    expiresIn: int


class TicketResponse(BaseModel):
    ticket: str
    expiresIn: int

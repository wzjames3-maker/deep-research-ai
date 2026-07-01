from passlib.context import CryptContext
from src.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password, rounds=settings.BCRYPT_ROUNDS)


def verify_password(plain: str, hash: str) -> bool:
    return _pwd_context.verify(plain, hash)

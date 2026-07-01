import re
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import String, Boolean, Integer, DateTime, Enum, text as sa_text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from src.models.base import Base


_USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,50}$")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa_text("gen_random_uuid()"),
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "locked", name="user_status", create_type=False),
        default="active",
        server_default="active",
        nullable=False,
    )
    failed_login_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    remember_me: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=sa_text("false"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa_text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa_text("NOW()"),
        onupdate=sa_text("NOW()"),
        nullable=False,
    )

    @classmethod
    def clean_username(cls, username: str) -> str:
        return username.strip().lower()

    @classmethod
    def validate_username(cls, username: str) -> str | None:
        cleaned = cls.clean_username(username)
        if not _USERNAME_PATTERN.match(cleaned):
            return None
        return cleaned

    def increment_failed_login(self) -> None:
        self.failed_login_count += 1
        if self.failed_login_count >= 5:
            self.status = "locked"
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

    def reset_failed_login(self) -> None:
        self.failed_login_count = 0
        self.locked_until = None
        self.status = "active"

    def check_and_auto_unlock(self) -> bool:
        if self.status != "locked":
            return False
        if self.locked_until is None or self.locked_until <= datetime.now(timezone.utc):
            self.reset_failed_login()
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "username": self.username,
            "status": self.status,
            "failed_login_count": self.failed_login_count,
            "locked_until": self.locked_until.isoformat() if self.locked_until else None,
            "remember_me": self.remember_me,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

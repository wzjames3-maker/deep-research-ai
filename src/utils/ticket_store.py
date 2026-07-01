import time
from uuid import UUID, uuid4

MAX_TICKETS_PER_USER = 3

_store: dict[str, tuple[UUID, float]] = {}


def _cleanup_expired() -> None:
    """Lazy cleanup: remove all expired tickets."""
    now = time.time()
    stale = [t for t, (_, exp) in _store.items() if now > exp]
    for t in stale:
        _store.pop(t, None)


def _enforce_user_limit(user_id: UUID) -> None:
    """Ensure user has at most MAX_TICKETS_PER_USER valid tickets."""
    now = time.time()
    user_tickets = [
        (t, exp) for t, (uid, exp) in _store.items()
        if uid == user_id and now <= exp
    ]
    if len(user_tickets) >= MAX_TICKETS_PER_USER:
        # Sort by expiry (earliest first) and remove oldest
        user_tickets.sort(key=lambda x: x[1])
        to_remove = len(user_tickets) - MAX_TICKETS_PER_USER + 1
        for t, _ in user_tickets[:to_remove]:
            _store.pop(t, None)


def create_ticket(user_id: UUID) -> str:
    _cleanup_expired()
    _enforce_user_limit(user_id)
    ticket = str(uuid4())
    _store[ticket] = (user_id, time.time() + 30)
    return ticket


def verify_ticket(ticket: str) -> UUID | None:
    _cleanup_expired()
    entry = _store.pop(ticket, None)
    if entry is None:
        return None
    user_id, expires_at = entry
    if time.time() > expires_at:
        return None
    return user_id


def cleanup_expired_tickets() -> None:
    _cleanup_expired()

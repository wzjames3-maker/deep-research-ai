import time
import pytest
from uuid import uuid4
from src.utils.bcrypt import hash_password, verify_password
from src.utils.jwt import create_token, verify_token, decode_token
from src.utils.ticket_store import create_ticket, verify_ticket, cleanup_expired_tickets, _store
from src.errors import TokenInvalidError


class TestBcrypt:
    def test_hash_starts_with_bcrypt(self):
        h = hash_password("MyPass123")
        assert h.startswith("$2b$12$") or h.startswith("$2a$12$")

    def test_verify_correct_password(self):
        h = hash_password("MyPass123")
        assert verify_password("MyPass123", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("MyPass123")
        assert verify_password("wrong", h) is False

    def test_different_passwords_different_hashes(self):
        h1 = hash_password("Pass1")
        h2 = hash_password("Pass2")
        assert h1 != h2


class TestJwt:
    def test_create_token_returns_three_segments(self):
        token = create_token(uuid4(), "test")
        parts = token.split(".")
        assert len(parts) == 3

    def test_verify_token_returns_payload(self):
        user_id = uuid4()
        token = create_token(user_id, "testuser")
        payload = verify_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["username"] == "testuser"
        assert "iat" in payload
        assert "exp" in payload

    def test_verify_expired_token_raises(self):
        user_id = uuid4()
        token = create_token(user_id, "test", expires_delta=-3600)
        with pytest.raises(TokenInvalidError):
            verify_token(token)

    def test_decode_token_no_exp_check(self):
        user_id = uuid4()
        token = create_token(user_id, "test", expires_delta=-3600)
        payload = decode_token(token)
        assert payload["sub"] == str(user_id)

    def test_token_expires_in_24h(self):
        user_id = uuid4()
        token = create_token(user_id, "test")
        payload = verify_token(token)
        assert payload["exp"] - payload["iat"] == 86400

    def test_remember_me_token_7d(self):
        user_id = uuid4()
        token = create_token(user_id, "test", expires_delta=604800)
        payload = verify_token(token)
        assert payload["exp"] - payload["iat"] == 604800

    def test_invalid_token_raises(self):
        with pytest.raises(TokenInvalidError):
            verify_token("not.a.valid.token")

    def test_username_lowercase_in_payload(self):
        user_id = uuid4()
        token = create_token(user_id, "TEST_USER")
        payload = verify_token(token)
        assert payload["username"] == "TEST_USER"


class TestTicketStore:
    def test_create_ticket_returns_uuid(self):
        ticket = create_ticket(uuid4())
        parts = ticket.split("-")
        assert len(parts) == 5

    def test_verify_valid_ticket(self):
        user_id = uuid4()
        ticket = create_ticket(user_id)
        result = verify_ticket(ticket)
        assert result == user_id

    def test_verify_expired_ticket(self):
        user_id = uuid4()
        ticket = create_ticket(user_id)
        uid, exp = _store[ticket]
        _store[ticket] = (uid, time.time() - 10)

        result = verify_ticket(ticket)
        assert result is None

    def test_verify_invalid_ticket(self):
        assert verify_ticket("invalid-uuid-ticket") is None

    def test_ticket_consumed_once(self):
        user_id = uuid4()
        ticket = create_ticket(user_id)
        assert verify_ticket(ticket) == user_id
        assert verify_ticket(ticket) is None

    def test_cleanup_expired(self):
        user_id = uuid4()
        ticket = create_ticket(user_id)
        uid, exp = _store[ticket]
        _store[ticket] = (uid, time.time() - 10)
        cleanup_expired_tickets()
        assert ticket not in _store

    def test_max_3_tickets_per_user(self):
        """RULE-AUTH-008: 同一用户最多同时持有 3 个有效 ticket"""
        user_id = uuid4()
        t1 = create_ticket(user_id)
        t2 = create_ticket(user_id)
        t3 = create_ticket(user_id)

        # All 3 should be valid
        assert t1 in _store
        assert t2 in _store
        assert t3 in _store

        # Creating 4th ticket should evict the oldest
        t4 = create_ticket(user_id)
        user_tickets = [t for t, (uid, _) in _store.items() if uid == user_id]
        assert len(user_tickets) <= 3
        assert t4 in _store

    def test_verify_cleans_up_expired(self):
        """RULE-AUTH-008: 惰性清理 — verify 时顺便清除过期条目"""
        user_id = uuid4()
        # Create ticket and manually expire it
        expired_ticket = create_ticket(user_id)
        uid, _ = _store[expired_ticket]
        _store[expired_ticket] = (uid, time.time() - 10)

        # Create a valid ticket for another user
        other_id = uuid4()
        valid_ticket = create_ticket(other_id)

        # Verify the valid ticket triggers lazy cleanup
        result = verify_ticket(valid_ticket)
        assert result == other_id
        # Expired ticket should have been cleaned up
        assert expired_ticket not in _store

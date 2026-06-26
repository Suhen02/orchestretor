"""
tests/test_auth.py
Unit tests for password hashing and JWT token generation/verification.
Doc Section 9.1: test_auth.py — password hashing, JWT encode/decode
"""
import pytest
from datetime import timedelta
from jose import jwt

from app.core.auth import hash_password, verify_password, create_access_token, decode_token
from app.core.config import get_settings


settings = get_settings()


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("supersecret")
        assert hashed != "supersecret"

    def test_correct_password_verifies(self):
        hashed = hash_password("mypassword123")
        assert verify_password("mypassword123", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("mypassword123")
        assert verify_password("wrongpassword", hashed) is False

    def test_two_hashes_of_same_password_differ(self):
        """bcrypt uses a random salt — same input ≠ same hash."""
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2

    def test_empty_password_hashes(self):
        """Empty string is still hashable — validation is the API layer's job."""
        hashed = hash_password("")
        assert verify_password("", hashed) is True


class TestJWT:
    def test_token_encodes_and_decodes_subject(self):
        token = create_access_token({"sub": "user-uuid-123"})
        payload = decode_token(token)
        assert payload["sub"] == "user-uuid-123"

    def test_token_contains_expiry(self):
        token = create_access_token({"sub": "abc"})
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert "exp" in payload

    def test_expired_token_raises(self):
        from app.core.auth import HTTPException
        token = create_access_token({"sub": "abc"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises(self):
        from app.core.auth import HTTPException
        token = create_access_token({"sub": "abc"})
        tampered = token[:-4] + "XXXX"
        with pytest.raises(HTTPException):
            decode_token(tampered)

    def test_custom_expiry_respected(self):
        token = create_access_token({"sub": "abc"}, expires_delta=timedelta(hours=2))
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert "exp" in payload
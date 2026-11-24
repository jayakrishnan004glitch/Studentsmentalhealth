"""Unit tests for token verification (no database needed)."""

import time
import uuid
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.security import InvalidTokenError, TokenVerifier
from tests.conftest import ISSUER, JWT_SECRET, make_token

pytestmark = []  # plain sync tests


def hs_verifier() -> TokenVerifier:
    return TokenVerifier(issuer=ISSUER, audience="authenticated", hs256_secret=JWT_SECRET)


def test_valid_hs256_token() -> None:
    uid = uuid.uuid4()
    claims = hs_verifier().verify(make_token(uid))
    assert claims.user_id == uid
    assert claims.email == "student@example.edu"


@pytest.mark.parametrize(
    "token_kwargs",
    [
        {"expires_in": -60},
        {"audience": "anon"},
        {"issuer": "http://evil.test/auth/v1"},
        {"secret": "another-secret-that-is-also-32-bytes-long!!"},
    ],
    ids=["expired", "wrong-audience", "wrong-issuer", "bad-signature"],
)
def test_rejected_tokens(token_kwargs: dict) -> None:
    with pytest.raises(InvalidTokenError):
        hs_verifier().verify(make_token(uuid.uuid4(), **token_kwargs))


def test_garbage_and_non_uuid_subject() -> None:
    with pytest.raises(InvalidTokenError):
        hs_verifier().verify("not-a-jwt")
    with pytest.raises(InvalidTokenError):
        hs_verifier().verify(make_token("not-a-uuid"))


def test_alg_none_is_rejected() -> None:
    now = int(time.time())
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "iss": ISSUER, "exp": now + 60},
        key=None,
        algorithm="none",
    )
    with pytest.raises(InvalidTokenError):
        hs_verifier().verify(token)


def _es256_token(private_key, sub: uuid.UUID) -> str:
    now = int(time.time())
    payload = {"sub": str(sub), "aud": "authenticated", "iss": ISSUER, "exp": now + 60}
    return jwt.encode(payload, private_key, algorithm="ES256", headers={"kid": "k1"})


class FakeJwks:
    """Stands in for PyJWKClient, which would fetch keys from Supabase."""

    def __init__(self, public_key) -> None:
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token: str):
        return SimpleNamespace(key=self._public_key)


def test_es256_token_via_jwks() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    verifier = TokenVerifier(
        issuer=ISSUER, audience="authenticated", jwks_client=FakeJwks(key.public_key())
    )
    uid = uuid.uuid4()
    assert verifier.verify(_es256_token(key, uid)).user_id == uid

    other = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(InvalidTokenError):
        verifier.verify(_es256_token(other, uid))


def test_hs256_token_rejected_when_only_jwks_configured() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    verifier = TokenVerifier(
        issuer=ISSUER, audience="authenticated", jwks_client=FakeJwks(key.public_key())
    )
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(uuid.uuid4()))

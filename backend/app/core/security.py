"""Verification of Supabase Auth access tokens (JWTs).

Supabase signs access tokens either with the project's asymmetric keys
(ES256/RS256, public keys published at the JWKS URL) or, on older projects,
with a shared HS256 secret. Both are supported; asymmetric is preferred.
"""

from dataclasses import dataclass
from uuid import UUID

import jwt
from jwt import PyJWKClient

ASYMMETRIC_ALGORITHMS = ["ES256", "RS256", "EdDSA"]


class InvalidTokenError(Exception):
    """The token is missing, malformed, expired or not issued for this app."""


@dataclass(frozen=True)
class TokenClaims:
    user_id: UUID
    email: str | None
    raw: dict


class TokenVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        hs256_secret: str = "",
        jwks_client: PyJWKClient | None = None,
    ) -> None:
        if not hs256_secret and jwks_client is None:
            raise ValueError("Provide either an HS256 secret or a JWKS client")
        self._issuer = issuer
        self._audience = audience
        self._secret = hs256_secret
        self._jwks = jwks_client

    def verify(self, token: str) -> TokenClaims:
        try:
            header = jwt.get_unverified_header(token)
            alg = header.get("alg")
            if alg == "HS256" and self._secret:
                key: object = self._secret
                algorithms = ["HS256"]
            elif alg in ASYMMETRIC_ALGORITHMS and self._jwks is not None:
                key = self._jwks.get_signing_key_from_jwt(token).key
                algorithms = ASYMMETRIC_ALGORITHMS
            else:
                raise InvalidTokenError(f"Unsupported signing algorithm: {alg}")

            payload = jwt.decode(
                token,
                key=key,
                algorithms=algorithms,
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "sub", "aud", "iss"]},
                leeway=10,
            )
            return TokenClaims(
                user_id=UUID(payload["sub"]), email=payload.get("email"), raw=payload
            )
        except InvalidTokenError:
            raise
        except (jwt.PyJWTError, ValueError, KeyError) as exc:
            raise InvalidTokenError(str(exc)) from exc

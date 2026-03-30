"""OOB Consent Tokens — application-layer consent management.

Commandment 6: OOB consent token is authored by the application layer.
Delegates cannot forge consent. Tokens are written by native code
outside the LLM context.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field


# Secret key for HMAC signing — in production this would be from env/config
_CONSENT_SECRET = secrets.token_bytes(32)


@dataclass
class ConsentToken:
    """A signed consent token with scope and expiry."""
    token_id: str
    scope: str
    granted_at_exchange: int
    ttl_exchanges: int
    signature: str
    revoked: bool = False

    @property
    def expires_at_exchange(self) -> int:
        return self.granted_at_exchange + self.ttl_exchanges


class ConsentManager:
    """Out-of-Band consent token manager.

    Tokens are authored by the application layer (native code),
    NEVER by an LLM delegate. Validates via HMAC signature + TTL.
    """

    def __init__(self, secret: bytes = _CONSENT_SECRET) -> None:
        self._secret = secret
        self._tokens: dict[str, ConsentToken] = {}

    def grant_consent(self, scope: str, current_exchange: int,
                      ttl_exchanges: int = 10) -> str:
        """Generate a signed consent token. Called by native app only."""
        token_id = secrets.token_hex(8)
        payload = f"{token_id}:{scope}:{current_exchange}:{ttl_exchanges}"
        signature = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()

        token = ConsentToken(
            token_id=token_id,
            scope=scope,
            granted_at_exchange=current_exchange,
            ttl_exchanges=ttl_exchanges,
            signature=signature,
        )
        self._tokens[token_id] = token
        return token_id

    def validate(self, token_id: str, current_exchange: int) -> bool:
        """Check token validity: exists, not revoked, signature valid, TTL not expired."""
        token = self._tokens.get(token_id)
        if token is None:
            return False

        if token.revoked:
            return False

        if current_exchange > token.expires_at_exchange:
            return False

        # Verify signature
        payload = f"{token.token_id}:{token.scope}:{token.granted_at_exchange}:{token.ttl_exchanges}"
        expected = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(token.signature, expected)

    def revoke(self, token_id: str) -> None:
        """Immediately invalidate a consent token."""
        token = self._tokens.get(token_id)
        if token:
            token.revoked = True

    def has_valid_consent(self, scope: str, current_exchange: int) -> bool:
        """Check if any valid consent exists for the given scope."""
        return any(
            self.validate(tid, current_exchange) and t.scope == scope
            for tid, t in self._tokens.items()
        )

"""Webhook signature verification.

GitHub signs every webhook body with the shared secret and sends the result in the
X-Hub-Signature-256 header. Anyone can send a request to /webhook, so this check is what proves
a request really came from GitHub.
"""

import hashlib
import hmac


def verify_signature(secret: str, body: bytes, header: str | None) -> bool:
    """Return True only if header is the correct signature of body.

    Compute it over the raw request bytes, before any JSON parsing. A parsed and re-encoded body
    can differ from what GitHub signed.
    """

    if not header or not header.startswith("sha256="):
        return False

    expected_signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header.encode(), expected_signature.encode())

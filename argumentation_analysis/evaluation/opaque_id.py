"""Deterministic opaque ID generation for privacy-safe references.

Produces stable, non-reversible identifiers from sensitive source names.
Same (name, salt) always yields the same 8-char hex prefix of sha256.
"""

import hashlib
import os

_DEFAULT_SALT = "epita-arg-analysis-2025"


def opaque_id(source_name: str, salt: str | None = None) -> str:
    """Return a deterministic 8-char opaque ID from a source name.

    Args:
        source_name: The sensitive identifier to obfuscate.
        salt: Optional salt. Falls back to ``OPAQUE_ID_SALT`` env var,
              then to a documented default.

    Returns:
        First 8 hex characters of ``sha256(salt + name)``.
    """
    effective_salt = salt or os.getenv("OPAQUE_ID_SALT", _DEFAULT_SALT)
    digest = hashlib.sha256(f"{effective_salt}{source_name}".encode()).hexdigest()
    return digest[:8]

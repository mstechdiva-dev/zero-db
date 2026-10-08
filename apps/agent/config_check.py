"""Which required settings are missing or invalid. Names only, never values."""

import base64
import os

REQUIRED = [
    "NEXT_PUBLIC_SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "ANTHROPIC_API_KEY",
    "ENCRYPTION_KEY",
]


def problems() -> list[str]:
    found = [name for name in REQUIRED if not os.environ.get(name)]
    key = os.environ.get("ENCRYPTION_KEY")
    if key:
        try:
            ok = len(base64.b64decode(key)) == 32
        except Exception:
            ok = False
        if not ok:
            found.append("ENCRYPTION_KEY (must be base64 for exactly 32 bytes)")
    return found

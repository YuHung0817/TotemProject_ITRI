import sys
from typing import Any


def safe_print(*values: Any, **kwargs: Any) -> None:
    """Print debug output without crashing on a limited Windows console encoding."""
    encoding = sys.stdout.encoding or "utf-8"
    safe_values = [
        str(value).encode(encoding, errors="backslashreplace").decode(encoding) for value in values
    ]
    print(*safe_values, **kwargs)

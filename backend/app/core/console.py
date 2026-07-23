import json
import sys
from typing import Any


def safe_print(*values: Any, **kwargs: Any) -> None:
    """Print debug output without crashing on a limited Windows console encoding."""
    encoding = sys.stdout.encoding or "utf-8"
    safe_values = [
        str(value).encode(encoding, errors="backslashreplace").decode(encoding) for value in values
    ]
    print(*safe_values, **kwargs)


def log_event(event: str, **fields: str | int | float | bool | None) -> None:
    """Write one structured event containing only explicitly selected summary fields."""
    safe_print(
        json.dumps(
            {"event": event, **fields},
            ensure_ascii=True,
            separators=(",", ":"),
        )
    )

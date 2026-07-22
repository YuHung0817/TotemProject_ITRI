from __future__ import annotations

from io import BytesIO
from pathlib import Path
import uuid

from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings

ALLOWED_IMAGE_FORMATS = {"PNG": ("image/png", ".png"), "JPEG": ("image/jpeg", ".jpg"), "WEBP": ("image/webp", ".webp")}
PUBLIC_IMAGE_PREFIX = "/generated/images"
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def storage_root() -> Path:
    configured = Path(get_settings().image_storage_root).expanduser()
    root = (configured if configured.is_absolute() else PROJECT_ROOT / configured).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def image_path(storage_key: str) -> Path:
    key = Path(storage_key)
    if key.name != storage_key or storage_key in {"", ".", ".."}:
        raise ValueError("Invalid image storage key")
    path = (storage_root() / key.name).resolve()
    if path.parent != storage_root():
        raise ValueError("Image path escapes the storage root")
    return path


def image_url(storage_key: str) -> str:
    return f"{PUBLIC_IMAGE_PREFIX}/{Path(storage_key).name}"


def _validated_image(data: bytes) -> tuple[str, str, tuple[int, int]]:
    settings = get_settings()
    if not data or len(data) > settings.image_max_bytes:
        raise ValueError(f"Image must be between 1 and {settings.image_max_bytes} bytes")
    try:
        with Image.open(BytesIO(data)) as source:
            image_format = (source.format or "").upper()
            if image_format not in ALLOWED_IMAGE_FORMATS:
                raise ValueError(f"Unsupported image format: {image_format or 'unknown'}")
            width, height = source.size
            if width < 1 or height < 1:
                raise ValueError("Image dimensions must be positive")
            if width > settings.image_max_dimension or height > settings.image_max_dimension:
                raise ValueError("Image dimensions exceed the configured limit")
            if width * height > settings.image_max_pixels:
                raise ValueError("Image pixel count exceeds the configured limit")
            source.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Invalid or corrupted image data") from exc
    mime_type, extension = ALLOWED_IMAGE_FORMATS[image_format]
    return mime_type, extension, (width, height)


def store_image_bytes(data: bytes, *, label: str | None = None) -> str:
    _, extension, _ = _validated_image(data)
    safe_label = f"_{label}" if label and label.replace("_", "").isalnum() else ""
    storage_key = f"{uuid.uuid4().hex}{safe_label}{extension}"
    destination = image_path(storage_key)
    temporary = image_path(f"{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(data)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return storage_key


def store_pillow_image(image: Image.Image, *, label: str | None = None) -> str:
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return store_image_bytes(output.getvalue(), label=label)


def delete_image(storage_key: str) -> None:
    image_path(storage_key).unlink(missing_ok=True)


def image_metadata(storage_key: str) -> tuple[str, int, int, int]:
    path = image_path(storage_key)
    data = path.read_bytes()
    mime_type, _, (width, height) = _validated_image(data)
    return mime_type, len(data), width, height

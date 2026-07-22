from io import BytesIO
from pathlib import Path

from PIL import Image
import pytest

from app.core.config import get_settings
from app.services.storage_service import image_metadata, image_path, store_image_bytes


def png_bytes(size: tuple[int, int] = (4, 3)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, "white").save(output, format="PNG")
    return output.getvalue()


def test_store_validates_and_uses_uuid_filename(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "image_storage_root", str(tmp_path))

    key = store_image_bytes(png_bytes(), label="preview")

    assert key.endswith("_preview.png")
    assert len(key.split("_", 1)[0]) == 32
    assert image_path(key).is_file()
    assert image_metadata(key) == ("image/png", len(png_bytes()), 4, 3)


def test_storage_key_cannot_escape_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "image_storage_root", str(tmp_path))

    with pytest.raises(ValueError, match="Invalid image storage key"):
        image_path("../outside.png")


def test_rejects_corrupt_and_oversized_images(tmp_path, monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "image_storage_root", str(tmp_path))

    with pytest.raises(ValueError, match="Invalid or corrupted image data"):
        store_image_bytes(b"not an image")

    monkeypatch.setattr(settings, "image_max_bytes", 10)
    with pytest.raises(ValueError, match="Image must be between"):
        store_image_bytes(png_bytes())

    assert list(Path(tmp_path).iterdir()) == []

import base64
from io import BytesIO

from PIL import Image

from app.prompts.options import PALETTE_COLORS
from app.schemas.image import GenerateRequest
from app.services import image_generation


class FakeImages:
    def __init__(self, encoded_image: str) -> None:
        self.encoded_image = encoded_image
        self.calls = 0

    def generate(self, **_kwargs):
        self.calls += 1
        data = type("ImageData", (), {"b64_json": self.encoded_image, "revised_prompt": None})()
        return type("ImageResponse", (), {"data": [data]})()


class FakeClient:
    def __init__(self, encoded_image: str) -> None:
        self.images = FakeImages(encoded_image)


def test_one_ai_image_becomes_four_pillow_palette_variants(monkeypatch) -> None:
    source = Image.new("RGB", (12, 4), (255, 255, 255))
    buffer = BytesIO()
    source.save(buffer, format="PNG")
    client = FakeClient(base64.b64encode(buffer.getvalue()).decode())
    selected_palettes = list(PALETTE_COLORS)[:4]
    recolored_with: list[list[tuple[int, int, int]]] = []

    monkeypatch.setattr(image_generation, "build_generation_prompt", lambda *_args: "compiled prompt")
    monkeypatch.setattr(image_generation.random, "sample", lambda _items, k: selected_palettes[:k])
    monkeypatch.setattr(image_generation, "crop_horizontal_background_margin", lambda image: image)
    monkeypatch.setattr(image_generation, "extract_dominant_palette", lambda *_args, **_kwargs: [(255, 255, 255)])
    monkeypatch.setattr(
        image_generation,
        "recolor_flat_motif",
        lambda image, _source_palette, target_palette: (
            recolored_with.append(list(target_palette)) or image.copy()
        ),
    )
    monkeypatch.setattr(
        image_generation,
        "save_source_image",
        lambda _image, image_id, crop_margin=False: (f"{image_id}.png", f"{image_id}-original.png"),
    )

    request = GenerateRequest(prompt="山林圖騰", elements=["山豬", "月亮"])
    records = image_generation.generate_random_palette_variants(client, request)

    assert client.images.calls == 1
    assert len(records) == 4
    assert recolored_with == [list(PALETTE_COLORS[name]) for name in selected_palettes]
    assert all(record["request"] == request.model_dump() for record in records)
    assert all(record["generation"]["user_prompt"] == "山林圖騰" for record in records)
    assert all(record["generation"]["elements"] == ["山豬", "月亮"] for record in records)

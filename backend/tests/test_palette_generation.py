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
        self.kwargs = {}

    def generate(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        data = [
            type("ImageData", (), {"b64_json": self.encoded_image, "revised_prompt": None})()
            for _ in range(kwargs["n"])
        ]
        return type("ImageResponse", (), {"data": data})()


class FakeClient:
    def __init__(self, encoded_image: str) -> None:
        self.images = FakeImages(encoded_image)


def test_image_api_generates_four_prompt_colored_variants_and_records_palettes(monkeypatch) -> None:
    source = Image.new("RGB", (12, 4), (255, 255, 255))
    buffer = BytesIO()
    source.save(buffer, format="PNG")
    client = FakeClient(base64.b64encode(buffer.getvalue()).decode())
    selected_palette = next(iter(PALETTE_COLORS))
    recolored_with: list[list[tuple[int, int, int]]] = []

    monkeypatch.setattr(image_generation, "build_generation_prompt", lambda *_args: "compiled prompt")
    monkeypatch.setattr(image_generation.random, "choice", lambda _items: selected_palette)
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
    assert client.images.kwargs["n"] == 4
    assert len(records) == 4
    assert [record["palette_name"] for record in records] == [selected_palette] * 4
    assert recolored_with == [list(PALETTE_COLORS[selected_palette])] * 4
    assert all(record["palette"]["colors"] == [{"rgb": [255, 255, 255]}] for record in records)
    assert f"Palette name: {selected_palette!r}" in client.images.kwargs["prompt"]
    for color in PALETTE_COLORS[selected_palette]:
        assert f"rgb{tuple(color)}" in client.images.kwargs["prompt"]
    assert all(record["request"] == request.model_dump() for record in records)
    assert all(record["generation"]["user_prompt"] == "山林圖騰" for record in records)
    assert all(record["generation"]["elements"] == ["山豬", "月亮"] for record in records)


def test_one_user_color_adds_white_and_skips_random_palette(monkeypatch) -> None:
    source = Image.new("RGB", (12, 4), (255, 255, 255))
    buffer = BytesIO()
    source.save(buffer, format="PNG")
    client = FakeClient(base64.b64encode(buffer.getvalue()).decode())
    recolored_with: list[list[tuple[int, int, int]]] = []

    monkeypatch.setattr(image_generation, "build_generation_prompt", lambda *_args: "compiled prompt")
    monkeypatch.setattr(
        image_generation.random,
        "choice",
        lambda _items: (_ for _ in ()).throw(AssertionError("random palette should not be used")),
    )
    monkeypatch.setattr(image_generation, "crop_horizontal_background_margin", lambda image: image)
    monkeypatch.setattr(
        image_generation,
        "extract_dominant_palette",
        lambda *_args, **_kwargs: [(255, 255, 255), (205, 47, 42)],
    )
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

    request = GenerateRequest(
        prompt="守護",
        elements=["山豬"],
        colors=[{"name": "紅色", "rgb": [205, 47, 42]}],
    )
    records = image_generation.generate_random_palette_variants(client, request)

    assert recolored_with == [[(255, 255, 255), (205, 47, 42)]] * 4
    assert all(record["palette_name"] == "自訂：紅色" for record in records)
    assert "rgb(255, 255, 255)" in client.images.kwargs["prompt"]
    assert "rgb(205, 47, 42)" in client.images.kwargs["prompt"]

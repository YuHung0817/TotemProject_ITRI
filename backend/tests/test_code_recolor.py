import base64
from io import BytesIO

from PIL import Image

from app.core.config import get_settings
from app.services import image_generation


def test_all_palette_colors_to_one_target_falls_back_to_image_edit(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(get_settings(), "image_storage_root", str(tmp_path))
    source = Image.new("RGB", (3, 1))
    source.putdata([(232, 185, 45), (35, 76, 125), (244, 239, 226)])
    source.save(tmp_path / "old_original.png")

    edited = Image.new("RGB", (3, 1))
    edited.putdata([(0, 0, 0), (0, 0, 0), (244, 239, 226)])
    buffer = BytesIO()
    edited.save(buffer, format="PNG")
    client = AllToBlackClient(base64.b64encode(buffer.getvalue()).decode())
    old = {
        "original_filename": "old_original.png",
        "palette_name": "original",
        "prompt": "original",
        "request": {"prompt": "diamond motif", "elements": ["bird"]},
    }

    record = image_generation.recolor_existing_variant(old, "黑色", client)

    assert record["_used_image_api"] is True
    assert len(client.images.calls) == 1
    result = Image.open(tmp_path / record["original_filename"]).convert("RGB")
    assert len(set(result.getdata())) == 2


def test_meaningful_color_count_rejects_antialiasing_noise() -> None:
    almost_black = Image.new("RGB", (200, 1), (0, 0, 0))
    almost_black.putpixel((0, 0), (2, 2, 2))
    two_color = Image.new("RGB", (200, 1), (0, 0, 0))
    for x in range(20):
        two_color.putpixel((x, 0), (244, 239, 226))

    assert image_generation.meaningful_color_count(almost_black) == 1
    assert image_generation.meaningful_color_count(two_color) == 2


class FakeResponses:
    def create(self, **_kwargs):
        return type(
            "Response",
            (),
            {
                "output_text": '{"confidence":0.98,"replacements":[{"source_rgb":[181,43,38],"target_rgb":[40,110,65],"source_name":"紅色","target_name":"綠色"}]}'
            },
        )()


class FakeClient:
    responses = FakeResponses()


class LowConfidenceResponses:
    def create(self, **_kwargs):
        return type(
            "Response",
            (),
            {
                "output_text": '{"confidence":0.90,"replacements":[{"source_rgb":[181,43,38],"target_rgb":[40,110,65],"source_name":"紅色","target_name":"綠色"}]}'
            },
        )()


class FakeImageEdits:
    def __init__(self, encoded_image: str) -> None:
        self.encoded_image = encoded_image
        self.calls: list[dict] = []

    def edit(self, **kwargs):
        self.calls.append(kwargs)
        data = type(
            "ImageData",
            (),
            {"b64_json": self.encoded_image, "revised_prompt": None},
        )()
        return type("ImageResponse", (), {"data": [data]})()


class LowConfidenceClient:
    responses = LowConfidenceResponses()

    def __init__(self, encoded_image: str) -> None:
        self.images = FakeImageEdits(encoded_image)


class LocalizedEditClient:
    responses = FakeResponses()

    def __init__(self, encoded_image: str) -> None:
        self.images = FakeImageEdits(encoded_image)


class AllToBlackResponses:
    def create(self, **_kwargs):
        return type(
            "Response",
            (),
            {
                "output_text": (
                    '{"confidence":0.95,"replacements":['
                    '{"source_rgb":[232,185,45],"target_rgb":[0,0,0],"source_name":"yellow","target_name":"black"},'
                    '{"source_rgb":[35,76,125],"target_rgb":[0,0,0],"source_name":"blue","target_name":"black"},'
                    '{"source_rgb":[244,239,226],"target_rgb":[0,0,0],"source_name":"white","target_name":"black"}'
                    ']}'
                )
            },
        )()


class AllToBlackClient:
    responses = AllToBlackResponses()

    def __init__(self, encoded_image: str) -> None:
        self.images = FakeImageEdits(encoded_image)


def test_named_color_replacement_uses_code_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "image_storage_root", str(tmp_path))
    source = Image.new("RGB", (2, 1))
    source.putdata([(181, 43, 38), (21, 21, 21)])
    source.save(tmp_path / "old_original.png")
    old = {
        "original_filename": "old_original.png",
        "palette_name": "原配色",
        "prompt": "original",
        "request": {"prompt": "守護", "elements": ["月亮"]},
    }

    record = image_generation.recolor_existing_variant(old, "把紅色換成綠色")
    result = Image.open(tmp_path / record["original_filename"]).convert("RGB")

    assert list(result.getdata()) == [(40, 110, 65), (21, 21, 21)]
    assert record["palette_name"] == "紅色→綠色"
    assert record["files"]["original"] == record["original_filename"]
    assert record["generation"]["user_prompt"] == "守護"
    assert record["palette"]["colors"]
    assert "preview" not in record


def test_gai_recolor_replaces_multiple_shades_of_the_same_hue(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "image_storage_root", str(tmp_path))
    source = Image.new("RGB", (3, 1))
    source.putdata([(181, 43, 38), (151, 0, 0), (21, 21, 21)])
    source.save(tmp_path / "old_original.png")
    old = {
        "original_filename": "old_original.png",
        "palette_name": "原配色",
        "prompt": "original",
        "request": {"prompt": "守護", "elements": []},
    }

    record = image_generation.recolor_existing_variant(old, "把紅色換成綠色", FakeClient())
    result = Image.open(tmp_path / record["original_filename"]).convert("RGB")

    assert list(result.getdata()) == [(40, 110, 65), (40, 110, 65), (21, 21, 21)]
    assert all(color["rgb"] != [151, 0, 0] for color in record["palette"]["colors"])


def test_actual_record_palette_is_used_even_when_name_is_not_a_preset() -> None:
    record = {
        "palette_name": "紅色→綠色",
        "palette": {
            "colors": [
                {"rgb": [244, 239, 226]},
                {"rgb": [40, 110, 65]},
                {"rgb": [21, 21, 21]},
            ]
        },
    }

    colors = image_generation.record_palette_colors(record)

    assert colors == [(244, 239, 226), (40, 110, 65), (21, 21, 21)]
    assert "rgb(40, 110, 65)" in image_generation.palette_instruction_from_colors(colors)


def test_low_confidence_recolor_falls_back_to_image_edit(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "image_storage_root", str(tmp_path))
    source = Image.new("RGB", (4, 2), (181, 43, 38))
    source.save(tmp_path / "old_original.png")
    edited = Image.new("RGB", (4, 2), (40, 110, 65))
    buffer = BytesIO()
    edited.save(buffer, format="PNG")
    client = LowConfidenceClient(base64.b64encode(buffer.getvalue()).decode())
    old = {
        "original_filename": "old_original.png",
        "palette_name": "原配色",
        "prompt": "original",
        "request": {"prompt": "守護", "elements": ["山豬"]},
    }

    record = image_generation.recolor_existing_variant(old, "更換山豬的顏色", client)

    assert record["_used_image_api"] is True
    assert record["palette_name"] == "AI 判斷換色"
    assert len(client.images.calls) == 1
    call = client.images.calls[0]
    assert call["model"] == get_settings().openai_image_model
    assert "更換山豬的顏色" in call["prompt"]
    assert "COLOR-ONLY" in call["prompt"]
    result = Image.open(tmp_path / record["original_filename"]).convert("RGB")
    assert list(result.getdata()) == [(40, 110, 65)] * 8


def test_localized_border_recolor_uses_image_edit_even_with_high_confidence(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(get_settings(), "image_storage_root", str(tmp_path))
    source = Image.new("RGB", (4, 2), (21, 21, 21))
    source.save(tmp_path / "old_original.png")
    buffer = BytesIO()
    Image.new("RGB", (4, 2), (181, 43, 38)).save(buffer, format="PNG")
    client = LocalizedEditClient(base64.b64encode(buffer.getvalue()).decode())
    old = {
        "original_filename": "old_original.png",
        "palette_name": "原配色",
        "prompt": "original",
        "request": {"prompt": "守護", "elements": ["山豬"]},
    }

    record = image_generation.recolor_existing_variant(
        old, "上下黑色的邊框改成紅色，其他的都不改", client
    )

    assert record["_used_image_api"] is True
    assert len(client.images.calls) == 1
    assert "上下黑色的邊框改成紅色，其他的都不改" in client.images.calls[0]["prompt"]


def test_blank_random_recolor_uses_image_edit_directly(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "image_storage_root", str(tmp_path))
    source = Image.new("RGB", (4, 2), (181, 43, 38))
    source.save(tmp_path / "old_original.png")
    buffer = BytesIO()
    Image.new("RGB", (4, 2), (35, 76, 125)).save(buffer, format="PNG")
    client = LowConfidenceClient(base64.b64encode(buffer.getvalue()).decode())
    old = {
        "original_filename": "old_original.png",
        "palette_name": "原配色",
        "prompt": "original",
        "request": {"prompt": "守護", "elements": ["山豬"]},
    }

    record = image_generation.recolor_existing_variant(old, "隨機更換配色", client)

    assert record["_used_image_api"] is True
    assert record["prompt"] == "隨機更換配色"
    assert len(client.images.calls) == 1
    assert "自由選擇一組與原圖不同" in client.images.calls[0]["prompt"]

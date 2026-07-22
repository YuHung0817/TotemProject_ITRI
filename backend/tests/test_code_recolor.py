from PIL import Image

from app.core.config import get_settings
from app.services import image_generation


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

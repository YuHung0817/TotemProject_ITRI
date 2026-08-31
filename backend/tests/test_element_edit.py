import base64
from io import BytesIO

from PIL import Image

from app.core.config import get_settings
from app.schemas.image import GenerateRequest, MotifRevisionResolution
from app.services import image_generation


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


class FakeClient:
    def __init__(self, encoded_image: str) -> None:
        self.images = FakeImageEdits(encoded_image)


def test_element_edit_uses_previous_image_and_records_resolved_state_and_palette(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(get_settings(), "image_storage_root", str(tmp_path))
    Image.new("RGB", (8, 1), (244, 239, 226)).save(tmp_path / "old_original.png")

    edited = Image.new("RGB", (8, 1))
    edited.putdata(
        [
            (244, 239, 226),
            (21, 21, 21),
            (181, 43, 38),
            (220, 170, 38),
            (35, 76, 125),
            (40, 110, 65),
            (105, 65, 125),
            (10, 130, 150),
        ]
    )
    buffer = BytesIO()
    edited.save(buffer, format="PNG")
    client = FakeClient(base64.b64encode(buffer.getvalue()).decode())

    request = GenerateRequest(
        prompt="山與月亮的圖騰",
        elements=["山", "山豬"],
        excluded_elements=["月亮"],
    )
    resolution = MotifRevisionResolution(
        final_elements=["山", "山豬"],
        added_elements=["山豬"],
        removed_elements=["月亮"],
        excluded_elements=["月亮"],
        revision_summary="移除月亮並加入山豬",
    )
    old = {
        "original_filename": "old_original.png",
        "request": {"prompt": "山與月亮的圖騰", "elements": ["山", "月亮"]},
    }

    record = image_generation.edit_motif_elements_with_image_model(
        old, request, "拿掉月亮，加入山豬", resolution, client
    )

    assert len(client.images.calls) == 1
    prompt = client.images.calls[0]["prompt"]
    assert "拿掉月亮，加入山豬" in prompt
    assert 'Add: ["山豬"]' in prompt
    assert 'Remove: ["月亮"]' in prompt
    assert record["request"]["elements"] == ["山", "山豬"]
    assert record["generation"]["elements"] == ["山", "山豬"]
    assert record["design_spec"]["final_elements"] == ["山", "山豬"]
    assert len(record["palette"]["colors"]) == 8
    assert {tuple(item["rgb"]) for item in record["palette"]["colors"]} == set(
        edited.getdata()
    )

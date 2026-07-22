from types import SimpleNamespace

import pytest

from app.schemas.image import GenerateRequest
from app.services.prompt_compiler import build_generation_prompt, resolve_motif_revision


class FakeResponses:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.last_call: dict | None = None

    def create(self, **kwargs):
        self.last_call = kwargs
        return SimpleNamespace(output_text=self.output_text)


class FakeClient:
    def __init__(self, output_text: str) -> None:
        self.responses = FakeResponses(output_text)


def test_revision_resolver_accepts_custom_elements_and_structured_state() -> None:
    client = FakeClient("""{
      "final_elements": ["山脈", "猴子", "守護家園", "猴子"],
      "added_elements": ["猴子", "守護家園"],
      "removed_elements": ["月亮"],
      "excluded_elements": ["月亮"],
      "changes_palette": false,
      "palette_instruction": "must be discarded",
      "revision_summary": "移除月亮，加入猴子與守護家園意象"
    }""")

    result = resolve_motif_revision(
        client,
        "自然與守護",
        ["山脈", "月亮"],
        "紅黑白",
        "拿掉月亮，加入猴子和守護家園",
    )

    assert result.final_elements == ["山脈", "猴子", "守護家園"]
    assert result.added_elements == ["猴子", "守護家園"]
    assert result.removed_elements == ["月亮"]
    assert result.excluded_elements == ["月亮"]
    assert result.changes_palette is False
    assert result.palette_instruction == ""
    assert "拿掉月亮" in client.responses.last_call["input"]


def test_revision_resolver_rejects_non_structured_output() -> None:
    client = FakeClient("我無法提供 JSON")
    with pytest.raises(ValueError, match="無法解析"):
        resolve_motif_revision(client, "守護", ["月亮"], None, "加入鳥")


def test_diamond_exclusion_overrides_default_diamond_prompt() -> None:
    client = FakeClient("A diamond-free geometric brief using zigzags and stepped triangles.")
    request = GenerateRequest(
        prompt="移除菱形，保留祭儀節奏",
        elements=["射耳祭"],
        excluded_elements=["菱形"],
    )

    prompt = build_generation_prompt(client, request, 0)

    assert "HIGHEST-PRIORITY USER EXCLUSIONS" in prompt
    assert "Do not depict, imply, or reintroduce these forms anywhere: 菱形" in prompt
    assert "no diamond or checkerboard forms" in prompt

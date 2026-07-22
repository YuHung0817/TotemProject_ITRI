from app.prompts.product_preview import (
    DISPLAY_STYLE_OPTIONS,
    PLACEMENT_OPTIONS,
    PRODUCT_OPTIONS,
    build_product_mockup_prompt,
)
from app.schemas.image import ProductPreviewRequest


def test_only_current_product_preview_options_are_enabled() -> None:
    assert set(PRODUCT_OPTIONS) == {
        "托特包",
        "束口袋",
        "午餐袋",
        "飲料提袋",
        "環形鑰匙圈",
    }
    assert set(PLACEMENT_OPTIONS) == {
        "AI自動決定位置",
        "袋子中央",
        "提袋處",
        "提袋",
        "袋身／杯套本體",
        "提把／提帶",
        "圖騰取代皮革帶",
    }
    assert set(DISPLAY_STYLE_OPTIONS) == {
        "白色商品＋白底",
        "黑色商品＋白底",
        "深紅色商品＋白底",
        "深綠色商品＋白底",
        "深藍色商品＋白底",
    }


def test_every_placement_builds_a_complete_prompt() -> None:
    for placement in PLACEMENT_OPTIONS:
        request = ProductPreviewRequest(placement=placement)
        prompt = build_product_mockup_prompt(request, 0)
        assert "The uploaded motif is immutable." in prompt
        assert "{placement_lock_text}" not in prompt
        assert "{top_start_text}" not in prompt
        assert "{cap_anchor_layering_text}" not in prompt


def test_motif_dialogue_is_not_reused_as_preview_requirement() -> None:
    request = ProductPreviewRequest(preview_prompt="")
    prompt = build_product_mockup_prompt(request, 0)
    assert "圖騰生成需求" not in prompt
    assert "No additional requirement." in prompt

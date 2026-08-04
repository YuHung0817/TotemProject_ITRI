from app.prompts.product_preview import (
    DISPLAY_STYLE_OPTIONS,
    PLACEMENT_OPTIONS,
    PRODUCT_OPTIONS,
    build_product_mockup_prompt,
)
from app.schemas.image import ProductPreviewRequest
from app.services.prompt_compiler import resolve_product_preview_instruction
from app.services.product_reference_service import (
    PRODUCT_REFERENCE_FILES,
    product_reference_path,
)
from app.services.product_preview import (
    add_product_reference_instructions,
)


def test_product_reference_allows_requested_camera_view_to_change() -> None:
    request = ProductPreviewRequest(instruction="我想看到側面的樣子")

    prompt = add_product_reference_instructions("BASE PROMPT", request)

    assert "我想看到側面的樣子" in prompt
    assert "you MUST\n  change the camera view accordingly" in prompt
    assert "Do not preserve the reference image's old view" in prompt
    assert "Only preserve the reference image's camera view when" in prompt


def test_product_reference_preserves_identity_during_revision() -> None:
    request = ProductPreviewRequest(instruction="背景改成白色")

    prompt = add_product_reference_instructions("BASE PROMPT", request)

    assert "product identity" in prompt
    assert "material, color, handles, seams" in prompt
    assert "BASE PROMPT" in prompt


def test_target_reference_is_not_described_as_current_product() -> None:
    request = ProductPreviewRequest(instruction="換成飲料提袋")

    prompt = add_product_reference_instructions(
        "BASE PROMPT", request, reference_role="target"
    )

    assert "DIRECT EDIT TARGET" in prompt
    assert "CURRENT PRODUCT PREVIEW" not in prompt
    assert "corner geometry" in prompt
    assert "Do not regenerate, redesign, recolor, replace, or restyle" in prompt


def test_school_shoulder_bag_uses_reference_instead_of_textual_redesign() -> None:
    request = ProductPreviewRequest(product="台灣高中生側背書包")

    prompt = build_product_mockup_prompt(request, 0)

    assert (
        "exact traditional Taiwanese high school student shoulder bag shown in Image A"
        in prompt
    )
    assert "20 W x 15 H x 6 D" not in prompt
    assert "width-to-height ratio near 4:3" not in prompt
    assert "Cambridge satchel" not in prompt


def test_school_bag_reference_instruction_limits_edit_to_front_flap() -> None:
    request = ProductPreviewRequest(product="台灣高中生側背書包")

    prompt = add_product_reference_instructions(
        "BASE PROMPT", request, reference_role="target"
    )

    assert "Image A is the DIRECT EDIT TARGET" in prompt
    assert "Image B is the MOTIF SOURCE ONLY" in prompt
    assert "Only modify the visible front-flap motif area" in prompt
    assert "Do not alter any other part of the bag" in prompt
    assert "FINAL OVERRIDING SQUARE-CORNER CHECK" not in prompt


def test_phone_lanyard_always_uses_the_entire_strap_as_motif_band() -> None:
    request = ProductPreviewRequest(
        product="圖騰織帶手機掛繩",
        placement="AI自動決定位置",
    )

    base_prompt = build_product_mockup_prompt(request, 0)
    prompt = add_product_reference_instructions(
        base_prompt, request, reference_role="target"
    )

    assert "replace the entire long textile strap" in prompt
    assert "along the full length of the strap" in prompt
    assert "existing long woven lanyard strap itself is the only edit area" in prompt
    assert "Nothing may span across the empty center space" in prompt
    assert "Do not add a patch, pouch, panel, bridge, banner, pocket, or rectangle" in prompt


def test_only_current_product_preview_options_are_enabled() -> None:
    assert set(PRODUCT_OPTIONS) == {
        "托特包",
        "帆布袋",
        "束口袋",
        "午餐袋",
        "飲料提袋",
        "環形鑰匙圈",
        "台灣高中生側背書包",
        "貝殼零錢包",
        "圖騰織帶手機掛繩",
    }
    assert set(PLACEMENT_OPTIONS) == {
        "AI自動決定位置",
        "袋子中央",
        "翻蓋偏下方",
        "肩帶",
        "提袋處",
        "提袋",
        "袋身／杯套本體",
        "提把／提帶",
        "圖騰取代皮革帶",
        "袋身中央直條",
        "圖騰取代整條織帶",
    }
    assert set(DISPLAY_STYLE_OPTIONS) == {
        "白色商品＋白底",
        "黑色商品＋白底",
        "深紅色商品＋白底",
        "深綠色商品＋白底",
        "深藍色商品＋白底",
    }
    assert set(PRODUCT_REFERENCE_FILES) == set(PRODUCT_OPTIONS)
    assert all(product_reference_path(product) for product in PRODUCT_OPTIONS)


def test_white_background_style_preserves_reference_product_color() -> None:
    style = DISPLAY_STYLE_OPTIONS["白色商品＋白底"]

    assert "Preserve the target product reference's exact product color" in style
    assert "Use a white or warm-white product" not in style
    assert "warm white or very light beige studio background" in style


def test_every_placement_builds_a_complete_prompt() -> None:
    for placement in PLACEMENT_OPTIONS:
        request = ProductPreviewRequest(placement=placement)
        prompt = build_product_mockup_prompt(request, 0)
        assert "The uploaded motif is immutable." in prompt
        assert "Show the entire product inside the final image." in prompt
        assert "Do not crop, cut off, or place any part of the product outside" in prompt
        assert "{placement_lock_text}" not in prompt
        assert "{top_start_text}" not in prompt
        assert "{cap_anchor_layering_text}" not in prompt


def test_motif_dialogue_is_not_reused_as_preview_requirement() -> None:
    request = ProductPreviewRequest(preview_prompt="")
    prompt = build_product_mockup_prompt(request, 0)
    assert "圖騰生成需求" not in prompt
    assert "No additional requirement." in prompt


class FakeResponses:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text

    def create(self, **kwargs):  # type: ignore[no-untyped-def]
        return type("Response", (), {"output_text": self.output_text})()


class FakeClient:
    def __init__(self, output_text: str) -> None:
        self.responses = FakeResponses(output_text)


def test_product_instruction_keeps_unknown_product_without_reference() -> None:
    resolution = resolve_product_preview_instruction(
        FakeClient(
            """
            {
              "product": "紅色木製滑板",
              "placement": "板面中央",
              "display_style": "紅色商品、白色攝影棚背景",
              "additional_instruction": "三分之四視角",
              "reference_product": null
            }
            """
        ),
        "換成紅色滑板，圖騰放在板面中央，白色背景",
    )

    assert resolution.product == "紅色木製滑板"
    assert resolution.reference_product is None


def test_product_instruction_accepts_exact_built_in_reference() -> None:
    product = next(iter(PRODUCT_OPTIONS))
    resolution = resolve_product_preview_instruction(
        FakeClient(
            f"""
            {{
              "product": "{product}",
              "placement": "袋子中央",
              "display_style": "黑色商品、白色背景",
              "additional_instruction": "",
              "reference_product": "{product}"
            }}
            """
        ),
        "換成黑色托特包",
    )

    assert resolution.reference_product == product


def test_product_instruction_reports_an_explicit_product_change() -> None:
    resolution = resolve_product_preview_instruction(
        FakeClient(
            """
            {
              "product": "飲料提袋",
              "placement": "袋身／杯套本體",
              "display_style": "白色背景",
              "additional_instruction": "",
              "reference_product": "飲料提袋",
              "changes_product": true
            }
            """
        ),
        "換成飲料提袋",
        current_product="托特包",
    )

    assert resolution.product == "飲料提袋"
    assert resolution.reference_product == "飲料提袋"
    assert resolution.changes_product is True


def test_product_instruction_defaults_to_same_product() -> None:
    resolution = resolve_product_preview_instruction(
        FakeClient(
            """
            {
              "product": "托特包",
              "placement": "袋子中央",
              "display_style": "橘色商品＋白底",
              "additional_instruction": "只改商品本體顏色",
              "reference_product": "托特包"
            }
            """
        ),
        "商品換成橘色",
        current_product="托特包",
    )

    assert resolution.product == "托特包"
    assert resolution.changes_product is False


def test_custom_display_style_is_preserved_in_prompt() -> None:
    request = ProductPreviewRequest(
        product="滑板",
        placement="板面中央",
        display_style="紅色商品、戶外水泥背景",
    )

    prompt = build_product_mockup_prompt(request, 0)

    assert "紅色商品、戶外水泥背景" in prompt

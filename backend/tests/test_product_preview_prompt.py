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


def test_red_school_bag_uses_the_school_bag_edit_protection() -> None:
    request = ProductPreviewRequest(
        product="高中生紅色側背包",
        placement="翻蓋偏下方",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "exact red Taiwanese high school student shoulder bag" in prompt
    assert "Only modify the visible front-flap motif area" in prompt
    assert "approximately 20% of that flap width" in prompt


def test_black_school_bag_uses_the_school_bag_edit_protection() -> None:
    request = ProductPreviewRequest(
        product="高中生黑色側背包",
        placement="翻蓋偏下方",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "exact black Taiwanese high school student shoulder bag" in prompt
    assert "Only modify the visible front-flap motif area" in prompt
    assert "approximately 20% of that flap width" in prompt


def test_hongye_bag_only_replaces_existing_bottom_motif_band() -> None:
    request = ProductPreviewRequest(
        product="紅葉少棒紅書包",
        placement="置換下方圖騰",
    )

    base_prompt = build_product_mockup_prompt(request, 0)
    prompt = add_product_reference_instructions(
        base_prompt, request, reference_role="target"
    )

    assert "existing black-and-white horizontal geometric motif band" in prompt
    assert "the only edit area" in prompt
    assert 'all text including "紅葉少棒 1968"' in prompt
    assert "Do not place the uploaded motif" in prompt
    assert "Only modify the visible front-flap motif area" not in prompt


def test_black_hongye_bag_preserves_its_own_product_details() -> None:
    request = ProductPreviewRequest(
        product="紅葉少棒黑書包",
        placement="置換下方圖騰",
    )

    base_prompt = build_product_mockup_prompt(request, 0)
    prompt = add_product_reference_instructions(
        base_prompt, request, reference_role="target"
    )

    assert "exact black Hongye youth baseball shoulder bag" in prompt
    assert "black fabric, maple-leaf patch" in prompt
    assert "the only edit area" in prompt
    assert "complete shoulder-strap loop" in prompt
    assert "no more than approximately 85% of the image height" in prompt
    assert "framing requirement overrides Image A's original product scale" in prompt
    assert "red fabric" not in prompt


def test_green_hongye_bag_only_replaces_its_bottom_motif_band() -> None:
    request = ProductPreviewRequest(
        product="紅葉少棒綠書包",
        placement="置換下方圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "exact green Hongye youth baseball shoulder bag" in prompt
    assert "green fabric, yellow maple leaf" in prompt
    assert "the only edit area" in prompt
    assert "visible red front panel" not in prompt


def test_hongye_coin_purse_replaces_only_its_two_side_bands() -> None:
    request = ProductPreviewRequest(
        product="紅葉少棒黑色零錢包",
        placement="置換兩側飾帶圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "two existing narrow colorful vertical decorative bands" in prompt
    assert "the only edit areas" in prompt
    assert 'Preserve the central red maple leaf' in prompt
    assert '"1960", "UNINANG"' in prompt
    assert "every surrounding white decorative symbol" in prompt
    assert "Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET" in prompt
    assert "Image B is the MOTIF REFERENCE ONLY" in prompt
    assert "scale, crop, simplify" in prompt
    assert "rearrange them vertically" in prompt
    assert "realistic woven fabric tape physically sewn into the pouch" in prompt
    assert "Preserve the rest of the pouch exactly" in prompt
    assert "outside the two side strips" in prompt


def test_red_hongye_coin_purse_uses_the_same_two_side_band_rule() -> None:
    request = ProductPreviewRequest(
        product="紅葉少棒紅色零錢包",
        placement="置換兩側飾帶圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "exact red-and-black Hongye youth baseball rectangular coin purse" in prompt
    assert "two existing narrow colorful vertical decorative bands" in prompt
    assert "all black and red fabric exactly as shown" in prompt
    assert 'Preserve the central red maple leaf' in prompt
    assert '"1960", "UNINANG"' in prompt


def test_white_hongye_shirt_only_replaces_both_cuff_bands() -> None:
    request = ProductPreviewRequest(
        product="白色紅葉少棒衣服",
        placement="置換左右袖口圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET" in prompt
    assert "Image B is the MOTIF REFERENCE ONLY" in prompt
    assert "left and right sleeve cuffs are the only edit areas" in prompt
    assert "realistic woven fabric trim" in prompt
    assert "into both cuffs" in prompt
    assert "Preserve the rest of the shirt exactly" in prompt
    assert '"HongYe", "1968"' in prompt
    assert "outside the two sleeve-cuff bands" in prompt


def test_black_hongye_shirt_only_replaces_its_lower_motif_band() -> None:
    request = ProductPreviewRequest(
        product="黑色紅葉少棒衣服",
        placement="置換衣服下方圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET" in prompt
    assert "Image B is the MOTIF REFERENCE ONLY" in prompt
    assert "wide horizontal" in prompt
    assert "across the lower shirt front" in prompt
    assert "the only edit area" in prompt
    assert "Preserve the rest of the shirt exactly" in prompt
    assert '"紅葉少棒"' in prompt
    assert '"1968"' in prompt
    assert "outside the original lower motif band" in prompt


def test_white_hongye_beverage_carrier_replaces_only_three_existing_bands() -> None:
    request = ProductPreviewRequest(
        product="紅葉飲料提袋－白",
        placement="置換三處圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET" in prompt
    assert "Image B is the MOTIF REFERENCE ONLY" in prompt
    assert "exactly three and only three areas" in prompt
    assert "front-facing decorative\n  strip running along the carrying handle" in prompt
    assert "upper horizontal decorative band" in prompt
    assert "lower horizontal decorative band" in prompt
    assert "realistic woven textile decoration" in prompt
    assert "transparent cup, lid, straw" in prompt
    assert "central red maple-leaf\n  emblem and all text" in prompt
    assert "outside those three original black-and-white motif bands" in prompt


def test_black_hongye_beverage_carrier_uses_same_three_band_rule() -> None:
    request = ProductPreviewRequest(
        product="紅葉飲料提袋－黑",
        placement="置換三處圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "exact black Hongye single-cup beverage carrier" in prompt
    assert "exactly three and only three areas" in prompt
    assert "front-facing decorative\n  strip running along the carrying handle" in prompt
    assert "upper horizontal decorative band" in prompt
    assert "lower horizontal decorative band" in prompt
    assert "black fabric and its texture" in prompt
    assert "transparent cup, lid, straw" in prompt
    assert "central red maple-leaf\n  emblem and all text" in prompt
    assert "original background" in prompt
    assert "white fabric and its texture" not in prompt


def test_white_hongye_canvas_bag_replaces_only_two_continuous_handle_bands() -> None:
    request = ProductPreviewRequest(
        product="紅葉帆布袋－白",
        placement="置換提帶及袋身兩側圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET" in prompt
    assert "Image B is the MOTIF REFERENCE ONLY" in prompt
    assert "two existing\n  symmetrical decorative bands" in prompt
    assert "one visually continuous woven strip" in prompt
    assert "continue vertically down the matching\n  side of the front bag body to the bottom edge" in prompt
    assert "only edit areas" in prompt
    assert "symmetric, aligned, equal in\n  width" in prompt
    assert "central red maple leaf" in prompt
    assert '"1968", "UNINANG"' in prompt
    assert "outside the two original continuous handle-and-body bands" in prompt


def test_black_hongye_canvas_bag_uses_same_continuous_band_rule() -> None:
    request = ProductPreviewRequest(
        product="紅葉帆布袋－黑",
        placement="置換提帶及袋身兩側圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "exact black Hongye canvas tote bag" in prompt
    assert "two existing\n  symmetrical decorative bands" in prompt
    assert "one visually continuous woven strip" in prompt
    assert "continue vertically down the matching\n  side of the front bag body to the bottom edge" in prompt
    assert "black canvas color and texture" in prompt
    assert "central red maple leaf" in prompt
    assert '"1968", "UNINANG"' in prompt
    assert "outside the two original continuous handle-and-body bands" in prompt
    assert "white canvas color and texture" not in prompt


def test_white_hongye_lunch_bag_replaces_only_bottom_band() -> None:
    request = ProductPreviewRequest(
        product="紅葉午餐袋－白",
        placement="置換下方圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "exact ivory-white Hongye insulated lunch bag" in prompt
    assert "Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET" in prompt
    assert "Image B is the MOTIF REFERENCE ONLY" in prompt
    assert "very bottom of the visible front panel is the only edit area" in prompt
    assert "original upper and lower boundaries" in prompt
    assert "ivory-white / off-white fabric body" in prompt
    assert "carrying handles,\n  zipper and zipper pull" in prompt
    assert "central red maple leaf and turquoise veins" in prompt
    assert '"1968" and "UNINANG" text with their exact original colors' in prompt
    assert "product angle, composition" in prompt
    assert "outside the original bottom\n  horizontal motif band" in prompt


def test_black_hongye_lunch_bag_uses_same_bottom_band_rule() -> None:
    request = ProductPreviewRequest(
        product="紅葉午餐袋－黑",
        placement="置換下方圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "exact black Hongye insulated lunch bag" in prompt
    assert "very bottom of the visible front panel is the only edit area" in prompt
    assert "original upper and lower boundaries" in prompt
    assert "black fabric body and its texture" in prompt
    assert "carrying handles,\n  zipper and zipper pull" in prompt
    assert "central red maple leaf and turquoise veins" in prompt
    assert '"1968" and "UNINANG" text with their exact original colors' in prompt
    assert "outside the original bottom\n  horizontal motif band" in prompt
    assert "ivory-white / off-white fabric body" not in prompt


def test_white_hongye_tote_replaces_only_continuous_handle_and_body_bands() -> None:
    request = ProductPreviewRequest(
        product="紅葉托特包－白",
        placement="置換提帶及袋身兩側圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "exact ivory-white structured Hongye tote bag" in prompt
    assert "Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET" in prompt
    assert "Image B is the MOTIF REFERENCE ONLY" in prompt
    assert "two existing\n  symmetrical decorative bands" in prompt
    assert "including its full curved upper section" in prompt
    assert "continue vertically along the matching decorative strip" in prompt
    assert "only edit areas" in prompt
    assert "symmetric, aligned, equal in width" in prompt
    assert "all metal hardware and attachments" in prompt
    assert "central red maple-leaf\n  embroidery and turquoise veins" in prompt
    assert '"1968", "UNINANG"' in prompt
    assert "outside the two original\n  continuous handle-and-body bands" in prompt


def test_black_hongye_tote_uses_same_continuous_handle_band_rule() -> None:
    request = ProductPreviewRequest(
        product="紅葉托特包－黑",
        placement="置換提帶及袋身兩側圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "exact black structured Hongye tote bag" in prompt
    assert "two existing\n  symmetrical decorative bands" in prompt
    assert "including its full curved upper section" in prompt
    assert "continue vertically along the matching decorative strip" in prompt
    assert "black tote body and its color and texture" in prompt
    assert "all metal hardware and attachments" in prompt
    assert "central red maple-leaf\n  embroidery and turquoise veins" in prompt
    assert '"1968", "UNINANG"' in prompt
    assert "outside the two original\n  continuous handle-and-body bands" in prompt
    assert "ivory-white tote body" not in prompt


def test_white_hongye_drawstring_bag_replaces_only_bottom_band() -> None:
    request = ProductPreviewRequest(
        product="紅葉束口袋－白",
        placement="置換下方圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "exact ivory-white Hongye drawstring pouch" in prompt
    assert "Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET" in prompt
    assert "Image B is the MOTIF REFERENCE ONLY" in prompt
    assert "very bottom of the visible pouch front is the only edit area" in prompt
    assert "from the left edge to the right edge" in prompt
    assert "Preserve Image B's original\n  colors and design as faithfully as possible" in prompt
    assert "bottom seam, wrinkles" in prompt
    assert "ivory-white pouch body" in prompt
    assert "drawstrings and knots" in prompt
    assert "central red\n  maple-leaf embroidery and turquoise veins" in prompt
    assert 'black "1968" and "UNINANG" text' in prompt
    assert "outside the original bottom horizontal motif band" in prompt
    assert "especially the central maple leaf and text" in prompt


def test_black_hongye_drawstring_bag_uses_same_bottom_band_rule() -> None:
    request = ProductPreviewRequest(
        product="紅葉束口袋－黑",
        placement="置換下方圖騰",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "exact black Hongye drawstring pouch" in prompt
    assert "very bottom of the visible pouch front is the only edit area" in prompt
    assert "from the left edge to the right edge" in prompt
    assert "Preserve Image B's original\n  colors and design as faithfully as possible" in prompt
    assert "black pouch body and its color and texture" in prompt
    assert 'white "1968" and "UNINANG" text' in prompt
    assert "drawstrings and knots" in prompt
    assert "central red\n  maple-leaf embroidery and turquoise veins" in prompt
    assert "outside the original bottom horizontal motif band" in prompt
    assert "ivory-white pouch body" not in prompt


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


def test_black_phone_lanyard_uses_the_same_full_strap_replacement_rule() -> None:
    request = ProductPreviewRequest(
        product="黑色手機掛繩",
        placement="圖騰取代整條織帶",
    )

    prompt = add_product_reference_instructions(
        build_product_mockup_prompt(request, 0),
        request,
        reference_role="target",
    )

    assert "exact black adjustable dual-hook phone lanyard" in prompt
    assert "existing long woven lanyard strap itself is the only edit area" in prompt
    assert "Preserve the strap's original width, path, construction" in prompt


def test_only_current_product_preview_options_are_enabled() -> None:
    assert set(PRODUCT_OPTIONS) == {
        "托特包",
        "黑色托特包",
        "紅葉托特包－白",
        "紅葉托特包－黑",
        "帆布袋",
        "黑色帆布袋",
        "紅葉帆布袋－白",
        "紅葉帆布袋－黑",
        "束口袋",
        "黑色束口袋",
        "紅葉束口袋－白",
        "紅葉束口袋－黑",
        "午餐袋",
        "黑色午餐袋",
        "紅葉午餐袋－白",
        "紅葉午餐袋－黑",
        "飲料提袋",
        "黑色飲料袋",
        "紅葉飲料提袋－白",
        "紅葉飲料提袋－黑",
        "環形鑰匙圈",
        "黑色環形鑰匙圈",
        "台灣高中生側背書包",
        "高中生紅色側背包",
        "高中生黑色側背包",
        "紅葉少棒紅書包",
        "紅葉少棒黑書包",
        "紅葉少棒綠書包",
        "貝殼零錢包",
        "黑色貝殼零錢包",
        "紅葉少棒黑色零錢包",
        "紅葉少棒紅色零錢包",
        "白色紅葉少棒衣服",
        "黑色紅葉少棒衣服",
        "圖騰織帶手機掛繩",
        "黑色手機掛繩",
    }
    assert set(PLACEMENT_OPTIONS) == {
        "AI自動決定位置",
        "袋子中央",
        "翻蓋偏下方",
        "置換下方圖騰",
        "置換兩側飾帶圖騰",
        "置換左右袖口圖騰",
        "置換衣服下方圖騰",
        "置換三處圖騰",
        "置換提帶及袋身兩側圖騰",
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

import base64
from pathlib import Path
from typing import Any, BinaryIO

from openai import OpenAI

from app.core.config import get_settings
from app.prompts.product_preview import build_product_mockup_prompt
from app.services.storage_service import image_url, store_image_bytes


def add_product_reference_instructions(
    prompt: str, request: Any, reference_role: str = "current"
) -> str:
    """Tell Image Edit what to preserve and what a revision may intentionally change."""
    school_bag = request.product in {
        "台灣高中生側背書包",
        "高中生紅色側背包",
        "高中生黑色側背包",
        "復古側背書包",
    }
    hongye_bag = request.product in {
        "紅葉少棒紅書包",
        "紅葉少棒黑書包",
        "紅葉少棒綠書包",
    }
    hongye_coin_purse = request.product in {
        "紅葉少棒黑色零錢包",
        "紅葉少棒紅色零錢包",
    }
    hongye_shirt = request.product == "白色紅葉少棒衣服"
    black_hongye_shirt = request.product == "黑色紅葉少棒衣服"
    phone_lanyard = request.product in {"圖騰織帶手機掛繩", "黑色手機掛繩"}
    if reference_role == "target":
        reference_description = """Image A is the DIRECT EDIT TARGET.
  Preserve Image A's overall shape, proportions, silhouette, design, corner geometry,
  fabric color and texture, strap, buckle, seams, gussets, camera angle, composition,
  lighting, and background. Do not regenerate, redesign, recolor, replace, or restyle
  any part outside the requested motif area."""
        continuity_instruction = (
            "Edit Image A directly instead of creating a redesigned product."
        )
    else:
        reference_description = """Image A is the CURRENT PRODUCT PREVIEW and DIRECT EDIT TARGET.
  Use it to preserve the same product identity: category, body shape, proportions,
  material, color, handles, seams, gussets, straps, hardware, construction, and other
  details not changed by the user."""
        continuity_instruction = (
            "Edit Image A directly instead of creating a redesigned product."
        )
    if black_hongye_shirt:
        edit_scope = """Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET, and main image to
  modify in place. Image B is the MOTIF REFERENCE ONLY. The existing wide horizontal
  geometric motif band across the lower shirt front is the only edit area. Remove that
  original band pattern and apply Image B within the exact same footprint, width, height,
  and boundaries. Scale, crop, simplify, repeat, and arrange it horizontally as needed while
  preserving motif identity and colors. Follow the fabric surface, drape, folds, lighting,
  and perspective; integrate realistic textile texture, printing or weaving, edge alignment,
  shadows, and material detail—not a flat pasted image or sticker. Preserve the rest of the
  shirt exactly, including its black color, cut, collar, sleeves, hems, seams, fabric, chest
  text "紅葉少棒", maple leaf, ball, yellow slash, "1968", proportions, camera angle,
  lighting, shadows, and background. Do not modify or cover anything outside the original
  lower motif band."""
    elif hongye_shirt:
        edit_scope = """Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET, and main image to
  modify in place. Image B is the MOTIF REFERENCE ONLY. The existing decorative bands at
  the left and right sleeve cuffs are the only edit areas. Replace both cuff bands with
  Image B, adapting, scaling, cropping, simplifying, repeating, and arranging it along each
  narrow cuff while preserving motif identity and colors. Follow each cuff's angle, curve,
  fabric shape, folds, lighting, and perspective. Render realistic woven fabric trim sewn
  into both cuffs, with textile weave, stitched edges, thickness, shadows, and material
  integration—not flat pasted images or stickers. Preserve the rest of the shirt exactly,
  including its white color, cut, collar, sleeves, hems, seams, fabric, chest maple leaf,
  "HongYe", "1968", proportions, camera angle, lighting, shadows, and background. Do not
  modify, cover, redraw, or redesign anything outside the two sleeve-cuff bands."""
    elif hongye_coin_purse:
        preserved_fabric = (
            "all black and red fabric"
            if request.product == "紅葉少棒紅色零錢包"
            else "all black fabric"
        )
        edit_scope = f"""Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET, and main image to
  modify in place. Image B is the MOTIF REFERENCE ONLY, never the product or composition.
  Replace only the left and right vertical decorative trim strips on Image A. Those two
  narrow strips are the only edit areas. Apply Image B to both strips within their original
  footprints. If Image B is horizontal, scale, crop, simplify, select recognizable components,
  repeat, and rearrange them vertically as needed while preserving the motif identity and colors.
  Render the result as realistic woven fabric tape physically sewn into the pouch, with textile
  weave, stitched edges, thickness, shadows, lighting, and perspective—not flat pasted images
  or stickers. Preserve the central red maple leaf, green details, "1960", "UNINANG",
  every surrounding white decorative symbol, and {preserved_fabric} exactly as shown.
  Preserve the rest of the pouch exactly, including the zipper, zipper pull, piping, seams,
  rounded corners, side and top panels, silhouette, camera angle, lighting, and background.
  Do not modify or cover anything outside the two side strips."""
    elif hongye_bag:
        preserved_details = {
            "紅葉少棒紅書包": 'the red fabric, yellow maple leaf, and all text including "紅葉少棒 1968"',
            "紅葉少棒黑書包": "the black fabric, maple-leaf patch, and all original Chinese text",
            "紅葉少棒綠書包": 'the green fabric, yellow maple leaf, and all text including "紅葉少棒 1968"',
        }[request.product]
        edit_scope = f"""The existing horizontal geometric motif band at the
  very bottom of the visible front panel is the only edit area. Replace that entire
  existing bottom band with Image B, fitted to the same long horizontal footprint and
  perspective. Preserve {preserved_details},
  seams, strap, hardware, silhouette, camera angle, lighting, and background exactly.
  Do not modify, cover, move, duplicate, or add anything outside that bottom motif band."""
    elif school_bag:
        edit_scope = """Only modify the visible front-flap motif area.
  Apply Image B as one sewn textile panel on that area.
  Do not alter any other part of the bag."""
    elif phone_lanyard:
        edit_scope = """The existing long woven lanyard strap itself is the only edit area.
  Replace the strap fabric along its full usable length with Image B as a continuous woven
  motif band, following the strap's long axis, width, folds, and perspective.
  Keep the motif fully inside the strap boundaries and repeat it lengthwise as needed.
  Preserve the strap's original width, path, construction, adjuster, loops, labels, connector
  tabs, rings, swivel clasps, and all hardware exactly as shown in Image A.
  Do not add a patch, pouch, panel, bridge, banner, pocket, or rectangle between the two
  hanging sides. Nothing may span across the empty center space between the straps."""
    else:
        edit_scope = """Only modify the motif placement area requested below.
  Do not alter unrelated product areas."""
    return f"""
TWO-IMAGE EDITING INSTRUCTIONS:
- {reference_description}
- Image B is the MOTIF SOURCE ONLY. Preserve its motif exactly.
- {continuity_instruction}
- {edit_scope}
- The user's latest written request overrides the current preview for camera angle,
  viewpoint, composition, background, product color, material, and other explicitly
  requested changes.
- If the user asks for a side, back, top, close-up, or three-quarter view, you MUST
  change the camera view accordingly. Do not preserve the reference image's old view.
- Only preserve the reference image's camera view when the user did not request a new one.
- Do not copy background text, labels, logos, or existing decoration from the reference.
- Do not merge the two source images side by side and do not output a collage.

LATEST USER REQUEST:
{request.instruction.strip() or "No additional requirement."}

{prompt}
""".strip()


def create_product_preview(
    client: OpenAI,
    motif_path: Path,
    request: Any,
    variant_index: int,
    product_reference: BinaryIO | None = None,
    product_reference_role: str = "target",
) -> dict[str, Any]:
    prompt = build_product_mockup_prompt(request, variant_index)
    if product_reference is not None:
        prompt = add_product_reference_instructions(
            prompt, request, reference_role=product_reference_role
        )
    if (
        request.product in {"台灣高中生側背書包", "高中生紅色側背包", "高中生黑色側背包", "復古側背書包"}
        and request.placement == "翻蓋偏下方"
    ):
        prompt += """

FINAL OVERRIDING SIZE CHECK — APPLY THIS AFTER ALL OTHER INSTRUCTIONS:
Before rendering, compare the motif's outer bounding-box width with the visible front-flap
width. The motif width MUST equal approximately 20% of the flap width (one fifth), never
80%. Keep at least 40% blank flap width on both the left and right. Center it horizontally,
but position it vertically below the flap midpoint around the lower third, with a clear
margin above the bottom edge. If the motif looks large or vertically centered, reduce and
move it down until this exact requirement is satisfied. This final requirement overrides
any conflicting visual inference from either source image.
""".rstrip()
    with motif_path.open("rb") as image_file:
        images = [product_reference, image_file] if product_reference is not None else image_file
        response = client.images.edit(
            model=get_settings().openai_product_image_model,
            image=images,
            prompt=prompt,
            size=request.preview_size,
            quality=request.preview_quality,
            output_format="png",
        )

    image_data = response.data[0]
    if not image_data.b64_json:
        raise RuntimeError("Image API did not return product preview image data.")

    filename = store_image_bytes(base64.b64decode(image_data.b64_json), label="mockup")
    return {
        "filename": filename,
        "url": image_url(filename),
        "prompt": prompt,
        "revised_prompt": getattr(image_data, "revised_prompt", None),
    }

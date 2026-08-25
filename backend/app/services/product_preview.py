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
    hongye_beverage_carrier = request.product in {
        "紅葉飲料提袋－白",
        "紅葉飲料提袋－黑",
    }
    hongye_canvas_bag = request.product in {
        "紅葉帆布袋－白",
        "紅葉帆布袋－黑",
    }
    hongye_lunch_bag = request.product in {
        "紅葉午餐袋－白",
        "紅葉午餐袋－黑",
    }
    hongye_tote_bag = request.product in {
        "紅葉托特包－白",
        "紅葉托特包－黑",
    }
    hongye_drawstring_bag = request.product in {
        "紅葉束口袋－白",
        "紅葉束口袋－黑",
    }
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
    if hongye_drawstring_bag:
        preserved_drawstring_details = (
            'the black pouch body and its color and texture, and the white "1968" and "UNINANG" text'
            if request.product == "紅葉束口袋－黑"
            else 'the ivory-white pouch body and its color and texture, and the black "1968" and "UNINANG" text'
        )
        edit_scope = f"""Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET, and main image to
  modify in place. Image B is the MOTIF REFERENCE ONLY, never the product, composition,
  background, or replacement object. The existing horizontal decorative motif band at the
  very bottom of the visible pouch front is the only edit area. Completely replace only the
  old motif within that exact band footprint with Image B, extending the new motif horizontally
  across the full original band from the left edge to the right edge. Preserve Image B's original
  colors and design as faithfully as possible; do not redesign it. Scale, crop, repeat, and arrange
  it horizontally only as needed to fit the band width while maintaining recognizable motif
  identity and continuous layout. Follow the pouch's actual bottom width, front-plane perspective,
  slight fabric undulations, bottom seam, wrinkles, lighting, and surface angle. Render a realistic
  printed or woven textile mockup with visible fabric weave, fibers, stitching, shadows, and natural
  material integration—not a flat pasted image or sticker. Preserve everything else in Image A
  exactly: {preserved_drawstring_details}, drawstrings and knots, drawstring
  channel, complete pouch shape and proportions, fabric wrinkles and folds, seams, central red
  maple-leaf embroidery and turquoise veins, every surrounding
  decorative symbol, camera angle, composition, lighting, shadows, background, and product-
  photography style. Do not modify, cover, redraw, recolor, move, resize, or regenerate anything
  outside the original bottom horizontal motif band, especially the central maple leaf and text."""
    elif hongye_tote_bag:
        preserved_tote_fabric = (
            "black tote body and its color and texture"
            if request.product == "紅葉托特包－黑"
            else "ivory-white tote body and its color and texture"
        )
        edit_scope = f"""Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET, and main image to
  modify in place. Image B is the MOTIF REFERENCE ONLY, never the product, composition,
  background, or replacement object. Replace only the old motif inside the two existing
  symmetrical decorative bands. Each side must remain one visually continuous woven band:
  cover the complete left or right handle, including its full curved upper section, follow
  the handle downward, pass naturally through its attachment point at the bag opening, and
  continue vertically along the matching decorative strip on the visible front bag body.
  The two original left and right handle-and-body band footprints are the only edit areas.
  Apply Image B continuously and consistently to both bands, adapting, scaling, cropping,
  repeating, and arranging it along their length while preserving the motif's recognizable
  identity and colors. Keep both sides symmetric, aligned, equal in width, and visually tidy.
  Follow the handles' actual width, upper curves, folds, direction, fabric shape, perspective,
  seams, lighting, and occlusion. Render realistic woven or embroidered textile bands with
  visible fabric weave, stitching, thickness, shadows, creases, and authentic material detail—
  not flat pasted images or stickers. Preserve everything else in Image A exactly: the
  {preserved_tote_fabric}, complete structured bag shape and proportions,
  opening, pocket, base, edges, seams, all metal hardware and attachments, central red maple-leaf
  embroidery and turquoise veins, "1968", "UNINANG", every surrounding decorative symbol,
  camera angle, composition, lighting, shadows, background, and product-photography style. Do not
  modify, cover, redraw, recolor, move, resize, or redesign anything outside the two original
  continuous handle-and-body bands."""
    elif hongye_lunch_bag:
        preserved_lunch_fabric = (
            "black fabric body and its texture"
            if request.product == "紅葉午餐袋－黑"
            else "ivory-white / off-white fabric body and its texture"
        )
        edit_scope = f"""Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET, and main image to
  modify in place. Image B is the MOTIF REFERENCE ONLY, never the product, composition,
  background, or replacement object. The existing horizontal decorative motif band at the
  very bottom of the visible front panel is the only edit area. Completely replace only the
  old motif inside that exact band footprint with Image B. Fit, scale, crop, repeat, and arrange
  the new motif horizontally as needed while preserving its recognizable identity and colors.
  Keep the band within its original upper and lower boundaries and follow the front panel's
  angle, slight perspective, fabric surface, seams, lighting, and shape. Render realistic woven
  or printed textile detail integrated into the bag—not a flat pasted image or sticker.
  Preserve everything else in Image A exactly: the {preserved_lunch_fabric}, carrying handles,
  zipper and zipper pull, side panels, gussets, piping, seams, complete
  product shape and construction, central red maple leaf and turquoise veins, the original
  "1968" and "UNINANG" text with their exact original colors, every surrounding small decorative
  symbol, product angle, composition,
  proportions, dimensions, lighting, shadows, background, and product-photography style. Do not
  modify, cover, redraw, recolor, move, resize, or redesign anything outside the original bottom
  horizontal motif band."""
    elif hongye_canvas_bag:
        preserved_canvas_fabric = (
            "black canvas color and texture"
            if request.product == "紅葉帆布袋－黑"
            else "white canvas color and texture"
        )
        edit_scope = f"""Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET, and main image to
  modify in place. Image B is the MOTIF REFERENCE ONLY, never the product, composition,
  background, or replacement object. Replace only the old motif inside the two existing
  symmetrical decorative bands. Each band must remain one visually continuous woven strip:
  follow the full visible length of the left or right carrying handle, pass naturally through
  its original attachment point at the bag opening, and continue vertically down the matching
  side of the front bag body to the bottom edge. The two original left and right band footprints
  are the only edit areas. Apply Image B continuously and consistently to both bands, adapting,
  scaling, cropping, repeating, and arranging it along their length as needed while preserving
  the motif's recognizable identity and colors. Keep both sides symmetric, aligned, equal in
  width, and visually tidy. Follow each handle's width, curve, folds, direction, fabric shape,
  perspective, seams, lighting, and occlusion. Render realistic woven textile bands physically
  integrated into the bag, with fabric weave, stitching, thickness, shadows, and authentic
  printed or woven detail—not flat pasted images or stickers. Preserve everything else in
  Image A exactly: the {preserved_canvas_fabric}, bag shape and construction, top opening,
  edges, seams, proportions, central red maple leaf, turquoise leaf veins, "1968", "UNINANG",
  every surrounding decorative symbol, camera angle, composition, lighting, shadows, transparent
  background, and product-photography style. Do not modify, cover, redraw, recolor, move, or
  redesign anything outside the two original continuous handle-and-body bands."""
    elif hongye_beverage_carrier:
        preserved_carrier_fabric = (
            "black fabric and its texture"
            if request.product == "紅葉飲料提袋－黑"
            else "white fabric and its texture"
        )
        edit_scope = f"""Image A is the PRODUCT IMAGE, DIRECT EDIT TARGET, and main image to
  modify in place. Image B is the MOTIF REFERENCE ONLY, never the product, composition,
  background, or replacement object. Replace the original black-and-white motif completely
  in exactly three and only three areas on Image A: (1) the long front-facing decorative
  strip running along the carrying handle, (2) the upper horizontal decorative band around
  the cup sleeve, and (3) the lower horizontal decorative band around the cup sleeve. These
  three existing band footprints are the only edit areas. Apply Image B continuously within
  each footprint, scaling and arranging it to suit each area's width, length, and aspect ratio
  while preserving the motif's recognizable identity and colors. Follow the handle and cup
  sleeve curvature, perspective, fabric shape, seams, lighting, and occlusion. Render the new
  motif as realistic woven textile decoration integrated into the fabric, with natural weave,
  stitching, thickness, shadows, and material detail—not as a flat pasted image or sticker.
  Preserve everything else in Image A exactly: the {preserved_carrier_fabric}, complete
  product construction and silhouette, transparent cup, lid, straw, central red maple-leaf
  emblem and all text, proportions, camera angle, lighting, shadows, original background,
  and product-photography style. Do not modify, cover, redraw, recolor, move, or redesign
  anything outside those three original black-and-white motif bands."""
    elif black_hongye_shirt:
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
  Keep the complete bag and complete shoulder-strap loop inside the canvas, including the
  strap apex, bag bottom, both side edges, and all hardware. Zoom out and leave clear
  background margin on all four sides; the full product including its strap must occupy no
  more than approximately 85% of the image height. Never use a close-up or crop any product
  edge. This framing requirement overrides Image A's original product scale.
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

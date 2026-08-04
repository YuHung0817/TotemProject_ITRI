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
    school_bag = request.product in {"台灣高中生側背書包", "復古側背書包"}
    phone_lanyard = request.product == "圖騰織帶手機掛繩"
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
    if school_bag:
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
        request.product in {"台灣高中生側背書包", "復古側背書包"}
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

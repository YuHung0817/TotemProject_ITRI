import base64
from pathlib import Path
from typing import Any, BinaryIO

from openai import OpenAI

from app.core.config import get_settings
from app.prompts.product_preview import build_product_mockup_prompt
from app.services.storage_service import image_url, store_image_bytes


def create_product_preview(
    client: OpenAI,
    motif_path: Path,
    request: Any,
    variant_index: int,
    product_reference: BinaryIO | None = None,
) -> dict[str, Any]:
    prompt = build_product_mockup_prompt(request, variant_index)
    if product_reference is not None:
        prompt = f"""
TWO-IMAGE EDITING INSTRUCTIONS:
- The first uploaded image is the PRODUCT REFERENCE. Preserve its product category, body
  shape, proportions, flap, seams, gussets, strap, hardware, construction, and camera view.
- The second uploaded image is the FINAL MOTIF ARTWORK. Preserve the motif exactly.
- Produce one realistic final product photograph by applying only the second image's motif
  to the first image's product at the requested placement.
- Do not copy the reference image's background text, labels, logos, or existing decoration.
- Do not merge the two source images side by side and do not output a collage.

{prompt}
""".strip()
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
            model=get_settings().openai_image_model,
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

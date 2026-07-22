import base64
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.prompts.product_preview import build_product_mockup_prompt
from app.services.storage_service import image_url, store_image_bytes


def create_product_preview(
    client: OpenAI,
    motif_path: Path,
    request: Any,
    variant_index: int,
) -> dict[str, Any]:
    prompt = build_product_mockup_prompt(request, variant_index)
    with motif_path.open("rb") as image_file:
        response = client.images.edit(
            model=get_settings().openai_image_model,
            image=image_file,
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

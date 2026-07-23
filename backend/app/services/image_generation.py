import base64
import colorsys
import json
import random
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from openai import OpenAI
from PIL import Image

from app.core.config import get_settings
from app.core.console import safe_print
from app.prompts.options import PALETTE_COLORS
from app.schemas.image import GenerateRequest
from app.services.storage_service import image_path, image_url
from app.services.image_processing import (
    crop_horizontal_background_margin,
    extract_dominant_palette,
    recolor_flat_motif,
    save_image_from_base64,
    save_source_image,
    REPEAT_COUNT,
)
from app.services.prompt_compiler import build_generation_prompt

DEFAULT_MODEL = get_settings().openai_image_model
DEFAULT_QUALITY = "high"
GENERATION_SIZE = "1536x1024"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def print_prompt_comparison(prompt: str, revised_prompt: str | None) -> None:
    safe_print(f"\n[prompt comparison] sent prompt chars: {len(prompt)}")
    if not revised_prompt:
        safe_print("[prompt comparison] revised_prompt: <empty>\n")
        return

    safe_print(f"[prompt comparison] revised_prompt chars: {len(revised_prompt)}")


def palette_record(source: Image.Image, color_count: int = 5) -> dict[str, Any]:
    colors = extract_dominant_palette(source.convert("RGB"), color_count=color_count)
    return {"colors": [{"rgb": list(color)} for color in colors]}


def record_palette_colors(record: dict[str, Any]) -> list[tuple[int, int, int]]:
    """Return the record's actual color set, independent of its display name."""
    colors = [
        tuple(int(channel) for channel in item.get("rgb", []))
        for item in (record.get("palette") or {}).get("colors", [])
        if len(item.get("rgb", [])) == 3
    ]
    if colors:
        return colors[:5]
    palette_name = record.get("palette_name")
    if palette_name in PALETTE_COLORS:
        return list(PALETTE_COLORS[palette_name])
    source_path = image_path(record.get("original_filename", ""))
    if source_path.exists():
        with Image.open(source_path) as source:
            return extract_dominant_palette(source.convert("RGB"), color_count=5)
    return []


def palette_instruction_from_colors(colors: list[tuple[int, int, int]]) -> str:
    """Tell the image model the same set that Pillow will enforce afterwards."""
    if not colors:
        return ""
    return (
        "Use only this exact color set (RGB), with no additional colors: "
        + ", ".join(f"rgb{tuple(color)}" for color in colors)
        + ". The colors may exchange positions within the motif."
    )


def self_contained_fields(
    request: GenerateRequest,
    compiled_prompt: str,
    source: Image.Image,
    filename: str,
    original_filename: str,
) -> dict[str, Any]:
    return {
        "files": {"repeat": filename, "original": original_filename},
        "generation": {
            "user_prompt": request.prompt,
            "elements": list(request.elements),
            "compiled_prompt": compiled_prompt,
        },
        "palette": palette_record(source),
    }


def generate_one_image(
    client: OpenAI, request: GenerateRequest, variant_index: int
) -> dict[str, Any]:
    image_id = uuid.uuid4().hex[:12]
    prompt = build_generation_prompt(client, request, variant_index)
    safe_print(f"[image generation] prompt chars: {len(prompt)}")
    response = client.images.generate(
        model=DEFAULT_MODEL,
        prompt=prompt,
        size=GENERATION_SIZE,
        quality=DEFAULT_QUALITY,
        output_format="png",
    )
    image_data = response.data[0]
    revised_prompt = getattr(image_data, "revised_prompt", None)
    print_prompt_comparison(prompt, revised_prompt)
    if not image_data.b64_json:
        raise RuntimeError("Image API did not return b64_json data.")

    filename, original_filename = save_image_from_base64(image_data.b64_json, image_id)
    return {
        "id": image_id,
        "filename": filename,
        "url": image_url(filename),
        "original_filename": original_filename,
        "original_url": image_url(original_filename),
        "created_at": utc_timestamp(),
        "prompt": prompt,
        "revised_prompt": revised_prompt,
        "request": {
            **request.model_dump(),
            "size": GENERATION_SIZE,
            "quality": DEFAULT_QUALITY,
            "repeat_count": REPEAT_COUNT,
        },
    }


def generate_random_palette_variants(
    client: OpenAI, request: GenerateRequest
) -> list[dict[str, Any]]:
    """Generate one motif, then create four geometry-identical random palette versions."""
    selected_palettes = random.sample(list(PALETTE_COLORS), k=4)
    prompt = build_generation_prompt(client, request, 0)
    safe_print(f"[image generation] prompt chars: {len(prompt)}")
    response = client.images.generate(
        model=DEFAULT_MODEL,
        prompt=prompt,
        size=GENERATION_SIZE,
        quality=DEFAULT_QUALITY,
        output_format="png",
    )
    image_data = response.data[0]
    revised_prompt = getattr(image_data, "revised_prompt", None)
    print_prompt_comparison(prompt, revised_prompt)
    if not image_data.b64_json:
        raise RuntimeError("Image API did not return b64_json data.")

    source = Image.open(BytesIO(base64.b64decode(image_data.b64_json))).convert("RGB")
    source = crop_horizontal_background_margin(source)
    source_palette = extract_dominant_palette(source, color_count=5)
    created_at = utc_timestamp()
    records = []

    for palette_name in selected_palettes:
        image_id = uuid.uuid4().hex[:12]
        recolored = recolor_flat_motif(source, source_palette, PALETTE_COLORS[palette_name])
        filename, original_filename = save_source_image(recolored, image_id, crop_margin=False)
        records.append(
            {
                "id": image_id,
                "filename": filename,
                "url": image_url(filename),
                "original_filename": original_filename,
                "original_url": image_url(original_filename),
                "totem_url": image_url(filename),
                "created_at": created_at,
                "prompt": prompt,
                "revised_prompt": revised_prompt,
                "totem_prompt": prompt,
                "request": request.model_dump(),
                "assets": {
                    "motif": {
                        "type": "motif",
                        "filename": filename,
                        "url": image_url(filename),
                        "saved": False,
                        "favorite": False,
                        "parameters": None,
                    }
                },
                "palette_name": palette_name,
                "score": None,
                "score_reason": None,
                **self_contained_fields(request, prompt, recolored, filename, original_filename),
            }
        )

    return records


def regenerate_palette_variant(
    client: OpenAI,
    request: GenerateRequest,
    palette_name: str | None,
    target_palette: list[tuple[int, int, int]] | None = None,
) -> dict[str, Any]:
    """Generate a new motif and preserve the selected record's output palette."""
    prompt = build_generation_prompt(client, request, 0)
    safe_print(f"[image generation] prompt chars: {len(prompt)}")
    response = client.images.generate(
        model=DEFAULT_MODEL,
        prompt=prompt,
        size=GENERATION_SIZE,
        quality=DEFAULT_QUALITY,
        output_format="png",
    )
    image_data = response.data[0]
    revised_prompt = getattr(image_data, "revised_prompt", None)
    print_prompt_comparison(prompt, revised_prompt)
    if not image_data.b64_json:
        raise RuntimeError("Image API did not return b64_json data.")

    source = Image.open(BytesIO(base64.b64decode(image_data.b64_json))).convert("RGB")
    source = crop_horizontal_background_margin(source)
    colors = target_palette or (
        list(PALETTE_COLORS[palette_name]) if palette_name in PALETTE_COLORS else []
    )
    if colors:
        source_palette = extract_dominant_palette(source, color_count=len(colors))
        source = recolor_flat_motif(source, source_palette, colors)

    image_id = uuid.uuid4().hex[:12]
    filename, original_filename = save_source_image(source, image_id, crop_margin=False)
    return {
        "id": image_id,
        "filename": filename,
        "url": image_url(filename),
        "original_filename": original_filename,
        "original_url": image_url(original_filename),
        "totem_url": image_url(filename),
        "created_at": utc_timestamp(),
        "prompt": prompt,
        "revised_prompt": revised_prompt,
        "totem_prompt": prompt,
        "request": request.model_dump(),
        "assets": {
            "motif": {
                "type": "motif",
                "filename": filename,
                "url": image_url(filename),
                "saved": False,
                "favorite": False,
                "parameters": None,
            }
        },
        "palette_name": palette_name,
        "score": None,
        "score_reason": None,
        **self_contained_fields(request, prompt, source, filename, original_filename),
    }


def regenerate_from_record(client: OpenAI, old: dict[str, Any]) -> dict[str, Any]:
    """Regenerate from one self-contained record without recompiling its prompt."""
    generation = old.get("generation") or {}
    prompt = generation.get("compiled_prompt") or old.get("totem_prompt") or old["prompt"]
    request = GenerateRequest(
        prompt=generation.get("user_prompt", old.get("request", {}).get("prompt", "")),
        elements=generation.get("elements", old.get("request", {}).get("elements", [])),
    )
    safe_print(f"[image regeneration] stored prompt chars: {len(prompt)}")
    response = client.images.generate(
        model=DEFAULT_MODEL,
        prompt=prompt,
        size=GENERATION_SIZE,
        quality=DEFAULT_QUALITY,
        output_format="png",
    )
    image_data = response.data[0]
    if not image_data.b64_json:
        raise RuntimeError("Image API did not return b64_json data.")
    source = Image.open(BytesIO(base64.b64decode(image_data.b64_json))).convert("RGB")
    source = crop_horizontal_background_margin(source)
    stored_colors = record_palette_colors(old)
    if stored_colors:
        source_palette = extract_dominant_palette(source, color_count=len(stored_colors))
        source = recolor_flat_motif(source, source_palette, stored_colors)
    image_id = uuid.uuid4().hex[:12]
    filename, original_filename = save_source_image(source, image_id, crop_margin=False)
    return {
        "id": image_id,
        "filename": filename,
        "url": image_url(filename),
        "original_filename": original_filename,
        "original_url": image_url(original_filename),
        "totem_url": image_url(filename),
        "created_at": utc_timestamp(),
        "prompt": prompt,
        "revised_prompt": getattr(image_data, "revised_prompt", None),
        "totem_prompt": prompt,
        "request": request.model_dump(),
        "assets": {
            "motif": {
                "type": "motif",
                "filename": filename,
                "url": image_url(filename),
                "saved": False,
                "favorite": False,
                "parameters": None,
            }
        },
        "palette_name": old.get("palette_name"),
        "score": None,
        "score_reason": None,
        **self_contained_fields(request, prompt, source, filename, original_filename),
    }


NAMED_COLORS = {
    "紅色": (181, 43, 38),
    "綠色": (40, 110, 65),
    "藍色": (35, 76, 125),
    "黃色": (220, 170, 38),
    "黑色": (21, 21, 21),
    "白色": (244, 239, 226),
    "紫色": (105, 65, 125),
}


def recolor_existing_variant(
    old: dict[str, Any],
    instruction: str,
    client: OpenAI | None = None,
) -> dict[str, Any]:
    """Recolor an existing motif with Pillow only; no generative API call."""
    source_path = image_path(old["original_filename"])
    source = Image.open(source_path).convert("RGB")
    compact = instruction.replace(" ", "")
    replacement: tuple[str, str] | None = next(
        (
            (start, end)
            for start in NAMED_COLORS
            for end in NAMED_COLORS
            if start != end and f"{start}換成{end}" in compact
        ),
        None,
    )
    palette_name: str | None = old.get("palette_name")
    replacements: list[tuple[tuple[int, int, int], tuple[int, int, int], str]] = []

    if replacement and client is None:
        start, end = replacement
        replacements = [(NAMED_COLORS[start], NAMED_COLORS[end], f"{start}→{end}")]
    elif instruction != "隨機更換配色" and client is not None:
        current_palette = extract_dominant_palette(source, color_count=5)
        resolver_prompt = f"""You convert a Chinese color-edit request into pixel replacements.
Current image palette (source_rgb MUST be exactly one of these RGB values):
{json.dumps(current_palette)}

User request:
{instruction}

Interpret flexible color descriptions such as 奶茶色, 霧霾藍, 珊瑚橘, 墨綠色,
or relative descriptions. Return JSON only, without markdown:
{{"confidence":0.0,"replacements":[{{"source_rgb":[0,0,0],"target_rgb":[0,0,0],"source_name":"", "target_name":""}}]}}
Use at most four replacements. target_rgb may be any RGB color. If the request is ambiguous,
return low confidence and an empty replacements list. If a generic source color such as red
matches multiple palette entries with different shades, include every matching source entry."""
        response = client.responses.create(
            model=get_settings().openai_prompt_compiler_model,
            input=resolver_prompt,
        )
        text = getattr(response, "output_text", "").strip()
        start_index, end_index = text.find("{"), text.rfind("}") + 1
        parsed = (
            json.loads(text[start_index:end_index])
            if start_index >= 0 and end_index > start_index
            else {}
        )
        confidence = float(parsed.get("confidence", 0))
        palette_set = {tuple(color) for color in current_palette}
        if confidence < 0.6:
            raise ValueError("無法確定要替換的顏色，請更明確描述來源色與目標色。")
        for item in parsed.get("replacements", [])[:4]:
            source_rgb = tuple(int(value) for value in item.get("source_rgb", []))
            target_rgb = tuple(max(0, min(255, int(value))) for value in item.get("target_rgb", []))
            if len(source_rgb) == 3 and len(target_rgb) == 3 and source_rgb in palette_set:
                label = (
                    f"{item.get('source_name', source_rgb)}→{item.get('target_name', target_rgb)}"
                )
                replacements.append((source_rgb, target_rgb, label))
        if not replacements:
            raise ValueError("沒有找到可安全執行的顏色替換。")
        expanded: dict[tuple[int, int, int], tuple[tuple[int, int, int], str]] = {}
        for source_rgb, target_rgb, label in replacements:
            source_h, source_s, source_v = colorsys.rgb_to_hsv(
                *(value / 255 for value in source_rgb)
            )
            expanded[source_rgb] = (target_rgb, label)
            if source_s < 0.25:
                continue
            for candidate in current_palette:
                candidate_rgb = tuple(candidate)
                hue, saturation, value = colorsys.rgb_to_hsv(
                    *(channel / 255 for channel in candidate_rgb)
                )
                hue_distance = min(abs(hue - source_h), 1 - abs(hue - source_h))
                if saturation >= 0.25 and hue_distance < 0.045 and abs(value - source_v) < 0.45:
                    expanded[candidate_rgb] = (target_rgb, label)
        replacements = [
            (source_rgb, target_and_label[0], target_and_label[1])
            for source_rgb, target_and_label in expanded.items()
        ]
        safe_print(
            "[debug:gai-color-resolution] "
            + json.dumps(
                {
                    "instruction_chars": len(instruction),
                    "palette_color_count": len(current_palette),
                    "confidence": confidence,
                    "replacement_count": len(replacements),
                },
                ensure_ascii=False,
            )
        )

    if replacements:
        pixels = []
        for pixel in source.getdata():
            nearest = min(
                replacements,
                key=lambda item: sum((left - right) ** 2 for left, right in zip(pixel, item[0])),
            )
            distance = sum((left - right) ** 2 for left, right in zip(pixel, nearest[0])) ** 0.5
            pixels.append(nearest[1] if distance < 50 else pixel)
        recolored = Image.new("RGB", source.size)
        recolored.putdata(pixels)
        palette_name = "、".join(item[2] for item in replacements)
    else:
        choices = [name for name in PALETTE_COLORS if name != old.get("palette_name")]
        palette_name = random.choice(choices or list(PALETTE_COLORS))
        source_palette = extract_dominant_palette(source, color_count=5)
        recolored = recolor_flat_motif(source, source_palette, PALETTE_COLORS[palette_name])

    image_id = uuid.uuid4().hex[:12]
    filename, original_filename = save_source_image(recolored, image_id, crop_margin=False)
    return {
        "id": image_id,
        "filename": filename,
        "url": image_url(filename),
        "original_filename": original_filename,
        "original_url": image_url(original_filename),
        "totem_url": image_url(filename),
        "created_at": utc_timestamp(),
        "prompt": instruction,
        "revised_prompt": None,
        "totem_prompt": old.get("totem_prompt") or old.get("prompt"),
        "request": old["request"],
        "assets": {
            "motif": {
                "type": "motif",
                "filename": filename,
                "url": image_url(filename),
                "saved": False,
                "favorite": False,
                "parameters": None,
            }
        },
        "palette_name": palette_name,
        "score": None,
        "score_reason": None,
        "files": {"repeat": filename, "original": original_filename},
        "generation": old.get("generation")
        or {
            "user_prompt": old.get("request", {}).get("prompt", ""),
            "elements": old.get("request", {}).get("elements", []),
            "compiled_prompt": old.get("totem_prompt") or old.get("prompt", ""),
        },
        "palette": palette_record(recolored),
    }

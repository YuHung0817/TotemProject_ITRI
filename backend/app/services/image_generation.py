import base64
import colorsys
import json
import random
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
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
RECOLOR_CONFIDENCE_THRESHOLD = 0.91
LOCAL_RECOLOR_TERMS = (
    "上方",
    "下方",
    "上面",
    "下面",
    "上下",
    "左邊",
    "右邊",
    "左右",
    "中間",
    "中央",
    "邊框",
    "外框",
    "內框",
    "邊緣",
    "背景",
    "前景",
    "局部",
    "區域",
    "部分",
)


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


def requires_localized_recolor(instruction: str, record: dict[str, Any]) -> bool:
    """Return whether a request needs spatial or element-aware image editing."""
    compact = instruction.replace(" ", "")
    if any(term in compact for term in LOCAL_RECOLOR_TERMS):
        return True
    elements = (
        (record.get("generation") or {}).get("elements")
        or (record.get("request") or {}).get("elements")
        or []
    )
    return any(str(element).replace(" ", "") in compact for element in elements)


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
    """Generate four motif variants, then enforce one shared palette with Pillow."""
    selected_colors = list(dict.fromkeys(tuple(color.rgb) for color in request.colors))
    if selected_colors:
        target_palette = (
            [(255, 255, 255), selected_colors[0]]
            if len(selected_colors) == 1
            else selected_colors
        )
        palette_name = "自訂：" + "、".join(color.name for color in request.colors)
    else:
        palette_name = random.choice(list(PALETTE_COLORS))
        target_palette = PALETTE_COLORS[palette_name]
    base_prompt = build_generation_prompt(client, request, 0)
    palette_assignment = palette_instruction_from_colors(target_palette)
    prompt = f"""{base_prompt}

Generate four separate output images. Keep the same requested motif direction, but render
four distinct motif variations using the same palette specified below. Do not create a collage
or contact sheet. Do not add gradients, shading, texture, or colors outside this RGB set.
Palette name: {palette_name!r}.
{palette_assignment}"""
    safe_print(f"[image generation] prompt chars: {len(prompt)}")
    response = client.images.generate(
        model=DEFAULT_MODEL,
        prompt=prompt,
        size=GENERATION_SIZE,
        quality=DEFAULT_QUALITY,
        output_format="png",
        n=4,
    )
    if len(response.data) != 4:
        raise RuntimeError(f"Image API returned {len(response.data)} images; expected 4.")

    created_at = utc_timestamp()
    records = []
    for image_data in response.data:
        revised_prompt = getattr(image_data, "revised_prompt", None)
        print_prompt_comparison(prompt, revised_prompt)
        if not image_data.b64_json:
            raise RuntimeError("Image API did not return b64_json data.")

        source = Image.open(BytesIO(base64.b64decode(image_data.b64_json))).convert("RGB")
        source = crop_horizontal_background_margin(source)
        source_palette = extract_dominant_palette(source, color_count=len(target_palette))
        recolored = recolor_flat_motif(source, source_palette, target_palette)
        image_id = uuid.uuid4().hex[:12]
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
    """Recolor with Pillow when resolvable, otherwise fall back to an image edit."""
    source_path = image_path(old["original_filename"])
    source = Image.open(source_path).convert("RGB")
    if instruction == "隨機更換配色" and client is not None:
        safe_print("[換色判斷] 留空隨機換色，直接使用 Image Edit。")
        return edit_palette_with_image_model(
            old,
            "請自由選擇一組與原圖不同、視覺協調且適合此圖騰的配色，"
            "並將現有圖騰區塊隨意換色。",
            client,
            source_path,
            user_instruction=instruction,
        )
    if client is not None and requires_localized_recolor(instruction, old):
        safe_print("[換色判斷] 偵測到指定區域或元素，改用 Image Edit。")
        return edit_palette_with_image_model(old, instruction, client, source_path)
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
        if confidence < RECOLOR_CONFIDENCE_THRESHOLD:
            safe_print(
                f"[換色判斷] 信心分數過低 "
                f"({confidence:.2f} < {RECOLOR_CONFIDENCE_THRESHOLD:.2f})，"
                "改用 Image Edit。"
            )
            return edit_palette_with_image_model(old, instruction, client, source_path)
        safe_print(
            f"[換色判斷] 信心分數 ≥ {RECOLOR_CONFIDENCE_THRESHOLD:.2f} "
            f"({confidence:.2f} ≥ {RECOLOR_CONFIDENCE_THRESHOLD:.2f})。"
        )
        for item in parsed.get("replacements", [])[:4]:
            source_rgb = tuple(int(value) for value in item.get("source_rgb", []))
            target_rgb = tuple(max(0, min(255, int(value))) for value in item.get("target_rgb", []))
            if len(source_rgb) == 3 and len(target_rgb) == 3 and source_rgb in palette_set:
                label = (
                    f"{item.get('source_name', source_rgb)}→{item.get('target_name', target_rgb)}"
                )
                replacements.append((source_rgb, target_rgb, label))
        if not replacements:
            safe_print("[換色判斷] 沒有有效的像素替換項目，改用 Image Edit。")
            return edit_palette_with_image_model(old, instruction, client, source_path)
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
        safe_print("[換色判斷] 使用 Pillow 換色。")
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
        "_used_image_api": False,
    }


def edit_palette_with_image_model(
    old: dict[str, Any],
    instruction: str,
    client: OpenAI,
    source_path: Path,
    *,
    user_instruction: str | None = None,
) -> dict[str, Any]:
    """Ask the image model to interpret a palette edit that Pillow cannot resolve."""
    prompt = f"""Edit the uploaded totem artwork according to this color request:
{instruction}

This is a COLOR-ONLY edit. Preserve the original totem design as closely as possible:
- Keep the exact composition, geometry, shapes, outlines, symmetry, spacing, proportions,
  orientation, canvas size, and flat illustration style.
- Do not add, remove, replace, redraw, move, resize, or restyle any motif element.
- Do not introduce gradients, shadows, highlights, texture, depth, text, or new details.
- Change only the color of the element or region identified by the user.
- If the user names an element, such as a boar, recolor only that element.
- If the user gives only a target color and does not identify a region, inspect the artwork
  and choose the most visually suitable existing motif region or color group to recolor.
- Keep all unaffected regions and colors as close to the uploaded image as possible.

The uploaded image is the source of truth. Minimize every change beyond the requested color edit."""
    with source_path.open("rb") as image_file:
        response = client.images.edit(
            model=DEFAULT_MODEL,
            image=image_file,
            prompt=prompt,
            size=GENERATION_SIZE,
            quality=DEFAULT_QUALITY,
            output_format="png",
        )
    image_data = response.data[0]
    if not image_data.b64_json:
        raise RuntimeError("Image API did not return edited motif image data.")

    edited = Image.open(BytesIO(base64.b64decode(image_data.b64_json))).convert("RGB")
    image_id = uuid.uuid4().hex[:12]
    filename, original_filename = save_source_image(edited, image_id, crop_margin=False)
    return {
        "id": image_id,
        "filename": filename,
        "url": image_url(filename),
        "original_filename": original_filename,
        "original_url": image_url(original_filename),
        "totem_url": image_url(filename),
        "created_at": utc_timestamp(),
        "prompt": user_instruction or instruction,
        "revised_prompt": getattr(image_data, "revised_prompt", None),
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
        "palette_name": "AI 判斷換色",
        "score": None,
        "score_reason": None,
        "files": {"repeat": filename, "original": original_filename},
        "generation": old.get("generation")
        or {
            "user_prompt": old.get("request", {}).get("prompt", ""),
            "elements": old.get("request", {}).get("elements", []),
            "compiled_prompt": old.get("totem_prompt") or old.get("prompt", ""),
        },
        "palette": palette_record(edited),
        "_used_image_api": True,
    }

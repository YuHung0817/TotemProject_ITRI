import json

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import get_settings
from app.prompts.bunun import (
    BUNUN_SYSTEM_PROMPT,
    IMAGE_PROMPT_TEMPLATE,
    PROMPT_COMPILER_INSTRUCTIONS,
)
from app.prompts.options import ELEMENT_OPTIONS, VARIANT_DIRECTIONS
from app.schemas.image import GenerateRequest, MotifRevisionResolution
from app.core.console import safe_print

settings = get_settings()
PROMPT_COMPILER_MODEL = settings.openai_prompt_compiler_model
USE_PROMPT_COMPILER = settings.use_prompt_compiler
BASE_PALETTE_TEXT = (
    "Use exactly five flat colors: warm off-white background, black, red, "
    "yellow, and dark blue. Keep every color region solid and distinct."
)

REVISION_RESOLVER_INSTRUCTIONS = """
You are a design-state revision resolver. Understand the user's latest Chinese revision request
in the context of the previous Bunun motif design. Return JSON only, without markdown, using
exactly these keys:
{
  "final_elements": [""],
  "added_elements": [""],
  "removed_elements": [""],
  "excluded_elements": [""],
  "changes_palette": false,
  "palette_instruction": "",
  "revision_summary": ""
}

Rules:
1. final_elements is the complete final list after applying the latest request, not only the changed items.
2. Preserve every previous element unless the user explicitly removes, replaces, or rejects it.
3. Include newly requested preset or free-form elements even if they are not in a known UI list.
4. Abstract concepts that the user wants represented visually may also appear in final_elements.
5. Resolve negation and replacements semantically; do not use simple keyword matching.
6. excluded_elements is the complete persistent list of visual forms the user explicitly forbids.
   Carry previous exclusions forward unless the user explicitly asks to restore one. Add an explicitly
   rejected form even when it was not present in previous_elements (for example, "不要菱形").
7. changes_palette is true only when the user actually asks to change color, palette, color mood,
   brightness, saturation, or contrast. Element phrases such as "把月亮改成太陽" are not color changes.
8. If changes_palette is true, palette_instruction must faithfully state the final color request.
   Otherwise palette_instruction must be an empty string.
9. Do not invent elements, removal requests, exclusions, or color changes.
10. Do not return IDs, file paths, URLs, assets, collection state, or any database fields.
""".strip()


def resolve_motif_revision(
    client: OpenAI,
    previous_prompt: str,
    previous_elements: list[str],
    previous_palette: str | None,
    instruction: str,
    previous_exclusions: list[str] | None = None,
) -> MotifRevisionResolution:
    """Use the text model to turn a free-form revision into validated design state."""
    source = f"""Previous user intent:
{previous_prompt.strip() or "(none)"}

Previous elements (JSON):
{json.dumps(previous_elements, ensure_ascii=False)}

Previous palette name:
{previous_palette or "(not specified)"}

Previous explicit exclusions (JSON):
{json.dumps(previous_exclusions or [], ensure_ascii=False)}

Latest user revision:
{instruction.strip()}
""".strip()
    response = client.responses.create(
        model=PROMPT_COMPILER_MODEL,
        instructions=REVISION_RESOLVER_INSTRUCTIONS,
        input=source,
    )
    text = getattr(response, "output_text", "").strip()
    start, end = text.find("{"), text.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError("無法解析這次的元素修改要求，請換一種方式描述。")
    try:
        resolution = MotifRevisionResolution.model_validate_json(text[start:end])
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("無法解析這次的元素修改要求，請換一種方式描述。") from exc

    def clean(values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))

    resolution.final_elements = clean(resolution.final_elements)
    resolution.added_elements = clean(resolution.added_elements)
    resolution.removed_elements = clean(resolution.removed_elements)
    resolution.excluded_elements = clean(resolution.excluded_elements)
    if not resolution.changes_palette:
        resolution.palette_instruction = ""
    return resolution


def build_user_brief_source(request: GenerateRequest) -> str:
    selected_elements = [ELEMENT_OPTIONS.get(item, item) for item in request.elements]
    element_text = (
        "; ".join(selected_elements)
        if selected_elements
        else "No quick elements selected. Follow the free-form Chinese prompt."
    )
    user_text = request.prompt.strip() or "自由發想一款可用於商品展示的十字繡格狀圖騰"
    exclusion_section = (
        "\n\nExplicit visual exclusions (highest priority):\n"
        + "; ".join(request.excluded_elements)
        if request.excluded_elements
        else ""
    )

    return f"""
Chinese user prompt:
{user_text}

Selected motif elements:
{element_text}

Selected palette:
{request.palette_instruction.strip() or BASE_PALETTE_TEXT}
{exclusion_section}
""".strip()


def compile_user_brief(client: OpenAI, request: GenerateRequest) -> str:
    """Use a text model to convert the Chinese UI request into an English image brief.

    If the compiler call fails or is disabled, fall back to a deterministic English/Chinese mixed brief
    so the image endpoint can still work during testing.
    """
    source = build_user_brief_source(request)
    if not USE_PROMPT_COMPILER:
        return source

    try:
        response = client.responses.create(
            model=PROMPT_COMPILER_MODEL,
            instructions=PROMPT_COMPILER_INSTRUCTIONS,
            input=source,
        )
        compiled = getattr(response, "output_text", "").strip()
        if compiled:
            return compiled
    except Exception as exc:
        safe_print(f"[prompt compiler skipped] error_type={type(exc).__name__}")

    return source


def build_generation_prompt(client: OpenAI, request: GenerateRequest, variant_index: int) -> str:
    diamond_excluded = any(
        "菱形" in item or "diamond" in item.casefold() for item in request.excluded_elements
    )
    diamond_free_variants = [
        "Use a continuous zigzag and stepped-triangle band with mirrored sawtooth borders and no diamond or checkerboard forms.",
        "Build alternating chevron, staircase, and parallel-stripe panels with strong horizontal rhythm and no diamond shapes.",
        "Use octagonal flower-like, stepped-arc, and interlocking zigzag units while strictly avoiding diamonds and checkerboards.",
        "Create a symmetrical repeating strip from hooked lines, stepped triangles, chevrons, and high-contrast blocks without diamonds.",
    ]
    variant_pool = diamond_free_variants if diamond_excluded else VARIANT_DIRECTIONS
    variant_text = variant_pool[variant_index % len(variant_pool)]
    compiled_user_brief = compile_user_brief(client, request)
    exclusion_text = ""
    if request.excluded_elements:
        exclusion_text = (
            "HIGHEST-PRIORITY USER EXCLUSIONS\n"
            "Do not depict, imply, or reintroduce these forms anywhere: "
            + ", ".join(request.excluded_elements)
            + ". These exclusions override every default visual-language, composition, and variant rule above. "
            "Use other Bunun geometric vocabulary such as zigzags, stepped triangles, chevrons, staircase forms, "
            "parallel bands, hooked lines, or octagonal flower-like units instead."
        )

    return "\n\n".join(
        [
            BUNUN_SYSTEM_PROMPT,
            IMAGE_PROMPT_TEMPLATE.format(
                variant_text=variant_text,
                compiled_user_brief=compiled_user_brief,
                exclusion_text=exclusion_text,
            ),
        ]
    )

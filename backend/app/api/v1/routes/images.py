import copy
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, BinaryIO, Literal
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import FileResponse, Response
from openai import APITimeoutError, OpenAI
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.api.errors import api_error
from app.core.console import log_event
from app.core.secrets import SecretConfigurationError, get_openai_api_key
from app.db.session import get_db
from app.schemas.image import (
    AssetCollectionsRequest,
    AssetStateRequest,
    CollectionCreateRequest,
    CollectionRecord,
    CollectionRenameRequest,
    GalleryAsset,
    GenerateRequest,
    GenerateResponse,
    ImageRecord,
    ProductPreviewRequest,
    RegenerateRequest,
)
from app.services.collection_service import FAVORITES_ID
from app.services.database_catalog_service import (
    collection_exists,
    create_collection,
    delete_collection,
    delete_asset,
    find_record,
    list_collections,
    list_product_preview_records,
    list_records,
    rename_collection,
    save_record,
    save_records,
)
from app.services.image_generation import (
    edit_motif_elements_with_image_model,
    generate_random_palette_variants,
    recolor_existing_variant,
    regenerate_from_record,
)
from app.services.generation_job_service import (
    acquire_generation_job,
    complete_generation_job,
    fail_generation_job,
    job_images,
)
from app.services.image_processing import create_cross_stitch_chart
from app.services.product_preview import create_product_preview
from app.services.product_reference_service import product_reference_path
from app.services.storage_service import (
    StorageCapacityError,
    delete_image,
    ensure_storage_capacity,
    image_path,
    image_url,
    store_image_bytes,
)
from app.prompts.product_preview import DISPLAY_STYLE_OPTIONS, PRODUCT_PLACEMENT_OPTIONS
from app.services.prompt_compiler import (
    resolve_motif_revision,
    resolve_product_preview_instruction,
)

router = APIRouter(prefix="/images")
IMAGE_API_TIMEOUT_SECONDS = 300.0
IMAGE_API_MAX_RETRIES = 0
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=16, max_length=100),
]
ChatroomId = Annotated[str | None, Header(alias="X-Chatroom-Id", max_length=32)]
ClientExchangeId = Annotated[
    str | None, Header(alias="X-Client-Exchange-Id", max_length=100)
]


def choose_product_reference_source(
    *,
    changes_product: bool,
    has_current_preview: bool,
    has_target_reference: bool,
) -> Literal["current_preview", "built_in", "none"]:
    if not changes_product and has_current_preview:
        return "current_preview"
    if has_target_reference:
        return "built_in"
    return "none"


def generation_context(
    data: dict, chatroom_id: str | None, client_exchange_id: str | None
) -> dict:
    return {
        **data,
        **({"chatroom_id": chatroom_id} if chatroom_id else {}),
        **({"client_exchange_id": client_exchange_id} if client_exchange_id else {}),
    }


def add_preview(record: dict, request: ProductPreviewRequest, result: dict) -> None:
    """Attach one generated product photo to an image record."""
    record.setdefault("assets", {})
    previous = record["assets"].get("preview") or {}
    record["assets"]["preview"] = {
        "type": "preview",
        "filename": result["filename"],
        "url": result["url"],
        "saved": previous.get("saved", False),
        "favorite": previous.get("favorite", False),
        "collection_ids": list(previous.get("collection_ids", [])),
        "parameters": {
            **request.model_dump(),
            "reference_source": result.get("reference_source")
            or ("built_in" if product_reference_path(request.product) else "none"),
            "reference_filename": result.get("reference_filename")
            or (
                product_reference_path(request.product).name
                if product_reference_path(request.product)
                else None
            ),
        },
    }


def save_preview_version(
    db: Session,
    source: dict,
    user_id: str,
    request: ProductPreviewRequest,
    result: dict,
    *,
    separate_message: bool = False,
) -> dict:
    """Save a preview, preserving the source record for a separate chat reply."""
    if not separate_message and not (source.get("assets") or {}).get("preview"):
        add_preview(source, request, result)
        return save_record(db, source, user_id, refresh_expiry=True)

    variant = copy.deepcopy(source)
    variant["id"] = uuid.uuid4().hex[:12]
    variant["created_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    variant["derived_from"] = source["id"]
    for asset in variant.get("assets", {}).values():
        asset["saved"] = False
        asset["favorite"] = False
        asset["collection_ids"] = []
    add_preview(variant, request, result)
    return save_record(db, variant, user_id, parent_image_id=source["id"])


def resolve_product_preview_request(
    request: ProductPreviewRequest, source: dict
) -> tuple[ProductPreviewRequest, bool]:
    instruction = request.instruction.strip()
    if not instruction:
        return request, False
    previous_parameters = (
        ((source.get("assets") or {}).get("preview") or {}).get("parameters") or {}
    )
    current_product = previous_parameters.get("product")
    resolution = resolve_product_preview_instruction(
        client(), instruction, current_product=current_product
    )
    product = resolution.reference_product or resolution.product
    preview_prompt = instruction
    if resolution.additional_instruction:
        preview_prompt = (
            f"{instruction}\nAdditional resolved requirement: "
            f"{resolution.additional_instruction}"
        )
    return (
        request.model_copy(
            update={
                "instruction": instruction,
                "product": product,
                "placement": resolution.placement,
                "display_style": resolution.display_style,
                "preview_prompt": preview_prompt,
            }
        ),
        resolution.changes_product,
    )


def fallback_product_preview_request(
    request: ProductPreviewRequest,
    source: dict,
) -> ProductPreviewRequest:
    """Preserve known product state while passing the raw revision to Image Edit."""
    previous_parameters = (
        ((source.get("assets") or {}).get("preview") or {}).get("parameters") or {}
    )
    return request.model_copy(
        update={
            "instruction": request.instruction.strip(),
            "product": previous_parameters.get("product") or request.product,
            "placement": previous_parameters.get("placement") or request.placement,
            "display_style": (
                previous_parameters.get("display_style") or request.display_style
            ),
            "preview_prompt": request.instruction.strip(),
        }
    )


def generate_preview_result(
    record: dict,
    request: ProductPreviewRequest,
    product_reference: BinaryIO | None = None,
) -> dict:
    motif_path = image_path(Path(record.get("original_filename") or record["filename"]).name)
    if not motif_path.exists():
        raise HTTPException(404, "Original motif image file not found")
    try:
        if product_reference is None:
            reference_path = product_reference_path(request.product)
            if reference_path is not None:
                with reference_path.open("rb") as reference_file:
                    return create_product_preview(
                        client(),
                        motif_path,
                        request,
                        0,
                        product_reference=reference_file,
                        product_reference_role="target",
                    )
        return create_product_preview(
            client(),
            motif_path,
            request,
            0,
            product_reference=product_reference,
            product_reference_role="current",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise internal_server_error("product_preview", exc) from exc


def inherit_product_preview(
    db: Session,
    source: dict,
    revised: dict,
    user_id: str,
    preview_mode: Literal["current", "template"] = "current",
) -> dict:
    """Reapply a revised motif to the source record's existing product preview."""
    preview_asset = (source.get("assets") or {}).get("preview") or {}
    parameters = preview_asset.get("parameters") or {}
    preview_filename = Path(preview_asset.get("filename") or "").name
    if not parameters.get("product"):
        return revised
    if preview_mode == "template":
        request = ProductPreviewRequest(
            product=parameters["product"],
            placement="AI自動決定位置",
            display_style="白色商品＋白底",
            preview_size=parameters.get("preview_size", "1024x1024"),
            preview_quality=parameters.get("preview_quality", "medium"),
        )
        preview_path = None
    else:
        if not preview_filename:
            return revised
        preview_path = image_path(preview_filename)
        if not preview_path.is_file():
            return revised
        request = ProductPreviewRequest.model_validate(parameters).model_copy(
            update={
                "instruction": (
                    "Keep the exact same product, product color, material, camera view, "
                    "composition, background, and motif placement. Replace only the old "
                    "motif artwork with the newly uploaded motif artwork."
                ),
                "preview_prompt": (
                    "Preserve the complete current product presentation and replace only "
                    "its motif with the new motif."
                ),
            }
        )
    try:
        if preview_path is None:
            result = generate_preview_result(revised, request)
        else:
            with preview_path.open("rb") as current_preview:
                result = generate_preview_result(
                    revised,
                    request,
                    product_reference=current_preview,
                )
            result["reference_source"] = "current_preview"
            result["reference_filename"] = preview_filename
        add_preview(revised, request, result)
        revised = save_record(
            db,
            revised,
            user_id,
            parent_image_id=source["id"],
        )
        log_event(
            "operation_succeeded",
            operation="inherit_product_preview",
            image_id=revised["id"],
            source_image_id=source["id"],
        )
    except Exception as exc:
        log_event(
            "operation_failed",
            operation="inherit_product_preview",
            image_id=revised["id"],
            source_image_id=source["id"],
            error_type=type(exc).__name__,
        )
    return revised


def gallery_asset(record: dict, asset_type: str, asset: dict) -> GalleryAsset:
    elements = (
        (record.get("generation") or {}).get("elements")
        or (record.get("request") or {}).get("elements")
        or []
    )
    return GalleryAsset(
        record_id=record["id"],
        asset_type=asset_type,
        url=asset["url"],
        saved=asset.get("saved", False),
        favorite=asset.get("favorite", False),
        collection_ids=list(asset.get("collection_ids", [])),
        created_at=record["created_at"],
        expires_at=record["expires_at"],
        elements=elements,
        width=asset.get("width"),
        height=asset.get("height"),
    )


def client() -> OpenAI:
    try:
        api_key = get_openai_api_key()
    except SecretConfigurationError as exc:
        raise HTTPException(503, "Image generation is temporarily unavailable") from exc
    if not api_key:
        raise HTTPException(400, "OPENAI_API_KEY is not set in the project .env file")
    return OpenAI(
        api_key=api_key,
        timeout=IMAGE_API_TIMEOUT_SECONDS,
        max_retries=IMAGE_API_MAX_RETRIES,
    )


def internal_server_error(
    operation: str,
    error: Exception,
    *,
    image_id: str | None = None,
    job_id: str | None = None,
) -> HTTPException:
    log_event(
        "operation_failed",
        operation=operation,
        image_id=image_id,
        job_id=job_id,
        error_type=type(error).__name__,
    )
    if isinstance(error, APITimeoutError):
        return api_error(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "image_generation_timeout",
        )
    return api_error(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "image_generation_failed",
    )


def require_storage_capacity(
    operation: str,
    *,
    image_id: str | None = None,
) -> None:
    try:
        ensure_storage_capacity()
    except StorageCapacityError as exc:
        log_event(
            "operation_rejected",
            operation=operation,
            image_id=image_id,
            reason="storage_capacity",
        )
        raise HTTPException(
            507,
            {
                "code": "storage_capacity_reached",
                "message": "圖片儲存空間不足，暫時無法建立新圖片。",
            },
        ) from exc


@router.post("/generate", response_model=GenerateResponse)
def generate_images(
    request: GenerateRequest,
    idempotency_key: IdempotencyKey,
    user: CurrentUser,
    chatroom_id: ChatroomId = None,
    client_exchange_id: ClientExchangeId = None,
    db: Session = Depends(get_db),
) -> GenerateResponse:
    require_storage_capacity("motif_generate")
    log_event(
        "operation_started",
        operation="motif_generate",
        prompt_chars=len(request.prompt),
        element_count=len(request.elements),
        excluded_element_count=len(request.excluded_elements),
    )
    job = acquire_generation_job(
        db,
        idempotency_key,
        generation_context(request.model_dump(), chatroom_id, client_exchange_id),
        user.id,
    )
    if job.status == "succeeded":
        return GenerateResponse(images=job_images(db, job))
    try:
        new_records = generate_random_palette_variants(client(), request)
        saved_records = save_records(db, new_records, user.id)
        if request.carrier:
            product = (
                request.carrier
                if request.carrier in PRODUCT_PLACEMENT_OPTIONS
                else random.choice(list(PRODUCT_PLACEMENT_OPTIONS))
            )
            completed_records: list[dict] = []
            for record in saved_records:
                preview_request = ProductPreviewRequest(
                    product=product,
                    placement="AI自動決定位置",
                    display_style="白色商品＋白底",
                )
                preview_result = generate_preview_result(record, preview_request)
                current_record = find_record(db, record["id"], user.id)
                add_preview(current_record, preview_request, preview_result)
                completed_records.append(
                    save_record(db, current_record, user.id, refresh_expiry=True)
                )
            saved_records = completed_records
        complete_generation_job(db, job, [record["id"] for record in saved_records])
    except HTTPException as exc:
        fail_generation_job(db, job.id, exc)
        raise
    except Exception as exc:
        fail_generation_job(db, job.id, exc)
        raise internal_server_error(
            "motif_generate", exc, job_id=job.id
        ) from exc
    log_event(
        "operation_succeeded",
        operation="motif_generate",
        job_id=job.id,
        image_count=len(saved_records),
    )
    return GenerateResponse(images=[ImageRecord(**x) for x in saved_records])


@router.get("", response_model=list[ImageRecord])
def list_images(user: CurrentUser, db: Session = Depends(get_db)) -> list[ImageRecord]:
    records = list_records(db, user.id)
    return [ImageRecord(**record) for record in records]


@router.get("/product-references/{product}", include_in_schema=False)
def product_reference_image(product: str) -> FileResponse:
    path = product_reference_path(product)
    if path is None:
        raise HTTPException(404, "Product reference image not found")
    with path.open("rb") as image_file:
        header = image_file.read(12)
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        media_type = "image/webp"
    elif header.startswith(b"\x89PNG\r\n\x1a\n"):
        media_type = "image/png"
    else:
        media_type = "image/jpeg"
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/assets", response_model=list[GalleryAsset])
def list_assets(
    user: CurrentUser,
    saved: bool | None = None,
    favorite: bool | None = None,
    db: Session = Depends(get_db),
) -> list[GalleryAsset]:
    results: list[GalleryAsset] = []
    seen_assets: set[tuple[str, str]] = set()

    records = sorted(
        list_records(db, user.id),
        key=lambda item: item.get("created_at", ""),
    )
    for record in records:
        elements = (
            (record.get("generation") or {}).get("elements")
            or (record.get("request") or {}).get("elements")
            or []
        )

        for asset_type, asset in record.get("assets", {}).items():
            url = asset.get("url")

            if not url:
                continue

            if saved is not None:
                if asset.get("saved", False) != saved:
                    continue

            if favorite is not None:
                if asset.get("favorite", False) != favorite:
                    continue

            asset_key = (asset_type, url)
            if asset_key in seen_assets:
                continue
            seen_assets.add(asset_key)

            results.append(
                GalleryAsset(
                    record_id=record["id"],
                    asset_type=asset_type,
                    url=url,
                    saved=asset.get("saved", False),
                    favorite=asset.get("favorite", False),
                    collection_ids=list(asset.get("collection_ids", [])),
                    created_at=record["created_at"],
                    expires_at=record["expires_at"],
                    elements=elements,
                    width=asset.get("width"),
                    height=asset.get("height"),
                )
            )

    results.sort(key=lambda item: item.created_at, reverse=True)
    return results


@router.get("/collections", response_model=list[CollectionRecord])
def list_collection_folders(
    user: CurrentUser, db: Session = Depends(get_db)
) -> list[CollectionRecord]:
    return [CollectionRecord(**collection) for collection in list_collections(db, user.id)]


@router.post("/collections", response_model=CollectionRecord)
def add_collection_folder(
    request: CollectionCreateRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> CollectionRecord:
    return CollectionRecord(**create_collection(db, user.id, request.name))


@router.patch("/collections/{collection_id}", response_model=CollectionRecord)
def rename_collection_folder(
    collection_id: str,
    request: CollectionRenameRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> CollectionRecord:
    return CollectionRecord(
        **rename_collection(db, collection_id, user.id, request.name)
    )


@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_collection_folder(
    collection_id: str, user: CurrentUser, db: Session = Depends(get_db)
) -> Response:
    delete_collection(db, collection_id, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/collections/{collection_id}/assets", response_model=list[GalleryAsset])
def list_collection_assets(
    collection_id: str, user: CurrentUser, db: Session = Depends(get_db)
) -> list[GalleryAsset]:
    if not collection_exists(db, collection_id, user.id):
        raise HTTPException(404, "Collection not found")
    return [
        gallery_asset(record, asset_type, asset)
        for record in list_records(db, user.id)
        for asset_type, asset in record.get("assets", {}).items()
        if collection_id in asset.get("collection_ids", [])
        and asset.get("url")
    ]


@router.get("/{image_id}/cross-stitch-chart")
def chart(
    image_id: str,
    user: CurrentUser,
    width: int = 100,
    height: int = 50,
    colors: int = 5,
    db: Session = Depends(get_db),
) -> Response:
    log_event(
        "operation_started",
        operation="cross_stitch_chart",
        image_id=image_id,
        width=width,
        height=height,
        color_count=colors,
    )
    if not 10 <= width <= 300 or not 10 <= height <= 300 or not 2 <= colors <= 20:
        raise HTTPException(422, "Invalid chart dimensions or colors")
    record = find_record(db, image_id, user.id)
    path = image_path(Path(record.get("original_filename") or record["filename"]).name)
    if not path.exists():
        raise HTTPException(404, "Original image file not found")
    return Response(
        create_cross_stitch_chart(path, width, height, colors),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@router.patch("/{image_id}/assets/{asset_type}", response_model=ImageRecord)
def update_asset(
    image_id: str,
    asset_type: Literal["motif", "preview", "chart"],
    request: AssetStateRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ImageRecord:
    record = find_record(db, image_id, user.id)
    record.setdefault("assets", {})

    asset = record["assets"].get(asset_type)
    generated_asset = asset_type == "chart" and asset is None

    if asset_type == "chart" and asset is None:
        # 取得 parameters
        parameters = request.parameters or {}

        width = int(parameters.get("width", 100))
        height = int(parameters.get("height", 50))
        colors = int(parameters.get("colors", 5))

        if not 10 <= width <= 300:
            raise HTTPException(422, "Invalid chart width")

        if not 10 <= height <= 300:
            raise HTTPException(422, "Invalid chart height")

        if not 2 <= colors <= 20:
            raise HTTPException(422, "Invalid chart colors")

        # 呼叫 create_cross_stitch_chart()
        # 寫入固定 PNG
        source_path = image_path(Path(record.get("original_filename") or record["filename"]).name)

        if not source_path.exists():
            raise HTTPException(404, "Original image file not found")
        chart_bytes = create_cross_stitch_chart(
            source_path,
            width,
            height,
            colors,
        )
        chart_filename = store_image_bytes(chart_bytes, label="chart")

        # 建立 chart asset
        asset = {
            "type": "chart",
            "filename": chart_filename,
            "url": image_url(chart_filename),
            "saved": False,
            "favorite": False,
            "parameters": {
                "width": width,
                "height": height,
                "colors": colors,
            },
        }

        record["assets"]["chart"] = asset

    if asset is None:
        raise HTTPException(404, f"Asset not found: {asset_type}")

    if request.saved is not None:
        asset["saved"] = request.saved

    if request.favorite is not None:
        asset["favorite"] = request.favorite
        collection_ids = asset.setdefault("collection_ids", [])
        if request.favorite and FAVORITES_ID not in collection_ids:
            collection_ids.append(FAVORITES_ID)
        if not request.favorite and FAVORITES_ID in collection_ids:
            collection_ids.remove(FAVORITES_ID)

        if request.favorite:
            asset["saved"] = True

    return ImageRecord(
        **save_record(db, record, user.id, refresh_expiry=generated_asset)
    )


@router.patch("/{image_id}/assets/{asset_type}/collections", response_model=ImageRecord)
def update_asset_collections(
    image_id: str,
    asset_type: Literal["motif", "preview", "chart"],
    request: AssetCollectionsRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ImageRecord:
    known_ids = {item["id"] for item in list_collections(db, user.id)}
    requested_ids = list(dict.fromkeys(request.collection_ids))
    unknown_ids = set(requested_ids) - known_ids
    if unknown_ids:
        raise HTTPException(422, f"Unknown collections: {sorted(unknown_ids)}")
    record = find_record(db, image_id, user.id)
    asset = record.get("assets", {}).get(asset_type)
    if asset is None:
        raise HTTPException(404, f"Asset not found: {asset_type}")
    asset["collection_ids"] = requested_ids
    asset["favorite"] = FAVORITES_ID in requested_ids
    return ImageRecord(**save_record(db, record, user.id))


@router.post("/{image_id}/preview", response_model=ImageRecord)
def preview(
    image_id: str,
    request: ProductPreviewRequest,
    idempotency_key: IdempotencyKey,
    user: CurrentUser,
    chatroom_id: ChatroomId = None,
    client_exchange_id: ClientExchangeId = None,
    db: Session = Depends(get_db),
) -> ImageRecord:
    record = find_record(db, image_id, user.id)
    used_products = {
        str(
            ((item.get("assets") or {}).get("preview") or {})
            .get("parameters", {})
            .get("product")
        )
        for item in list_product_preview_records(db, image_id, user.id)
    }
    if request.product in used_products:
        raise HTTPException(409, "This product carrier has already been generated")
    require_storage_capacity("product_preview", image_id=image_id)
    log_event("operation_started", operation="product_preview", image_id=image_id)
    job = acquire_generation_job(
        db,
        idempotency_key,
        generation_context(
            {"operation": "product_preview", "image_id": image_id, **request.model_dump()},
            chatroom_id,
            client_exchange_id,
        ),
        user.id,
    )
    if job.status == "succeeded":
        return job_images(db, job)[0]
    try:
        result = generate_preview_result(record, request)
        # Re-read after the slow API call so concurrent collection changes survive.
        record = find_record(db, image_id, user.id)
        record = save_preview_version(
            db,
            record,
            user.id,
            request,
            result,
            # This endpoint adds a product photo after the initial generation.
            # Always preserve the source record, even if optional chat headers
            # are temporarily unavailable on the client.
            separate_message=True,
        )
        complete_generation_job(db, job, [record["id"]])
    except Exception as exc:
        fail_generation_job(db, job.id, exc)
        raise
    log_event(
        "operation_succeeded",
        operation="product_preview",
        image_id=image_id,
        job_id=job.id,
    )
    return ImageRecord(**record)


@router.get("/{image_id}/product-previews", response_model=list[ImageRecord])
def product_previews(
    image_id: str,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> list[ImageRecord]:
    return [
        ImageRecord(**record)
        for record in list_product_preview_records(db, image_id, user.id)
    ]


@router.post("/{image_id}/preview/random", response_model=ImageRecord)
def random_preview(
    image_id: str,
    idempotency_key: IdempotencyKey,
    user: CurrentUser,
    chatroom_id: ChatroomId = None,
    client_exchange_id: ClientExchangeId = None,
    db: Session = Depends(get_db),
) -> ImageRecord:
    require_storage_capacity("random_product_preview", image_id=image_id)
    record = find_record(db, image_id, user.id)
    selected_carrier = (record.get("request") or {}).get("carrier")
    product = (
        selected_carrier
        if selected_carrier in PRODUCT_PLACEMENT_OPTIONS
        else random.choice(list(PRODUCT_PLACEMENT_OPTIONS))
    )
    placement_choices = [
        placement
        for placement in PRODUCT_PLACEMENT_OPTIONS[product]
        if placement != "AI自動決定位置"
    ]
    request = ProductPreviewRequest(
        product=product,
        placement=random.choice(placement_choices),
        display_style=random.choice(list(DISPLAY_STYLE_OPTIONS)),
    )
    log_event("operation_started", operation="random_product_preview", image_id=image_id)
    job = acquire_generation_job(
        db,
        idempotency_key,
        generation_context(
            {"operation": "random_product_preview", "image_id": image_id, **request.model_dump()},
            chatroom_id,
            client_exchange_id,
        ),
        user.id,
    )
    if job.status == "succeeded":
        return job_images(db, job)[0]
    try:
        result = generate_preview_result(record, request)
        # Do not save the stale snapshot from before the image API call.
        record = find_record(db, image_id, user.id)
        record = save_preview_version(db, record, user.id, request, result)
        complete_generation_job(db, job, [record["id"]])
        return ImageRecord(**record)
    except Exception as exc:
        fail_generation_job(db, job.id, exc)
        raise


@router.post("/{image_id}/preview/variant", response_model=ImageRecord)
def preview_variant(
    image_id: str,
    request: ProductPreviewRequest,
    idempotency_key: IdempotencyKey,
    user: CurrentUser,
    chatroom_id: ChatroomId = None,
    client_exchange_id: ClientExchangeId = None,
    db: Session = Depends(get_db),
) -> ImageRecord:
    require_storage_capacity("product_preview_variant", image_id=image_id)
    source = find_record(db, image_id, user.id)
    if not request.instruction.strip() and request.product not in PRODUCT_PLACEMENT_OPTIONS:
        raise HTTPException(422, "Unsupported product")
    if (
        not request.instruction.strip()
        and request.placement not in PRODUCT_PLACEMENT_OPTIONS[request.product]
    ):
        raise HTTPException(422, "Placement is not valid for this product")
    if not request.instruction.strip() and request.display_style not in DISPLAY_STYLE_OPTIONS:
        raise HTTPException(422, "Unsupported display style")
    job = acquire_generation_job(
        db,
        idempotency_key,
        generation_context(
            {"operation": "product_preview_variant", "image_id": image_id, **request.model_dump()},
            chatroom_id,
            client_exchange_id,
        ),
        user.id,
    )
    if job.status == "succeeded":
        return job_images(db, job)[0]
    try:
        parser_fallback_reason: str | None = None
        try:
            resolved_request, changes_product = resolve_product_preview_request(
                request, source
            )
        except Exception as exc:
            resolved_request = fallback_product_preview_request(request, source)
            changes_product = False
            parser_fallback_reason = type(exc).__name__

        preview_asset = (source.get("assets") or {}).get("preview") or {}
        preview_filename = Path(preview_asset.get("filename") or "").name
        preview_path = image_path(preview_filename) if preview_filename else None
        has_current_preview = bool(preview_path and preview_path.is_file())
        reference_source = choose_product_reference_source(
            changes_product=changes_product,
            has_current_preview=has_current_preview,
            has_target_reference=product_reference_path(resolved_request.product)
            is not None,
        )
        if parser_fallback_reason:
            log_event(
                "product_preview_parser_fallback",
                image_id=image_id,
                reason=parser_fallback_reason,
                has_current_preview=has_current_preview,
            )

        if reference_source == "current_preview" and preview_path:
            with preview_path.open("rb") as current_preview:
                result = generate_preview_result(
                    source,
                    resolved_request,
                    product_reference=current_preview,
                )
            result["reference_source"] = "current_preview"
            result["reference_filename"] = preview_filename
        else:
            result = generate_preview_result(source, resolved_request)
        variant = copy.deepcopy(source)
        variant["id"] = uuid.uuid4().hex[:12]
        variant["created_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        variant["derived_from"] = image_id
        for asset in variant.get("assets", {}).values():
            asset["saved"] = False
            asset["favorite"] = False
            asset["collection_ids"] = []
        add_preview(variant, resolved_request, result)
        variant = save_record(db, variant, user.id, parent_image_id=image_id)
        complete_generation_job(db, job, [variant["id"]])
        return ImageRecord(**variant)
    except Exception as exc:
        fail_generation_job(db, job.id, exc)
        raise


@router.post("/{image_id}/regenerate", response_model=ImageRecord)
def regenerate_image(
    image_id: str,
    revision: RegenerateRequest,
    idempotency_key: IdempotencyKey,
    user: CurrentUser,
    chatroom_id: ChatroomId = None,
    client_exchange_id: ClientExchangeId = None,
    db: Session = Depends(get_db),
) -> ImageRecord:
    require_storage_capacity("motif_regenerate", image_id=image_id)
    # Validate the source before consuming quota or taking the global generation lock.
    find_record(db, image_id, user.id)
    job = acquire_generation_job(
        db,
        idempotency_key,
        generation_context(
            {"operation": "regenerate", "image_id": image_id, **revision.model_dump()},
            chatroom_id,
            client_exchange_id,
        ),
        user.id,
    )
    if job.status == "succeeded":
        return job_images(db, job)[0]
    try:
        result = _regenerate_image(image_id, revision, db, user.id)
        complete_generation_job(db, job, [result.id])
        return result
    except Exception as exc:
        fail_generation_job(db, job.id, exc)
        raise


def _regenerate_image(
    image_id: str, revision: RegenerateRequest, db: Session, user_id: str
) -> ImageRecord:
    log_event(
        "operation_started",
        operation="motif_regenerate",
        image_id=image_id,
        instruction_chars=len(revision.instruction),
    )
    old = find_record(db, image_id, user_id)
    if revision.mode == "palette":
        try:
            new = recolor_existing_variant(old, revision.instruction, client())
        except ValueError as exc:
            log_event(
                "operation_needs_clarification",
                operation="code_recolor",
                image_id=image_id,
                instruction_chars=len(revision.instruction),
            )
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            raise internal_server_error(
                "image_recolor", exc, image_id=image_id
            ) from exc
        used_image_api = bool(new.pop("_used_image_api", False))
        new = save_record(db, new, user_id, parent_image_id=image_id)
        new = inherit_product_preview(
            db, old, new, user_id, preview_mode=revision.preview_mode
        )
        log_event(
            "operation_succeeded",
            operation="image_recolor" if used_image_api else "code_recolor",
            image_id=new["id"],
            source_image_id=image_id,
            used_image_api=used_image_api,
        )
        return ImageRecord(**new)
    if revision.mode == "same":
        try:
            new = regenerate_from_record(client(), old)
        except Exception as exc:
            raise internal_server_error(
                "regenerate_same", exc, image_id=image_id
            ) from exc
        new = save_record(db, new, user_id, parent_image_id=image_id)
        new = inherit_product_preview(
            db, old, new, user_id, preview_mode=revision.preview_mode
        )
        log_event(
            "operation_succeeded",
            operation="regenerate_same",
            image_id=new["id"],
            source_image_id=image_id,
            used_stored_prompt=True,
            used_stored_palette=bool(old.get("palette")),
        )
        return ImageRecord(**new)
    openai_client = client()
    try:
        previous_request = GenerateRequest(**old["request"])
        previous_design_spec = old.get("design_spec") or {}
        previous_elements = (
            previous_design_spec.get("final_elements") or previous_request.elements
        )
        resolution = resolve_motif_revision(
            openai_client,
            previous_request.prompt,
            previous_elements,
            old.get("palette_name"),
            revision.instruction,
            previous_design_spec.get("excluded_elements", []),
        )
        request = GenerateRequest(
            prompt=previous_request.prompt,
            elements=resolution.final_elements,
            excluded_elements=resolution.excluded_elements,
            palette_instruction=resolution.palette_instruction,
        )
        new = edit_motif_elements_with_image_model(
            old,
            request,
            revision.instruction,
            resolution,
            openai_client,
        )
        new.pop("_used_image_api", None)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise internal_server_error(
            "motif_regenerate", exc, image_id=image_id
        ) from exc
    new = save_record(db, new, user_id, parent_image_id=image_id)
    new = inherit_product_preview(
        db, old, new, user_id, preview_mode=revision.preview_mode
    )
    log_event(
        "operation_succeeded",
        operation="motif_regenerate",
        image_id=new["id"],
        source_image_id=image_id,
        palette_changed=resolution.changes_palette,
        final_element_count=len(resolution.final_elements),
        added_element_count=len(resolution.added_elements),
        removed_element_count=len(resolution.removed_elements),
    )
    return ImageRecord(**new)


@router.delete(
    "/{image_id}/assets/{asset_type}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_asset(
    image_id: str,
    asset_type: Literal["motif", "preview", "chart"],
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> Response:
    path = delete_asset(db, image_id, asset_type, user.id)
    if path is not None:
        delete_image(path.name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

import copy
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, BinaryIO, Literal
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import Response
from openai import OpenAI
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.console import log_event
from app.core.secrets import SecretConfigurationError, get_openai_api_key
from app.db.session import get_db
from app.schemas.image import (
    AssetCollectionsRequest,
    AssetStateRequest,
    CollectionCreateRequest,
    CollectionRecord,
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
    delete_asset,
    find_record,
    list_collections,
    list_records,
    save_record,
    save_records,
)
from app.services.image_generation import (
    generate_random_palette_variants,
    palette_instruction_from_colors,
    recolor_existing_variant,
    record_palette_colors,
    regenerate_from_record,
    regenerate_palette_variant,
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
from app.services.storage_service import delete_image, image_path, image_url, store_image_bytes
from app.prompts.product_preview import DISPLAY_STYLE_OPTIONS, PRODUCT_PLACEMENT_OPTIONS
from app.services.prompt_compiler import resolve_motif_revision

router = APIRouter(prefix="/images")
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=16, max_length=100),
]
ChatroomId = Annotated[str | None, Header(alias="X-Chatroom-Id", max_length=32)]
ClientExchangeId = Annotated[
    str | None, Header(alias="X-Client-Exchange-Id", max_length=100)
]


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
        "parameters": request.model_dump(),
    }


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
                    )
        return create_product_preview(
            client(), motif_path, request, 0, product_reference=product_reference
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise internal_server_error("product_preview", exc) from exc


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
    return OpenAI(api_key=api_key)


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
    return HTTPException(500, "The image operation failed")


@router.post("/generate", response_model=GenerateResponse)
def generate_images(
    request: GenerateRequest,
    idempotency_key: IdempotencyKey,
    user: CurrentUser,
    chatroom_id: ChatroomId = None,
    client_exchange_id: ClientExchangeId = None,
    db: Session = Depends(get_db),
) -> GenerateResponse:
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


@router.get("/assets", response_model=list[GalleryAsset])
def list_assets(
    user: CurrentUser,
    saved: bool | None = None,
    favorite: bool | None = None,
    db: Session = Depends(get_db),
) -> list[GalleryAsset]:
    results: list[GalleryAsset] = []

    for record in list_records(db, user.id):
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
        if collection_id in asset.get("collection_ids", []) and asset.get("url")
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

    return ImageRecord(**save_record(db, record, user.id))


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
    log_event("operation_started", operation="product_preview", image_id=image_id)
    record = find_record(db, image_id, user.id)
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
        add_preview(record, request, result)
        record = save_record(db, record, user.id)
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


@router.post("/{image_id}/preview/random", response_model=ImageRecord)
def random_preview(
    image_id: str,
    idempotency_key: IdempotencyKey,
    user: CurrentUser,
    chatroom_id: ChatroomId = None,
    client_exchange_id: ClientExchangeId = None,
    db: Session = Depends(get_db),
) -> ImageRecord:
    record = find_record(db, image_id, user.id)
    product = random.choice(list(PRODUCT_PLACEMENT_OPTIONS))
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
        add_preview(record, request, result)
        record = save_record(db, record, user.id)
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
    source = find_record(db, image_id, user.id)
    if request.product not in PRODUCT_PLACEMENT_OPTIONS:
        raise HTTPException(422, "Unsupported product")
    if request.placement not in PRODUCT_PLACEMENT_OPTIONS[request.product]:
        raise HTTPException(422, "Placement is not valid for this product")
    if request.display_style not in DISPLAY_STYLE_OPTIONS:
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
        result = generate_preview_result(source, request)
        variant = copy.deepcopy(source)
        variant["id"] = uuid.uuid4().hex[:12]
        variant["created_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        variant["derived_from"] = image_id
        for asset in variant.get("assets", {}).values():
            asset["saved"] = False
            asset["favorite"] = False
            asset["collection_ids"] = []
        add_preview(variant, request, result)
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
            color_client = None if revision.instruction == "隨機更換配色" else client()
            new = recolor_existing_variant(old, revision.instruction, color_client)
        except ValueError as exc:
            log_event(
                "operation_needs_clarification",
                operation="code_recolor",
                image_id=image_id,
                instruction_chars=len(revision.instruction),
            )
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        new = save_record(db, new, user_id, parent_image_id=image_id)
        log_event(
            "operation_succeeded",
            operation="code_recolor",
            image_id=new["id"],
            source_image_id=image_id,
            used_image_api=False,
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
        resolution = resolve_motif_revision(
            openai_client,
            previous_request.prompt,
            previous_request.elements,
            old.get("palette_name"),
            revision.instruction,
            (old.get("design_spec") or {}).get("excluded_elements", []),
        )
        preserved_palette = record_palette_colors(old)
        request = GenerateRequest(
            prompt="\n\n".join(
                filter(
                    None,
                    [
                        previous_request.prompt.strip(),
                        "使用者針對上一張圖騰提出的修改要求：" + revision.instruction.strip(),
                        "解析後的修改摘要：" + resolution.revision_summary.strip(),
                    ],
                )
            ),
            elements=resolution.final_elements,
            excluded_elements=resolution.excluded_elements,
            palette_instruction=(
                resolution.palette_instruction
                if resolution.changes_palette
                else palette_instruction_from_colors(preserved_palette)
            ),
        )
        new = regenerate_palette_variant(
            openai_client,
            request,
            None if resolution.changes_palette else old.get("palette_name"),
            None if resolution.changes_palette else preserved_palette,
        )
        new["design_spec"] = resolution.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise internal_server_error(
            "motif_regenerate", exc, image_id=image_id
        ) from exc
    new = save_record(db, new, user_id, parent_image_id=image_id)
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

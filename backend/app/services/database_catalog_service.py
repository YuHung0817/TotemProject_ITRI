from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import mimetypes
from pathlib import Path
from typing import Any
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Collection, CollectionAsset, ImageAsset, ImageRecord, User
from app.services.storage_service import delete_image, image_metadata, image_path, image_url
from app.services.collection_service import FAVORITES_ID, FAVORITES_NAME
from app.core.config import get_settings

DEFAULT_USER_ID = "single-store"
DEFAULT_USERNAME = "store"
logger = logging.getLogger(__name__)


def parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or timezone.utc)
    if value:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)
    return datetime.now(timezone.utc)


def has_not_expired(value: datetime) -> bool:
    return value.replace(tzinfo=value.tzinfo or timezone.utc) > datetime.now(timezone.utc)


def format_datetime(value: datetime) -> str:
    normalized = value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)
    return normalized.isoformat(timespec="seconds").replace("+00:00", "Z")


def ensure_default_data(db: Session) -> User:
    user = db.get(User, DEFAULT_USER_ID)
    if user is None:
        user = User(id=DEFAULT_USER_ID, username=DEFAULT_USERNAME, password_hash="")
        db.add(user)
        db.flush()
    favorite = db.get(Collection, FAVORITES_ID)
    if favorite is None:
        db.add(
            Collection(
                id=FAVORITES_ID,
                user_id=user.id,
                name=FAVORITES_NAME,
                is_system=True,
                expires_at=None,
            )
        )
        db.flush()
    return user


def storage_key(asset: dict[str, Any]) -> str | None:
    filename = asset.get("filename")
    if filename:
        return Path(str(filename)).name
    url = asset.get("url")
    return Path(str(url)).name if url else None


def _load_record(db: Session, image_id: str, user_id: str) -> ImageRecord | None:
    return db.scalar(
        select(ImageRecord)
        .where(
            ImageRecord.id == image_id,
            ImageRecord.user_id == user_id,
            ImageRecord.deleted_at.is_(None),
        )
        .options(
            selectinload(ImageRecord.assets)
            .selectinload(ImageAsset.collection_links)
            .selectinload(CollectionAsset.collection)
        )
    )


def record_to_dict(record: ImageRecord) -> dict[str, Any]:
    result = dict(record.generation_data or {})
    result.update(
        {
            "id": record.id,
            "created_at": format_datetime(record.created_at),
            "expires_at": format_datetime(record.expires_at),
            "prompt": record.prompt,
            "totem_prompt": record.compiled_prompt,
        }
    )
    result.setdefault("request", {"prompt": record.prompt, "elements": []})
    result["assets"] = {}
    for asset in record.assets:
        if (
            asset.deleted_at is not None
            or asset.deletion_status != "active"
        ):
            continue
        url = image_url(asset.storage_key)
        collection_ids = [link.collection_id for link in asset.collection_links]
        if asset.asset_type == "original":
            result["original_filename"] = asset.storage_key
            result["original_url"] = url
            continue
        asset_dict = {
            "type": asset.asset_type,
            "filename": asset.storage_key,
            "url": url,
            "saved": asset.is_saved,
            "favorite": FAVORITES_ID in collection_ids,
            "collection_ids": collection_ids,
            "parameters": asset.parameters,
            "width": asset.width,
            "height": asset.height,
        }
        result["assets"][asset.asset_type] = asset_dict
        if asset.asset_type == "motif":
            result["filename"] = asset.storage_key
            result["url"] = url
            result["totem_url"] = url
    if "filename" not in result:
        raise RuntimeError(f"Image record {record.id} has no motif asset")
    return result


def list_records(db: Session, user_id: str) -> list[dict[str, Any]]:
    records = db.scalars(
        select(ImageRecord)
        .where(
            ImageRecord.user_id == user_id,
            ImageRecord.deleted_at.is_(None),
            ImageRecord.expires_at > datetime.now(timezone.utc),
        )
        .options(
            selectinload(ImageRecord.assets)
            .selectinload(ImageAsset.collection_links)
            .selectinload(CollectionAsset.collection)
        )
        .order_by(ImageRecord.created_at.desc())
    ).all()
    return [record_to_dict(record) for record in records]


def find_record(db: Session, image_id: str, user_id: str) -> dict[str, Any]:
    record = _load_record(db, image_id, user_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")
    return record_to_dict(record)


def list_product_preview_records(
    db: Session, image_id: str, user_id: str
) -> list[dict[str, Any]]:
    """Return every active product preview that uses the exact same motif file."""
    source = _load_record(db, image_id, user_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")
    motif = next(
        (
            asset
            for asset in source.assets
            if asset.asset_type == "motif"
            and asset.deleted_at is None
            and asset.deletion_status == "active"
        ),
        None,
    )
    if motif is None:
        return []

    records = (
        db.scalars(
            select(ImageRecord)
            .join(ImageAsset)
            .where(
                ImageRecord.user_id == user_id,
                ImageRecord.deleted_at.is_(None),
                ImageRecord.expires_at > datetime.now(timezone.utc),
                ImageAsset.asset_type == "motif",
                ImageAsset.storage_key == motif.storage_key,
                ImageAsset.deleted_at.is_(None),
                ImageAsset.deletion_status == "active",
            )
            .options(
                selectinload(ImageRecord.assets)
                .selectinload(ImageAsset.collection_links)
                .selectinload(CollectionAsset.collection)
            )
            .order_by(ImageRecord.created_at.asc())
        )
        .unique()
        .all()
    )
    return [
        record_to_dict(record)
        for record in records
        if any(
            asset.asset_type == "preview"
            and asset.deleted_at is None
            and asset.deletion_status == "active"
            for asset in record.assets
        )
    ]


def _upsert_asset(
    db: Session,
    record: ImageRecord,
    asset_type: str,
    data: dict[str, Any],
    created_at: datetime,
    expires_at: datetime,
) -> tuple[ImageAsset | None, str | None]:
    key = storage_key(data)
    if not key:
        return None, None
    asset = next((item for item in record.assets if item.asset_type == asset_type), None)
    replaced_key = None
    if asset is None:
        asset = ImageAsset(
            id=uuid.uuid4().hex,
            image_record_id=record.id,
            asset_type=asset_type,
            storage_key=key,
            created_at=created_at,
            expires_at=expires_at,
        )
        db.add(asset)
        record.assets.append(asset)
    elif asset.storage_key != key:
        replaced_key = asset.storage_key
        asset.created_at = created_at
    asset.storage_key = key
    asset.expires_at = expires_at
    asset.mime_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
    stored_path = image_path(key)
    if stored_path.is_file():
        mime_type, size_bytes, width, height = image_metadata(key)
        asset.mime_type = mime_type
        asset.size_bytes = size_bytes
        asset.width = width
        asset.height = height
    else:
        asset.size_bytes = None
        asset.width = None
        asset.height = None
    asset.parameters = data.get("parameters")
    asset.is_saved = bool(data.get("saved", False))
    asset.deletion_status = "active"
    asset.deleted_at = None
    db.flush()

    requested_ids = list(dict.fromkeys(data.get("collection_ids") or []))
    if data.get("favorite") and FAVORITES_ID not in requested_ids:
        requested_ids.append(FAVORITES_ID)
    known_ids = set(
        db.scalars(
            select(Collection.id).where(
                Collection.user_id == record.user_id,
                Collection.id.in_(requested_ids),
            )
        ).all()
    )
    existing_links = {link.collection_id: link for link in asset.collection_links}
    for collection_id, link in existing_links.items():
        if collection_id not in known_ids:
            db.delete(link)
    for collection_id in known_ids - existing_links.keys():
        db.add(CollectionAsset(collection_id=collection_id, image_asset_id=asset.id))
    return asset, replaced_key


def save_record(
    db: Session,
    raw_record: dict[str, Any],
    user_id: str,
    parent_image_id: str | None = None,
    *,
    refresh_expiry: bool = False,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    row = dict(raw_record)
    for asset in row.setdefault("assets", {}).values():
        asset.setdefault("collection_ids", [FAVORITES_ID] if asset.get("favorite") else [])
    record_id = str(row["id"])
    created_at = parse_datetime(row.get("created_at"))
    event_time = generated_at or datetime.now(timezone.utc)
    record = _load_record(db, record_id, user_id)
    is_new = record is None
    if record is None:
        expires_at = event_time + timedelta(
            minutes=get_settings().data_retention_minutes
        )
        record = ImageRecord(
            id=record_id,
            user_id=user_id,
            created_at=created_at,
            expires_at=expires_at,
        )
        db.add(record)
        db.flush()
    elif refresh_expiry:
        record.expires_at = event_time + timedelta(
            minutes=get_settings().data_retention_minutes
        )
    expires_at = record.expires_at
    generation = row.get("generation") or {}
    record.prompt = str(row.get("prompt") or generation.get("user_prompt") or "")
    record.compiled_prompt = row.get("totem_prompt") or generation.get("compiled_prompt")
    record.parent_image_id = parent_image_id or row.get("derived_from")
    record.generation_data = {key: value for key, value in row.items() if key != "assets"}

    assets = dict(row.get("assets") or {})
    original_filename = row.get("original_filename") or (row.get("files") or {}).get("original")
    if original_filename:
        assets["original"] = {
            "filename": original_filename,
            "url": row.get("original_url"),
            "saved": False,
            "collection_ids": [],
        }
    replaced_keys: set[str] = set()
    asset_created_at = event_time if is_new or refresh_expiry else created_at
    for asset_type, asset_data in assets.items():
        _, replaced_key = _upsert_asset(
            db,
            record,
            asset_type,
            dict(asset_data or {}),
            asset_created_at,
            expires_at,
        )
        if replaced_key:
            replaced_keys.add(replaced_key)
    # A record version is retained as one coherent bundle. Metadata-only saves
    # preserve the deadline; successful generation refreshes it explicitly.
    for asset in record.assets:
        if asset.deleted_at is None and asset.deletion_status == "active":
            asset.expires_at = expires_at
    db.commit()
    for key in replaced_keys:
        still_referenced = db.scalar(
            select(func.count(ImageAsset.id)).where(
                ImageAsset.storage_key == key,
                ImageAsset.deleted_at.is_(None),
                ImageAsset.deletion_status == "active",
            )
        )
        if not still_referenced:
            try:
                delete_image(key)
            except OSError:
                # The database already points at the newly generated file.
                # Leave an undeletable orphan for maintenance rather than
                # reporting the successful generation as failed.
                logger.warning("Unable to remove replaced image file %s", key, exc_info=True)
    saved = _load_record(db, record.id, user_id)
    if saved is None:
        raise RuntimeError("Saved image record could not be reloaded")
    return record_to_dict(saved)


def save_records(db: Session, records: list[dict[str, Any]], user_id: str) -> list[dict[str, Any]]:
    return [save_record(db, record, user_id) for record in records]


def list_collections(db: Session, user_id: str) -> list[dict[str, Any]]:
    collections = db.scalars(
        select(Collection)
        .where(Collection.user_id == user_id)
        .options(
            selectinload(Collection.asset_links)
            .selectinload(CollectionAsset.image_asset)
            .selectinload(ImageAsset.image_record)
        )
        .order_by(Collection.is_system.desc(), Collection.created_at)
    ).all()
    result = []
    for collection in collections:
        active = [
            link.image_asset
            for link in collection.asset_links
            if link.image_asset.deleted_at is None
            and link.image_asset.deletion_status == "active"
            and has_not_expired(link.image_asset.expires_at)
            and link.image_asset.image_record.deleted_at is None
            and has_not_expired(link.image_asset.image_record.expires_at)
        ]
        active.sort(key=lambda item: item.created_at, reverse=True)
        urls = [image_url(asset.storage_key) for asset in active]
        result.append(
            {
                "id": collection.id,
                "name": FAVORITES_NAME if collection.is_system else collection.name,
                "system": collection.is_system,
                "image_count": len(active),
                "preview_url": urls[0] if urls else None,
                "preview_urls": urls[:3],
            }
        )
    return result


def create_collection(db: Session, user_id: str, name: str) -> dict[str, Any]:
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(422, "Collection name cannot be empty")
    duplicate = db.scalar(
        select(Collection).where(
            Collection.user_id == user_id,
            func.lower(Collection.name) == clean_name.casefold(),
        )
    )
    if duplicate is not None:
        raise HTTPException(409, "Collection name already exists")
    collection = Collection(user_id=user_id, name=clean_name)
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return {
        "id": collection.id,
        "name": collection.name,
        "system": collection.is_system,
        "image_count": 0,
        "preview_url": None,
        "preview_urls": [],
    }


def rename_collection(
    db: Session, collection_id: str, user_id: str, name: str
) -> dict[str, Any]:
    collection = db.scalar(
        select(Collection).where(
            Collection.id == collection_id,
            Collection.user_id == user_id,
        )
    )
    if collection is None:
        raise HTTPException(404, "Collection not found")
    if collection.is_system:
        raise HTTPException(422, "System collections cannot be renamed")
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(422, "Collection name cannot be empty")
    duplicate = db.scalar(
        select(Collection).where(
            Collection.user_id == user_id,
            Collection.id != collection_id,
            func.lower(Collection.name) == clean_name.casefold(),
        )
    )
    if duplicate is not None:
        raise HTTPException(409, "Collection name already exists")
    collection.name = clean_name
    db.commit()
    return next(
        item for item in list_collections(db, user_id) if item["id"] == collection_id
    )


def delete_collection(db: Session, collection_id: str, user_id: str) -> None:
    collection = db.scalar(
        select(Collection).where(
            Collection.id == collection_id,
            Collection.user_id == user_id,
        )
    )
    if collection is None:
        raise HTTPException(404, "Collection not found")
    if collection.is_system:
        raise HTTPException(422, "System collections cannot be deleted")
    db.delete(collection)
    db.commit()


def collection_exists(db: Session, collection_id: str, user_id: str) -> bool:
    return db.scalar(
        select(Collection.id).where(
            Collection.id == collection_id,
            Collection.user_id == user_id,
        )
    ) is not None


def delete_asset(db: Session, image_id: str, asset_type: str, user_id: str) -> Path | None:
    record = _load_record(db, image_id, user_id)
    if record is None:
        raise HTTPException(404, "Image not found")
    asset = next(
        (item for item in record.assets if item.asset_type == asset_type and item.deleted_at is None),
        None,
    )
    if asset is None:
        raise HTTPException(404, f"Asset not found: {asset_type}")
    asset.deleted_at = datetime.now(timezone.utc)
    asset.deletion_status = "deleted"
    path = image_path(asset.storage_key)
    remaining_references = db.scalar(
        select(func.count(ImageAsset.id)).where(
            ImageAsset.storage_key == asset.storage_key,
            ImageAsset.id != asset.id,
            ImageAsset.deleted_at.is_(None),
            ImageAsset.deletion_status == "active",
        )
    )
    db.commit()
    return path if not remaining_references else None

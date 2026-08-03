from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db import Base
from app.db.models import Collection, CollectionAsset, ImageAsset, ImageRecord, User
from app.core.config import get_settings
from app.services.database_catalog_service import (
    DEFAULT_USER_ID,
    create_collection,
    delete_collection,
    delete_asset,
    find_record,
    list_collections,
    list_product_preview_records,
    list_records,
    rename_collection,
    save_record,
)


def sqlite_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


def test_collection_links_are_removed_when_asset_is_deleted() -> None:
    engine = sqlite_engine()
    with Session(engine) as db:
        user = User(id="user-1", username="store")
        collection = Collection(id="collection-1", user=user, name="提案")
        record = ImageRecord(id="record-1", user=user, prompt="test")
        asset = ImageAsset(
            id="asset-1",
            image_record=record,
            asset_type="motif",
            storage_key="record-1.png",
        )
        link = CollectionAsset(collection=collection, image_asset=asset)
        db.add_all([user, collection, record, asset, link])
        db.commit()
        db.delete(asset)
        db.commit()
        assert db.get(CollectionAsset, (collection.id, "asset-1")) is None


def test_deleting_collection_removes_links_but_preserves_assets() -> None:
    engine = sqlite_engine()
    with Session(engine) as db:
        user = User(id="user-1", username="store")
        collection = Collection(id="collection-1", user=user, name="提案")
        record = ImageRecord(id="record-1", user=user, prompt="test")
        asset = ImageAsset(
            id="asset-1",
            image_record=record,
            asset_type="motif",
            storage_key="record-1.png",
        )
        db.add_all(
            [
                user,
                collection,
                record,
                asset,
                CollectionAsset(collection=collection, image_asset=asset),
            ]
        )
        db.commit()

        delete_collection(db, collection.id, user.id)

        assert db.get(Collection, collection.id) is None
        assert db.get(CollectionAsset, (collection.id, asset.id)) is None
        assert db.get(ImageAsset, asset.id) is not None


def test_custom_collection_can_be_renamed() -> None:
    engine = sqlite_engine()
    with Session(engine) as db:
        db.add(User(id=DEFAULT_USER_ID, username="store"))
        db.commit()
        folder = create_collection(db, DEFAULT_USER_ID, "舊名稱")

        renamed = rename_collection(db, folder["id"], DEFAULT_USER_ID, " 新名稱 ")

        saved = db.get(Collection, folder["id"])
        assert renamed["name"] == "新名稱"
        assert saved is not None and saved.name == "新名稱"


def test_database_catalog_round_trip_preserves_api_shape_and_collections() -> None:
    engine = sqlite_engine()
    with Session(engine) as db:
        user = User(id=DEFAULT_USER_ID, username="store")
        db.add_all([user, Collection(id="favorites", user=user, name="我的最愛", is_system=True)])
        db.commit()
        folder = create_collection(db, DEFAULT_USER_ID, "提案")
        saved = save_record(
            db,
            {
                "id": "record-1",
                "filename": "record-1.png",
                "url": "/generated/images/record-1.png",
                "original_filename": "record-1_original.png",
                "original_url": "/generated/images/record-1_original.png",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "prompt": "山與河流",
                "request": {"prompt": "山與河流", "elements": ["山", "河流"]},
                "assets": {
                    "motif": {
                        "type": "motif",
                        "filename": "record-1.png",
                        "url": "/generated/images/record-1.png",
                        "saved": True,
                        "favorite": True,
                        "collection_ids": ["favorites", folder["id"]],
                        "parameters": None,
                    }
                },
            },
            DEFAULT_USER_ID,
        )
        assert saved["filename"] == "record-1.png"
        assert saved["original_filename"] == "record-1_original.png"
        assert saved["assets"]["motif"]["favorite"] is True
        assert set(saved["assets"]["motif"]["collection_ids"]) == {
            "favorites",
            folder["id"],
        }
        assert find_record(db, "record-1", DEFAULT_USER_ID)["request"]["elements"] == ["山", "河流"]
        assert len(list_records(db, DEFAULT_USER_ID)) == 1
        counts = {
            item["id"]: item["image_count"]
            for item in list_collections(db, DEFAULT_USER_ID)
        }
        assert counts == {"favorites": 1, folder["id"]: 1}


def test_legacy_system_collection_is_presented_as_my_favorites() -> None:
    engine = sqlite_engine()
    with Session(engine) as db:
        user = User(id=DEFAULT_USER_ID, username="store")
        db.add_all(
            [
                user,
                Collection(
                    id="favorites",
                    user=user,
                    name="我的收藏",
                    is_system=True,
                ),
            ]
        )
        db.commit()

        collections = list_collections(db, DEFAULT_USER_ID)

        assert collections[0]["id"] == "favorites"
        assert collections[0]["name"] == "我的最愛"


def test_shared_image_file_is_only_unlinked_after_last_asset_reference() -> None:
    engine = sqlite_engine()
    with Session(engine) as db:
        db.add(User(id=DEFAULT_USER_ID, username="store"))
        db.commit()
        base = {
            "filename": "shared.png",
            "url": "/generated/images/shared.png",
            "created_at": "2026-07-21T10:00:00+00:00",
            "prompt": "共享圖片",
            "request": {"prompt": "共享圖片", "elements": []},
            "assets": {
                "motif": {
                    "type": "motif",
                    "filename": "shared.png",
                    "url": "/generated/images/shared.png",
                }
            },
        }
        save_record(db, {"id": "record-1", **base}, DEFAULT_USER_ID)
        save_record(
            db,
            {"id": "record-2", **base},
            DEFAULT_USER_ID,
            parent_image_id="record-1",
        )
        assert delete_asset(db, "record-1", "motif", DEFAULT_USER_ID) is None
        final_path = delete_asset(db, "record-2", "motif", DEFAULT_USER_ID)
        assert final_path is not None
        assert final_path.name == "shared.png"


def test_generated_asset_refreshes_the_whole_record_bundle_expiry(
    monkeypatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "data_retention_minutes", 60)
    engine = sqlite_engine()
    first_generation = datetime(2026, 7, 27, 1, 0, tzinfo=timezone.utc)
    preview_generation = first_generation + timedelta(minutes=20)
    metadata_update = preview_generation + timedelta(minutes=10)
    base = {
        "id": "bundle-record",
        "filename": "motif.png",
        "url": "/generated/images/motif.png",
        "created_at": first_generation.isoformat(),
        "prompt": "bundle",
        "assets": {
            "motif": {
                "type": "motif",
                "filename": "motif.png",
                "url": "/generated/images/motif.png",
            }
        },
    }

    with Session(engine) as db:
        db.add(User(id=DEFAULT_USER_ID, username="store"))
        db.commit()
        save_record(
            db,
            base,
            DEFAULT_USER_ID,
            generated_at=first_generation,
        )
        with_preview = {
            **base,
            "assets": {
                **base["assets"],
                "preview": {
                    "type": "preview",
                    "filename": "preview.png",
                    "url": "/generated/images/preview.png",
                },
            },
        }
        save_record(
            db,
            with_preview,
            DEFAULT_USER_ID,
            refresh_expiry=True,
            generated_at=preview_generation,
        )

        record = db.get(ImageRecord, "bundle-record")
        assert record is not None
        expected = preview_generation + timedelta(minutes=60)
        assert record.expires_at.replace(tzinfo=timezone.utc) == expected
        assert {
            asset.expires_at.replace(tzinfo=timezone.utc)
            for asset in record.assets
        } == {expected}
        preview = next(
            asset for asset in record.assets if asset.asset_type == "preview"
        )
        assert preview.created_at.replace(tzinfo=timezone.utc) == preview_generation

        save_record(
            db,
            with_preview,
            DEFAULT_USER_ID,
            generated_at=metadata_update,
        )
        db.refresh(record)
        assert record.expires_at.replace(tzinfo=timezone.utc) == expected
        assert {
            asset.expires_at.replace(tzinfo=timezone.utc)
            for asset in record.assets
        } == {expected}


def test_derived_version_has_an_independent_bundle_expiry(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "data_retention_minutes", 60)
    engine = sqlite_engine()
    parent_time = datetime(2026, 7, 27, 1, 0, tzinfo=timezone.utc)
    child_time = parent_time + timedelta(minutes=30)
    base = {
        "filename": "shared-motif.png",
        "url": "/generated/images/shared-motif.png",
        "created_at": parent_time.isoformat(),
        "prompt": "version",
        "assets": {
            "motif": {
                "type": "motif",
                "filename": "shared-motif.png",
                "url": "/generated/images/shared-motif.png",
            }
        },
    }

    with Session(engine) as db:
        db.add(User(id=DEFAULT_USER_ID, username="store"))
        db.commit()
        save_record(
            db,
            {"id": "parent-version", **base},
            DEFAULT_USER_ID,
            generated_at=parent_time,
        )
        save_record(
            db,
            {
                "id": "child-version",
                **base,
                "created_at": child_time.isoformat(),
            },
            DEFAULT_USER_ID,
            parent_image_id="parent-version",
            generated_at=child_time,
        )

        parent = db.get(ImageRecord, "parent-version")
        child = db.get(ImageRecord, "child-version")
        assert parent is not None and child is not None
        assert parent.expires_at.replace(tzinfo=timezone.utc) == (
            parent_time + timedelta(minutes=60)
        )
        assert child.expires_at.replace(tzinfo=timezone.utc) == (
            child_time + timedelta(minutes=60)
        )
        assert child.parent_image_id == parent.id
        assert parent.assets[0].storage_key == child.assets[0].storage_key


def test_product_previews_are_grouped_by_shared_motif_storage_key() -> None:
    engine = sqlite_engine()
    now = datetime.now(timezone.utc)

    def record(record_id: str, motif: str, preview: str | None) -> dict:
        assets = {
            "motif": {
                "type": "motif",
                "filename": motif,
                "url": f"/generated/images/{motif}",
            }
        }
        if preview:
            assets["preview"] = {
                "type": "preview",
                "filename": preview,
                "url": f"/generated/images/{preview}",
            }
        return {
            "id": record_id,
            "filename": motif,
            "url": f"/generated/images/{motif}",
            "created_at": now.isoformat(),
            "prompt": "group",
            "request": {"prompt": "group", "elements": []},
            "assets": assets,
        }

    with Session(engine) as db:
        db.add(User(id=DEFAULT_USER_ID, username="store"))
        db.commit()
        save_record(db, record("source", "shared.png", "shirt.png"), DEFAULT_USER_ID)
        save_record(
            db,
            record("variant", "shared.png", "bag.png"),
            DEFAULT_USER_ID,
            parent_image_id="source",
        )
        save_record(db, record("no-preview", "shared.png", None), DEFAULT_USER_ID)
        save_record(db, record("other", "other.png", "other-preview.png"), DEFAULT_USER_ID)

        previews = list_product_preview_records(db, "source", DEFAULT_USER_ID)

        assert {item["id"] for item in previews} == {"source", "variant"}
        assert {
            item["assets"]["preview"]["filename"] for item in previews
        } == {"shirt.png", "bag.png"}


def test_expired_records_are_hidden_from_images_and_collections() -> None:
    engine = sqlite_engine()
    with Session(engine) as db:
        user = User(id=DEFAULT_USER_ID, username="store")
        collection = Collection(id="favorites", user=user, name="我的最愛", is_system=True)
        expired_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        record = ImageRecord(
            id="expired-record",
            user=user,
            prompt="expired",
            expires_at=expired_at,
        )
        asset = ImageAsset(
            id="expired-asset",
            image_record=record,
            asset_type="motif",
            storage_key="expired.png",
            expires_at=expired_at,
        )
        db.add_all(
            [
                user,
                collection,
                record,
                asset,
                CollectionAsset(collection=collection, image_asset=asset),
            ]
        )
        db.commit()

        assert list_records(db, DEFAULT_USER_ID) == []
        folders = list_collections(db, DEFAULT_USER_ID)
        assert folders[0]["image_count"] == 0
        assert folders[0]["preview_url"] is None

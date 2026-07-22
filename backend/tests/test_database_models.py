from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db import Base
from app.db.models import Collection, CollectionAsset, ImageAsset, ImageRecord, User
from app.services.database_catalog_service import (
    DEFAULT_USER_ID,
    create_collection,
    delete_asset,
    find_record,
    list_collections,
    list_records,
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
                "created_at": "2026-07-21T10:00:00+00:00",
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

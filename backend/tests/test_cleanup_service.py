from datetime import datetime, timedelta, timezone
from io import BytesIO

from PIL import Image
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import Base
from app.db.models import Chatroom, ImageAsset, ImageRecord, Message, User
from app.services.cleanup_service import cleanup_expired_data
from app.services.storage_service import image_path, store_image_bytes


def png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (3, 2), "white").save(output, format="PNG")
    return output.getvalue()


def sqlite_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


def test_cleanup_is_dry_run_safe_retriable_and_preserves_shared_file(
    tmp_path, monkeypatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "image_storage_root", str(tmp_path))
    monkeypatch.setattr(settings, "data_retention_minutes", 1)
    now = datetime.now(timezone.utc)
    expired = now - timedelta(minutes=2)
    future = now + timedelta(minutes=2)
    expired_only_key = store_image_bytes(png_bytes())
    shared_key = store_image_bytes(png_bytes())
    engine = sqlite_engine()

    with Session(engine) as db:
        db.add(User(id="single-store", username="store", password_hash=""))
        room = Chatroom(
            id="expired-room",
            user_id="single-store",
            title="expired",
            created_at=expired,
            expires_at=expired,
        )
        expired_record = ImageRecord(
            id="expired-image",
            user_id="single-store",
            prompt="",
            created_at=expired,
            expires_at=expired,
        )
        live_record = ImageRecord(
            id="live-image",
            user_id="single-store",
            prompt="",
            created_at=now,
            expires_at=future,
        )
        db.add_all(
            [
                room,
                Message(
                    id="expired-message",
                    chatroom_id=room.id,
                    role="assistant",
                    message_type="generation",
                    client_exchange_id="exchange",
                    content="pending",
                    created_at=expired,
                    expires_at=expired,
                ),
                expired_record,
                live_record,
                ImageAsset(
                    id="expired-only-asset",
                    image_record_id=expired_record.id,
                    asset_type="original",
                    storage_key=expired_only_key,
                    created_at=expired,
                    expires_at=expired,
                ),
                ImageAsset(
                    id="expired-shared-asset",
                    image_record_id=expired_record.id,
                    asset_type="motif",
                    storage_key=shared_key,
                    created_at=expired,
                    expires_at=expired,
                ),
                ImageAsset(
                    id="live-shared-asset",
                    image_record_id=live_record.id,
                    asset_type="motif",
                    storage_key=shared_key,
                    created_at=now,
                    expires_at=future,
                ),
            ]
        )
        db.commit()
        expired_record_id = expired_record.id
        live_record_id = live_record.id
        room_id = room.id

        preview = cleanup_expired_data(db, dry_run=True, now=now)
        assert preview.image_records == 1
        assert preview.image_assets == 2
        assert preview.image_files == 1
        assert db.get(ImageRecord, expired_record_id) is not None
        assert image_path(expired_only_key).exists()

        result = cleanup_expired_data(db, dry_run=False, now=now)
        assert result.image_records == 1
        assert db.get(ImageRecord, expired_record_id) is None
        assert db.get(Chatroom, room_id) is None
        assert not image_path(expired_only_key).exists()
        assert image_path(shared_key).exists()
        assert db.scalar(select(ImageRecord.id).where(ImageRecord.id == live_record_id))

        repeated = cleanup_expired_data(db, dry_run=False, now=now)
        assert repeated.image_records == 0
        assert repeated.image_files == 0

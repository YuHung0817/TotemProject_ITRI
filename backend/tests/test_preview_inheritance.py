from pathlib import Path
from types import SimpleNamespace

import pytest

from app.api.v1.routes import images


def source_record(preview_filename: str = "old-preview.png") -> dict:
    return {
        "id": "source-record",
        "assets": {
            "preview": {
                "filename": preview_filename,
                "url": f"/generated/images/{preview_filename}",
                "parameters": {
                    "product": "托特包",
                    "placement": "袋子中央",
                    "display_style": "深綠色商品＋白底",
                    "preview_size": "1024x1024",
                    "preview_quality": "medium",
                },
            }
        },
    }


def revised_record() -> dict:
    return {
        "id": "revised-record",
        "filename": "new-motif.png",
        "original_filename": "new-motif-original.png",
        "assets": {
            "motif": {
                "filename": "new-motif.png",
                "url": "/generated/images/new-motif.png",
            }
        },
    }


def test_revised_motif_inherits_existing_product_preview(
    monkeypatch, tmp_path: Path
) -> None:
    old_preview = tmp_path / "old-preview.png"
    old_preview.write_bytes(b"preview")
    generated_requests = []

    monkeypatch.setattr(images, "image_path", lambda _filename: old_preview)

    def fake_generate(record, request, product_reference=None):  # type: ignore[no-untyped-def]
        assert record["id"] == "revised-record"
        assert product_reference is not None
        generated_requests.append(request)
        return {
            "filename": "new-preview.png",
            "url": "/generated/images/new-preview.png",
        }

    monkeypatch.setattr(images, "generate_preview_result", fake_generate)
    monkeypatch.setattr(
        images,
        "save_record",
        lambda _db, record, _user_id, parent_image_id=None: record,
    )

    result = images.inherit_product_preview(
        None, source_record(), revised_record(), "user-id"  # type: ignore[arg-type]
    )

    assert len(generated_requests) == 1
    request = generated_requests[0]
    assert request.product == "托特包"
    assert request.placement == "袋子中央"
    assert request.display_style == "深綠色商品＋白底"
    assert result["assets"]["preview"]["filename"] == "new-preview.png"
    assert (
        result["assets"]["preview"]["parameters"]["reference_source"]
        == "current_preview"
    )
    assert (
        result["assets"]["preview"]["parameters"]["reference_filename"]
        == "old-preview.png"
    )


def test_revised_motif_skips_preview_when_source_has_none(monkeypatch) -> None:
    monkeypatch.setattr(
        images,
        "generate_preview_result",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("preview generation should not run")
        ),
    )
    revised = revised_record()

    result = images.inherit_product_preview(
        None, {"id": "source-record", "assets": {}}, revised, "user-id"  # type: ignore[arg-type]
    )

    assert result is revised
    assert "preview" not in result["assets"]


def test_revised_product_source_can_use_built_in_template_pipeline(
    monkeypatch,
) -> None:
    generated_requests = []

    def fake_generate(record, request, product_reference=None):  # type: ignore[no-untyped-def]
        assert record["id"] == "revised-record"
        assert product_reference is None
        generated_requests.append(request)
        return {
            "filename": "template-preview.png",
            "url": "/generated/images/template-preview.png",
            "reference_source": "built_in",
            "reference_filename": "tote-bag.jpg",
        }

    monkeypatch.setattr(images, "generate_preview_result", fake_generate)
    monkeypatch.setattr(
        images,
        "save_record",
        lambda _db, record, _user_id, parent_image_id=None: record,
    )

    result = images.inherit_product_preview(
        None,  # type: ignore[arg-type]
        source_record(),
        revised_record(),
        "user-id",
        preview_mode="template",
    )

    request = generated_requests[0]
    assert request.product == "托特包"
    assert request.placement == "AI自動決定位置"
    assert request.display_style == "白色商品＋白底"
    assert result["assets"]["preview"]["parameters"]["reference_source"] == "built_in"


def test_first_preview_for_separate_chat_message_creates_a_new_record(
    monkeypatch,
) -> None:
    source = {
        "id": "original-motif",
        "created_at": "2026-08-03 01:25:03",
        "assets": {
            "motif": {
                "filename": "motif.png",
                "url": "/generated/images/motif.png",
                "saved": True,
                "favorite": True,
                "collection_ids": ["favorites"],
            }
        },
    }
    saved: list[tuple[dict, str | None]] = []

    def fake_save(
        _db,
        record,
        _user_id,
        parent_image_id=None,
        **_kwargs,
    ):  # type: ignore[no-untyped-def]
        saved.append((record, parent_image_id))
        return record

    monkeypatch.setattr(images, "save_record", fake_save)
    result = images.save_preview_version(
        None,  # type: ignore[arg-type]
        source,
        "user-id",
        images.ProductPreviewRequest(product="托特包"),
        {
            "filename": "preview.png",
            "url": "/generated/images/preview.png",
        },
        separate_message=True,
    )

    assert result["id"] != source["id"]
    assert result["derived_from"] == source["id"]
    assert result["assets"]["preview"]["filename"] == "preview.png"
    assert "preview" not in source["assets"]
    assert saved[0][1] == source["id"]
    assert result["assets"]["motif"]["saved"] is False
    assert result["assets"]["motif"]["favorite"] is False
    assert result["assets"]["motif"]["collection_ids"] == []


def test_first_preview_without_separate_message_stays_on_source_record(
    monkeypatch,
) -> None:
    source = {
        "id": "initial-generation",
        "assets": {
            "motif": {
                "filename": "motif.png",
                "url": "/generated/images/motif.png",
            }
        },
    }
    save_calls: list[dict] = []

    def fake_save(_db, record, _user_id, **kwargs):  # type: ignore[no-untyped-def]
        save_calls.append(kwargs)
        return record

    monkeypatch.setattr(images, "save_record", fake_save)
    result = images.save_preview_version(
        None,  # type: ignore[arg-type]
        source,
        "user-id",
        images.ProductPreviewRequest(product="托特包"),
        {
            "filename": "preview.png",
            "url": "/generated/images/preview.png",
        },
    )

    assert result["id"] == source["id"]
    assert result["assets"]["preview"]["filename"] == "preview.png"
    assert save_calls == [{"refresh_expiry": True}]


def test_preview_endpoint_forces_new_record_without_chat_headers(monkeypatch) -> None:
    source = {
        "id": "original-motif",
        "assets": {
            "motif": {
                "filename": "motif.png",
                "url": "/generated/images/motif.png",
            }
        },
    }
    separate_values: list[bool] = []

    class SaveReached(RuntimeError):
        pass

    monkeypatch.setattr(images, "find_record", lambda *_args: source)
    monkeypatch.setattr(images, "list_product_preview_records", lambda *_args: [])
    monkeypatch.setattr(images, "require_storage_capacity", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(images, "log_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        images,
        "acquire_generation_job",
        lambda *_args, **_kwargs: SimpleNamespace(status="pending", id="job-id"),
    )
    monkeypatch.setattr(
        images,
        "generate_preview_result",
        lambda *_args, **_kwargs: {
            "filename": "preview.png",
            "url": "/generated/images/preview.png",
        },
    )

    def capture_save(*_args, separate_message=False, **_kwargs):  # type: ignore[no-untyped-def]
        separate_values.append(separate_message)
        raise SaveReached

    monkeypatch.setattr(images, "save_preview_version", capture_save)
    monkeypatch.setattr(images, "fail_generation_job", lambda *_args, **_kwargs: None)

    with pytest.raises(SaveReached):
        images.preview(
            "original-motif",
            images.ProductPreviewRequest(product="貝殼零錢包"),
            "idempotency-key",
            SimpleNamespace(id="user-id"),
            chatroom_id=None,
            client_exchange_id=None,
            db=None,  # type: ignore[arg-type]
        )

    assert separate_values == [True]

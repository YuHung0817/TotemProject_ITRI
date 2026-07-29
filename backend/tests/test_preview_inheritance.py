from pathlib import Path

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

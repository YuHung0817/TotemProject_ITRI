from app.schemas.image import GenerateRequest


def test_generate_request_only_exposes_user_inputs() -> None:
    request = GenerateRequest(prompt="守護", elements=["月亮"])
    assert request.model_dump() == {
        "prompt": "守護",
        "elements": ["月亮"],
        "colors": [],
        "carrier": None,
    }


def test_legacy_catalog_fields_are_ignored() -> None:
    request = GenerateRequest(
        prompt="守護",
        elements=["月亮"],
        palette="紅黑白",
        count=4,
        size="1536x1024",
    )
    assert request.model_dump() == {
        "prompt": "守護",
        "elements": ["月亮"],
        "colors": [],
        "carrier": None,
    }


def test_product_and_placement_are_user_selectable() -> None:
    from app.schemas.image import ProductPreviewRequest

    request = ProductPreviewRequest(product="托特包", placement="提袋處")
    assert request.product == "托特包"
    assert request.placement == "提袋處"


def test_gallery_assets_include_expiry(monkeypatch) -> None:
    from app.api.v1.routes import images

    monkeypatch.setattr(
        images,
        "list_records",
        lambda _db, _user_id: [
            {
                "id": "image-1",
                "created_at": "2026-07-21T07:00:00Z",
                "expires_at": "2026-08-04T07:00:00Z",
                "request": {"elements": []},
                "assets": {
                    "motif": {
                        "url": "/generated/images/image.png",
                        "saved": False,
                        "favorite": False,
                    }
                },
            }
        ],
    )

    user = type("User", (), {"id": "single-store"})()
    result = images.list_assets(user=user, db=None)  # type: ignore[arg-type]

    assert result[0].expires_at == "2026-08-04T07:00:00Z"


def test_gallery_assets_deduplicate_inherited_files(monkeypatch) -> None:
    from app.api.v1.routes import images

    shared_motif = {
        "url": "/generated/images/shared-motif.png",
        "saved": False,
        "favorite": False,
    }
    monkeypatch.setattr(
        images,
        "list_records",
        lambda _db, _user_id: [
            {
                "id": "variant-1",
                "created_at": "2026-07-22T07:00:00Z",
                "expires_at": "2026-08-05T07:00:00Z",
                "derived_from": "image-1",
                "request": {"elements": []},
                "assets": {
                    "motif": dict(shared_motif),
                    "preview": {
                        "url": "/generated/images/preview-1.png",
                        "saved": False,
                        "favorite": False,
                    },
                },
            },
            {
                "id": "image-1",
                "created_at": "2026-07-21T07:00:00Z",
                "expires_at": "2026-08-04T07:00:00Z",
                "request": {"elements": []},
                "assets": {"motif": dict(shared_motif)},
            },
        ],
    )

    user = type("User", (), {"id": "single-store"})()
    result = images.list_assets(user=user, db=None)  # type: ignore[arg-type]

    assert [(item.record_id, item.asset_type) for item in result] == [
        ("variant-1", "preview"),
        ("image-1", "motif"),
    ]


def test_product_parser_fallback_preserves_current_preview_settings() -> None:
    from app.api.v1.routes.images import fallback_product_preview_request
    from app.schemas.image import ProductPreviewRequest

    source = {
        "assets": {
            "preview": {
                "filename": "current_mockup.png",
                "parameters": {
                    "product": "帆布袋",
                    "placement": "袋子中央",
                    "display_style": "黑色商品＋白底",
                },
            }
        }
    }

    fallback = fallback_product_preview_request(
        ProductPreviewRequest(instruction="換成綠色"),
        source,
    )

    assert fallback.product == "帆布袋"
    assert fallback.placement == "袋子中央"
    assert fallback.display_style == "黑色商品＋白底"
    assert fallback.preview_prompt == "換成綠色"


def test_preview_record_marks_current_image_fallback_reference() -> None:
    from app.api.v1.routes.images import add_preview
    from app.schemas.image import ProductPreviewRequest

    record = {
        "assets": {
            "preview": {
                "saved": False,
                "favorite": False,
                "collection_ids": [],
            }
        }
    }
    add_preview(
        record,
        ProductPreviewRequest(instruction="換成綠色"),
        {
            "filename": "new_mockup.png",
            "url": "/generated/images/new_mockup.png",
            "reference_source": "current_preview",
            "reference_filename": "old_mockup.png",
        },
    )

    parameters = record["assets"]["preview"]["parameters"]
    assert parameters["reference_source"] == "current_preview"
    assert parameters["reference_filename"] == "old_mockup.png"

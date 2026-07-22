from app.schemas.image import GenerateRequest


def test_generate_request_only_exposes_user_inputs() -> None:
    request = GenerateRequest(prompt="守護", elements=["月亮"])
    assert request.model_dump() == {"prompt": "守護", "elements": ["月亮"]}


def test_legacy_catalog_fields_are_ignored() -> None:
    request = GenerateRequest(
        prompt="守護",
        elements=["月亮"],
        palette="紅黑白",
        count=4,
        size="1536x1024",
    )
    assert request.model_dump() == {"prompt": "守護", "elements": ["月亮"]}


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

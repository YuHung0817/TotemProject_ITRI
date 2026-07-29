from app.api.v1.routes.images import choose_product_reference_source


def test_same_product_uses_current_preview() -> None:
    assert (
        choose_product_reference_source(
            changes_product=False,
            has_current_preview=True,
            has_target_reference=True,
        )
        == "current_preview"
    )


def test_changed_product_uses_target_built_in_reference() -> None:
    assert (
        choose_product_reference_source(
            changes_product=True,
            has_current_preview=True,
            has_target_reference=True,
        )
        == "built_in"
    )


def test_changed_unknown_product_does_not_reuse_current_preview() -> None:
    assert (
        choose_product_reference_source(
            changes_product=True,
            has_current_preview=True,
            has_target_reference=False,
        )
        == "none"
    )


def test_missing_current_preview_can_use_target_reference() -> None:
    assert (
        choose_product_reference_source(
            changes_product=False,
            has_current_preview=False,
            has_target_reference=True,
        )
        == "built_in"
    )

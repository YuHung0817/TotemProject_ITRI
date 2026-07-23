from pathlib import Path


REFERENCE_DIRECTORY = Path(__file__).resolve().parents[1] / "assets" / "product_references"

PRODUCT_REFERENCE_FILES = {
    "托特包": "tote-bag.jpg",
    "帆布袋": "canvas-bag.jpg",
    "束口袋": "drawstring-bag.jpg",
    "午餐袋": "lunch-bag.jpg",
    "飲料提袋": "beverage-carrier.jpg",
    "環形鑰匙圈": "loop-key-fob.jpg",
    "台灣高中生側背書包": "taiwan-school-shoulder-bag.jpg",
    "貝殼零錢包": "shell-coin-purse.jpg",
    "圖騰織帶手機掛繩": "phone-lanyard.jpg",
}


def product_reference_path(product: str) -> Path | None:
    filename = PRODUCT_REFERENCE_FILES.get(product)
    if filename is None:
        return None
    path = REFERENCE_DIRECTORY / filename
    return path if path.is_file() else None

from pathlib import Path


REFERENCE_DIRECTORY = Path(__file__).resolve().parents[1] / "assets" / "product_references"

PRODUCT_REFERENCE_FILES = {
    "托特包": "tote-bag.jpg",
    "黑色托特包": "black-tote-bag.png",
    "帆布袋": "canvas-bag.jpg",
    "黑色帆布袋": "black-canvas-bag.png",
    "束口袋": "drawstring-bag.jpg",
    "黑色束口袋": "black-drawstring-bag.png",
    "午餐袋": "lunch-bag.jpg",
    "黑色午餐袋": "black-lunch-bag.png",
    "飲料提袋": "beverage-carrier.jpg",
    "黑色飲料袋": "black-beverage-carrier.png",
    "環形鑰匙圈": "loop-key-fob.jpg",
    "黑色環形鑰匙圈": "black-loop-key-fob.png",
    "台灣高中生側背書包": "taiwan-school-shoulder-bag.jpg",
    "高中生紅色側背包": "red-school-shoulder-bag.png",
    "高中生黑色側背包": "black-school-shoulder-bag.png",
    "紅葉少棒紅書包": "hongye-baseball-bag.png",
    "紅葉少棒黑書包": "hongye-black-baseball-bag.png",
    "紅葉少棒綠書包": "hongye-green-baseball-bag.png",
    "貝殼零錢包": "shell-coin-purse.jpg",
    "黑色貝殼零錢包": "black-shell-coin-purse.png",
    "紅葉少棒黑色零錢包": "hongye-black-coin-purse.png",
    "紅葉少棒紅色零錢包": "hongye-red-coin-purse.png",
    "白色紅葉少棒衣服": "white-hongye-shirt.png",
    "黑色紅葉少棒衣服": "black-hongye-shirt.png",
    "圖騰織帶手機掛繩": "phone-lanyard.jpg",
    "黑色手機掛繩": "black-phone-lanyard.png",
}


def product_reference_path(product: str) -> Path | None:
    filename = PRODUCT_REFERENCE_FILES.get(product)
    if filename is None:
        return None
    path = REFERENCE_DIRECTORY / filename
    return path if path.is_file() else None

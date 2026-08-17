from typing import Any


PRODUCT_OPTIONS = {
    # "棒球帽": "baseball cap",
    # "漁夫帽": "bucket hat",
    # "圓領T-shirt": "crew neck T-shirt",
    # "短版T-shirt": "cropped crew-neck T-shirt with a clearly shortened body length and a bottom hem ending around the upper waist",
    # "Polo衫": "polo shirt",
    # "帽T": "hoodie",
    # "拉鍊帽T": "zip-up hoodie",
    # "飛行外套": "bomber jacket",
    # "牛仔外套": "denim jacket",
    # "教練外套": "coach jacket",
    # "背心": "sleeveless open-front vest with a V-shaped neckline",
    "托特包": "canvas tote bag",
    "黑色托特包": "the exact black structured tote bag shown in Image A",
    "帆布袋": (
        "simple lightweight flat canvas shopping bag with a tall rectangular body, "
        "two long narrow fabric handles, an open top, and no rigid structure"
    ),
    "黑色帆布袋": "the exact black canvas shopping bag shown in Image A",
    "束口袋": "drawstring bag",
    "黑色束口袋": "the exact black drawstring bag shown in Image A",
    "午餐袋": "insulated lunch bag with a structured fabric body, zippered top opening, and carrying handles",
    "黑色午餐袋": "the exact black insulated lunch bag shown in Image A",
    "飲料提袋": "reusable single-cup beverage carrier bag with a fabric main body wrapping the drink cup and a long narrow carrying handle",
    "黑色飲料袋": "the exact black single-cup beverage carrier shown in Image A",
    "環形鑰匙圈": "loop key fob with one folded strap, one metal rivet, and one silver split key ring",
    "黑色環形鑰匙圈": "the exact black woven loop key fob shown in Image A",
    "台灣高中生側背書包": (
        "the exact traditional Taiwanese high school student shoulder bag shown in Image A"
    ),
    "高中生紅色側背包": (
        "the exact red Taiwanese high school student shoulder bag shown in Image A"
    ),
    "高中生黑色側背包": (
        "the exact black Taiwanese high school student shoulder bag shown in Image A"
    ),
    "紅葉少棒紅書包": (
        "the exact red Hongye youth baseball shoulder bag shown in Image A"
    ),
    "紅葉少棒黑書包": (
        "the exact black Hongye youth baseball shoulder bag shown in Image A"
    ),
    "紅葉少棒綠書包": (
        "the exact green Hongye youth baseball shoulder bag shown in Image A"
    ),
    "貝殼零錢包": (
        "small structured shell-shaped coin purse with a flat bottom, rounded dome top, "
        "slightly gusseted fabric body, and a zipper following the curved top edge"
    ),
    "黑色貝殼零錢包": (
        "the exact black shell-shaped coin purse shown in Image A"
    ),
    "紅葉少棒黑色零錢包": (
        "the exact black Hongye youth baseball rectangular coin purse shown in Image A"
    ),
    "紅葉少棒紅色零錢包": (
        "the exact red-and-black Hongye youth baseball rectangular coin purse shown in Image A"
    ),
    "白色紅葉少棒衣服": (
        "the exact white Hongye youth baseball short-sleeve shirt shown in Image A"
    ),
    "黑色紅葉少棒衣服": (
        "the exact black Hongye youth baseball short-sleeve shirt shown in Image A"
    ),
    "圖騰織帶手機掛繩": (
        "adjustable crossbody phone lanyard made from one long flat woven textile strap, "
        "with a strap adjuster, metal swivel clasp, connecting ring, and phone tether tab"
    ),
    "黑色手機掛繩": "the exact black adjustable dual-hook phone lanyard shown in Image A",
}


PLACEMENT_OPTIONS = {
    "AI自動決定位置": "let the AI choose the most natural, stable, and visually clear placement for this "
    "product. Choose a location that best fits the product shape and the uploaded motif's "
    "aspect ratio. Prioritize full motif visibility, realistic attachment to the product "
    "surface, and a clean catalog-ready result. For hats, prefer a readable front panel, "
    "crown band, or brim placement only when it suits the motif. For apparel, prefer left "
    "chest, center chest, sleeve, back, hem, or side-seam placement only when it looks "
    "natural. For bags and mugs, choose the cleanest visible front-facing area. Do not "
    "use an awkward, hidden, overly curved, cropped, or visually unstable placement.",
    "袋子中央": "on the center front of the bag",
    "翻蓋偏下方": (
        "on the lower portion of the visible front flap of the Taiwanese high school shoulder "
        "bag. Center the motif horizontally, but place it vertically below the flap's midpoint, "
        "around the lower third of the flap. Keep it clear of the bottom edge and all seams"
    ),
    "置換下方圖騰": (
        "replace only the existing black-and-white horizontal motif band at the very bottom "
        "of the Hongye youth baseball bag's visible front panel with the uploaded motif"
    ),
    "置換兩側飾帶圖騰": (
        "replace only the two existing colorful vertical side bands on the coin purse's "
        "visible black woven front panel with the uploaded motif"
    ),
    "置換左右袖口圖騰": (
        "replace only the existing decorative motif bands at the left and right sleeve cuffs "
        "with the uploaded motif"
    ),
    "置換衣服下方圖騰": (
        "replace only the existing wide horizontal motif band across the lower front of "
        "the shirt with the uploaded motif"
    ),
    "提袋處": "on the visible front-facing carrying handle / shoulder strap of the tote bag. Apply the "
    "motif as one continuous textile strip running along the direction of the handle. The "
    "motif strip must occupy approximately 80% of the handle's width, leaving only narrow and "
    "even handle-fabric margins on both sides. The 80% measurement refers to the width of the "
    "tote handle itself, not the width of the bag body. Keep the motif entirely on the handle "
    "surface; do not place it on the main bag body, opening, or background.",
    "提袋": "on one clearly visible carrying handle / hand strap of the lunch bag. Apply the motif as "
    "one continuous textile strip running along the lengthwise direction of the handle. Keep "
    "the motif entirely inside the handle edges and conform it to the handle's fabric, width, "
    "curve, folds, and perspective. Do not place it on the lunch-bag body, zipper, opening, or "
    "background.",
    "袋身／杯套本體": "on the Body / Main Panel of the beverage carrier: the main and largest fabric section "
    "that wraps around and supports the drink cup. Place the complete motif on the visible "
    "front-facing surface of this cup-sleeve / cup-bag body. Keep it entirely within the "
    "main panel boundaries; do not place it on the handle, cup, lid, straw, or background.",
    "提把／提帶": "on the Handle of the beverage carrier: the long narrow fabric strap connected to the "
    "main body for hand or wrist carrying. Run the motif along the lengthwise direction of "
    "the visible handle and keep it entirely inside the handle edges. Do not place it on the "
    "main cup-sleeve body, cup, lid, straw, or background.",
    "圖騰取代皮革帶": "replace the entire leather loop strap of the key fob with a textile strap made from "
    "the uploaded motif. The uploaded motif must become the actual structural loop "
        "material, not a print, patch, or decoration placed on top of leather. No leather may "
        "remain visible. Preserve the silver split key ring, the folded loop construction, and "
        "the metal fastening rivet.",
    "肩帶": "on the clearly visible nylon webbing shoulder strap of the traditional Taiwanese high "
    "school student shoulder bag. Apply the motif "
    "as one continuous textile strip running along the length of the strap. Keep the motif "
    "entirely inside the strap edges and conform it to the strap's width, curve, folds, and "
    "perspective. Do not place it on the bag body, opening, hardware, or background.",
    "袋身中央直條": "as one vertical woven textile strip centered on the visible front panel of the "
    "shell-shaped coin purse. Run the strip continuously from the curved upper seam to the "
    "flat bottom edge, occupying approximately 20-28% of the purse's front width. Keep the "
    "strip straight, fully inside the front panel, and realistically integrated into its "
    "fabric, curvature, seams, lighting, and perspective. Do not place it on the zipper, "
    "side gusset, back panel, or background.",
    "圖騰取代整條織帶": "replace the entire long textile strap of the phone lanyard with woven fabric "
    "made from the uploaded motif. Repeat the motif cleanly along the full length of the strap "
    "while preserving its exact design, colors, proportions, and orientation. The motif must "
    "be woven into the actual structural strap material, not printed as a small logo, patch, "
    "or floating decoration. Keep the strap width consistent and show enough of its full loop "
    "to make the product recognizable. Preserve the strap adjuster, metal swivel clasp, "
    "connecting ring, and phone tether tab. Do not apply the motif to the phone, metal hardware, "
    "plastic tab, or background.",
}

# Disabled placement options retained for possible future re-enabling.
# _ALL_PLACEMENT_OPTIONS = {
#     "AI自動決定位置": (
#         "let the AI choose the most natural, stable, and visually clear placement for this product. "
#         "Choose a location that best fits the product shape and the uploaded motif's aspect ratio. "
#         "Prioritize full motif visibility, realistic attachment to the product surface, and a clean catalog-ready result. "
#         "For hats, prefer a readable front panel, crown band, or brim placement only when it suits the motif. "
#         "For apparel, prefer left chest, center chest, sleeve, back, hem, or side-seam placement only when it looks natural. "
#         "For bags and mugs, choose the cleanest visible front-facing area. "
#         "Do not use an awkward, hidden, overly curved, cropped, or visually unstable placement."
#     ),
#     "帽前": "on the front panel of the hat",
#     "帽簷": (
#         "on the top surface of the baseball-cap visor/brim, oriented perpendicular to the brim's curved front edge. "
#         "Run the motif in the front-to-back radial direction: from the crown-to-brim seam outward toward the front edge of the visor. "
#         "Do not run the motif horizontally from left to right along the brim edge."
#     ),
#     "帽子右前側邊線": (
#         "as one visible woven trim strip near the right front-side seam of the cap. "
#         "Place it on the front crown area, slightly right of center, like the sample side-trim photo. "
#         "It should be close to the right front-side seam, not close to the center front seam. "
#         "At the exact highest center point of the cap, find the small round fabric-covered raised knob where all crown-panel seams converge. "
#         "The strip's top endpoint must physically touch the bottom edge of this raised center knob. "
#         "The raised center knob must overlap and visibly cover the strip's very top edge, as if the strip is clamped underneath it. "
#         "From this highest center knob, the strip must run downward while conforming closely to the cap crown's curved three-dimensional surface. "
#         "It must visibly follow the rounded slope of the crown from top to bottom, like a textile strip laid directly onto the curved cap surface. "
#         "This top endpoint is the only exception to the right-of-center placement rule: it must begin at that exact highest center point first, "
#         "then leave the knob and follow the radiating right front-side crown seam downward. "
#         "There must be zero visible cap fabric between the raised center knob and the strip. "
#         "If the strip crosses a construction stitch or crown seam, render the strip as lying underneath that stitching: "
#         "the stitch line may remain visible on top and naturally cover a small part of the motif. "
#         "Do not cut, stop, or reroute the strip at the stitch line. "
#         "If the strip encounters a cap ventilation eyelet, let the motif pass continuously over and cover the eyelet. "
#         "The eyelet must remain underneath the motif; do not punch a hole in, cut, interrupt, or route the motif around it. "
#         "End at the seam where the crown fabric meets the brim. "
#         "The strip should be about 14-20% of the cap front width, with a constant medium-narrow width. "
#         "Keep it on the crown fabric only. Do not continue onto the visor/brim surface. "
#         "Do not place it on the exact center seam, do not make it a large front-panel patch, and do not make it diagonal or triangular."
#     ),
#     "頭頂到右前帽簷":
#     "as one visible woven trim strip near the right front-side seam of the cap, about 14-20% of the cap front width. Place it slightly right of center like a side-trim sample, close to the right front-side seam and not close to the center front seam. Start near the top button / top crown point and stop at the seam where the crown meets the brim. Do not place it on the exact center seam, do not make it a large front-panel patch, and do not extend it onto the visor/brim.",
#     "帽後": "on the back of the hat",
#     "帽子整圈織帶": "as a horizontal woven band wrapping around the hat",
#     "左胸": "on the left chest",
#     "胸前中央": "on the center chest",
#     "背面中央": "on the center back",
#     "左袖": "on the left sleeve",
#     "右袖": "on the right sleeve",
#     "左袖及右袖": (
#         "apply the same uploaded motif simultaneously to both Polo-shirt sleeves: one complete motif on the wearer's left sleeve and one complete motif on the wearer's right sleeve. "
#         "Both sleeve placements are mandatory and must be clearly visible in the same front-view image. "
#         "Match their size, height, orientation, and distance from the sleeve openings so the two placements look balanced and symmetrical. "
#         "Do not place either motif on the chest, collar, body panel, or only one sleeve."
#     ),
#     "下擺": "as a horizontal band near the bottom hem",
#     "下擺及左右袖口反摺處": (
#         "apply the same uploaded motif simultaneously to all three folded-and-stitched T-shirt hem locations: "
#         "(1) the bottom hem (Hem), (2) the wearer's left sleeve-opening hem, and (3) the wearer's right sleeve-opening hem. "
#         "All three locations are mandatory and must be clearly visible in the same output image. "
#         "At the bottom, run the motif horizontally inside the folded hem band between the bottom edge and hem stitch line. "
#         "At both sleeves, place the motif along each folded sleeve-opening band, following its curve and perspective. "
#         "Use three faithful copies of the complete uploaded motif, one at each required location."
#     ),
#     "背心整圈邊框": (
#         "apply the uploaded motif as a coordinated decorative textile border to all required vest edges in the same image: "
#         "down the left neckline/front-opening edge, down the right neckline/front-opening edge, and horizontally across the entire bottom hem. "
#         "The three border sections must visually connect at both lower front corners to form one continuous U-shaped frame. "
#         "All required sections must be present simultaneously; do not omit either front edge or the bottom hem."
#     ),
#     "口袋蓋": (
#         "on one clearly visible front flap pocket of the jacket. "
#         "Place the complete motif on the pocket flap (Flap): the separate folded fabric panel attached above the pocket opening that folds downward to cover it. "
#         "Keep the motif entirely inside the flap boundaries and conform it to the flap's shape, fabric, seam, fold, and perspective. "
#         "Do not place the motif on the pocket body, inside the pocket opening, or on the surrounding jacket panel."
#     ),
#     "下擺及左右袖口": (
#         "apply the same uploaded motif simultaneously to all three outerwear trim locations: "
#         "(1) the full bottom hem / waistband, (2) the wearer's left sleeve cuff, and (3) the wearer's right sleeve cuff. "
#         "All three locations are mandatory and must be clearly visible in the same front-view image. "
#         "Run the motif horizontally along the bottom hem and around each sleeve cuff, keeping it confined to those edge bands. "
#         "At all three locations, the motif strip must occupy approximately 60% of the corresponding hem/cuff band's width, "
#         "leaving approximately 20% of the original garment band visible as an even margin on each side. "
#         "The 60% measurement refers to the narrow crosswise width of each band, not the motif's length along the hem or cuff. "
#         "Use three faithful copies of the complete uploaded motif, one at each required location."
#     ),
#     "右前側肩膀到下擺": (
#         "as one continuous vertical woven band on the right-front body panel of a crew-neck garment. "
#         "Start the top of the band at the inner end of the wearer's right shoulder seam (Shoulder Seam), "
#         "immediately beside the right outer edge of the round rib-knit crew-neck collar (Rib Collar). "
#         "The shoulder seam is the professional garment-construction seam where the T-shirt front and back panels are sewn together. "
#         "The band must touch this collar-adjacent shoulder-seam starting point with no blank garment gap above it, "
#         "If the shoulder seam is diagonal, trim only the band's top boundary at the same angle as the shoulder seam so the top edge fits flush against it. "
#         "Do not rotate or tilt the whole band to follow the diagonal seam; immediately below the trimmed top edge, the band must run vertically down the front panel. "
#         "then run downward along the garment front until it reaches the bottom hem. "
#         "The full band must be clearly visible from the front view. "
#         "Keep it on the front body panel beside the collar, not out near the shoulder tip, sleeve, armhole, actual side seam, underarm, or back. "
#         "Do not make it diagonal, and do not wrap it around the shirt."
#     ),
#     "肩膀到下擺": (
#         "as one continuous vertical woven band on the right-front body panel of a crew-neck garment. "
#         "Start the top of the band at the inner end of the wearer's right shoulder seam (Shoulder Seam), "
#         "immediately beside the right outer edge of the round rib-knit crew-neck collar (Rib Collar). "
#         "The shoulder seam is the professional garment-construction seam where the T-shirt front and back panels are sewn together. "
#         "The band must touch this collar-adjacent shoulder-seam starting point with no blank garment gap above it, "
#         "If the shoulder seam is diagonal, trim only the band's top boundary at the same angle as the shoulder seam so the top edge fits flush against it. "
#         "Do not rotate or tilt the whole band to follow the diagonal seam; immediately below the trimmed top edge, the band must run vertically down the front panel. "
#         "then run downward along the garment front until it reaches the bottom hem. "
#         "The full band must be clearly visible from the front view. "
#         "Keep it on the front body panel beside the collar, not out near the shoulder tip, sleeve, armhole, actual side seam, underarm, or back. "
#         "Do not make it diagonal, and do not wrap it around the shirt."
#     ),
#     "袋子中央": "on the center front of the bag",
#     "提袋處": (
#         "on the visible front-facing carrying handle / shoulder strap of the tote bag. "
#         "Apply the motif as one continuous textile strip running along the direction of the handle. "
#         "The motif strip must occupy approximately 80% of the handle's width, leaving only narrow and even handle-fabric margins on both sides. "
#         "The 80% measurement refers to the width of the tote handle itself, not the width of the bag body. "
#         "Keep the motif entirely on the handle surface; do not place it on the main bag body, opening, or background."
#     ),
#     "提袋": (
#         "on one clearly visible carrying handle / hand strap of the lunch bag. "
#         "Apply the motif as one continuous textile strip running along the lengthwise direction of the handle. "
#         "Keep the motif entirely inside the handle edges and conform it to the handle's fabric, width, curve, folds, and perspective. "
#         "Do not place it on the lunch-bag body, zipper, opening, or background."
#     ),
#     "圖騰取代皮革帶": (
#         "replace the entire leather loop strap of the key fob with a textile strap made from the uploaded motif. "
#         "The uploaded motif must become the actual structural loop material, not a print, patch, or decoration placed on top of leather. "
#         "No leather may remain visible. Preserve the silver split key ring, the folded loop construction, and the metal fastening rivet."
#     ),
#     "袋身／杯套本體": (
#         "on the Body / Main Panel of the beverage carrier: the main and largest fabric section that wraps around and supports the drink cup. "
#         "Place the complete motif on the visible front-facing surface of this cup-sleeve / cup-bag body. "
#         "Keep it entirely within the main panel boundaries; do not place it on the handle, cup, lid, straw, or background."
#     ),
#     "提把／提帶": (
#         "on the Handle of the beverage carrier: the long narrow fabric strap connected to the main body for hand or wrist carrying. "
#         "Run the motif along the lengthwise direction of the visible handle and keep it entirely inside the handle edges. "
#         "Do not place it on the main cup-sleeve body, cup, lid, straw, or background."
#     ),
# }


DISPLAY_STYLE_OPTIONS = {
    "白色商品＋白底": (
        "Preserve the target product reference's exact product color. Use a clean warm "
        "white or very light beige studio background. Keep gentle shadows so the product "
        "edges remain readable."
    ),
    "黑色商品＋白底": (
        "Use a black or deep charcoal product on a clean white, warm-white, or very "
        "light gray studio background. The background must stay bright enough to "
        "make the black product silhouette, brim, seams, sleeves, handles, or edges "
        "clearly visible. Use soft studio lighting and subtle highlights on the "
        "product texture without washing out the uploaded motif."
    ),
    "深紅色商品＋白底": (
        "Use a deep dark red, burgundy, or wine-red product on a clean white, warm-white, "
        "or very light gray studio background. Preserve the product's deep red fabric color "
        "while keeping the uploaded motif crisp, unchanged, and clearly visible."
    ),
    "深綠色商品＋白底": (
        "Use a deep forest-green or dark bottle-green product on a clean white, warm-white, "
        "or very light gray studio background. Preserve the product's deep green fabric color "
        "while keeping the uploaded motif crisp, unchanged, and clearly visible."
    ),
    "深藍色商品＋白底": (
        "Use a deep navy-blue or dark indigo-blue product on a clean white, warm-white, "
        "or very light gray studio background. Preserve the product's deep blue fabric color "
        "while keeping the uploaded motif crisp, unchanged, and clearly visible."
    ),
}

# Only placements that make sense for each currently enabled product.
PRODUCT_PLACEMENT_OPTIONS = {
    "托特包": ["AI自動決定位置", "袋子中央", "提袋處"],
    "黑色托特包": ["AI自動決定位置", "袋子中央", "提袋處"],
    "帆布袋": ["AI自動決定位置", "袋子中央", "提袋處"],
    "黑色帆布袋": ["AI自動決定位置", "袋子中央", "提袋處"],
    "束口袋": ["AI自動決定位置", "袋子中央"],
    "黑色束口袋": ["AI自動決定位置", "袋子中央"],
    "午餐袋": ["AI自動決定位置", "袋子中央", "提袋"],
    "黑色午餐袋": ["AI自動決定位置", "袋子中央", "提袋"],
    "飲料提袋": ["袋身／杯套本體", "提把／提帶"],
    "黑色飲料袋": ["袋身／杯套本體", "提把／提帶"],
    "環形鑰匙圈": ["圖騰取代皮革帶"],
    "黑色環形鑰匙圈": ["圖騰取代皮革帶"],
    "台灣高中生側背書包": ["AI自動決定位置", "翻蓋偏下方", "肩帶"],
    "高中生紅色側背包": ["AI自動決定位置", "翻蓋偏下方", "肩帶"],
    "高中生黑色側背包": ["AI自動決定位置", "翻蓋偏下方", "肩帶"],
    "紅葉少棒紅書包": ["置換下方圖騰"],
    "紅葉少棒黑書包": ["置換下方圖騰"],
    "紅葉少棒綠書包": ["置換下方圖騰"],
    "貝殼零錢包": ["AI自動決定位置", "袋身中央直條"],
    "黑色貝殼零錢包": ["AI自動決定位置", "袋身中央直條"],
    "紅葉少棒黑色零錢包": ["置換兩側飾帶圖騰"],
    "紅葉少棒紅色零錢包": ["置換兩側飾帶圖騰"],
    "白色紅葉少棒衣服": ["置換左右袖口圖騰"],
    "黑色紅葉少棒衣服": ["置換衣服下方圖騰"],
    "圖騰織帶手機掛繩": ["圖騰取代整條織帶"],
    "黑色手機掛繩": ["圖騰取代整條織帶"],
}


def build_product_mockup_prompt(request: Any, variant_index: int) -> str:
    product_text = PRODUCT_OPTIONS.get(request.product, request.product)
    # Keep previously saved requests compatible after the product's display-name correction.
    if request.product == "復古側背書包":
        product_text = PRODUCT_OPTIONS["台灣高中生側背書包"]
    placement_text = PLACEMENT_OPTIONS.get(request.placement, request.placement)
    if request.product in {"圖騰織帶手機掛繩", "黑色手機掛繩"}:
        placement_text = PLACEMENT_OPTIONS["圖騰取代整條織帶"]
    display_style_text = DISPLAY_STYLE_OPTIONS.get(
        request.display_style,
        request.display_style,
    )
    # The main UI text belongs to motif generation; preview requirements are separate.
    user_text = request.preview_prompt.strip()
    placement_lock_text = ""
    product_lock_text = ""
    if request.product in {"台灣高中生側背書包", "高中生紅色側背包", "高中生黑色側背包", "復古側背書包"}:
        product_lock_text = ""
        if request.placement == "翻蓋偏下方":
            product_lock_text += """

STRICT LOWER-FLAP MOTIF POSITION AND SCALE:

- Place one complete motif below the vertical midpoint, around the lower third of the flap.
- The motif's complete outer bounding box must be approximately 20% of that flap width.
- In other words, the motif must be visibly small: about one fifth of the flap width.
- Preserve the motif's aspect ratio; derive its height proportionally from that 20% width.
- Leave generous, even, clearly visible blank flap fabric around all sides of the motif.
- Keep a clear fabric margin between the motif and the flap's bottom edge and seams.
- Do not enlarge the motif beyond 20% of the flap width, especially not to 80%.
- Do not fill most of the flap, turn it into an all-over print, or let it touch any flap edge or seam.
""".rstrip()
    if request.product in {"紅葉少棒紅書包", "紅葉少棒黑書包", "紅葉少棒綠書包"}:
        preserved_details = {
            "紅葉少棒紅書包": 'the red bag body, yellow maple leaf, and all text including "紅葉少棒 1968"',
            "紅葉少棒黑書包": "the black bag body, maple-leaf patch, and all original Chinese text",
            "紅葉少棒綠書包": 'the green bag body, yellow maple leaf, and all text including "紅葉少棒 1968"',
        }[request.product]
        product_lock_text = f"""

STRICT HONGYE BAG BOTTOM-MOTIF REPLACEMENT LOCK:

- Image A is the exact product and composition to preserve.
- Locate the existing black-and-white horizontal geometric motif band at the very bottom of the visible front panel.
- Replace that existing bottom band only with Image B, the uploaded motif.
- Fit Image B into the same long horizontal band footprint, boundaries, width, height, fabric surface, folds, lighting, and perspective.
- Preserve {preserved_details}, seams, edges, strap, buckle, rings, hardware, silhouette, camera angle, and background exactly as shown in Image A.
- Do not place the uploaded motif above the original bottom band, on the text or maple leaf, on the strap, or anywhere else.
- Do not retain, duplicate, or overlay the original black-and-white geometric design after replacement.
""".rstrip()
    if request.product in {"紅葉少棒黑色零錢包", "紅葉少棒紅色零錢包"}:
        product_lock_text = """

STRICT HONGYE COIN-PURSE TWO-SIDE-BAND REPLACEMENT LOCK:

- Image A is the PRODUCT IMAGE, the DIRECT EDIT TARGET, and the main image to modify. Edit Image A in place; do not generate or redesign a different pouch.
- Image B is the MOTIF REFERENCE ONLY. Use it only as the source design for the two replacement trim strips; never treat Image B as the product image, background, or overall composition.
- The only edit areas are the two existing narrow colorful vertical decorative bands, one near the left edge and one near the right edge of the visible front panel.
- Replace only the left and right vertical decorative trim strips. Show the uploaded motif on both strips, fitted to each strip's original narrow vertical footprint, width, height, fabric surface, lighting, and perspective.
- Because Image B may be a wide horizontal design while the product strips are narrow and vertical, adapt it appropriately for this application: scale, crop, simplify, select recognizable motif components, repeat, and rearrange them vertically as needed. Preserve the motif's identity, key shapes, and colors while making it legible in both narrow strips.
- Render both replacements as realistic woven fabric tape physically sewn into the pouch, with visible textile weave, stitched edges, natural thickness, surface integration, shadows, lighting, and perspective. Do not paste flat rectangular images or stickers onto the pouch.
- Preserve the central red maple leaf, green leaf veins and stem, "1960", "UNINANG", and every surrounding white decorative symbol exactly as shown in Image A.
- Preserve the rest of the pouch exactly: the black fabric panel, top and side panels and their original colors, zipper, zipper pull, piping, seams, rounded corners, bag dimensions, silhouette, camera angle, lighting, and background.
- Do not place the uploaded motif in the central artwork area, on the zipper, piping, side panels, top panel, or background.
- Do not remove, cover, redraw, move, resize, recolor, or alter any part of the preserved central artwork.
""".rstrip()
    if request.product == "白色紅葉少棒衣服":
        product_lock_text = """

STRICT HONGYE SHIRT TWO-SLEEVE-CUFF REPLACEMENT LOCK:

- Image A is the PRODUCT IMAGE, the DIRECT EDIT TARGET, and the main image to modify. Edit Image A in place; do not regenerate, redesign, or redraw a different shirt.
- Image B is the MOTIF REFERENCE ONLY. Use it only as the source design for the two sleeve-cuff replacement bands.
- Replace only the existing decorative motif band at the left sleeve cuff and the matching band at the right sleeve cuff. These two cuff bands are the only edit areas.
- Apply Image B to both cuffs, adapting, scaling, cropping, simplifying, repeating, and arranging it along each narrow cuff band as needed while preserving the motif's identity, key shapes, and colors.
- Make the new motif follow each sleeve opening's angle, curve, fabric shape, folds, lighting, and perspective.
- Render it as realistic woven fabric trim physically sewn into each cuff, with textile weave, stitched edges, natural thickness, shadows, and material integration. Do not paste flat images or stickers onto the sleeves.
- Preserve the rest of the shirt exactly: white color, silhouette, cut, collar, sleeves, hems, seams, fabric texture, proportions, and all chest artwork and text, including the maple leaf, "HongYe", and "1968".
- Preserve the original camera angle, framing, lighting, shadows, material appearance, scale, and background exactly as shown in Image A.
- Do not modify, cover, move, resize, recolor, redraw, or redesign any area outside the two sleeve-cuff bands.
""".rstrip()
    if request.product == "黑色紅葉少棒衣服":
        product_lock_text = """

STRICT BLACK HONGYE SHIRT LOWER-BAND REPLACEMENT LOCK:

- Image A is the PRODUCT IMAGE, the DIRECT EDIT TARGET, and the main image to modify. Edit Image A in place; do not regenerate, redesign, or redraw a different shirt.
- Image B is the MOTIF REFERENCE ONLY. Use it only as the source design for the lower-front replacement band.
- Replace only the existing wide horizontal geometric motif band across the lower front of the shirt, below the central chest artwork. That exact band footprint is the only edit area.
- Remove the original lower-band pattern and apply Image B within the same width, height, and boundaries. Scale, crop, simplify, repeat, and arrange the motif horizontally as needed while preserving its identity, key shapes, and colors.
- Follow the shirt fabric's surface, drape, folds, lighting, and perspective. Integrate the motif naturally into the textile with realistic fabric texture, printing or weaving, edge alignment, shadows, and material detail. Do not paste a flat rectangular image or sticker onto the shirt.
- Preserve the rest of the shirt exactly: black color, silhouette, cut, collar, sleeves, hems, seams, fabric texture, proportions, and all upper chest artwork and text, including "紅葉少棒", the red maple leaf, ball, yellow slash, and "1968".
- Preserve the original camera angle, framing, lighting, shadows, material appearance, scale, and background exactly as shown in Image A.
- Do not modify, cover, move, resize, recolor, redraw, or redesign any area outside the original lower motif band.
""".rstrip()
    if request.placement == "帽簷":
        placement_lock_text = """
STRICT BASEBALL-CAP VISOR PERPENDICULAR PLACEMENT LOCK:

Place the motif only on the top surface of the baseball-cap visor / brim.

Required direction:
- orient the motif front-to-back in a radial direction across the visor
- start near the seam where the cap crown joins the visor
- extend outward toward the visor's curved front edge
- the motif's long axis must be perpendicular to the local tangent of the curved front brim edge
- visually, the motif should cross the brim depth rather than follow the brim width

Forbidden direction and placement:
- motif running horizontally left-to-right along the curved front edge
- motif following the brim-edge curve
- motif placed around the brim as a horizontal band
- motif placed on the crown, front panel, side panel, or underside of the visor
- motif floating outside the visor boundaries

Keep the motif fully inside the visor surface and conform it to the visor's curve, material, seams, lighting, and perspective.
""".strip()
    elif request.placement in {
        "帽子右前側邊線",
        "頭頂到右前帽簷",
    }:
        side_text = "right"
        cap_anchor_layering_text = ""
        top_start_text = "- starts near the top button / top crown point"
        if request.placement == "帽子右前側邊線":
            top_start_text = "- top endpoint physically touches and is overlapped by the small round fabric-covered raised knob at the exact highest center point where all crown-panel seams converge; zero gap is allowed"
            cap_anchor_layering_text = f"""
{side_text.upper()}-SIDE CROWN-APEX ANCHOR AND STITCH-LAYERING RULES:
- Identify the exact highest center point of the cap where all crown-panel seam lines meet.
- At that seam intersection there is a small, round, fabric-covered raised knob. This visible geometric object is the required starting anchor.
- TOP-END CONTACT IS MANDATORY: the strip's top endpoint must physically touch the bottom edge of that raised knob.
- The raised knob must overlap and visibly cover the strip's very top edge, as if clamping the strip beneath it.
- FROM THIS HIGHEST CENTER ANCHOR, RUN THE STRIP DOWNWARD ALONG THE CAP CROWN'S CURVED SURFACE.
- The entire strip must conform to and visibly follow the rounded three-dimensional slope of the crown from top to bottom.
- Treat it as a textile strip physically laid onto the cap's curved fabric surface, not as a flat graphic floating near the button.
- Zero pixels / zero visible cap fabric may appear between the raised knob's bottom edge and the strip's top endpoint.
- The strip must not begin beside the raised knob, merely near it, or lower down on the crown.
- The raised knob must not float above the strip without overlapping the strip's top edge.
- At the very top only, ignore the general instruction to stay {side_text} of center: begin at the exact crown-panel seam intersection, then follow the radiating {side_text} front-side crown seam downward.
- The strip may naturally change direction immediately below the raised knob to follow that {side_text} front-side seam; this is not an unwanted diagonal placement.
- Where a construction stitch or crown seam crosses the strip, keep the stitch line visibly on top of the motif.
- A narrow portion of the motif may be naturally occluded by the overlying stitch line to create correct physical depth.
- The motif must remain continuous underneath the stitch; do not cut, stop, split, or divert it around the seam.
- If the strip crosses a ventilation eyelet, place the motif on top of the eyelet and allow it to cover the eyelet completely.
- Keep the ventilation eyelet underneath the motif; do not preserve or redraw the eyelet on top of the artwork.
- Do not punch a hole in, cut, interrupt, split, or divert the motif around a ventilation eyelet.
""".strip()
        placement_lock_text = """
STRICT CAP SIDE-SEAM PLACEMENT LOCK:

The motif must become a visible side-trim strip on the cap front crown.

Required appearance:
- constant medium-narrow strip
- about 14-20% of the visible cap front width
- slightly {side_text} of center, similar to a cap side-trim sample photo
- close to the {side_text} front-side seam
- not close to the center front seam
- not on the exact center front seam
{top_start_text}
- ends at the crown-to-brim seam
- remains on crown fabric only

{cap_anchor_layering_text}

Forbidden appearance:
- large patch covering a front panel
- wide diagonal band
- triangular or wedge-shaped panel fill
- motif placed exactly on the center front seam between the two front crown panels
- motif placed in the center front logo area
- motif placed too close to the center line instead of the requested {side_text} front-side seam
- motif extending onto the visor/brim
- motif wrapping around the cap

If the motif is too wide, scale it down and crop the visible strip less aggressively only as needed,
but keep the final placement as a medium-narrow side-trim strip near the requested {side_text} front-side seam.
""".format(
            side_text=side_text,
            cap_anchor_layering_text=cap_anchor_layering_text,
            top_start_text=top_start_text,
        ).strip()
    elif request.placement in {"右前側肩膀到下擺", "肩膀到下擺"}:
        placement_lock_text = """
STRICT RIGHT-FRONT GARMENT STRIPE PLACEMENT LOCK:

The motif must become a continuous vertical stripe on the garment's visible right-front body panel, starting beside the round rib-knit crew-neck collar and ending at the bottom hem.

Required appearance:
- full stripe visible from the front view
- vertical or nearly vertical
- top edge starts at the inner end of the wearer's right shoulder seam (Shoulder Seam), immediately beside the right outer edge of the round rib-knit crew-neck collar (Rib Collar)
- Shoulder Seam means the garment-construction seam where the T-shirt front panel and back panel are sewn together
- the required anchor is the collar-side inner end of that shoulder seam, with no blank garment gap above the stripe
- if the shoulder seam is diagonal, trim only the stripe's top boundary to the same diagonal angle so it fits flush against the seam
- this angled top-edge trim is allowed even though the rest of the uploaded motif must not be cropped or redesigned
- immediately below the trimmed top boundary, the stripe must turn into a straight vertical path down the garment front
- keep the stripe body vertical; do not rotate, tilt, or run the entire stripe diagonally along the shoulder seam
- ends at the bottom hem
- remains beside the rib collar on the visible right-front body panel
- runs continuously downward on the garment front to the bottom hem
- not hidden on the outer shoulder tip, sleeve, armhole, actual side seam, underarm, or back

Forbidden appearance:
- stripe covering the rib collar itself instead of beginning immediately beside its outer edge
- stripe starting far away from the rib collar
- stripe starting lower on the chest with a blank gap above it
- required anchor is the inner end of the right shoulder seam immediately beside the outer edge of the rib collar
- outer shoulder tip and armhole are forbidden starting anchors, but the collar-adjacent inner end of the shoulder seam is mandatory
- stripe starting near the collar center instead of touching the right shoulder / upper armhole seam
- stripe failing to continue all the way down to the bottom hem
- entire stripe tilted diagonally merely because the shoulder seam is diagonal
- stripe following the shoulder seam sideways instead of descending vertically down the front panel
- diagonal stripe
- stripe wrapping around the side or back

The starting landmark is where the right edge of the rib collar meets the inner end of the right shoulder seam. Do not use the outer shoulder tip or armhole.
""".strip()
    elif request.placement in {"提袋處", "提袋"}:
        placement_lock_text = """
STRICT BAG HANDLE PLACEMENT LOCK:

Place the motif only on one clearly visible front-facing bag handle / carrying strap.

Required appearance:
- motif is one continuous textile strip aligned with and running along the handle
- motif width is approximately 80% of the handle width
- narrow, even margins of the original handle fabric remain visible along both sides of the motif
- motif follows the handle's shape, curve, perspective, and fabric surface
- motif remains clearly visible on the handle

Measurement rule:
- 80% means 80% of the carrying handle's width, measured across the narrow dimension of the handle
- 80% does NOT refer to the bag body's width, the handle's length, or the entire image width

Forbidden appearance:
- motif placed on the main bag body instead of the handle
- motif wider than the handle or spilling outside the handle edges
- motif filling 100% of the handle width with no visible margins
- motif floating beside the handle or appearing in the background
- motif split into disconnected decorative pieces
""".strip()
    elif request.placement == "下擺及左右袖口反摺處":
        placement_lock_text = """
STRICT SIMULTANEOUS THREE-HEM PLACEMENT LOCK:

Create exactly three faithful placements of the uploaded motif in the same T-shirt image.

All three locations are mandatory:
1. Bottom hem: one motif runs horizontally inside the folded-and-stitched bottom hem band, between the garment's bottom edge and its hem stitch line.
2. Wearer's left sleeve opening: one motif follows the narrow folded-and-stitched sleeve-hem band at the left sleeve opening.
3. Wearer's right sleeve opening: one motif follows the narrow folded-and-stitched sleeve-hem band at the right sleeve opening.

Required appearance:
- all three motif placements appear simultaneously and are clearly visible in one output image
- each placement preserves the complete uploaded motif faithfully
- each motif stays confined to its corresponding narrow folded hem band
- motifs conform to the fabric surface, folds, curves, stitch lines, and perspective
- both sleeve openings and the full bottom hem remain visible in the composition

Forbidden appearance:
- only one or two of the three required placements shown
- either sleeve-opening motif missing
- bottom-hem motif missing
- motif floating above the bottom hem on the main body panel
- motif placed in the middle or upper portion of either sleeve
- motif extending outside a garment edge or appearing on the collar, chest, shoulder, or background
""".strip()
    elif request.placement == "背心整圈邊框":
        placement_lock_text = """
STRICT COMPLETE VEST BORDER PLACEMENT LOCK:

Show one sleeveless open-front vest in a straight-on front view. Apply the motif to the complete front border in one operation.

All three border sections are mandatory in the same image:
1. Left border: from the left shoulder / neckline top, follow the left V-neckline and left front-opening edge continuously down to the lower-left corner.
2. Right border: from the right shoulder / neckline top, follow the right V-neckline and right front-opening edge continuously down to the lower-right corner.
3. Bottom border: run horizontally across the full bottom hem, connecting the lower-left and lower-right corners.

Required appearance:
- both vertical/V-shaped front borders and the full horizontal bottom border are clearly visible simultaneously
- the three sections meet cleanly at both lower corners and read as one continuous U-shaped decorative frame
- border width remains consistent and medium-narrow around the vest edges
- motif conforms to the vest fabric, edge shape, seams, folds, and perspective
- vest remains open at the center front; do not close or fill the opening with artwork

Forbidden appearance:
- only one front edge decorated
- either left or right border missing
- bottom-hem border missing
- motif placed in the center of a vest panel instead of along the edges
- border crossing or filling the open center-front gap
- motif placed on the armholes, background, or inside lining
""".strip()
    elif request.placement == "口袋蓋":
        placement_lock_text = """
STRICT JACKET POCKET-FLAP PLACEMENT LOCK:

Show a jacket with at least one clearly visible front flap pocket. Place the motif on one pocket flap only.

Pocket-flap definition:
- the Flap is a distinct folded fabric panel sewn above the pocket opening
- it folds downward over the pocket entrance to help block rain, dust, and debris
- it is not the pocket pouch/body and not the surrounding jacket body panel

Required appearance:
- complete motif is clearly visible on the outward-facing surface of the flap
- motif remains fully inside the flap's left, right, top, and bottom boundaries
- motif is centered and uniformly scaled to fit the flap without distortion
- motif follows the flap's fabric texture, fold, stitching, shape, and perspective
- flap remains recognizable as a separate functional fabric panel covering the pocket opening

Forbidden appearance:
- motif placed on the pocket body below the flap
- motif placed inside or across the pocket opening
- motif placed on the chest or jacket body beside the pocket
- motif spilling beyond or floating outside the flap edges
- motif replacing the flap or turning the entire pocket into artwork
""".strip()
    elif request.placement == "下擺及左右袖口":
        placement_lock_text = """
STRICT OUTERWEAR BOTTOM-HEM AND BOTH-CUFFS PLACEMENT LOCK:

Show the complete selected jacket or zip-up hoodie in a straight-on front view with the bottom hem and both sleeve cuffs clearly visible. Create exactly three faithful motif placements in the same image.

All three locations are mandatory:
1. Bottom hem: one motif runs horizontally across the full bottom hem / waistband edge of the garment.
2. Wearer's left cuff: one motif follows the complete folded cuff band at the left sleeve opening.
3. Wearer's right cuff: one motif follows the complete folded cuff band at the right sleeve opening.

Required appearance:
- bottom hem and both cuff motifs appear simultaneously
- each placement preserves the complete uploaded motif faithfully
- motifs stay confined to the bottom-hem band and the two sleeve-cuff bands
- at each of the three locations, motif width is approximately 60% of the corresponding hem/cuff band width
- approximately 20% of the original garment band remains visible as an even margin on each side of the motif
- 60% refers to the narrow crosswise width of the band, not the motif's running length along the hem or cuff
- motifs conform to the selected garment's material, texture, seams, folds, cuff shapes, and perspective
- both sleeves must be positioned so neither cuff is hidden, cropped, or behind the jacket body

Forbidden appearance:
- only one or two of the three required locations decorated
- either cuff motif missing
- bottom-hem motif missing
- motif placed in the middle of a sleeve or above the jacket hem
- motif placed on the collar, chest, pockets, background, or outside the garment edges
- motif filling 100% of a hem/cuff band with no visible garment margins
- motif wider than 60% of the band or spilling beyond the band edges
""".strip()
    elif request.placement == "左袖及右袖":
        placement_lock_text = """
STRICT POLO-SHIRT BOTH-SLEEVES PLACEMENT LOCK:

Show one Polo shirt in a straight-on front view with both sleeves fully visible. Create exactly two faithful placements of the uploaded motif in the same image.

Both locations are mandatory:
1. Wearer's left sleeve: one complete motif on the visible outer surface of the left sleeve.
2. Wearer's right sleeve: one complete motif on the visible outer surface of the right sleeve.

Required appearance:
- both sleeve motifs appear simultaneously and are equally clear
- both copies preserve the complete uploaded motif
- placements use matching scale, height, orientation, and spacing from their respective sleeve openings
- motifs conform to sleeve fabric, folds, curvature, and perspective
- both sleeves remain uncropped and unobstructed

Forbidden appearance:
- motif shown on only one sleeve
- either left or right sleeve motif missing
- mismatched motif sizes or noticeably uneven placement heights
- motif placed on the chest, collar, placket, main body panel, or background
- either sleeve hidden behind the body or cropped out of the image
""".strip()
    elif request.placement == "圖騰取代皮革帶":
        placement_lock_text = """
STRICT KEY-FOB LEATHER-REPLACEMENT LOCK:

Create one loop key fob consisting of one silver split key ring, one fastening rivet, and one folded loop strap. Replace the original leather strap completely with a textile strap constructed from the uploaded motif.

Replacement rule:
- the motif textile IS the strap material itself
- remove 100% of the leather from the loop strap
- do not place, print, emboss, laminate, or stitch the motif on top of leather
- no brown, tan, black, or other leather layer may remain visible at the front, edges, fold, or underside

Required construction:
- motif textile forms one continuous flat strap that folds back into a loop
- both strap ends meet at the silver metal split ring
- one visible metal rivet fastens the folded strap near the ring
- strap retains realistic thickness, woven texture, edge finishing, flexibility, and physical connection to the ring
- uploaded motif remains recognizable along the visible strap surface
- show exactly one complete key fob in a clean catalog-style composition

Forbidden appearance:
- motif merely printed or attached on top of a leather strap
- leather borders, leather backing, or leather underside still visible
- motif floating inside the loop instead of forming the loop
- missing split ring, missing rivet, broken strap, or disconnected parts
- two key fobs shown instead of one
""".strip()
    elif request.placement == "袋身／杯套本體":
        placement_lock_text = """
STRICT BEVERAGE-CARRIER MAIN-BODY PLACEMENT LOCK:

Show one reusable beverage carrier holding one drink cup. Place the complete motif only on the carrier's Body / Main Panel.

Body / Main Panel definition:
- the largest primary fabric section that wraps around and physically supports the cup body
- for a half-height carrier, this is the cup sleeve surrounding the cup's middle section
- for a full-height carrier, this is the cup-bag body covering most of the cup
- it is not the carrying handle, cup surface, lid, straw, or background

Required appearance:
- complete motif is centered and clearly visible on the outward-facing main panel
- motif stays fully inside the main-panel boundaries
- motif conforms to the panel's fabric texture, curve around the cup, seams, folds, and perspective
- main body remains recognizable as the structural fabric section carrying the cup

Forbidden appearance:
- motif placed on the handle or carrying strap
- motif printed directly on the drink cup
- motif placed on the lid, straw, hand, or background
- motif spilling outside the cup-sleeve/main-panel edges
""".strip()
    elif request.placement == "提把／提帶":
        placement_lock_text = """
STRICT BEVERAGE-CARRIER HANDLE PLACEMENT LOCK:

Show one reusable beverage carrier holding one drink cup, with its complete carrying handle clearly visible. Place the motif only on the Handle.

Handle definition:
- the long narrow fabric strap connected to the carrier body for hand or wrist carrying
- it may also be called a carrying strap, hand loop, wrist strap, or fabric handle
- it is not the cup-sleeve Body / Main Panel

Required appearance:
- complete motif runs along the lengthwise direction of the visible handle
- motif stays fully inside both long edges of the handle
- motif conforms to the handle's fabric, width, curve, folds, and perspective
- handle remains structurally connected to the beverage-carrier body
- composition keeps enough of the handle visible to make the motif recognizable

Forbidden appearance:
- motif placed on the main cup-sleeve body instead of the handle
- motif placed directly on the drink cup, lid, straw, hand, or background
- motif wider than the handle or spilling outside its edges
- handle hidden, cropped, broken, or disconnected from the carrier body
""".strip()

    variant_directions = [
        "Use a clean front-facing product photography composition.",
        "Use a slightly angled product photography composition to show fabric depth.",
        "Use a realistic catalog-style mockup with soft studio lighting.",
        "Use a simple premium product display composition with a neutral background.",
    ]
    variant_text = variant_directions[variant_index % len(variant_directions)]

    return f"""
You are a professional apparel and product mockup designer.

Image B is not a product reference.

Image B is the FINAL motif artwork.

It is a finished embroidery / cross-stitch / woven motif that has already been approved.

Your job is ONLY to place this exact artwork onto a product.

━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTE RULES
━━━━━━━━━━━━━━━━━━━━━━

The uploaded motif is immutable.

You MUST preserve it exactly.

DO NOT:

- redesign it
- simplify it
- beautify it
- reinterpret it
- repaint it
- vectorize it
- regenerate it
- crop important parts
- mirror it
- stretch it
- distort it
- change the geometry
- change the layout
- change the symmetry
- change the borders
- change the embroidery stitches
- add decorative elements
- remove decorative elements
- invent new patterns
- invent missing areas
- change motif proportions
- extract individual symbols from the motif
- replace the motif with a similar-looking design

DO NOT change:

- colors
- color palette
- saturation
- brightness
- hue
- stitch pattern
- geometric shapes
- diamonds
- triangles
- borders
- spacing
- rhythm
- embroidery texture

Treat the uploaded motif exactly like a customer-provided logo or protected design asset.

Pixel-level similarity to the uploaded artwork is preferred.

━━━━━━━━━━━━━━━━━━━━━━
STRICT MOTIF COLOR FIDELITY
━━━━━━━━━━━━━━━━━━━━━━

Match the motif colors to the uploaded image as closely and accurately as possible.

The uploaded image is the only source of truth for every motif color.

You MUST preserve:

- exact hue and color identity
- saturation level
- brightness and value relationships
- contrast between adjacent colors
- relative proportion and location of every color

Do NOT recolor, color-grade, harmonize, mute, brighten, darken, warm, cool, tint, or restyle the motif to match the product, background, lighting, or photographic mood.

Do NOT replace any original motif color with a similar, more fashionable, more vivid, or more aesthetically pleasing color.

Studio lighting and fabric curvature may create only minimal realistic surface shading. They must not change the motif's underlying base colors or make the palette look different from the uploaded image.

When uncertain, copy the uploaded motif's original colors rather than inventing or estimating new colors.

The output should look like the original motif has been physically attached to the product,
NOT regenerated by AI.

━━━━━━━━━━━━━━━━━━━━━━
LONG HORIZONTAL MOTIF RULES
━━━━━━━━━━━━━━━━━━━━━━

If the uploaded motif is a long horizontal woven band:

- keep the complete band continuous
- do not break it into multiple pieces
- do not rearrange the composition
- do not extract individual symbols
- do not repeat only one small part
- do not redesign the band
- only scale it uniformly if needed

━━━━━━━━━━━━━━━━━━━━━━
YOUR ONLY TASK
━━━━━━━━━━━━━━━━━━━━━━

Apply the uploaded motif onto the requested product.

Product:
{product_text}

Placement:
{placement_text}

{placement_lock_text}

{product_lock_text}

The motif should look physically attached to the product as one of these:

- embroidery
- woven band
- woven patch
- textile decoration
- printed fabric band

according to the requested placement.

━━━━━━━━━━━━━━━━━━━━━━
COMPLETE PRODUCT FRAMING
━━━━━━━━━━━━━━━━━━━━━━

Show the entire product inside the final image.

- Do not crop, cut off, or place any part of the product outside the image boundaries.
- Keep the product's complete body, top, bottom, left edge, and right edge visible.
- Keep all handles, straps, closures, hardware, and other defining product parts visible.
- Zoom out when necessary so the complete product fits naturally in the composition.
- Leave clear breathing room between the product and every edge of the image.
- Prefer a slightly smaller fully visible product over a large product that is cropped.
- For unusually long straps or accessories, arrange them naturally within the frame while
  keeping the complete product as visible and uncropped as possible.

━━━━━━━━━━━━━━━━━━━━━━
VISUAL STYLE
━━━━━━━━━━━━━━━━━━━━━━

{variant_text}

Realistic commercial product photography.

Studio lighting.

Product and background color direction:
{display_style_text}

High-quality product catalog style.

The product must be clearly visible.

The motif must remain fully recognizable.

Do NOT let folds, shadows, perspective, wrinkles, or lighting destroy the motif.

Do NOT let the product color, background color, studio lighting, white balance, or shadows alter the motif's original color palette.

━━━━━━━━━━━━━━━━━━━━━━
USER REQUIREMENT
━━━━━━━━━━━━━━━━━━━━━━

{user_text if user_text else "No additional requirement."}

━━━━━━━━━━━━━━━━━━━━━━
FINAL PRIORITY
━━━━━━━━━━━━━━━━━━━━━━

The highest priority is preserving the uploaded motif exactly.

Exact motif color fidelity to the uploaded image is a top-priority requirement.

If there is any conflict between realism and motif preservation,
always preserve the motif.
""".strip()

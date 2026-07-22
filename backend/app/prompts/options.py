ELEMENT_OPTIONS = {
    # 設計原則：Recognizable Abstraction（可辨識的抽象）
    # 不要把元素抽象到完全看不出來；要保留第一眼可辨識的剪影特徵，
    # 再用布農織帶常見的菱形、三角形、鋸齒、階梯、棋盤格轉譯。
    "山豬": (
        "Keep the motif clearly recognizable as a wild boar, while simplifying it into Bunun woven geometry. "
        "Preserve a broad low body, rounded snout, short legs, and upward tusks. "
        "Build the body from nested diamonds and checkerboard diamond fills; use mirrored stepped triangles for tusks, "
        "short blocky legs, and zigzag bands for movement. Avoid realistic fur, eyes, or anatomy, but the silhouette should still read as a wild boar."
    ),
    "山羌": (
        "Keep the motif clearly recognizable as a barking deer or small muntjac-like deer, while simplifying it into Bunun woven geometry. "
        "Preserve a slender body, long thin legs, small upright antlers or ears, and an alert standing pose. "
        "Use elongated diamonds for the body, narrow stepped triangles for legs and antlers, and small repeated diamond footprints. "
        "Avoid realistic anatomy, but the silhouette should remain visibly different from the wild boar."
    ),
    "山羊": (
        "Use mountain goat cues only as secondary geometric accents within the dominant diamond/checkerboard woven band. "
        "Suggest a compact body, sure-footed stance, short tail, and curved horns through nested diamonds and stepped triangles, "
        "but do not let the goat become the main visual subject or an isolated silhouette. Avoid realistic fur or facial details."
    ),
    "水鹿": (
        "Keep the motif recognizable as a sambar deer, larger and more solid than the barking deer. "
        "Preserve a tall body, long legs, upright neck, and branching antler silhouette. "
        "Use elongated diamonds, stepped antler branches, and small repeated hoof marks, while keeping the form geometric and woven."
    ),
    "台灣黑熊": (
        "Keep the motif recognizable as a Formosan black bear, with a strong rounded body, short legs, rounded ears, and a clear V-shaped chest mark. "
        "Construct the body from bold nested diamonds and blocky stepped forms, using the V chest as a woven triangular highlight. "
        "Avoid realistic claws, fur, facial expression, or mascot styling."
    ),
    "月亮": (
        "Keep the crescent moon clearly recognizable. Represent it as a stepped crescent or half-diamond arc made from repeated X-stitch cells, "
        "then integrate it into the border rhythm so it feels woven rather than like a floating icon."
    ),
    "太陽": (
        "Keep the sun recognizable as an eight-point woven sun or octagonal flower-like motif. "
        "Use nested diamonds, short radiating stepped triangles, and red/yellow contrast. Do not reduce it to a generic diamond only."
    ),
    "山脈": (
        "Keep a readable mountain ridge. Transform it into continuous stepped triangles and zigzag skyline borders, "
        "with the mountain form still visible as a repeated woven horizon."
    ),
    "河流": (
        "Represent a flowing river using continuous zigzag or wave-like stepped bands that pass through the composition. "
        "It should feel like movement across the textile, not an isolated icon or literal illustration."
    ),
    "鳥": (
        "Keep the motif readable as a bird in flight, but translate it into Bunun woven geometry rather than a standing bird illustration. "
        "Use a clear spread-wing shape made from mirrored stepped triangles or chevrons, with a small central diamond or cross-stitch block as the body. "
        "A tiny triangular beak-like point is acceptable only if it helps the flying-bird reading, but avoid legs, toes, eyes, perched poses, realistic feathers, or cartoon anatomy."
    ),
    "小米": (
        "Keep millet recognizable as a grain-bearing stalk. Use a slim vertical or diagonal stem made from short stitches, "
        "with clustered small diamonds or seed-like X-stitch cells along the head. Integrate it as a harvest rhythm inside the woven band."
    ),
    "菖蒲": (
        "Keep sweet flag recognizable through long blade-like leaves. Use narrow paired triangles, diagonal stitch blades, "
        "and repeated upright leaf clusters arranged as a protective plant border, not a realistic botanical drawing."
    ),
    "葫蘆": (
        "Keep the gourd recognizable by preserving its rounded double-lobed silhouette. Build it from stacked rounded diamond forms, "
        "with a short stepped stem and small vine-like zigzags, integrated into the central band."
    ),
    "玉米": (
        "Keep corn recognizable as an ear with rows of kernels. Use an elongated diamond or oval-like stepped shape filled with checkerboard kernels, "
        "with angular husk leaves made from mirrored triangles."
    ),
    "稻米": (
        "Keep rice recognizable as bending grain heads. Use fine diagonal stalks with small repeated diamond grains, "
        "arranged like a modest harvest border that remains flat, counted, and geometric."
    ),
    "樹豆": (
        "Keep pigeon pea recognizable as pods and small beans. Use paired pod-like diamond chains, tiny roundish square beans, "
        "and short branch angles woven into a repeating plant motif."
    ),
    "茅草": (
        "Keep cogon grass recognizable as tall grass blades and plume-like seed heads. Use thin stepped verticals, diagonal blade clusters, "
        "and small light diamond tips as a woven grass border."
    ),
    "星星": (
        "Keep the star recognizable as a small eight-point cross-stitch star or octagonal flower motif. "
        "Use a central diamond with tiny stepped points around it, integrated into the woven band rhythm."
    ),
    "菱形": (
        "Use Bunun-inspired checkerboard diamonds, snake-pattern continuous diamonds, nested diamonds, and optional octagonal flower-like motifs inside selected diamonds."
    ),
    "射耳祭": (
        "Translate the Ear-Shooting Festival as a respectful ceremonial motif, not a literal scene. "
        "Use target-like nested diamonds, arrow or spear-like stepped lines, small repeated ear-shaped diamond cues, and balanced ceremonial borders. "
        "Avoid people, weapons as realistic objects, blood, hunting violence, or narrative illustration."
    ),
}

PALETTE_OPTIONS = {
    "天然麻布色": (
        "undyed natural ramie cloth background in warm off-white or light beige, "
        "with traditional Bunun geometric weaving in black, red, yellow, green, and dark blue."
    ),
    "白底祭儀風": (
        "off-white ceremonial ramie cloth background, "
        "with red and black as the dominant woven colors, "
        "plus yellow, green, blue, or purple used throughout the geometric pattern."
    ),
    "深色布底": (
        "black or deep navy woven cloth background, "
        "with high-contrast red, white, yellow, blue, and green geometric woven motifs."
    ),
    "滿版織帶": (
        "A seamless full-coverage Bunun woven textile. "
        "The entire canvas is woven pattern. "
        "There is no separate background layer. "
        "Every stitch belongs to the textile pattern. "
        "The image should resemble a close-up photograph or scan of an authentic woven band, "
        "cropped from the middle of a long textile, with continuous geometric motifs extending beyond all four edges."
    ),
    "黑白": (
        "black and off-white only, "
        "using continuous woven geometric patterns without additional colors."
    ),
    "紅黑白": (
        "red, black, and off-white as the dominant colors, "
        "with yellow used as a secondary color distributed throughout the woven motif."
    ),
    "紅綠黃": (
        "off-white or natural ramie background, "
        "with red as the dominant color, black outlines, "
        "and green and yellow distributed throughout the geometric pattern."
    ),
}

# 第一色固定為底色，其餘依序為主要色與輔助色。每次生成會隨機抽四組，
# 但四張都由同一張基礎圖重新映色，因此圖騰形狀與位置完全相同。
PALETTE_COLORS = {
    "天然麻布色": [(239, 230, 205), (23, 19, 16), (165, 42, 36), (213, 166, 42), (23, 59, 85)],
    "白底祭儀風": [(245, 240, 228), (177, 38, 34), (23, 19, 16), (216, 169, 39), (62, 83, 107)],
    "深色布底": [(17, 24, 39), (244, 239, 226), (185, 43, 39), (213, 166, 42), (53, 99, 74)],
    "黑白": [(244, 239, 226), (21, 21, 21)],
    "紅黑白": [(244, 239, 226), (181, 43, 38), (21, 21, 21)],
    "紅綠黃": [(241, 232, 210), (181, 43, 38), (40, 86, 58), (213, 166, 42), (21, 21, 21)],
}

VARIANT_DIRECTIONS = [
    "Design A: use a continuous checkerboard diamond band inspired by Bunun woven diamond and snake-pattern geometry.",
    "Design B: build alternating large and small diamond panels with stepped triangular borders above and below.",
    "Design C: use a dense black-white-red geometric band with octagonal flower-like motifs inside selected diamonds.",
    "Design D: create a symmetrical repeating strip with zigzag edges, nested diamonds, and high-contrast color blocks.",
]

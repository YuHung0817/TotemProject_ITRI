import base64
import math
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from app.services.storage_service import store_pillow_image

REPEAT_COUNT = 3


def crop_horizontal_background_margin(source: Image.Image) -> Image.Image:
    """Trim generated blank side margins before making the repeat preview."""
    width, height = source.size
    rgb_image = source.convert("RGB")
    pixels = rgb_image.load()
    significant_columns: list[int] = []
    minimum_content_pixels = max(6, int(height * 0.02))

    for x in range(width):
        content_pixels = 0
        for y in range(height):
            red, green, blue = pixels[x, y]
            maximum = max(red, green, blue)
            minimum = min(red, green, blue)
            saturation = maximum - minimum
            luminance = (0.299 * red) + (0.587 * green) + (0.114 * blue)
            is_dark_motif = luminance < 90
            is_red_motif = red > 120 and red > green * 1.25 and red > blue * 1.25
            is_green_motif = green > 70 and green > red * 1.15 and green > blue * 1.15
            is_yellow_motif = red > 120 and green > 85 and blue < 105 and abs(red - green) < 100
            is_saturated_motif = saturation > 65 and luminance < 210
            if (
                is_dark_motif
                or is_red_motif
                or is_green_motif
                or is_yellow_motif
                or is_saturated_motif
            ):
                content_pixels += 1
        if content_pixels >= minimum_content_pixels:
            significant_columns.append(x)

    if not significant_columns:
        return source

    padding = max(2, width // 256)
    left = max(0, significant_columns[0] - padding)
    right = min(width, significant_columns[-1] + padding + 1)
    cropped_width = right - left

    if cropped_width < width * 0.6 or cropped_width >= width:
        return source

    return source.crop((left, 0, right, height))


def save_source_image(
    source: Image.Image,
    image_id: str,
    crop_margin: bool = True,
) -> tuple[str, str]:
    source = source.convert("RGBA")
    original_filename = store_pillow_image(source, label="original")
    repeat_source = crop_horizontal_background_margin(source) if crop_margin else source
    repeated = Image.new("RGBA", (repeat_source.width * REPEAT_COUNT, repeat_source.height))
    for index in range(REPEAT_COUNT):
        repeated.paste(repeat_source, (repeat_source.width * index, 0))
    filename = store_pillow_image(repeated, label="repeat")
    return filename, original_filename


def save_image_from_base64(image_base64: str, image_id: str) -> tuple[str, str]:
    source = Image.open(BytesIO(base64.b64decode(image_base64))).convert("RGBA")
    return save_source_image(source, image_id)


def recolor_flat_motif(
    source: Image.Image,
    source_palette: list[tuple[int, int, int]],
    target_palette: list[tuple[int, int, int]],
) -> Image.Image:
    """Map one flat source motif to a fixed palette without changing its geometry."""
    rgb_source = source.convert("RGB")
    source_labs = [rgb_to_lab(color) for color in source_palette]
    target_for_source = [
        target_palette[index % len(target_palette)] for index in range(len(source_palette))
    ]
    cache: dict[tuple[int, int, int], tuple[int, int, int]] = {}

    def replacement(color: tuple[int, int, int]) -> tuple[int, int, int]:
        if color not in cache:
            color_lab = rgb_to_lab(color)
            nearest_index = min(
                range(len(source_palette)),
                key=lambda index: lab_distance(color_lab, source_labs[index]),
            )
            cache[color] = target_for_source[nearest_index]
        return cache[color]

    recolored = Image.new("RGB", rgb_source.size)
    recolored.putdata([replacement(color) for color in rgb_source.getdata()])
    return recolored


def rgb_to_lab(color: tuple[int, int, int]) -> tuple[float, float, float]:
    channels = []
    for value in color:
        value /= 255
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    x = (red * 0.4124564 + green * 0.3575761 + blue * 0.1804375) / 0.95047
    y = red * 0.2126729 + green * 0.7151522 + blue * 0.0721750
    z = (red * 0.0193339 + green * 0.1191920 + blue * 0.9503041) / 1.08883

    def pivot(value: float) -> float:
        return value ** (1 / 3) if value > 0.008856 else (7.787 * value) + (16 / 116)

    fx, fy, fz = pivot(x), pivot(y), pivot(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def lab_distance(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    return math.sqrt(sum((left - right) ** 2 for left, right in zip(first, second)))


def extract_dominant_palette(source: Image.Image, color_count: int) -> list[tuple[int, int, int]]:
    """Merge the closest color groups into the more frequent existing color."""
    sample = source.copy()
    sample.thumbnail((512, 512), Image.Resampling.NEAREST)
    exact_counts = Counter(sample.getdata())

    buckets: dict[tuple[int, int, int], Counter] = defaultdict(Counter)
    for color, count in exact_counts.items():
        buckets[tuple(channel // 16 for channel in color)][color] += count

    candidates = []
    for colors in buckets.values():
        representative, peak = colors.most_common(1)[0]
        candidates.append(
            {
                "color": representative,
                "count": sum(colors.values()),
                "peak": peak,
                "lab": rgb_to_lab(representative),
            }
        )

    clusters = sorted(candidates, key=lambda item: (item["count"], item["peak"]), reverse=True)[:96]
    while len(clusters) > color_count:
        closest_pair = (0, 1)
        closest_distance = float("inf")
        for first_index in range(len(clusters) - 1):
            for second_index in range(first_index + 1, len(clusters)):
                distance = lab_distance(clusters[first_index]["lab"], clusters[second_index]["lab"])
                if distance < closest_distance:
                    closest_distance = distance
                    closest_pair = (first_index, second_index)

        first_index, second_index = closest_pair
        first, second = clusters[first_index], clusters[second_index]
        winner, loser = (first, second) if first["count"] >= second["count"] else (second, first)
        merged = {**winner, "count": winner["count"] + loser["count"]}
        clusters.pop(second_index)
        clusters.pop(first_index)
        clusters.append(merged)

    return [
        item["color"] for item in sorted(clusters, key=lambda item: item["count"], reverse=True)
    ]


def reduce_to_chart_cells(
    source: Image.Image,
    chart_width: int,
    chart_height: int,
    palette: list[tuple[int, int, int]],
) -> Image.Image:
    """Select stitches by local palette voting without creating interpolation shades."""
    scale = 3
    sampled = source.resize((chart_width * scale, chart_height * scale), Image.Resampling.NEAREST)
    sampled_pixels = sampled.load()
    palette_labs = [rgb_to_lab(color) for color in palette]
    nearest_cache: dict[tuple[int, int, int], tuple[int, int, int]] = {}

    def nearest_color(color: tuple[int, int, int]) -> tuple[int, int, int]:
        if color not in nearest_cache:
            color_lab = rgb_to_lab(color)
            nearest_cache[color] = min(
                zip(palette, palette_labs),
                key=lambda item: lab_distance(color_lab, item[1]),
            )[0]
        return nearest_cache[color]

    reduced = Image.new("RGB", (chart_width, chart_height))
    reduced_pixels = reduced.load()
    for y in range(chart_height):
        for x in range(chart_width):
            votes = Counter(
                nearest_color(sampled_pixels[x * scale + dx, y * scale + dy])
                for dy in range(scale)
                for dx in range(scale)
            )
            reduced_pixels[x, y] = votes.most_common(1)[0][0]
    return reduced


def create_cross_stitch_chart(
    source_path: Path,
    chart_width: int,
    chart_height: int,
    color_count: int,
) -> bytes:
    """Convert an original image to a limited-color, counted cross-stitch preview."""
    with Image.open(source_path) as source_image:
        source = source_image.convert("RGB")
        palette = extract_dominant_palette(source, color_count)
        reduced = reduce_to_chart_cells(source, chart_width, chart_height, palette)

    cell_size = 8
    canvas = Image.new(
        "RGB",
        (chart_width * cell_size + 1, chart_height * cell_size + 1),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    pixels = reduced.load()
    for y in range(chart_height):
        for x in range(chart_width):
            left = x * cell_size
            top = y * cell_size
            draw.rectangle(
                (left, top, left + cell_size - 1, top + cell_size - 1),
                fill=pixels[x, y],
            )

    # Thin cell lines plus a stronger guide every ten stitches.
    for x in range(chart_width + 1):
        position = x * cell_size
        color = (70, 70, 70) if x % 10 == 0 else (195, 195, 195)
        draw.line((position, 0, position, chart_height * cell_size), fill=color)
    for y in range(chart_height + 1):
        position = y * cell_size
        color = (70, 70, 70) if y % 10 == 0 else (195, 195, 195)
        draw.line((0, position, chart_width * cell_size, position), fill=color)

    output = BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue()

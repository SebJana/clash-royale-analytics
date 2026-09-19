from pathlib import Path
import base64
import colorsys
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
import math
import random
import re
from statistics import mean
from time import perf_counter

import cairosvg
from PIL import Image, ImageChops, ImageDraw

# ~1.4:1 ratio pixel ratio
CARD_WIDTH = 320
CARD_HEIGHT = 448
FRUIT_SIZE = 96
# Fewer fruits have more card space, so they can be noticeably larger.
FRUIT_SCALE_RANGES = {
    1: (1.10, 1.35),
    2: (1.00, 1.25),
    3: (0.90, 1.18),
    4: (0.82, 1.04),
    5: (0.75, 0.93),
}
# Dense cards use smaller rotation bounds so all randomized layouts fit.
FRUIT_ROTATION_RANGES = {
    1: (-28, 28),
    2: (-24, 24),
    3: (-20, 20),
    4: (-14, 14),
    5: (-10, 10),
}
FRUIT_POSITION_JITTER = 18
FRUIT_GAP = 8
FRUIT_PLACEMENT_ATTEMPTS = 100
FRUIT_LAYOUT_ATTEMPTS = 50
CARD_CORNER_RADIUS = 16
BACKGROUND_COLOR_RANGE = (235, 253)
BACKGROUND_NOISE_STANDARD_DEVIATION = 7

AVAILABLE_FRUITS = ("banana", "grapes", "orange", "strawberry")

# Relative center-coordinates in [0.0, 1.0] for the fruit items
# (x, y) measured from top-left, based on how many elements are on the card
FRUIT_POSITIONS = {
    1: [
        (0.50, 0.50),
    ],
    2: [
        (0.50, 0.33),
        (0.50, 0.67),
    ],
    3: [
        (0.50, 0.25),
        (0.32, 0.65),
        (0.68, 0.65),
    ],
    4: [
        (0.32, 0.32),
        (0.68, 0.32),
        (0.32, 0.68),
        (0.68, 0.68),
    ],
    5: [
        (0.30, 0.28),
        (0.70, 0.28),
        (0.50, 0.50),
        (0.30, 0.72),
        (0.70, 0.72),
    ],
}

HEX_COLOR_PATTERN = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\\b")
DOCKER_HALLI_GALLI_DIR = Path("/app/shared_resources/halli_galli")


@dataclass(frozen=True)
class FruitStyle:
    """Random visual variation applied to one fruit icon."""

    scale: float
    is_horizontally_flipped: bool
    rotation_degrees: float
    hue_shift: float
    saturation_multiplier: float
    lightness_multiplier: float


@dataclass(frozen=True)
class FruitPlacement:
    """A scaled fruit's center position and appearance on the card."""

    center_x: float
    center_y: float
    style: FruitStyle

    @property
    def half_extent(self) -> float:
        """Return a rotation-aware half-size for overlap detection."""

        half_size = FRUIT_SIZE * self.style.scale / 2
        rotation = math.radians(self.style.rotation_degrees)
        return half_size * (abs(math.cos(rotation)) + abs(math.sin(rotation)))


def _random_source(rng: random.Random | None):
    """Return an injectable random source, defaulting to the module generator."""

    return rng if rng is not None else random


def find_halli_galli_asset_dir() -> Path:
    """Find assets in Docker first, then locate them from a local checkout."""

    if DOCKER_HALLI_GALLI_DIR.is_dir():
        return DOCKER_HALLI_GALLI_DIR

    for parent in Path(__file__).resolve().parents:
        asset_dir = parent / "shared_resources" / "halli_galli"
        if asset_dir.is_dir():
            return asset_dir

    raise FileNotFoundError("Could not locate shared_resources/halli_galli")


def load_random_fruit_svg(fruit: str, rng: random.Random | None = None) -> str:
    """Load a random SVG variation for the given fruit."""

    fruit_path = find_halli_galli_asset_dir() / fruit

    svg_files = list(fruit_path.glob("*.svg"))

    if not svg_files:
        raise FileNotFoundError(f"No SVG files found in {fruit_path}")

    # Pick one of the variations in the fruit directory
    file_path = _random_source(rng).choice(svg_files)

    return file_path.read_text(encoding="utf-8")


def create_fruit_style(amount: int, rng: random.Random | None = None) -> FruitStyle:
    """Create subtle, independently testable visual variation for one fruit."""

    source = _random_source(rng)
    return FruitStyle(
        scale=source.uniform(*FRUIT_SCALE_RANGES[amount]),
        is_horizontally_flipped=source.choice((True, False)),
        rotation_degrees=source.uniform(*FRUIT_ROTATION_RANGES[amount]),
        hue_shift=source.uniform(-0.05, 0.05),
        saturation_multiplier=source.uniform(0.85, 1.15),
        lightness_multiplier=source.uniform(0.90, 1.10),
    )


def clamp(value: float, lower: float, upper: float) -> float:
    """Clamp ``value`` to an inclusive numeric interval."""

    return max(lower, min(value, upper))


def placement_is_non_overlapping(
    candidate: FruitPlacement, placements: list[FruitPlacement]
) -> bool:
    """Check whether a candidate has the required gap from every fruit."""

    return all(
        abs(candidate.center_x - placement.center_x)
        >= candidate.half_extent + placement.half_extent + FRUIT_GAP
        or abs(candidate.center_y - placement.center_y)
        >= candidate.half_extent + placement.half_extent + FRUIT_GAP
        for placement in placements
    )


def create_fruit_placements(
    relative_positions: list[tuple[float, float]],
    amount: int,
    rng: random.Random | None = None,
) -> list[FruitPlacement]:
    """Jitter fruit centers while enforcing card bounds and no-overlap spacing."""

    source = _random_source(rng)
    styles = [create_fruit_style(amount, source) for _ in relative_positions]

    # A valid early jitter can still leave too little room for a later fruit.
    # Retry the entire layout rather than weakening the no-overlap constraint.
    for _ in range(FRUIT_LAYOUT_ATTEMPTS):
        placements = []

        for (relative_x, relative_y), style in zip(relative_positions, styles):
            half_extent = FruitPlacement(0, 0, style).half_extent
            base_x = CARD_WIDTH * relative_x
            base_y = CARD_HEIGHT * relative_y

            for _ in range(FRUIT_PLACEMENT_ATTEMPTS):
                center_x = clamp(
                    base_x
                    + source.uniform(-FRUIT_POSITION_JITTER, FRUIT_POSITION_JITTER),
                    half_extent + CARD_CORNER_RADIUS,
                    CARD_WIDTH - half_extent - CARD_CORNER_RADIUS,
                )
                center_y = clamp(
                    base_y
                    + source.uniform(-FRUIT_POSITION_JITTER, FRUIT_POSITION_JITTER),
                    half_extent + CARD_CORNER_RADIUS,
                    CARD_HEIGHT - half_extent - CARD_CORNER_RADIUS,
                )
                candidate = FruitPlacement(center_x, center_y, style)

                if placement_is_non_overlapping(candidate, placements):
                    placements.append(candidate)
                    break
            else:
                break

        if len(placements) == len(relative_positions):
            return placements

    raise RuntimeError("Could not place fruit without overlapping another fruit")


def augment_svg_colors(svg: str, style: FruitStyle) -> str:
    """Apply a small hue, saturation, and lightness shift to SVG hex colors."""

    def replace_color(match: re.Match) -> str:
        hex_color = match.group(1)
        if len(hex_color) == 3:
            hex_color = "".join(component * 2 for component in hex_color)

        red, green, blue = (
            int(hex_color[index : index + 2], 16) / 255 for index in (0, 2, 4)
        )
        hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
        hue = (hue + style.hue_shift) % 1
        saturation = clamp(saturation * style.saturation_multiplier, 0, 1)
        lightness = clamp(lightness * style.lightness_multiplier, 0, 1)
        red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)

        return "#{:02x}{:02x}{:02x}".format(
            round(red * 255), round(green * 255), round(blue * 255)
        )

    return HEX_COLOR_PATTERN.sub(replace_color, svg)


def create_fruit_element(fruit_svg: str, placement: FruitPlacement) -> str:
    """Build the SVG image element for one transformed and recolored fruit."""

    styled_svg = augment_svg_colors(fruit_svg, placement.style)
    encoded_svg = base64.b64encode(styled_svg.encode("utf-8")).decode("ascii")
    x = placement.center_x - FRUIT_SIZE / 2
    y = placement.center_y - FRUIT_SIZE / 2
    scale_x = (
        -placement.style.scale
        if placement.style.is_horizontally_flipped
        else placement.style.scale
    )
    transform = (
        f"translate({placement.center_x:.2f} {placement.center_y:.2f}) "
        f"rotate({placement.style.rotation_degrees:.2f}) "
        f"scale({scale_x:.3f} {placement.style.scale:.3f}) "
        f"translate({-placement.center_x:.2f} {-placement.center_y:.2f})"
    )

    return (
        f'<image href="data:image/svg+xml;base64,{encoded_svg}" '
        f'x="{x:.2f}" y="{y:.2f}" '
        f'width="{FRUIT_SIZE}" height="{FRUIT_SIZE}" '
        f'transform="{transform}" '
        'preserveAspectRatio="xMidYMid meet" />'
    )


def build_card_svg(fruit_elements: list[str]) -> str:
    """Build the transparent SVG foreground containing the border and fruits."""

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" '
        f'height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}">'
        f'<rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" '
        f'rx="{CARD_CORNER_RADIUS}" fill="none" stroke="#1f2937" stroke-width="4" />'
        f'{"".join(fruit_elements)}'
        "</svg>"
    )


def render_svg_foreground(card_svg: str) -> Image.Image:
    """Rasterize a card SVG into a transparent RGBA foreground image."""

    png = cairosvg.svg2png(bytestring=card_svg.encode("utf-8"))
    return Image.open(BytesIO(png)).convert("RGBA")


def create_noisy_background(rng: random.Random | None = None) -> Image.Image:
    """Create a subtly tinted, lightly noisy background clipped to the card."""

    source = _random_source(rng)
    base_color = tuple(source.randint(*BACKGROUND_COLOR_RANGE) for _ in range(3))
    background = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), base_color)
    noise = Image.effect_noise(
        (CARD_WIDTH, CARD_HEIGHT), BACKGROUND_NOISE_STANDARD_DEVIATION
    ).convert("RGB")
    background = ImageChops.add(background, noise, offset=-128).convert("RGBA")

    card_mask = Image.new("L", (CARD_WIDTH, CARD_HEIGHT), 0)
    ImageDraw.Draw(card_mask).rounded_rectangle(
        (0, 0, CARD_WIDTH - 1, CARD_HEIGHT - 1),
        radius=CARD_CORNER_RADIUS,
        fill=255,
    )
    background.putalpha(card_mask)
    return background


def compose_card(background: Image.Image, foreground: Image.Image) -> bytes:
    """Layer the fruit foreground over the generated background and encode PNG."""

    card = Image.alpha_composite(background, foreground)
    output = BytesIO()
    card.save(output, format="PNG")
    return output.getvalue()


def create_card(fruit: str, amount: int) -> bytes | None:
    """Create a PNG card containing ``amount`` of ``fruit``.

    Fruit SVGs are embedded in an intermediate SVG and then turned into a png.

    Returns:
        bytes: The completed PNG image.
        None: If ``fruit`` or ``amount`` is unsupported.
    """
    # Card-generation flow:
    # 1. Validate the requested fruit/count so only supported cards
    #    enter the rendering pipeline.
    # 2. Select different source icons and independently vary their size, flip,
    #    rotation, placement, and colors. This prevents a card type from having
    #    one fixed image signature that is easy to classify automatically.
    # 3. Reject jittered layouts that would overlap, preserving a fair and
    #    readable card even with the intentionally stronger visual variation.
    # 4. Composite the icons over a randomized, lightly noisy background and
    #    rasterize the complete result on the server.
    #
    # The response is a flattened PNG rather than JSON, client-side drawing
    # instructions, or SVG. Those formats expose semantic details such as the
    # fruit name, count, source paths, element boundaries, and transforms that
    # would make programmatic detection/classification much cheaper. PNG sends
    # only the final pixels, requiring an automated client to interpret the
    # visual result. A general-purpose multimodal LLM or a specialized computer
    # vision model can still often identify and count the fruit more reliably
    # and quickly than a human. This is therefore not a security boundary; it
    # adds model-building, inference, maintenance, and unforeseen edge-case
    # hurdles for automation.
    if fruit not in AVAILABLE_FRUITS:
        return None
    if amount not in FRUIT_POSITIONS:
        return None

    placements = create_fruit_placements(FRUIT_POSITIONS[amount], amount)
    fruit_elements = [
        create_fruit_element(load_random_fruit_svg(fruit), placement)
        for placement in placements
    ]
    foreground = render_svg_foreground(build_card_svg(fruit_elements))
    return compose_card(create_noisy_background(), foreground)

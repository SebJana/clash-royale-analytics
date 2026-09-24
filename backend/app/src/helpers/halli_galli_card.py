from pathlib import Path
import base64
import colorsys
from io import BytesIO
import math
import random
import re
from pydantic import BaseModel, ConfigDict, Field

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
# Sparse cards can use stronger position variation; vertical movement is
# deliberately larger than horizontal movement on every card type.
FRUIT_POSITION_JITTER = {
    1: (32, 56),
    2: (32, 48),
    3: (28, 40),
    4: (22, 32),
    5: (18, 26),
}
# Shift the base formation as a whole before independently jittering fruits.
FORMATION_POSITION_SHIFT = {
    1: (30, 42),
    2: (28, 38),
    3: (22, 32),
    4: (18, 26),
    5: (14, 20),
}
FRUIT_GAP = 8
FRUIT_PLACEMENT_ATTEMPTS = 100
FRUIT_LAYOUT_ATTEMPTS = 50
CARD_CORNER_RADIUS = 16
BACKGROUND_COLOR_RANGE = (235, 253)
BACKGROUND_NOISE_STANDARD_DEVIATION = 7

AVAILABLE_FRUITS = ("banana", "grapes", "orange", "strawberry")

# Source assets and their painted hulls do not change while the application is
# running, so retain them directly in process memory after their first use to avoid
# unnecessary file read and calculation workload
FRUIT_SVG_CACHE: dict[str, tuple[str, ...]] = {}
VISIBLE_SVG_HULL_CACHE: dict[str, tuple[tuple[float, float], ...]] = {}

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

# Match literal SVG palette values only; this avoids changing IDs or dimensions.
HEX_COLOR_PATTERN = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
DOCKER_HALLI_GALLI_DIR = Path("/app/shared_resources/halli_galli")


class FruitStyle(BaseModel):
    """Random visual variation applied to one fruit icon."""

    # Variation is generated once per fruit, then reused during layout retries
    # so retries change positions without unexpectedly changing the artwork.
    model_config = ConfigDict(frozen=True)

    scale: float
    is_horizontally_flipped: bool
    rotation_degrees: float
    hue_shift: float
    saturation_multiplier: float
    lightness_multiplier: float


class FruitCreationPlacement(BaseModel):
    """Internal placement and styling used while generating a fruit image."""

    model_config = ConfigDict(frozen=True)

    relative_x: float = Field(ge=0, le=1)
    relative_y: float = Field(ge=0, le=1)
    style: FruitStyle

    @property
    def center_x(self) -> float:
        """Return the horizontal center in card pixels for rendering.

        Returns:
            float: Pixel coordinate measured from the left edge.
        """

        return self.relative_x * CARD_WIDTH

    @property
    def center_y(self) -> float:
        """Return the vertical center in card pixels for rendering.

        Returns:
            float: Pixel coordinate measured from the top edge.
        """

        return self.relative_y * CARD_HEIGHT

    def to_image_bounds(
        self, visible_hull: tuple[tuple[float, float], ...]
    ) -> "FruitImageBounds":
        """Transform the cached painted SVG hull into an unchecked image box.

        Args:
            visible_hull (tuple[tuple[float, float], ...]): Painted SVG outline
                in the source icon's pixel coordinates.

        Returns:
            FruitImageBounds: Normalized box before on-card checks.
        """

        image_x = self.center_x - FRUIT_SIZE / 2
        image_y = self.center_y - FRUIT_SIZE / 2
        horizontal_scale = (
            -self.style.scale
            if self.style.is_horizontally_flipped
            else self.style.scale
        )
        vertical_scale = self.style.scale
        rotation = math.radians(self.style.rotation_degrees)
        cosine = math.cos(rotation)
        sine = math.sin(rotation)

        transformed_points = []
        for source_x, source_y in visible_hull:
            # This matches the translate -> rotate -> scale SVG transform used
            # for rendering each image element below.
            offset_x = (image_x + source_x - self.center_x) * horizontal_scale
            offset_y = (image_y + source_y - self.center_y) * vertical_scale
            transformed_points.append(
                (
                    self.center_x + offset_x * cosine - offset_y * sine,
                    self.center_y + offset_x * sine + offset_y * cosine,
                )
            )

        min_x = min(point[0] for point in transformed_points)
        max_x = max(point[0] for point in transformed_points)
        min_y = min(point[1] for point in transformed_points)
        max_y = max(point[1] for point in transformed_points)
        return FruitImageBounds(
            x=min_x / CARD_WIDTH,
            y=min_y / CARD_HEIGHT,
            width=(max_x - min_x) / CARD_WIDTH,
            height=(max_y - min_y) / CARD_HEIGHT,
        )

    def to_image_position(
        self, visible_hull: tuple[tuple[float, float], ...]
    ) -> "FruitImagePosition":
        """Return a validated final-image box for an accepted placement.

        Args:
            visible_hull (tuple[tuple[float, float], ...]): Painted SVG outline.

        Returns:
            FruitImagePosition: Normalized box kept for server-side click checks.
        """

        return FruitImagePosition(**self.to_image_bounds(visible_hull).model_dump())


class FruitImageBounds(BaseModel):
    """Internal normalized box that may temporarily extend outside the card."""

    model_config = ConfigDict(frozen=True)

    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class FruitImagePosition(BaseModel):
    """A normalized painted fruit bounding box on the final card image."""

    model_config = ConfigDict(frozen=True)

    # x/y identify the top-left corner in normalized 0-1 card coordinates.
    # Bounds derive from source SVG alpha pixels, not the full viewport, and
    # remain usable when the PNG is displayed at a different size.
    # Keep these values server-side for click hit testing: a submitted pointer
    # coordinate can be checked against the target fruit's painted bounds. This
    # means automation must locate the fruit on the image, not merely classify
    # the card's fruit type or count. Do not expose these boxes to the client.
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)


class HalliGalliCard(BaseModel):
    """A rendered card and the server-side metadata used to produce it."""

    # The renderer has finished when this model is created; immutable metadata
    # prevents its answer from drifting away from the rendered image in memory.
    model_config = ConfigDict(frozen=True)

    image: bytes
    fruit: str
    amount: int
    fruit_positions: list[FruitImagePosition]


def find_halli_galli_asset_dir() -> Path:
    """Find assets in Docker first, then locate them from a local checkout.

    Returns:
        Path: Directory containing the source fruit SVG folders.
    """

    if DOCKER_HALLI_GALLI_DIR.is_dir():
        # Docker copies shared resources to this stable runtime location.
        return DOCKER_HALLI_GALLI_DIR

    # Local paths vary by developer, so discover the repository resource folder
    # from this module rather than relying on a machine-specific absolute path.
    for parent in Path(__file__).resolve().parents:
        asset_dir = parent / "shared_resources" / "halli_galli"
        if asset_dir.is_dir():
            return asset_dir

    raise FileNotFoundError("Could not locate shared_resources/halli_galli")


def get_fruit_svgs(fruit: str) -> tuple[str, ...]:
    """Load and retain every SVG variation for one fruit in process memory.

    Args:
        fruit (str): Fruit folder to load.

    Returns:
        tuple[str, ...]: SVG source strings for that fruit.
    """

    cached_svgs = FRUIT_SVG_CACHE.get(fruit)
    if cached_svgs is not None:
        return cached_svgs

    fruit_path = find_halli_galli_asset_dir() / fruit
    svg_files = sorted(fruit_path.glob("*.svg"))

    if not svg_files:
        raise FileNotFoundError(f"No SVG files found in {fruit_path}")

    svg_contents = tuple(
        file_path.read_text(encoding="utf-8") for file_path in svg_files
    )
    FRUIT_SVG_CACHE[fruit] = svg_contents
    return svg_contents


def load_random_fruit_svg(fruit: str) -> str:
    """Select a random SVG variation from the cached source assets.

    Args:
        fruit (str): Fruit whose source artwork is needed.

    Returns:
        str: One SVG variation for this fruit.
    """

    return random.choice(get_fruit_svgs(fruit))


def _convex_hull(
    points: set[tuple[float, float]],
) -> tuple[tuple[float, float], ...]:
    """Return the convex hull used for fast affine bounding-box transforms.

    Args:
        points (set[tuple[float, float]]): Corners of painted source pixels.

    Returns:
        tuple[tuple[float, float], ...]: Outer points in hull order.
    """

    sorted_points = sorted(points)
    if len(sorted_points) <= 1:
        return tuple(sorted_points)

    def cross(
        origin: tuple[float, float],
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> float:
        """Measure which side of an edge the next hull point lies on.

        Args:
            origin (tuple[float, float]): Edge starting point.
            first (tuple[float, float]): Edge ending point.
            second (tuple[float, float]): Candidate next point.

        Returns:
            float: Signed turn value used to remove inner points.
        """
        return (first[0] - origin[0]) * (second[1] - origin[1]) - (
            first[1] - origin[1]
        ) * (second[0] - origin[0])

    lower = []
    for point in sorted_points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)

    upper = []
    for point in reversed(sorted_points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)

    return tuple(lower[:-1] + upper[:-1])


def get_visible_svg_hull(svg: str) -> tuple[tuple[float, float], ...]:
    """Cache the convex hull of a fixed SVG's non-transparent source pixels.

    Args:
        svg (str): Source icon before scaling, rotation, or recoloring.

    Returns:
        tuple[tuple[float, float], ...]: Painted outline used to compute the
            actual click box after the icon is transformed.
    """

    cached_hull = VISIBLE_SVG_HULL_CACHE.get(svg)
    if cached_hull is not None:
        return cached_hull

    # Rendering source assets at their displayed 96px viewport captures their
    # real paths, fills, strokes, clipping, and transparent padding at once.
    png = cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        output_width=FRUIT_SIZE,
        output_height=FRUIT_SIZE,
    )
    alpha = Image.open(BytesIO(png)).convert("RGBA").getchannel("A")
    pixel_corners = set()

    for index, opacity in enumerate(alpha.getdata()):
        if opacity == 0:
            continue

        pixel_x = index % FRUIT_SIZE
        pixel_y = index // FRUIT_SIZE
        # Pixel corners, rather than centers, avoid under-reporting the visible
        # extent by half a pixel before scale and rotation are applied.
        pixel_corners.update(
            {
                (pixel_x, pixel_y),
                (pixel_x + 1, pixel_y),
                (pixel_x, pixel_y + 1),
                (pixel_x + 1, pixel_y + 1),
            }
        )

    if not pixel_corners:
        raise ValueError("Fruit SVG has no visible pixels")

    hull = _convex_hull(pixel_corners)
    VISIBLE_SVG_HULL_CACHE[svg] = hull
    return hull


def create_fruit_style(amount: int) -> FruitStyle:
    """Create subtle, independently testable visual variation for one fruit.

    Args:
        amount (int): Fruit count used to choose safe size and rotation ranges.

    Returns:
        FruitStyle: Scale, flip, rotation, and color changes for one icon.
    """

    # Amount-specific ranges keep sparse cards expressive without making dense
    # layouts impossible to place after rotation and collision checks.
    return FruitStyle(
        scale=random.uniform(*FRUIT_SCALE_RANGES[amount]),
        is_horizontally_flipped=random.choice((True, False)),
        rotation_degrees=random.uniform(*FRUIT_ROTATION_RANGES[amount]),
        hue_shift=random.uniform(-0.03, 0.03),
        saturation_multiplier=random.uniform(0.90, 1.10),
        lightness_multiplier=random.uniform(0.94, 1.06),
    )


def create_formation_offset(amount: int) -> tuple[float, float]:
    """Create one shared x/y offset for the card's entire fruit formation.

    Args:
        amount (int): Fruit count used to choose the shift range.

    Returns:
        tuple[float, float]: Horizontal and vertical shifts in pixels.
    """

    max_x_shift, max_y_shift = FORMATION_POSITION_SHIFT[amount]
    return (
        random.uniform(-max_x_shift, max_x_shift),
        random.uniform(-max_y_shift, max_y_shift),
    )


def clamp(value: float, lower: float, upper: float) -> float:
    """Clamp ``value`` to an inclusive numeric interval.

    Args:
        value (float): Number being limited.
        lower (float): Smallest accepted value.
        upper (float): Largest accepted value.

    Returns:
        float: Value within the given limits.
    """

    return max(lower, min(value, upper))


def image_position_is_valid(
    candidate: FruitImageBounds,
    placed_positions: list[FruitImageBounds],
) -> bool:
    """Check that a painted bounding box stays on-card and clear of others.

    Args:
        candidate (FruitImageBounds): Proposed fruit box after transforms.
        placed_positions (list[FruitImageBounds]): Boxes already accepted.

    Returns:
        bool: Whether the new box fits without touching another fruit.
    """

    horizontal_margin = CARD_CORNER_RADIUS / CARD_WIDTH
    vertical_margin = CARD_CORNER_RADIUS / CARD_HEIGHT
    horizontal_gap = FRUIT_GAP / CARD_WIDTH
    vertical_gap = FRUIT_GAP / CARD_HEIGHT

    if not (
        candidate.x >= horizontal_margin
        and candidate.y >= vertical_margin
        and candidate.x + candidate.width <= 1 - horizontal_margin
        and candidate.y + candidate.height <= 1 - vertical_margin
    ):
        return False

    # The returned painted boxes are the same boxes used here. A separating-axis
    # check is therefore enough to reject boxes that touch or overlap.
    return all(
        candidate.x + candidate.width + horizontal_gap <= position.x
        or position.x + position.width + horizontal_gap <= candidate.x
        or candidate.y + candidate.height + vertical_gap <= position.y
        or position.y + position.height + vertical_gap <= candidate.y
        for position in placed_positions
    )


def create_standard_fruit_placements(
    relative_positions: list[tuple[float, float]],
    styles: list[FruitStyle],
) -> list[FruitCreationPlacement]:
    """Return the original unshifted formation when random placement is exhausted.

    Args:
        relative_positions (list[tuple[float, float]]): Base fruit centers.
        styles (list[FruitStyle]): Artwork changes selected for these fruits.

    Returns:
        list[FruitCreationPlacement]: Original centers with the same styles.
    """

    # The base formations were chosen to be readable before any variation. Keep
    # the already-selected styles so a fallback does not unexpectedly reroll art.
    return [
        FruitCreationPlacement(
            relative_x=relative_x,
            relative_y=relative_y,
            style=style,
        )
        for (relative_x, relative_y), style in zip(relative_positions, styles)
    ]


def create_fruit_placements(
    relative_positions: list[tuple[float, float]],
    amount: int,
    visible_hulls: list[tuple[tuple[float, float], ...]],
) -> list[FruitCreationPlacement]:
    """Jitter fruits while enforcing their final painted bounds and spacing.

    Args:
        relative_positions (list[tuple[float, float]]): Base fruit centers.
        amount (int): Fruit count used for position and style limits.
        visible_hulls (list[tuple[tuple[float, float], ...]]): Painted outline
            for each selected source SVG.

    Returns:
        list[FruitCreationPlacement]: Non-overlapping randomized positions, or
            the original formation when the retry limit is exhausted.
    """

    if len(relative_positions) != len(visible_hulls):
        raise ValueError("Each fruit position requires one visible SVG hull")

    # Keep visual identity fixed while trying alternate positions for it.
    styles = [create_fruit_style(amount) for _ in relative_positions]

    # A valid early jitter can still leave too little room for a later fruit.
    # Retry the entire layout rather than weakening the no-overlap constraint.
    for _ in range(FRUIT_LAYOUT_ATTEMPTS):
        placements = []
        image_positions = []
        # This moves the die-like formation as one unit before each fruit gets
        # its own jitter, avoiding a recognizable fixed formation origin.
        formation_x, formation_y = create_formation_offset(amount)
        max_x_jitter, max_y_jitter = FRUIT_POSITION_JITTER[amount]

        for (relative_x, relative_y), style, visible_hull in zip(
            relative_positions, styles, visible_hulls
        ):
            base_x = CARD_WIDTH * relative_x + formation_x
            base_y = CARD_HEIGHT * relative_y + formation_y

            for _ in range(FRUIT_PLACEMENT_ATTEMPTS):
                center_x = base_x + random.uniform(-max_x_jitter, max_x_jitter)
                center_y = base_y + random.uniform(-max_y_jitter, max_y_jitter)
                candidate = FruitCreationPlacement(
                    relative_x=center_x / CARD_WIDTH,
                    relative_y=center_y / CARD_HEIGHT,
                    style=style,
                )
                candidate_position = candidate.to_image_bounds(visible_hull)

                if image_position_is_valid(candidate_position, image_positions):
                    placements.append(candidate)
                    image_positions.append(candidate_position)
                    break
            else:
                break

        if len(placements) == len(relative_positions):
            return placements

    # Random variation is optional; retain a predictable base formation if an
    # unusually constrained randomized layout exhausts its attempts.
    return create_standard_fruit_placements(relative_positions, styles)


def augment_svg_colors(svg: str, style: FruitStyle) -> str:
    """Apply a small hue, saturation, and lightness shift to SVG hex colors.

    Args:
        svg (str): Selected source fruit SVG.
        style (FruitStyle): Color changes chosen for this fruit instance.

    Returns:
        str: SVG with its literal hex colors adjusted.
    """

    def replace_color(match: re.Match) -> str:
        """Adjust one literal SVG hex color while preserving its format.

        Args:
            match (re.Match): Hex color matched in the SVG source.

        Returns:
            str: Shifted color written as a six-digit hex value.
        """
        hex_color = match.group(1)
        if len(hex_color) == 3:
            # Normalize shorthand (#abc) before converting it through HLS.
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


def create_fruit_element(fruit_svg: str, placement: FruitCreationPlacement) -> str:
    """Build the SVG image element for one transformed and recolored fruit.

    Args:
        fruit_svg (str): Source SVG variation selected for this fruit.
        placement (FruitCreationPlacement): Position and visual style to apply.

    Returns:
        str: Embedded SVG image element for the card foreground.
    """

    styled_svg = augment_svg_colors(fruit_svg, placement.style)
    # Embed the asset so the intermediate SVG remains portable to CairoSVG and
    # never needs to expose a resource path to a client.
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
    """Build the transparent SVG foreground containing the border and fruits.

    Args:
        fruit_elements (list[str]): Renderable image elements for this card.

    Returns:
        str: Complete intermediate card SVG without its background.
    """

    # The background is intentionally omitted here: it is added as raster data
    # later, allowing the SVG foreground to stay transparent at rounded corners.
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" '
        f'height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}">'
        f'<rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" '
        f'rx="{CARD_CORNER_RADIUS}" fill="none" stroke="#1f2937" stroke-width="4" />'
        f'{"".join(fruit_elements)}'
        "</svg>"
    )


def render_svg_foreground(card_svg: str) -> Image.Image:
    """Rasterize a card SVG into a transparent RGBA foreground image.

    Args:
        card_svg (str): Intermediate SVG containing border and fruit icons.

    Returns:
        Image.Image: Transparent foreground for the final PNG.
    """

    png = cairosvg.svg2png(bytestring=card_svg.encode("utf-8"))
    return Image.open(BytesIO(png)).convert("RGBA")


def create_noisy_background() -> Image.Image:
    """Create a subtly tinted, lightly noisy background clipped to the card.

    Returns:
        Image.Image: RGBA background with transparent rounded corners.
    """

    # Per-channel base variation avoids every card sharing identical flat white.
    base_color = tuple(random.randint(*BACKGROUND_COLOR_RANGE) for _ in range(3))
    background = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), base_color)
    noise = Image.effect_noise(
        (CARD_WIDTH, CARD_HEIGHT), BACKGROUND_NOISE_STANDARD_DEVIATION
    ).convert("RGB")
    # Noise is centered around 128, so the negative offset preserves the chosen
    # base color while adding only a low-strength texture.
    background = ImageChops.add(background, noise, offset=-128).convert("RGBA")

    # Mask the background as well as the SVG border so corners stay transparent.
    card_mask = Image.new("L", (CARD_WIDTH, CARD_HEIGHT), 0)
    ImageDraw.Draw(card_mask).rounded_rectangle(
        (0, 0, CARD_WIDTH - 1, CARD_HEIGHT - 1),
        radius=CARD_CORNER_RADIUS,
        fill=255,
    )
    background.putalpha(card_mask)
    return background


def compose_card(background: Image.Image, foreground: Image.Image) -> bytes:
    """Layer the fruit foreground over the generated background and encode PNG.

    Args:
        background (Image.Image): Tinted card background.
        foreground (Image.Image): Rasterized border and fruit icons.

    Returns:
        bytes: Complete flattened PNG for caching and later encryption.
    """

    card = Image.alpha_composite(background, foreground)
    output = BytesIO()
    card.save(output, format="PNG")
    return output.getvalue()


def create_card(fruit: str, amount: int) -> HalliGalliCard | None:
    """Create a PNG card containing ``amount`` of ``fruit``.

    Fruit SVGs are embedded in an intermediate SVG and then turned into a png.

    Args:
        fruit (str): Fruit type to draw on the card.
        amount (int): Number of fruit icons to draw.

    Returns:
        HalliGalliCard | None: Completed PNG and server-side hit boxes, or None
            when the requested fruit/count is unsupported.
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
    # 5. Retain the final painted bounds server-side so click validation can use
    #    the rendered target location without sending its coordinates to clients.
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

    fruit_svgs = [load_random_fruit_svg(fruit) for _ in FRUIT_POSITIONS[amount]]
    visible_hulls = [get_visible_svg_hull(fruit_svg) for fruit_svg in fruit_svgs]
    placements = create_fruit_placements(FRUIT_POSITIONS[amount], amount, visible_hulls)
    fruit_elements = []
    fruit_positions = []
    for fruit_svg, visible_hull, placement in zip(
        fruit_svgs, visible_hulls, placements
    ):
        fruit_elements.append(create_fruit_element(fruit_svg, placement))
        fruit_positions.append(placement.to_image_position(visible_hull))

    foreground = render_svg_foreground(build_card_svg(fruit_elements))
    return HalliGalliCard(
        image=compose_card(create_noisy_background(), foreground),
        fruit=fruit,
        amount=amount,
        fruit_positions=fruit_positions,
    )


def pick_random_card() -> tuple[str, int]:
    """Pick one random valid Halli Galli card.

    A fruit and supported count are selected independently.

    Returns:
        tuple[str, int]: The fruit type and amount of fruit on the card.
    """
    random_fruit = random.choice(AVAILABLE_FRUITS)
    random_amount = random.choice(tuple(FRUIT_POSITIONS))

    return random_fruit, random_amount

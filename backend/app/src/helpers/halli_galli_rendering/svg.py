"""SVG color variation, composition, rasterization and the rounded card mask."""

import base64
import colorsys
import re
from functools import lru_cache
from io import BytesIO

import cairosvg
from PIL import Image

from .assets import (
    HEX_COLOR_PATTERN,
)
from ..halli_galli_card import (
    CARD_CORNER_RADIUS,
    CARD_HEIGHT,
    CARD_WIDTH,
    FRUIT_SIZE,
)
from .layout import (
    clamp,
)
from .models import (
    FruitCreationPlacement,
    FruitStyle,
)


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
        if saturation >= 0.35 and lightness >= 0.65:
            # Only bright, colored fills need darkening against the light paper.
            # Compress their lightness toward 0.62 by retaining 35% of the excess;
            # this preserves shade variation without washing out the artwork.
            lightness = 0.62 + (lightness - 0.62) * 0.35
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
    """Build the transparent SVG foreground containing the fruits.

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
        f'{"".join(fruit_elements)}'
        "</svg>"
    )


def render_svg_foreground(card_svg: str) -> Image.Image:
    """Rasterize a card SVG into a transparent RGBA foreground image.

    Args:
        card_svg (str): Intermediate SVG containing fruit icons.

    Returns:
        Image.Image: Transparent foreground for the final PNG.
    """

    png = cairosvg.svg2png(bytestring=card_svg.encode("utf-8"))
    return Image.open(BytesIO(png)).convert("RGBA")


@lru_cache(maxsize=1)
def get_card_mask() -> Image.Image:
    """Rasterize the card's outer curve once for both background and final PNG."""
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" '
        f'height="{CARD_HEIGHT}">'
        f'<rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" '
        f'rx="{CARD_CORNER_RADIUS}" fill="white" />'
        "</svg>"
    )
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"))
    return Image.open(BytesIO(png)).convert("RGBA").getchannel("A")

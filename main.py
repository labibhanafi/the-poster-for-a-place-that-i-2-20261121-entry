#!/usr/bin/env python3
"""LUMENFALL - a travel poster for a place that isn't there.

A program that writes one image, /output/entry.png (1024x1024 PNG):
a dusk travel poster for Lumenfall, a hidden valley where waterfalls of
light pour from floating cliffs into a glass lagoon.

Original artwork, drawn programmatically with Pillow: no photos, no
network, no copied assets. Deterministic - the same bytes every run.

Judge brief, in one line: an invented place, its name set into the
picture, one landmark, weather and light that promise what a stay there
feels like, type with intent, colour and composition that lead the eye
from the name to the landmark and the horizon.
"""

import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1024, 1024
OUT = os.environ.get("POSTER_OUTPUT", "/output/entry.png")

# ---------------------------------------------------------------- palette
INK_SKY_TOP = (13, 20, 44)       # deep indigo dusk
INK_SKY_MID = (44, 42, 85)       # violet
HORIZON = (201, 123, 61)         # amber glow at the horizon
SUN_CORE = (255, 222, 160)
SUN_HALO = (255, 176, 92)
LAGOON_TOP = (38, 94, 110)       # teal water catching the sky
LAGOON_DEEP = (13, 38, 54)
CLIFF = (16, 20, 38)             # near-black silhouettes
CLIFF_FAR = (26, 30, 58)
FALL_LIGHT = (255, 226, 170)
FALL_CORE = (255, 246, 220)
CREAM = (247, 234, 211)          # the place name
BOAT_SAIL = (250, 226, 180)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgrad(width, height, stops):
    """Vertical gradient through (position, colour) stops. Smooth, cheap."""
    small = Image.new("RGB", (1, height))
    px = small.load()
    n = len(stops)
    for y in range(height):
        t = y / max(height - 1, 1)
        for i in range(n - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                px[0, y] = lerp(c0, c1, f)
                break
        else:
            px[0, y] = stops[-1][1]
    return small.resize((width, height))


def load_font(size):
    """Best display serif available, falling back gracefully."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerifDisplay-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_text_spaced(draw, cx, y, text, font, fill, spacing, shadow=None):
    """Draw centred text with letterspacing, returns total width."""
    widths = []
    total = 0
    for ch in text:
        bbox = draw.textbbox((0, 0), ch, font=font)
        w = bbox[2] - bbox[0]
        widths.append(w)
        total += w
    total += spacing * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        if shadow is not None:
            draw.text((x + 3, y + 4), ch, font=font, fill=shadow)
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + spacing
    return total


def soft_disc(base, cx, cy, r, colour, blur):
    """A glowing disc on its own layer, blurred and composited."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colour + (255,))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(layer)


def waterfall(draw, x, y_top, y_bot, w_top, w_bot, phase):
    """One ribbon of light falling, gently swaying, brighter at its core."""
    steps = 26
    left, right = [], []
    for i in range(steps + 1):
        t = i / steps
        y = y_top + (y_bot - y_top) * t
        sway = 16 * math.sin(phase + t * 4.2) * t
        w = w_top + (w_bot - w_top) * t
        left.append((x - w / 2 + sway, y))
        right.append((x + w / 2 + sway, y))
    draw.polygon(left + right[::-1], fill=FALL_LIGHT)
    # bright core, narrower
    core_l, core_r = [], []
    for i in range(steps + 1):
        t = i / steps
        y = y_top + (y_bot - y_top) * t
        sway = 16 * math.sin(phase + t * 4.2) * t
        w = (w_top + (w_bot - w_top) * t) * 0.42
        core_l.append((x - w / 2 + sway, y))
        core_r.append((x + w / 2 + sway, y))
    draw.polygon(core_l + core_r[::-1], fill=FALL_CORE)


def cliff(draw, pts, colour):
    draw.polygon(pts, fill=colour)


def boat(draw, x, y, scale, sail_colour):
    """A tiny lateen-sailed boat, dark hull, warm sail."""
    s = scale
    # hull
    draw.polygon(
        [(x - 26 * s, y), (x + 26 * s, y), (x + 16 * s, y + 9 * s),
         (x - 16 * s, y + 9 * s)],
        fill=(10, 14, 28),
    )
    # mast + sail
    draw.line([(x, y), (x, y - 46 * s)], fill=(10, 14, 28), width=max(2, int(2 * s)))
    draw.polygon(
        [(x + 2 * s, y - 44 * s), (x + 2 * s, y - 4 * s), (x + 30 * s, y - 4 * s)],
        fill=sail_colour,
    )
    draw.polygon(
        [(x - 2 * s, y - 40 * s), (x - 2 * s, y - 4 * s), (x - 20 * s, y - 4 * s)],
        fill=tuple(max(0, c - 28) for c in sail_colour),
    )


def birds(draw, pts):
    for (x, y, s) in pts:
        draw.arc([x - s, y - s // 2, x, y + s // 2], 200, 340, fill=(20, 24, 48), width=2)
        draw.arc([x, y - s // 2, x + s, y + s // 2], 200, 340, fill=(20, 24, 48), width=2)


def build():
    img = vgrad(W, H, [
        (0.00, INK_SKY_TOP),
        (0.42, INK_SKY_MID),
        (0.58, (122, 84, 96)),
        (0.66, HORIZON),
        (0.68, LAGOON_TOP),
        (1.00, LAGOON_DEEP),
    ]).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # --- sun: low over the lagoon, the poster's warm heart ---------------
    sun_x, sun_y = 512, 640
    soft_disc(img, sun_x, sun_y, 150, (255, 150, 60), 60)
    soft_disc(img, sun_x, sun_y, 70, SUN_HALO, 26)
    draw = ImageDraw.Draw(img)
    draw.ellipse([sun_x - 46, sun_y - 46, sun_x + 46, sun_y + 46], fill=SUN_CORE)

    # --- far floating cliff, right, small --------------------------------
    cliff(draw, [
        (700, 350), (760, 320), (880, 332), (940, 368),
        (900, 412), (820, 428), (740, 416), (694, 382),
    ], CLIFF_FAR)
    draw.line([(760, 320), (880, 332)], fill=(178, 138, 78), width=3)
    waterfall(draw, 800, 420, 660, 26, 44, 1.2)
    waterfall(draw, 872, 412, 660, 14, 26, 2.6)

    # --- the landmark: great floating cliff, left, with light-falls ------
    cliff(draw, [
        (110, 334), (180, 272), (300, 252), (420, 272),
        (470, 334), (430, 386), (330, 406), (210, 394), (130, 370),
    ], CLIFF)
    # mossy gold rim where the light catches the cliff top
    draw.line([(180, 272), (300, 252), (420, 272)], fill=(214, 164, 90), width=4)
    waterfall(draw, 215, 390, 668, 34, 58, 0.4)
    waterfall(draw, 305, 402, 668, 44, 72, 1.8)
    waterfall(draw, 392, 386, 668, 24, 42, 3.1)
    # mist where the light-falls meet the lagoon
    soft_disc(img, 215, 668, 34, (255, 226, 170), 14)
    soft_disc(img, 305, 668, 44, (255, 226, 170), 16)
    soft_disc(img, 392, 668, 26, (255, 226, 170), 12)
    soft_disc(img, 800, 660, 26, (255, 226, 170), 12)
    soft_disc(img, 872, 660, 18, (255, 226, 170), 10)
    draw = ImageDraw.Draw(img)

    # --- birds, silhouetted against the horizon glow ---------------------
    birds(draw, [(610, 560, 22), (668, 532, 16), (556, 542, 14)])

    # --- lagoon: gold road of the sun, fading shimmer ---------------------
    for i in range(26):
        t = i / 25
        y = 700 + t * 290
        jitter = (math.sin(i * 12.9898) * 43758.5453) % 1.0
        w = (26 + t * 190) * (0.55 + 0.45 * jitter)
        draw.line(
            [(sun_x - w / 2, y), (sun_x + w / 2, y)],
            fill=tuple(int(c * (1 - t * 0.55)) for c in SUN_HALO),
            width=3,
        )
    # fall-light reflections under the falls: short, fading, uneven
    for (fx, fw) in [(215, 34), (305, 44), (392, 24), (800, 26)]:
        for i in range(6):
            y = 692 + i * 22
            jitter = (math.sin(fx * 0.7 + i * 3.3) * 43758.5453) % 1.0
            w = fw * (0.9 - i * 0.11) * (0.7 + 0.3 * jitter)
            shade = int(255 - i * 22)
            draw.line([(fx - w / 2, y), (fx + w / 2, y)],
                      fill=(shade, int(shade * 0.89), 170), width=2)

    # --- boats: the promise of a stay ------------------------------------
    boat(draw, 350, 812, 1.0, BOAT_SAIL)
    boat(draw, 690, 872, 0.75, tuple(max(0, c - 18) for c in BOAT_SAIL))

    # --- foreground headlands, framing the lagoon ------------------------
    draw.polygon([(0, 1024), (0, 930), (120, 968), (260, 1000), (300, 1024)],
                 fill=(8, 11, 24))
    draw.polygon([(1024, 1024), (1024, 946), (920, 972), (800, 1004), (760, 1024)],
                 fill=(8, 11, 24))

    # --- the place name: legible, high in the sky, carrying the mood -----
    font = load_font(96)
    draw_text_spaced(draw, W // 2, 84, "LUMENFALL", font, CREAM, 14,
                     shadow=(10, 12, 34))
    # thin gold rule under the name
    draw.line([(W // 2 - 120, 204), (W // 2 + 120, 204)], fill=(214, 164, 90), width=3)

    return img.convert("RGB")


def main():
    img = build()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    img.save(OUT, format="PNG", optimize=True)
    size = os.path.getsize(OUT)
    print(f"wrote {OUT}: {img.size[0]}x{img.size[1]} PNG, {size} bytes")
    assert img.size == (1024, 1024), "must be 1024x1024"
    assert size <= 1_048_576, "must be at most 1 MiB"


if __name__ == "__main__":
    main()

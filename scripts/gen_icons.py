"""One-off generator for the Atlas app icon set.

Not part of the fetch -> dedupe -> panelize -> render pipeline (icons are
static, regenerate manually if the design changes). Draws the icon
programmatically (rounded-square dark frame, porthole bezel, blue globe with
green continents + cloud highlights) at high resolution, then downsamples to
each required output size. Writes directly into docs/, which the refresh
workflow does not touch (it only `git add`s docs/index.html + data/seen.json).
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"

MASTER = 1024

# Palette matched to the site's dark theme (see PAGE_TEMPLATE in render.py).
TILE_BG = (21, 23, 28, 255)          # close to #15171c
TILE_BORDER = (0, 0, 0, 255)
TILE_INNER_STROKE = (44, 44, 44, 255)  # #2c2c2c, matches .tag-pill border
BEZEL = (11, 13, 16, 255)            # near-black porthole ring, #0b0d10
GLOBE_BASE = (28, 95, 160, 255)      # #1c5fa0
GLOBE_HIGHLIGHT = (58, 143, 209, 70)  # #3a8fd1 @ ~27% alpha
GLOBE_SHADOW = (13, 58, 99, 65)      # #0d3a63 @ ~25% alpha
LAND_DARK = (61, 127, 68, 255)       # #3d7f44
LAND_LIGHT = (74, 157, 82, 255)      # #4a9d52
CLOUD = (245, 245, 245, 225)


def rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def circle_mask(size: int, cx: int, cy: int, r: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    return mask


def build_master() -> Image.Image:
    S = MASTER
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # --- outer tile: rounded square, dark frame ---
    tile_radius = int(S * 0.22)
    tile = Image.new("RGBA", (S, S), TILE_BG)
    border_w = int(S * 0.018)
    d = ImageDraw.Draw(tile)
    d.rounded_rectangle(
        [border_w // 2, border_w // 2, S - 1 - border_w // 2, S - 1 - border_w // 2],
        radius=tile_radius, outline=TILE_BORDER, width=border_w,
    )
    inset = int(S * 0.045)
    d.rounded_rectangle(
        [inset, inset, S - 1 - inset, S - 1 - inset],
        radius=int(tile_radius * 0.85), outline=TILE_INNER_STROKE, width=max(2, int(S * 0.006)),
    )
    tile.putalpha(rounded_mask(S, tile_radius))
    img = Image.alpha_composite(img, tile)

    cx, cy = S // 2, S // 2

    # --- porthole bezel ---
    bezel_r = int(S * 0.40)
    bezel_layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(bezel_layer).ellipse(
        [cx - bezel_r, cy - bezel_r, cx + bezel_r, cy + bezel_r], fill=BEZEL
    )
    img = Image.alpha_composite(img, bezel_layer)

    # --- globe base ---
    globe_r = int(S * 0.345)
    globe_mask = circle_mask(S, cx, cy, globe_r)
    globe = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(globe).ellipse(
        [cx - globe_r, cy - globe_r, cx + globe_r, cy + globe_r], fill=GLOBE_BASE
    )

    # continents - irregular hand-placed polygons, clipped to the globe circle
    def poly(points, color):
        ImageDraw.Draw(globe).polygon(points, fill=color)

    def pt(fx, fy):
        return (cx + int(fx * globe_r), cy + int(fy * globe_r))

    # large upper-left landmass (organic blob, smoothed silhouette via many points)
    poly([
        pt(-0.85, -0.42), pt(-0.72, -0.66), pt(-0.48, -0.78), pt(-0.22, -0.72),
        pt(-0.08, -0.55), pt(-0.14, -0.38), pt(-0.06, -0.22), pt(-0.22, -0.08),
        pt(-0.42, -0.02), pt(-0.62, -0.08), pt(-0.78, -0.20), pt(-0.88, -0.30),
    ], LAND_LIGHT)
    poly([
        pt(-0.66, -0.58), pt(-0.46, -0.68), pt(-0.26, -0.60), pt(-0.24, -0.44),
        pt(-0.36, -0.30), pt(-0.55, -0.28), pt(-0.66, -0.42),
    ], LAND_DARK)

    # lower-right cluster
    poly([
        pt(0.14, 0.20), pt(0.30, 0.02), pt(0.54, -0.06), pt(0.76, 0.06),
        pt(0.86, 0.28), pt(0.82, 0.52), pt(0.66, 0.70), pt(0.42, 0.76),
        pt(0.22, 0.62), pt(0.10, 0.42),
    ], LAND_LIGHT)
    poly([
        pt(0.32, 0.20), pt(0.50, 0.10), pt(0.66, 0.24), pt(0.68, 0.44),
        pt(0.52, 0.58), pt(0.34, 0.50), pt(0.26, 0.34),
    ], LAND_DARK)

    # small islands - soft irregular blobs, not hard diamonds
    def island(fx, fy, r, color):
        ex, ey = pt(fx, fy)
        rr = int(r * globe_r)
        ImageDraw.Draw(globe).ellipse([ex - rr, ey - int(rr * 0.7), ex + int(rr * 1.3), ey + int(rr * 0.85)], fill=color)

    island(-0.48, 0.52, 0.10, LAND_LIGHT)
    island(0.62, -0.42, 0.08, LAND_LIGHT)
    island(0.00, 0.80, 0.065, LAND_DARK)
    island(-0.30, 0.68, 0.05, LAND_DARK)

    globe.putalpha(Image.composite(globe.split()[3], Image.new("L", (S, S), 0), globe_mask))

    # sphere shading: highlight top-left, shadow bottom-right, clipped to globe
    shade = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    hi_r = int(globe_r * 1.05)
    sd.ellipse([cx - hi_r - int(globe_r * 0.55), cy - hi_r - int(globe_r * 0.55),
                cx + hi_r - int(globe_r * 0.55), cy + hi_r - int(globe_r * 0.55)],
               fill=GLOBE_HIGHLIGHT)
    sh_r = int(globe_r * 1.05)
    sd.ellipse([cx - sh_r + int(globe_r * 0.55), cy - sh_r + int(globe_r * 0.55),
                cx + sh_r + int(globe_r * 0.55), cy + sh_r + int(globe_r * 0.55)],
               fill=GLOBE_SHADOW)
    shade = shade.filter(ImageFilter.GaussianBlur(globe_r * 0.18))
    shade.putalpha(Image.composite(shade.split()[3], Image.new("L", (S, S), 0), globe_mask))
    globe = Image.alpha_composite(globe, shade)

    img = Image.alpha_composite(img, globe)

    # --- cloud / ice highlights near top ---
    clouds = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cd = ImageDraw.Draw(clouds)
    for fx, fy, frx, fry in [(-0.15, -0.62, 0.16, 0.06), (0.22, -0.70, 0.11, 0.045),
                              (0.02, -0.50, 0.09, 0.035)]:
        ex, ey = pt(fx, fy)
        rx, ry = int(frx * globe_r), int(fry * globe_r)
        cd.ellipse([ex - rx, ey - ry, ex + rx, ey + ry], fill=CLOUD)
    clouds = clouds.filter(ImageFilter.GaussianBlur(S * 0.004))
    clouds.putalpha(Image.composite(clouds.split()[3], Image.new("L", (S, S), 0), globe_mask))
    img = Image.alpha_composite(img, clouds)

    return img


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    master = build_master()

    apple = master.resize((180, 180), Image.LANCZOS)
    apple.save(DOCS_DIR / "apple-touch-icon.png")

    i192 = master.resize((192, 192), Image.LANCZOS)
    i192.save(DOCS_DIR / "icon-192.png")

    i512 = master.resize((512, 512), Image.LANCZOS)
    i512.save(DOCS_DIR / "icon-512.png")

    master.save(
        DOCS_DIR / "favicon.ico",
        sizes=[(16, 16), (32, 32), (48, 48)],
    )

    print("Wrote favicon.ico, apple-touch-icon.png, icon-192.png, icon-512.png to", DOCS_DIR)


if __name__ == "__main__":
    main()

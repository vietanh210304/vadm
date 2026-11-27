"""Builds every app, extension, docs and website icon size from art/VADM.png.

Writes crates/app/assets/icons/app/vadm-<size>.png, vadm.ico (all sizes),
extension/icons/icon-<size>.png, docs/images/logo.png, and website icons.
Run from the repository root: python -I tools/icon/build_icon.py
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "art" / "VADM.png"
APP = ROOT / "crates" / "app" / "assets" / "icons" / "app"
EXT = ROOT / "extension" / "icons"
DOCS = ROOT / "docs" / "images"
WEB = ROOT / "website"
SIZES = [16, 20, 24, 32, 48, 64, 128, 256]


def main() -> None:
    src = Image.open(SRC).convert("RGBA")
    bbox = src.split()[3].point(lambda v: 255 if v > 16 else 0).getbbox()
    c = src.crop(bbox)
    w, h = c.size
    side = int(max(w, h) * 1.04)
    base = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    base.paste(c, ((side - w) // 2, (side - h) // 2), c)

    icons = {}
    for size in SIZES:
        icons[size] = base.resize((size, size), Image.LANCZOS)
        icons[size].save(APP / f"vadm-{size}.png")

    icons[256].save(
        APP / "vadm.ico",
        sizes=[(s, s) for s in SIZES],
        append_images=[icons[s] for s in SIZES if s != 256],
    )

    for size in (16, 32, 48, 128):
        icons[size].save(EXT / f"icon-{size}.png")

    if DOCS.is_dir():
        base.resize((320, 320), Image.LANCZOS).save(DOCS / "logo.png")

    if (WEB / "assets").is_dir():
        icons[32].save(WEB / "assets" / "favicon-32.png")
        icons[64].save(WEB / "assets" / "logo-64.png")
        icons[256].save(WEB / "assets" / "apple-touch-icon.png")
        icons[256].save(WEB / "assets" / "logo-256.webp", format="WEBP", lossless=True)
        base.resize((640, 640), Image.LANCZOS).save(WEB / "assets" / "logo-640.png")
        icons[64].save(
            WEB / "favicon.ico",
            sizes=[(16, 16), (32, 32), (48, 48), (64, 64)],
            append_images=[icons[16], icons[32], icons[48]],
        )

    print("wrote", ", ".join(str(s) for s in SIZES), "+ vadm.ico + extension/docs/website icons")


if __name__ == "__main__":
    main()

"""用本机中文字体生成图集，网页端不依赖系统字体。"""

import json
import pathlib

import pygame

ROOT = pathlib.Path(__file__).resolve().parent
OUT_DIR = ROOT / "assets"
SIZE = 32
ATLAS_W = 768


def collect_chars():
    chars = set(" 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    chars.update(".,/:()%+-<>[]{}!?~@#_='\"\\|")
    chars.update("，。！？、：；（）【】《》「」—…·×♥←→↑↓")
    for p in ROOT.glob("*.py"):
        if p.name == "bake_glyphs.py":
            continue
        text = p.read_text(encoding="utf-8")
        chars.update(ch for ch in text if ord(ch) > 127)
    return "".join(sorted(chars))


def sys_font(size):
    pygame.font.init()
    # Windows names first, then the CJK fonts available on Linux CI.
    for name in (
        "microsoftyahei",
        "msyh",
        "simhei",
        "simsun",
        "wenquanyimicrohei",
        "notosanscjksc",
        "droidsansfallback",
    ):
        path = pygame.font.match_font(name)
        if path:
            print("glyph font", name, path)
            return pygame.font.Font(path, size)
    raise SystemExit(
        "bake_glyphs: no CJK font found "
        "(expected Microsoft YaHei/SimHei, WenQuanYi Micro Hei, or Noto Sans CJK)"
    )


def main():
    pygame.init()
    font = sys_font(SIZE)
    chars = collect_chars()
    glyphs = {}
    rendered = [(ch, font.render(ch, True, (255, 255, 255))) for ch in chars]
    row_h = SIZE + 8
    x = y = 1
    for _ch, img in rendered:
        w, h = img.get_size()
        if x + w + 1 >= ATLAS_W:
            x = 1
            y += row_h
        x += w + 1
    atlas_h = y + row_h + 8
    x = y = 1
    atlas = pygame.Surface((ATLAS_W, atlas_h), pygame.SRCALPHA)
    atlas.fill((0, 0, 0, 0))
    for ch, img in rendered:
        w, h = img.get_size()
        if x + w + 1 >= ATLAS_W:
            x = 1
            y += row_h
        atlas.blit(img, (x, y))
        glyphs[ch] = {"x": x, "y": y, "w": w, "h": h}
        x += w + 1
    OUT_DIR.mkdir(exist_ok=True)
    out_png = OUT_DIR / "glyphs.png"
    pygame.image.save(atlas, str(out_png))
    try:
        from PIL import Image

        img = Image.open(out_png).convert("RGBA")
        img.save(out_png, format="PNG", optimize=True, compress_level=9)
    except Exception:
        pass
    (OUT_DIR / "glyphs.json").write_text(
        json.dumps({"size": SIZE, "glyphs": glyphs}, ensure_ascii=False),
        encoding="utf-8",
    )
    print("baked", len(glyphs), "glyphs", "atlas", ATLAS_W, "x", atlas_h, "->", out_png.stat().st_size, "bytes")


if __name__ == "__main__":
    main()

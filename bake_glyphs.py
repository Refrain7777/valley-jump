"""用本机中文字体生成图集，网页端不依赖系统字体。"""

import json
import pathlib
import re

import pygame

ROOT = pathlib.Path(__file__).resolve().parent
OUT_DIR = ROOT / "assets"
SIZE = 32


def collect_chars():
    chars = set(" 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    chars.update(".,/:()%+-<>[]{}!?~@#_='\"\\|")
    chars.update("，。！？、：；（）【】《》—…·♥←→↑↓")
    for p in ROOT.glob("*.py"):
        if p.name == "bake_glyphs.py":
            continue
        text = p.read_text(encoding="utf-8")
        chars.update(ch for ch in text if "\u4e00" <= ch <= "\u9fff")
    return "".join(sorted(chars))


def sys_font(size):
    pygame.font.init()
    for name in ("microsoftyahei", "msyh", "simhei", "simsun"):
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def main():
    pygame.init()
    font = sys_font(SIZE)
    chars = collect_chars()
    glyphs = {}
    x = y = 1
    row_h = SIZE + 8
    atlas_w = 1024
    atlas_h = 1024
    atlas = pygame.Surface((atlas_w, atlas_h), pygame.SRCALPHA)
    atlas.fill((0, 0, 0, 0))
    for ch in chars:
        img = font.render(ch, True, (255, 255, 255))
        w, h = img.get_size()
        if x + w + 1 >= atlas_w:
            x = 1
            y += row_h
        atlas.blit(img, (x, y))
        glyphs[ch] = {"x": x, "y": y, "w": w, "h": h}
        x += w + 1
    OUT_DIR.mkdir(exist_ok=True)
    pygame.image.save(atlas, str(OUT_DIR / "glyphs.png"))
    (OUT_DIR / "glyphs.json").write_text(
        json.dumps({"size": SIZE, "glyphs": glyphs}, ensure_ascii=False),
        encoding="utf-8",
    )
    print("baked", len(glyphs), "glyphs")


if __name__ == "__main__":
    main()

"""山谷跳跃入口。本机 python main.py；浏览器用 pygbag 打包。"""

import asyncio
import sys

import pygame

from display import hide_web_loader, set_web_progress, setup_web_page
from game import Game
from ui import SCREEN_H, SCREEN_W


def _draw_boot(screen, fonts, pct, msg):
    screen.fill((26, 20, 16))
    w, h = screen.get_size()
    # 简易木质进度条，字体未就绪时用矩形即可
    bar = pygame.Rect(w // 2 - 180, h // 2 + 20, 360, 22)
    pygame.draw.rect(screen, (74, 44, 22), bar, border_radius=11)
    fill = bar.copy()
    fill.width = max(8, int(bar.width * max(0.0, min(1.0, pct / 100.0))))
    pygame.draw.rect(screen, (240, 196, 64), fill, border_radius=11)
    pygame.draw.rect(screen, (255, 236, 198), bar, 2, border_radius=11)
    if fonts is not None:
        from ui import CREAM, GOLD, blit_text

        blit_text(screen, fonts.big, "山谷跳跃", GOLD, center=(w // 2, h // 2 - 50))
        blit_text(screen, fonts.small, msg, CREAM, center=(w // 2, h // 2 - 8))
        blit_text(screen, fonts.small, f"{int(pct)}%", CREAM, center=(w // 2, h // 2 + 56))
    pygame.display.flip()


async def main():
    set_web_progress(98, "初始化画面…")
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    pygame.display.set_caption("山谷跳跃")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    setup_web_page()
    if hasattr(pygame.key, "stop_text_input"):
        pygame.key.stop_text_input()

    fonts = None
    _draw_boot(screen, fonts, 30, "加载中…")
    set_web_progress(99, "加载字体…")
    await asyncio.sleep(0)

    from ui import Fonts

    fonts = Fonts()
    _draw_boot(screen, fonts, 55, "加载字体…")
    set_web_progress(99.2, "准备关卡…")
    await asyncio.sleep(0)

    # Game 内部音效延后生成，先尽快进可玩状态
    game = Game(screen, defer_audio=True, fonts=fonts)
    _draw_boot(screen, fonts, 78, "准备关卡…")
    set_web_progress(99.5, "生成音效…")
    await asyncio.sleep(0)

    game.audio.ensure_ready()
    game.audio.play_bgm()
    _draw_boot(screen, fonts, 100, "完成")
    set_web_progress(100, "完成")
    await asyncio.sleep(0)
    hide_web_loader()

    clock = pygame.time.Clock()
    while game.running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        game.handle_events()
        game.update(dt)
        game.draw()
        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())

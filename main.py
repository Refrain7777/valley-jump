"""山谷跳跃入口。本机 python main.py；浏览器用 pygbag 打包。"""

import asyncio
import pygame

from game import Game
from ui import SCREEN_H, SCREEN_W


async def main():
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    pygame.display.set_caption("山谷跳跃")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    if hasattr(pygame.key, "stop_text_input"):
        pygame.key.stop_text_input()
    game = Game(screen)
    clock = pygame.time.Clock()

    while game.running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        game.handle_events()
        game.update(dt)
        game.draw()
        pygame.display.flip()
        # pygbag 网页端必须让出控制权，否则画面会卡住
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())

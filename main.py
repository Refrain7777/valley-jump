"""山谷跳跃入口。本机 python main.py；浏览器用 pygbag 打包。"""

import asyncio
import sys

import pygame

from display import Viewport, setup_web_page
from game import Game
from ui import SCREEN_H, SCREEN_W


def current_win_size_safe(win):
    if sys.platform == "emscripten":
        try:
            from platform import window

            return max(320, int(window.innerWidth)), max(240, int(window.innerHeight))
        except Exception:
            pass
    return win.get_size()


def remap_event(event, vp, win):
    ww, wh = win.get_size()
    if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        if hasattr(event, "pos"):
            data = dict(event.dict)
            data["pos"] = vp.to_game(event.pos)
            return pygame.event.Event(event.type, data)
    if event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
        data = dict(event.dict)
        gx, gy = vp.to_game((event.x * ww, event.y * wh))
        data["x"] = gx / float(SCREEN_W)
        data["y"] = gy / float(SCREEN_H)
        return pygame.event.Event(event.type, data)
    return event


async def main():
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    pygame.display.set_caption("山谷跳跃")
    setup_web_page()
    if sys.platform == "emscripten":
        ww, wh = current_win_size_safe(None)
        window = pygame.display.set_mode((ww, wh))
    else:
        window = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
    if hasattr(pygame.key, "stop_text_input"):
        pygame.key.stop_text_input()

    game_surf = pygame.Surface((SCREEN_W, SCREEN_H))
    game = Game(game_surf)
    view = Viewport()
    clock = pygame.time.Clock()

    while game.running:
        ww, wh = current_win_size_safe(window)
        if window.get_size() != (ww, wh):
            window = pygame.display.set_mode((ww, wh), pygame.RESIZABLE)
        view.layout(ww, wh)

        dt = min(clock.tick(60) / 1000.0, 0.05)
        events = [remap_event(e, view, window) for e in pygame.event.get()]
        game.handle_events(events)
        game.update(dt)
        game.draw()
        view.present(window, game_surf)
        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())

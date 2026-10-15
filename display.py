"""把 960x540 画面适配到窗口：横屏等比留黑边，竖屏自动旋转成横屏玩法。"""

import sys

import pygame

from ui import SCREEN_H, SCREEN_W


def window_size():
    if sys.platform == "emscripten":
        try:
            from platform import window

            return max(320, int(window.innerWidth)), max(240, int(window.innerHeight))
        except Exception:
            pass
    return pygame.display.get_surface().get_size()


def setup_web_page():
    if sys.platform != "emscripten":
        return
    try:
        from platform import document

        style = document.createElement("style")
        style.textContent = (
            "html,body{margin:0;padding:0;width:100%;height:100%;overflow:hidden;"
            "background:#050608;touch-action:none;-webkit-user-select:none;user-select:none;}"
            "canvas,canvas.emscripten,#canvas,#pygame{width:100vw!important;height:100vh!important;"
            "object-fit:contain!important;display:block;}"
        )
        document.head.appendChild(style)
        document.body.style.margin = "0"
        document.body.style.overflow = "hidden"
    except Exception:
        pass


class Viewport:
    def __init__(self):
        self.offset = (0.0, 0.0)
        self.scale = 1.0
        self.portrait = False
        self.draw_size = (float(SCREEN_W), float(SCREEN_H))

    def layout(self, win_w, win_h):
        self.portrait = win_h > win_w + 8
        if self.portrait:
            self.scale = min(win_w / SCREEN_H, win_h / SCREEN_W)
            dw, dh = SCREEN_H * self.scale, SCREEN_W * self.scale
        else:
            self.scale = min(win_w / SCREEN_W, win_h / SCREEN_H)
            dw, dh = SCREEN_W * self.scale, SCREEN_H * self.scale
        self.draw_size = (dw, dh)
        self.offset = ((win_w - dw) / 2.0, (win_h - dh) / 2.0)

    def present(self, window, game_surf):
        window.fill((5, 6, 8))
        src = pygame.transform.rotate(game_surf, -90) if self.portrait else game_surf
        dw, dh = max(1, int(self.draw_size[0])), max(1, int(self.draw_size[1]))
        scaled = pygame.transform.smoothscale(src, (dw, dh))
        window.blit(scaled, (int(self.offset[0]), int(self.offset[1])))

    def to_game(self, pos):
        x, y = pos
        ox, oy = self.offset
        s = self.scale
        if s <= 0:
            return 0, 0
        lx = (x - ox) / s
        ly = (y - oy) / s
        if self.portrait:
            gx = SCREEN_W - ly
            gy = lx
        else:
            gx, gy = lx, ly
        gx = max(0, min(SCREEN_W - 1, gx))
        gy = max(0, min(SCREEN_H - 1, gy))
        return int(gx), int(gy)

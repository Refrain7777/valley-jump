"""木质 HUD、对话框、手机虚拟按键。"""

import json
import pathlib

import pygame

SCREEN_W = 960
SCREEN_H = 540

WOOD = (122, 78, 42)
WOOD_DARK = (74, 44, 22)
CREAM = (255, 236, 198)
GOLD = (240, 196, 64)
INK = (48, 32, 18)


def _asset_path(name):
    for base in (
        pathlib.Path(__file__).resolve().parent / "assets",
        pathlib.Path("assets"),
        pathlib.Path(".") / "assets",
    ):
        path = base / name
        try:
            if path.exists():
                return str(path)
        except Exception:
            continue
    return "assets/" + name


class AtlasFont:
    """网页/手机没有系统中文字体时，用打包进去的文字图集绘制。"""

    def __init__(self, atlas, glyphs, px):
        self.atlas = atlas
        self.glyphs = glyphs
        self.scale = px / 32.0

    def render(self, text, _aa, color):
        text = "" if text is None else str(text)
        if not text:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        parts = []
        width = 0
        height = 1
        for ch in text:
            g = self.glyphs.get(ch) or self.glyphs.get("?") or self.glyphs.get(" ")
            if not g:
                continue
            w = max(1, int(g["w"] * self.scale))
            h = max(1, int(g["h"] * self.scale))
            src = pygame.Rect(g["x"], g["y"], g["w"], g["h"])
            piece = pygame.Surface((g["w"], g["h"]), pygame.SRCALPHA)
            piece.blit(self.atlas, (0, 0), src)
            if (w, h) != (g["w"], g["h"]):
                piece = pygame.transform.scale(piece, (w, h))
            piece.fill(color[:3] + (255,), special_flags=pygame.BLEND_RGB_MULT)
            parts.append(piece)
            width += w
            height = max(height, h)
        surf = pygame.Surface((max(1, width), height), pygame.SRCALPHA)
        x = 0
        for piece in parts:
            surf.blit(piece, (x, height - piece.get_height()))
            x += piece.get_width()
        return surf


def load_font(size):
    try:
        atlas = pygame.image.load(_asset_path("glyphs.png"))
        if hasattr(atlas, "convert_alpha"):
            atlas = atlas.convert_alpha()
        data = json.loads(pathlib.Path(_asset_path("glyphs.json")).read_text(encoding="utf-8"))
        return AtlasFont(atlas, data["glyphs"], size)
    except Exception:
        candidates = (
            "microsoftyahei",
            "msyh",
            "simhei",
            "simsun",
            "notosanscjksc",
            "arialunicode",
        )
        for name in candidates:
            path = pygame.font.match_font(name)
            if path:
                return pygame.font.Font(path, size)
        return pygame.font.Font(None, size)


class Fonts:
    def __init__(self):
        self.small = load_font(18)
        self.mid = load_font(24)
        self.big = load_font(42)


def wood_panel(surf, rect, border=3):
    pygame.draw.rect(surf, WOOD, rect, border_radius=8)
    pygame.draw.rect(surf, WOOD_DARK, rect, border, border_radius=8)
    inner = rect.inflate(-10, -10)
    pygame.draw.rect(surf, (160, 112, 64), inner, 1, border_radius=4)


def blit_text(surf, font, text, color, center=None, topleft=None):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = center
    if topleft:
        rect.topleft = topleft
    surf.blit(img, rect)
    return rect


class TouchControls:
    """画在游戏画面里的方向键 / 跳跃，手机浏览器触摸可用。"""

    def __init__(self):
        self.left = False
        self.right = False
        self.jump = False
        self.jump_clicked = False
        self.shoot_clicked = False
        self.start_clicked = False
        self.mute_clicked = False
        self.shop_clicked = False
        self._held = {}  # finger_id / 'mouse' -> action

    def layout(self, screen_size):
        w, h = screen_size
        btn = 96
        gap = 16
        y = h - 16 - btn
        self.left_r = pygame.Rect(16, y, btn, btn)
        self.right_r = pygame.Rect(16 + btn + gap, y, btn, btn)
        self.jump_r = pygame.Rect(w - 16 - btn, y, btn, btn)
        self.shoot_r = pygame.Rect(w - 16 - btn, y - btn - 12, btn, btn)
        self.mute_r = pygame.Rect(w - 78, 12, 64, 36)
        self.shop_r = pygame.Rect(w - 150, 12, 64, 36)
        self.start_r = pygame.Rect(w // 2 - 110, h // 2 + 70, 220, 52)

    def _pos_from_event(self, event, screen_size):
        if event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            x, y = float(event.x), float(event.y)
            # pygbag 有时给 0~1，有时已经是像素
            if 0.0 <= x <= 1.5 and 0.0 <= y <= 1.5:
                return int(x * screen_size[0]), int(y * screen_size[1])
            return int(x), int(y)
        if hasattr(event, "pos"):
            return event.pos
        return None

    def _hit(self, pos, state):
        actions = []
        # 手机点按区域比绘制按钮略大，好点一些
        pad = 12
        if self.left_r.inflate(pad, pad).collidepoint(pos):
            actions.append("left")
        if self.right_r.inflate(pad, pad).collidepoint(pos):
            actions.append("right")
        if self.jump_r.inflate(pad, pad).collidepoint(pos):
            actions.append("jump")
            if state == "down":
                self.jump_clicked = True
        if self.shoot_r.inflate(pad, pad).collidepoint(pos):
            actions.append("shoot")
            if state == "down":
                self.shoot_clicked = True
        if self.mute_r.inflate(pad, pad).collidepoint(pos) and state == "down":
            self.mute_clicked = True
        if self.shop_r.inflate(pad, pad).collidepoint(pos) and state == "down":
            self.shop_clicked = True
        if self.start_r.inflate(pad, pad).collidepoint(pos) and state == "down":
            self.start_clicked = True
        return actions

    def ingest_web_pointers(self, pointers):
        """用浏览器换算后的指针更新按键，不依赖 pygame 触摸事件。"""
        live = set()
        for item in pointers:
            pid = f"js-{item['id']}"
            live.add(pid)
            pos = (int(item["x"]), int(item["y"]))
            state = "move" if pid in self._held else "down"
            self._held[pid] = self._hit(pos, state)
        for key in list(self._held):
            if str(key).startswith("js-") and key not in live:
                self._held.pop(key, None)
        self._refresh_held()

    def _refresh_held(self):
        self.left = self.right = self.jump = False
        for acts in self._held.values():
            if "left" in acts:
                self.left = True
            if "right" in acts:
                self.right = True
            if "jump" in acts:
                self.jump = True

    def begin_frame(self):
        self.jump_clicked = False
        self.shoot_clicked = False
        self.start_clicked = False
        self.mute_clicked = False
        self.shop_clicked = False

    def handle(self, event, screen_size):
        down_types = (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN)
        up_types = (pygame.MOUSEBUTTONUP, pygame.FINGERUP)
        move_types = (pygame.FINGERMOTION, pygame.MOUSEMOTION)

        if event.type not in down_types + up_types + move_types:
            return
        # 手机浏览器常把点击报成 button=0，不能只接受 1
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) not in (0, 1):
            return
        if event.type == pygame.MOUSEMOTION and not (event.buttons and event.buttons[0]):
            return

        pos = self._pos_from_event(event, screen_size)
        if pos is None:
            return

        key = getattr(event, "finger_id", getattr(event, "fingerId", "mouse"))
        if event.type in down_types:
            acts = self._hit(pos, "down")
            self._held[key] = acts
        elif event.type in up_types:
            self._held.pop(key, None)
        else:
            self._held[key] = self._hit(pos, "move")
        self._refresh_held()

    def draw(self, surf, fonts, show_start=False):
        def btn(rect, label, active):
            color = (90, 160, 80) if active else (48, 36, 28)
            s = pygame.Surface(rect.size, pygame.SRCALPHA)
            s.fill((0, 0, 0, 0))
            pygame.draw.rect(s, (*color, 170), s.get_rect(), border_radius=18)
            pygame.draw.rect(s, (255, 236, 198, 200), s.get_rect(), 3, border_radius=18)
            surf.blit(s, rect.topleft)
            blit_text(surf, fonts.mid, label, CREAM, center=rect.center)

        btn(self.left_r, "<", self.left)
        btn(self.right_r, ">", self.right)
        btn(self.jump_r, "跳", self.jump)
        btn(self.shoot_r, "攻", False)

        if show_start:
            wood_panel(surf, self.start_r)
            blit_text(surf, fonts.mid, "开始游戏", CREAM, center=self.start_r.center)


def draw_hud(surf, fonts, coins, hp, max_hp, muted, mute_rect, shop_rect, distance):
    wood_panel(surf, pygame.Rect(12, 10, 150, 48))
    blit_text(surf, fonts.small, f"金币  {coins}", CREAM, topleft=(22, 24))

    hp_box = pygame.Rect(170, 10, 220, 48)
    wood_panel(surf, hp_box)
    blit_text(surf, fonts.small, f"生命  {hp}/{max_hp}", CREAM, topleft=(182, 16))
    bar = pygame.Rect(182, 36, 190, 12)
    pygame.draw.rect(surf, WOOD_DARK, bar, border_radius=4)
    fill = bar.copy()
    fill.width = max(0, int(bar.width * (hp / max(1, max_hp))))
    pygame.draw.rect(surf, (200, 72, 64), fill, border_radius=4)

    wood_panel(surf, pygame.Rect(400, 10, 160, 48))
    blit_text(surf, fonts.small, f"路程  {distance}m", CREAM, topleft=(412, 24))

    wood_panel(surf, shop_rect)
    blit_text(surf, fonts.small, "商店", CREAM, center=shop_rect.center)
    wood_panel(surf, mute_rect)
    blit_text(surf, fonts.small, "静音" if not muted else "开音", CREAM, center=mute_rect.center)


def draw_title(surf, fonts):
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    overlay.fill((20, 16, 10, 90))
    surf.blit(overlay, (0, 0))
    box = pygame.Rect(230, 90, 500, 280)
    wood_panel(surf, box, 4)
    blit_text(surf, fonts.big, "山谷跳跃", GOLD, center=(SCREEN_W // 2, 150))
    blit_text(surf, fonts.small, "无限关卡，越跑越难", CREAM, center=(SCREEN_W // 2, 200))
    blit_text(surf, fonts.small, "电脑：WASD 移动跳跃，J 攻击，B 商店", CREAM, center=(SCREEN_W // 2, 232))
    blit_text(surf, fonts.small, "金币弹 100，踩踏 200；怪越往后越痛", CREAM, center=(SCREEN_W // 2, 258))
    blit_text(surf, fonts.small, "手机：左下方向，右下跳 / 攻", CREAM, center=(SCREEN_W // 2, 282))


def draw_pc_hints(surf, fonts, ime_on):
    """电脑模式常驻提示：WASD，以及中文输入时的英文切换提醒。"""
    bar = pygame.Rect(180, SCREEN_H - 52, 600, 36)
    wood_panel(surf, bar, 2)
    blit_text(
        surf,
        fonts.small,
        "电脑：WASD 移动  空格跳  J 攻击  B 商店",
        CREAM,
        center=bar.center,
    )
    if ime_on:
        warn = pygame.Rect(180, 64, 600, 40)
        pygame.draw.rect(surf, (160, 60, 40), warn, border_radius=8)
        pygame.draw.rect(surf, CREAM, warn, 2, border_radius=8)
        blit_text(
            surf,
            fonts.small,
            "检测到中文输入：请切到英文（Shift 或任务栏「中」→「英」）",
            CREAM,
            center=warn.center,
        )


SHOP_ITEMS = (
    ("jump", "1  弹跳强化", "跳得更高（最多6级）"),
    ("dmg", "2  锋刃强化", "金币弹与踩踏伤害提升"),
    ("hp", "3  体魄强化", "生命上限 +25，并补满差额"),
    ("heal", "4  草药恢复", "立刻恢复 40 点生命"),
)


def shop_item_rects():
    rects = []
    for i, (kind, _, _) in enumerate(SHOP_ITEMS):
        rects.append((kind, pygame.Rect(220, 145 + i * 58, 520, 52)))
    return rects


def draw_shop(surf, fonts, stats, coins, hp, max_hp):
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    overlay.fill((20, 16, 10, 150))
    surf.blit(overlay, (0, 0))
    box = pygame.Rect(190, 70, 580, 400)
    wood_panel(surf, box, 4)
    blit_text(surf, fonts.big, "旅途商店", GOLD, center=(SCREEN_W // 2, 108))
    blit_text(surf, fonts.small, f"金币 {coins}    生命 {hp}/{max_hp}    B/关闭", CREAM, center=(SCREEN_W // 2, 138))
    lv_map = {"jump": stats.jump_lv, "dmg": stats.dmg_lv, "hp": stats.hp_lv, "heal": "-"}
    for (kind, title, desc), (_, rect) in zip(SHOP_ITEMS, shop_item_rects()):
        wood_panel(surf, rect, 2)
        cost = stats.cost(kind)
        cost_txt = "已满级" if cost is None else f"{cost} 金币"
        lv = lv_map[kind]
        extra = f"  Lv{lv}" if kind != "heal" else ""
        blit_text(surf, fonts.small, title + extra, CREAM, topleft=(rect.x + 14, rect.y + 8))
        blit_text(surf, fonts.small, f"{desc}    {cost_txt}", GOLD, topleft=(rect.x + 14, rect.y + 28))


def draw_end(surf, fonts, title, subtitle):
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    overlay.fill((20, 16, 10, 120))
    surf.blit(overlay, (0, 0))
    box = pygame.Rect(250, 140, 460, 200)
    wood_panel(surf, box, 4)
    blit_text(surf, fonts.big, title, GOLD, center=(SCREEN_W // 2, 200))
    blit_text(surf, fonts.mid, subtitle, CREAM, center=(SCREEN_W // 2, 255))

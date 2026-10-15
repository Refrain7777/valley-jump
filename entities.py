"""玩家、史莱姆、金币、金币弹。"""

import pygame

from level import TILE


def _rect(x, y, w, h):
    return pygame.Rect(int(x), int(y), w, h)


class Player:
    def __init__(self, x, y, max_hp=100):
        self.spawn = (x, y)
        self.w, self.h = 22, 28
        self.x, self.y = float(x), float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.facing = 1
        self.invuln = 0.0
        self.flash = 0.0
        self.max_hp = max_hp
        self.hp = max_hp

    @property
    def rect(self):
        return _rect(self.x, self.y, self.w, self.h)

    def reset(self):
        self.x, self.y = self.spawn
        self.vx = self.vy = 0
        self.on_ground = True
        self.invuln = 1.0

    def take_hit(self, amount):
        if self.invuln > 0:
            return False
        self.hp -= amount
        self.invuln = 0.9
        if self.hp <= 0:
            self.hp = 0
            return True
        return False

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def draw(self, surf, cam):
        if self.invuln > 0 and int(self.flash * 12) % 2 == 0:
            return
        r = self.rect.move(-cam.x, -cam.y)
        hat = pygame.Rect(r.x + 2, r.y, 18, 6)
        pygame.draw.rect(surf, (212, 168, 75), hat)
        pygame.draw.rect(surf, (120, 80, 32), hat, 1)
        pygame.draw.rect(surf, (242, 208, 164), (r.x + 5, r.y + 6, 12, 8))
        pygame.draw.rect(surf, (70, 140, 88), (r.x + 3, r.y + 14, 16, 10))
        pygame.draw.rect(surf, (92, 58, 36), (r.x + 4, r.y + 24, 6, 5))
        pygame.draw.rect(surf, (92, 58, 36), (r.x + 12, r.y + 24, 6, 5))
        eye_x = r.x + (12 if self.facing > 0 else 6)
        pygame.draw.rect(surf, (40, 28, 20), (eye_x, r.y + 8, 2, 2))


class Slime:
    def __init__(self, x, y, hp=100):
        self.w, self.h = 24, 18
        self.x, self.y = float(x), float(y + TILE - 18)
        self.vx = 48.0
        self.max_hp = max(100, hp)
        self.hp = self.max_hp
        self.alive = True

    @property
    def rect(self):
        return _rect(self.x, self.y, self.w, self.h)

    @property
    def contact_damage(self):
        # 怪越肥撞人越痛：100 血约 20，300 血约 60
        return max(15, int(self.max_hp * 0.2))

    def hurt(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    def draw(self, surf, cam, t):
        if not self.alive:
            return
        r = self.rect.move(-cam.x, -cam.y)
        squash = 2 if int(t * 4) % 2 == 0 else 0
        body = pygame.Rect(r.x, r.y + squash, r.w, r.h - squash)
        # 血越厚颜色越深
        shade = max(40, 86 - (self.max_hp - 100) // 8)
        pygame.draw.ellipse(surf, (shade, 176, 92), body)
        pygame.draw.ellipse(surf, (36, 92, 48), body, 2)
        pygame.draw.rect(surf, (20, 40, 24), (r.x + 6, r.y + 6 + squash, 3, 3))
        pygame.draw.rect(surf, (20, 40, 24), (r.x + 15, r.y + 6 + squash, 3, 3))
        # 血条
        bw = r.w
        ratio = self.hp / self.max_hp
        pygame.draw.rect(surf, (40, 20, 20), (r.x, r.y - 6, bw, 4))
        pygame.draw.rect(surf, (220, 70, 60), (r.x, r.y - 6, int(bw * ratio), 4))


class Coin:
    def __init__(self, x, y):
        self.x, self.y = x + 8, y + 8
        self.w = self.h = 16
        self.taken = False

    @property
    def rect(self):
        return _rect(self.x, self.y, self.w, self.h)

    def draw(self, surf, cam, t):
        if self.taken:
            return
        r = self.rect.move(-cam.x, -cam.y)
        bounce = int(2 * (1 if int(t * 6) % 2 == 0 else -1))
        pygame.draw.ellipse(surf, (240, 196, 64), (r.x + 2, r.y + bounce, 12, 14))
        pygame.draw.ellipse(surf, (160, 110, 20), (r.x + 2, r.y + bounce, 12, 14), 1)


class Shot:
    """消耗 1 枚金币向前飞，伤害 100。"""

    DAMAGE = 100
    SPEED = 460

    def __init__(self, x, y, facing):
        self.x = float(x)
        self.y = float(y)
        self.facing = 1 if facing >= 0 else -1
        self.w = self.h = 12
        self.alive = True
        self.life = 1.1

    @property
    def rect(self):
        return _rect(self.x, self.y, self.w, self.h)

    def update(self, dt):
        self.x += self.facing * self.SPEED * dt
        self.life -= dt
        if self.life <= 0:
            self.alive = False

    def draw(self, surf, cam):
        if not self.alive:
            return
        r = self.rect.move(-cam.x, -cam.y)
        pygame.draw.ellipse(surf, (240, 196, 64), r)
        pygame.draw.ellipse(surf, (160, 110, 20), r, 1)

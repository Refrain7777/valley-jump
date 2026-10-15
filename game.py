"""关卡逻辑：无限生成、金币射击、碰撞。"""

import sys

import pygame

from audio import Audio
from display import poll_web_pointers, toggle_web_flip
from entities import Coin, Player, Shot, Slime
from ime import is_chinese_ime
from level import CHUNK_W, GROUND_ROW, PIT_Y, ROWS, SOLID, TILE, World
from stats import HEAL_AMOUNT, RunStats
from ui import (
    SCREEN_H,
    SCREEN_W,
    Fonts,
    TouchControls,
    draw_end,
    draw_help,
    draw_hud,
    draw_ime_warn,
    draw_pause,
    draw_shop,
    draw_title,
    shop_item_rects,
)

SKY_TOP = (126, 186, 214)
SKY_BOT = (196, 226, 168)
GRASS = (86, 150, 62)
DIRT = (140, 92, 52)
DIRT_DARK = (96, 62, 34)
WOOD_BOX = (176, 124, 70)
WOOD_EDGE = (96, 62, 30)

GRAVITY = 1050
MOVE_SPEED = 250


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.running = True
        self.state = "play"
        self.time = 0.0
        self.audio = Audio()
        self.touch = TouchControls()
        self.touch.layout(screen.get_size())
        self.fonts = Fonts()
        self.cam = pygame.Vector2(0, 0)
        self.world = World()
        self.coins_got = 0
        self.stats = RunStats()
        self.jump_held = False
        self.coyote = 0.0
        self.jump_buf = 0.0
        self.ime_blocked = False
        self.shots = []
        self.shoot_cd = 0.0
        self.best_distance = 0
        self.reset_world(full=True)
        self.audio.play_bgm()

    def reset_world(self, full=False):
        if full:
            self.coins_got = 0
            self.stats = RunStats()
            self.best_distance = 0
        self.world.reset()
        self.coins = []
        self.slimes = []
        self.shots = []
        self._absorb_spawns()
        self.player = Player(2 * TILE + 5, GROUND_ROW * TILE - 28, self.stats.max_hp())
        self.player.on_ground = True
        self.coyote = 0.1
        self.jump_buf = 0.0
        self.shoot_cd = 0.0

    def _absorb_spawns(self):
        for x, y in self.world.pending_coins:
            self.coins.append(Coin(x * TILE, y * TILE))
        self.world.pending_coins.clear()
        for x, y, hp in self.world.pending_slimes:
            self.slimes.append(Slime(x * TILE, y * TILE, hp))
        self.world.pending_slimes.clear()

    def solid_at(self, tx, ty):
        return self.world.solid_at(tx, ty)

    def tiles_for(self, rect):
        hits = []
        if rect.width <= 0 or rect.height <= 0:
            return hits
        x0 = rect.left // TILE
        x1 = (rect.right - 1) // TILE
        y0 = rect.top // TILE
        y1 = (rect.bottom - 1) // TILE
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if self.solid_at(tx, ty):
                    hits.append(pygame.Rect(tx * TILE, ty * TILE, TILE, TILE))
        return hits

    def move_actor(self, actor, dx, dy):
        actor.x += dx
        if actor.x < 8:
            actor.x = 8
        body = actor.rect
        for tile in self.tiles_for(body):
            if not body.colliderect(tile):
                continue
            if dx > 0:
                actor.x = tile.left - actor.w
            elif dx < 0:
                actor.x = tile.right
            body = actor.rect

        actor.y += dy
        body = actor.rect
        for tile in self.tiles_for(body):
            if not body.colliderect(tile):
                continue
            if dy > 0:
                actor.y = tile.top - actor.h
                actor.vy = 0
            elif dy < 0:
                actor.y = tile.bottom
                actor.vy = 0
            body = actor.rect

        feet = actor.rect.move(0, 1)
        actor.on_ground = any(feet.colliderect(t) for t in self.tiles_for(feet))

    def handle_events(self, events=None):
        self.touch.begin_frame()
        if events is None:
            events = pygame.event.get()
        if sys.platform == "emscripten":
            self.touch.ingest_web_pointers(poll_web_pointers())
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state in ("shop", "help", "pause"):
                        self._resume()
                    elif self.state == "play":
                        self._pause()
                    else:
                        self.running = False
                elif event.key == pygame.K_p:
                    self._toggle_pause()
                elif event.key == pygame.K_b:
                    self._toggle_shop()
                elif event.key == pygame.K_h:
                    self._toggle_help()
                elif event.key == pygame.K_m:
                    self.audio.toggle_mute()
                elif self.state == "shop" and event.key in (
                    pygame.K_1,
                    pygame.K_2,
                    pygame.K_3,
                    pygame.K_4,
                ):
                    kinds = {pygame.K_1: "jump", pygame.K_2: "dmg", pygame.K_3: "hp", pygame.K_4: "heal"}
                    self._buy(kinds[event.key])
                elif self.state == "pause" and event.key in (
                    pygame.K_SPACE,
                    pygame.K_RETURN,
                ):
                    self._resume()
                elif self.state in ("win", "lose", "title") and event.key in (
                    pygame.K_SPACE,
                    pygame.K_RETURN,
                ):
                    self._start_or_retry()
                elif event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    if self.state == "lose":
                        self._start_or_retry()
                    self.jump_buf = 0.12
                    self._try_jump()
                elif event.key in (pygame.K_j, pygame.K_k, pygame.K_f):
                    self._try_shoot()
            elif self.state == "shop" and event.type == pygame.MOUSEBUTTONDOWN:
                self._shop_click(event.pos)
            elif self.state == "help" and event.type == pygame.MOUSEBUTTONDOWN:
                self._resume()
            elif self.state == "pause" and event.type == pygame.MOUSEBUTTONDOWN:
                if self.touch.start_r.collidepoint(event.pos) or self.touch.pause_r.collidepoint(event.pos):
                    self._resume()
            self.touch.handle(event, self.screen.get_size())

        if self.touch.flip_clicked:
            toggle_web_flip()
            return
        if self.touch.mute_clicked:
            self.audio.toggle_mute()
            return
        if self.touch.pause_clicked:
            self._toggle_pause()
            return
        if self.touch.help_clicked:
            self._toggle_help()
            return
        if self.touch.shop_clicked:
            self._toggle_shop()
            return

        if self.state == "help":
            if self.touch.down_pos and not self.touch.help_r.collidepoint(self.touch.down_pos):
                self._resume()
            return
        if self.state == "shop":
            if self.touch.down_pos:
                self._shop_click(self.touch.down_pos)
            return
        if self.state == "pause":
            if self.touch.start_clicked or self.touch.jump_clicked:
                self._resume()
            return
        if self.state != "play":
            if self.touch.start_clicked or self.touch.jump_clicked:
                self._start_or_retry()
            return

        if self.touch.jump_clicked:
            self.jump_buf = 0.12
            self._try_jump()
        if self.touch.shoot_clicked:
            self._try_shoot()

    def _start_or_retry(self):
        self.reset_world(full=True)
        self._resume()

    def _clear_hold(self):
        self.touch._held.clear()
        self.touch.left = self.touch.right = self.touch.jump = False
        self.jump_held = False
        self.jump_buf = 0.0

    def _pause(self):
        if self.state != "play":
            return
        self._clear_hold()
        self.state = "pause"
        self.audio.pause_game()

    def _resume(self):
        self._clear_hold()
        self.state = "play"
        self.audio.resume_game()

    def _toggle_pause(self):
        if self.state == "play":
            self._pause()
        elif self.state == "pause":
            self._resume()

    def _try_jump(self):
        if self.state != "play":
            return
        if self.player.on_ground or self.coyote > 0:
            self.player.vy = self.stats.jump_speed()
            self.player.on_ground = False
            self.coyote = 0
            self.jump_buf = 0
            self.audio.play("jump")

    def _try_shoot(self):
        if self.state != "play" or self.shoot_cd > 0:
            return
        if self.coins_got <= 0:
            self.audio.play("empty")
            return
        self.coins_got -= 1
        self.shoot_cd = 0.22
        px = self.player.x + (self.player.w if self.player.facing > 0 else -12)
        py = self.player.y + 8
        self.shots.append(Shot(px, py, self.player.facing))
        self.audio.play("shoot")

    def _input_axis(self):
        keys = pygame.key.get_pressed()
        ax = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a] or self.touch.left:
            ax -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d] or self.touch.right:
            ax += 1
        jump_down = (
            keys[pygame.K_SPACE]
            or keys[pygame.K_w]
            or keys[pygame.K_UP]
            or self.touch.jump
        )
        return ax, jump_down

    def update(self, dt):
        self.time += dt
        self.player.flash += dt
        if self.player.invuln > 0:
            self.player.invuln -= dt
        self.shoot_cd = max(0.0, self.shoot_cd - dt)
        self.ime_blocked = is_chinese_ime()

        if self.state != "play":
            return

        self.world.ensure(int(self.player.x // TILE) + CHUNK_W * 2)
        self._absorb_spawns()

        ax, jump_down = self._input_axis()
        self.player.vx = ax * MOVE_SPEED
        if ax:
            self.player.facing = 1 if ax > 0 else -1

        if self.jump_held and not jump_down and self.player.vy < 0:
            self.player.vy *= 0.45
        self.jump_held = jump_down

        if not self.player.on_ground:
            self.player.vy = min(self.player.vy + GRAVITY * dt, 780)
            self.coyote = max(0.0, self.coyote - dt)
        else:
            self.coyote = 0.1
            if self.player.vy > 0:
                self.player.vy = 0
            self.player.spawn = (self.player.x, self.player.y)

        self.jump_buf = max(0.0, self.jump_buf - dt)
        if self.jump_buf > 0:
            self._try_jump()

        self.move_actor(self.player, self.player.vx * dt, self.player.vy * dt)

        if self.player.y > PIT_Y:
            self._hurt(int(self.stats.max_hp() * 0.35), pit=True)
            return

        self._update_slimes(dt)
        self._update_coins()
        self._update_shots(dt)
        self._prune_behind()

        dist = int(self.player.x // TILE)
        if dist > self.best_distance:
            self.best_distance = dist

        target_x = self.player.x + self.player.w / 2 - SCREEN_W / 2
        target_y = self.player.y + self.player.h / 2 - SCREEN_H / 2
        map_h = ROWS * TILE
        self.cam.x = max(0, target_x)
        self.cam.y = max(0, min(target_y, map_h - SCREEN_H))

    def _update_slimes(self, dt):
        for slime in self.slimes:
            if not slime.alive:
                continue
            slime.x += slime.vx * dt
            probe_x = slime.x + (slime.w if slime.vx > 0 else 0)
            foot_x = slime.x + slime.w / 2 + (14 if slime.vx > 0 else -14)
            tx, ty = int(probe_x // TILE), int(slime.y // TILE)
            ftx, fty = int(foot_x // TILE), int((slime.y + slime.h + 2) // TILE)
            if self.solid_at(tx, ty) or not self.solid_at(ftx, fty):
                slime.vx *= -1
                slime.x += slime.vx * dt

            pr = self.player.rect
            sr = slime.rect
            if not pr.colliderect(sr):
                continue
            stomped = self.player.vy > 40 and pr.bottom <= sr.centery + 12
            if stomped:
                dead = slime.hurt(self.stats.stomp_dmg())
                self.player.vy = self.stats.stomp_bounce()
                self.player.on_ground = False
                self.audio.play("stomp")
                if not dead:
                    self.audio.play("hit")
            elif self.player.invuln <= 0:
                self._hurt(slime.contact_damage)

    def _update_coins(self):
        for coin in self.coins:
            if coin.taken:
                continue
            if self.player.rect.colliderect(coin.rect):
                coin.taken = True
                self.coins_got += 1
                self.audio.play("coin")

    def _update_shots(self, dt):
        for shot in self.shots:
            if not shot.alive:
                continue
            shot.update(dt)
            if self.solid_at(int(shot.x // TILE), int(shot.y // TILE)):
                shot.alive = False
                continue
            for slime in self.slimes:
                if slime.alive and shot.rect.colliderect(slime.rect):
                    slime.hurt(self.stats.coin_dmg())
                    shot.alive = False
                    self.audio.play("hit")
                    break
        self.shots = [s for s in self.shots if s.alive]

    def _prune_behind(self):
        left = self.player.x - SCREEN_W * 2
        self.coins = [c for c in self.coins if (not c.taken) and c.x > left]
        self.slimes = [s for s in self.slimes if s.alive and s.x > left]

    def _toggle_shop(self):
        if self.state in ("play", "pause"):
            self._clear_hold()
            self.state = "shop"
        elif self.state == "shop":
            self._resume()
        elif self.state == "help":
            self.state = "shop"

    def _toggle_help(self):
        if self.state in ("play", "pause"):
            self._clear_hold()
            self.state = "help"
        elif self.state == "help":
            self._resume()
        elif self.state == "shop":
            self.state = "help"

    def _shop_click(self, pos):
        for kind, rect in shop_item_rects():
            if rect.collidepoint(pos):
                self._buy(kind)
                return

    def _buy(self, kind):
        cost = self.stats.cost(kind)
        if cost is None or self.coins_got < cost:
            self.audio.play("empty")
            return
        if kind == "heal":
            if self.player.hp >= self.player.max_hp:
                self.audio.play("empty")
                return
            self.coins_got -= cost
            self.player.heal(HEAL_AMOUNT)
            self.audio.play("coin")
            return
        self.coins_got -= cost
        if kind == "jump":
            self.stats.jump_lv += 1
        elif kind == "dmg":
            self.stats.dmg_lv += 1
        elif kind == "hp":
            self.stats.hp_lv += 1
            old = self.player.max_hp
            self.player.max_hp = self.stats.max_hp()
            self.player.hp += self.player.max_hp - old
        self.audio.play("coin")

    def _hurt(self, amount, pit=False):
        dead = self.player.take_hit(amount)
        self.audio.play("hurt")
        if dead:
            self.state = "lose"
            return
        if pit:
            self.player.reset()
            self.player.on_ground = True
            self.coyote = 0.1

    def draw_world(self):
        self._draw_sky()
        cam = self.cam
        x0 = max(0, int(cam.x // TILE) - 1)
        x1 = int((cam.x + SCREEN_W) // TILE) + 2
        y0 = max(0, int(cam.y // TILE) - 1)
        y1 = min(ROWS, int((cam.y + SCREEN_H) // TILE) + 2)
        self.world.ensure(x1 + CHUNK_W)
        self._absorb_spawns()
        for ty in range(y0, y1):
            for tx in range(x0, x1):
                ch = self.world.get(tx, ty)
                if ch not in SOLID:
                    continue
                r = pygame.Rect(tx * TILE - cam.x, ty * TILE - cam.y, TILE, TILE)
                if ch == "#":
                    pygame.draw.rect(self.screen, DIRT, r)
                    pygame.draw.rect(self.screen, GRASS, (r.x, r.y, r.w, 10))
                    pygame.draw.line(self.screen, (60, 110, 40), (r.x, r.y), (r.right, r.y), 2)
                elif ch == "D":
                    pygame.draw.rect(self.screen, DIRT, r)
                    pygame.draw.line(
                        self.screen, DIRT_DARK, (r.x, r.bottom - 1), (r.right, r.bottom - 1)
                    )
                else:
                    pygame.draw.rect(self.screen, WOOD_BOX, r)
                    pygame.draw.rect(self.screen, WOOD_EDGE, r, 2)

        for coin in self.coins:
            coin.draw(self.screen, cam, self.time)
        for slime in self.slimes:
            slime.draw(self.screen, cam, self.time)
        for shot in self.shots:
            shot.draw(self.screen, cam)
        self.player.draw(self.screen, cam)

    def _draw_sky(self):
        self.screen.fill(SKY_TOP)
        w, h = SCREEN_W, SCREEN_H
        pygame.draw.rect(self.screen, SKY_BOT, (0, int(h * 0.55), w, int(h * 0.45)))
        pygame.draw.ellipse(self.screen, (168, 196, 120), (-80, h * 0.48, 420, 220))
        pygame.draw.ellipse(self.screen, (148, 180, 108), (280, h * 0.50, 500, 240))
        pygame.draw.ellipse(self.screen, (255, 252, 230), (70, 48, 86, 86))

    def draw(self):
        self.touch.layout(self.screen.get_size())
        self.draw_world()
        dist = int(self.player.x // TILE)
        draw_hud(
            self.screen,
            self.fonts,
            self.coins_got,
            max(0, int(self.player.hp)),
            self.player.max_hp,
            self.audio.muted,
            self.touch.mute_r,
            self.touch.shop_r,
            self.touch.help_r,
            self.touch.pause_r,
            self.state == "pause",
            dist,
            self.touch.flip_r,
        )
        if self.state == "title":
            draw_title(self.screen, self.fonts)
            self.touch.draw(self.screen, self.fonts, show_start=True)
        elif self.state == "shop":
            self.touch.draw(self.screen, self.fonts, show_start=False)
            draw_shop(
                self.screen,
                self.fonts,
                self.stats,
                self.coins_got,
                int(self.player.hp),
                self.player.max_hp,
            )
        elif self.state == "help":
            self.touch.draw(self.screen, self.fonts, show_start=False)
            draw_help(self.screen, self.fonts)
        elif self.state == "pause":
            self.touch.draw(self.screen, self.fonts, show_start=False)
            draw_pause(self.screen, self.fonts, self.touch.start_r)
        elif self.state == "lose":
            draw_end(
                self.screen,
                self.fonts,
                "再试一次",
                f"这次跑了 {self.best_distance}m，金币 {self.coins_got}",
            )
            self.touch.draw(self.screen, self.fonts, show_start=True)
        else:
            self.touch.draw(self.screen, self.fonts, show_start=False)
        if self.state not in ("shop", "help", "pause"):
            draw_ime_warn(self.screen, self.fonts, self.ime_blocked)

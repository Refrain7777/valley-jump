"""无限向右生成的关卡。悬浮平台按跳跃高度来：全力跳约 3 格。"""

import random

TILE = 32
GROUND_ROW = 14
ROWS = 17
CHUNK_W = 22
PIT_Y = GROUND_ROW * TILE
SOLID = {"#", "D", "B"}

# 全力跳大约 3.1 格，所以 3 格要跳满，4 格必须踩怪借力
HEIGHT_FULL_JUMP = 3  # 相对地面
HEIGHT_STOMP = 4


def enemy_hp(chunk_id):
    """越往后血越厚：1 金币 = 100，踩 = 200。"""
    return 100 * (1 + chunk_id // 2)


class World:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.tiles = {}
        self.generated_to = -1
        self.pending_coins = []
        self.pending_slimes = []

    def reset(self):
        self.rng.seed()
        self.tiles.clear()
        self.generated_to = -1
        self.pending_coins.clear()
        self.pending_slimes.clear()
        self.ensure(CHUNK_W * 2)

    def get(self, tx, ty):
        return self.tiles.get((tx, ty), ".")

    def solid_at(self, tx, ty):
        if ty < 0 or ty >= ROWS:
            return False
        if tx < 0:
            return True
        self.ensure(tx + CHUNK_W)
        return self.get(tx, ty) in SOLID

    def ensure(self, tx):
        while self.generated_to < tx:
            start = self.generated_to + 1
            self._build_chunk(start, start + CHUNK_W - 1)
            self.generated_to = start + CHUNK_W - 1

    def _fill_ground(self, x0, x1):
        for x in range(x0, x1 + 1):
            self.tiles[(x, GROUND_ROW)] = "#"
            for y in range(GROUND_ROW + 1, ROWS):
                self.tiles[(x, y)] = "D"

    def _platform(self, x0, width, height_up):
        """height_up=3 表示在地面上方 3 格（row 11）。"""
        row = GROUND_ROW - height_up
        if row < 4:
            row = 4
        for x in range(x0, x0 + width):
            self.tiles[(x, row)] = "B"
        return row

    def _build_chunk(self, x0, x1):
        chunk_id = max(0, x0 // CHUNK_W)
        self._fill_ground(x0, x1)

        # 第一段保底地面，方便出生
        if chunk_id == 0:
            plat_x = x0 + 10
            row = self._platform(plat_x, 4, HEIGHT_FULL_JUMP)
            self.pending_coins.append((plat_x + 1, row - 1))
            self.pending_coins.append((plat_x + 2, row - 1))
            self.pending_slimes.append((x0 + 16, GROUND_ROW - 1, enemy_hp(0)))
            self.pending_coins.append((x0 + 6, GROUND_ROW - 1))
            return

        rng = self.rng
        pit_w = 3 if chunk_id < 3 else 4
        if x1 - x0 > pit_w + 8:
            pit_start = x0 + rng.randint(6, 10)
            pit_end = min(x1 - 3, pit_start + pit_w - 1)
            for x in range(pit_start, pit_end + 1):
                for y in range(GROUND_ROW, ROWS):
                    self.tiles.pop((x, y), None)

        # 全力跳平台（3 格），中后期再加必须踩怪才够的 4 格
        p1 = x0 + rng.randint(3, 7)
        row = self._platform(p1, rng.randint(3, 5), HEIGHT_FULL_JUMP)
        self.pending_coins.append((p1 + 1, row - 1))

        if chunk_id >= 1:
            p2 = min(x1 - 5, p1 + rng.randint(8, 12))
            hi = HEIGHT_STOMP if chunk_id >= 2 or rng.random() < 0.55 else HEIGHT_FULL_JUMP
            row2 = self._platform(p2, rng.randint(3, 4), hi)
            self.pending_coins.append((p2 + 1, row2 - 1))
            if hi == HEIGHT_STOMP:
                self.pending_coins.append((p2 + 2, row2 - 1))

        hp = enemy_hp(chunk_id)
        n_enemy = 1 if chunk_id < 2 else 2
        for _ in range(n_enemy):
            ex = rng.randint(x0 + 4, x1 - 2)
            if self.get(ex, GROUND_ROW) == "#":
                self.pending_slimes.append((ex, GROUND_ROW - 1, hp))

        if rng.random() < 0.7:
            cx = rng.randint(x0 + 2, x1 - 2)
            if self.get(cx, GROUND_ROW) == "#":
                self.pending_coins.append((cx, GROUND_ROW - 1))

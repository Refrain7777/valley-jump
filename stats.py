"""本局养成：花费递增、有等级上限，避免一次买满碾压后期。"""

JUMP_BASE = -460
STOMP_BOUNCE_BASE = -580
COIN_DMG_BASE = 100
STOMP_DMG_BASE = 200
HP_BASE = 100
MAX_STAT_LV = 6
HEAL_AMOUNT = 40
HEAL_COST = 6


class RunStats:
    def __init__(self):
        self.jump_lv = 0
        self.dmg_lv = 0
        self.hp_lv = 0

    def jump_speed(self):
        # 每级约 +8% 高度，6 级后大约能摸到 4 格高台，仍摸不到更高
        return JUMP_BASE * (1 + 0.08 * self.jump_lv)

    def stomp_bounce(self):
        return STOMP_BOUNCE_BASE * (1 + 0.05 * self.jump_lv)

    def coin_dmg(self):
        return int(COIN_DMG_BASE * (1 + 0.2 * self.dmg_lv))

    def stomp_dmg(self):
        return int(STOMP_DMG_BASE * (1 + 0.2 * self.dmg_lv))

    def max_hp(self):
        return HP_BASE + 25 * self.hp_lv

    def cost(self, kind):
        if kind == "heal":
            return HEAL_COST
        lv = getattr(self, f"{kind}_lv")
        if lv >= MAX_STAT_LV:
            return None
        base = {"jump": 8, "dmg": 10, "hp": 12}[kind]
        return int(base * (1.5 ** lv))

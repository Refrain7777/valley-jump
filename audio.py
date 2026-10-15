"""简单民谣风循环 BGM 和短音效（不使用任何正版曲库）。"""

import array
import math

import pygame

SAMPLE_RATE = 22050


def _raw_tone(freq, ms, volume=0.18, decay=True):
    n_samples = max(1, int(SAMPLE_RATE * ms / 1000))
    buf = array.array("h")
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        env = 1.0 - i / n_samples if decay else 1.0
        # 基频 + 轻弱五度，听起来更像木琴/民谣拨弦
        wave = math.sin(2 * math.pi * freq * t)
        wave += 0.25 * math.sin(2 * math.pi * freq * 1.5 * t)
        sample = int(volume * env * 16000 * wave)
        buf.append(max(-32767, min(32767, sample)))
    return buf


def _tone(freq, ms, volume=0.18, decay=True):
    return pygame.mixer.Sound(buffer=_raw_tone(freq, ms, volume, decay))


class Audio:
    def __init__(self):
        self.enabled = True
        self.muted = False
        self.bgm = None
        self.sfx = {}
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(SAMPLE_RATE, -16, 1, 512)
            notes = [262, 294, 330, 392, 440, 392, 330, 294, 247, 262, 330, 294]
            melody = array.array("h")
            for freq in notes:
                melody.extend(_raw_tone(freq, 280, 0.08, True))
            self.bgm = pygame.mixer.Sound(buffer=melody)
            self.sfx = {
                "jump": _tone(520, 90, 0.14),
                "coin": _tone(880, 120, 0.16),
                "stomp": _tone(180, 140, 0.2),
                "hurt": _tone(140, 280, 0.22),
                "shoot": _tone(700, 70, 0.14),
                "hit": _tone(240, 90, 0.16),
                "empty": _tone(110, 80, 0.12),
                "win": _tone(523, 400, 0.16, decay=False),
            }
        except (pygame.error, Exception):
            self.enabled = False

    def play_bgm(self):
        if self.enabled and not self.muted and self.bgm:
            self.bgm.play(loops=-1)

    def stop_bgm(self):
        if self.bgm:
            self.bgm.stop()

    def play(self, name):
        if self.enabled and not self.muted:
            sound = self.sfx.get(name)
            if sound:
                sound.play()

    def pause_game(self):
        if self.enabled:
            pygame.mixer.pause()

    def resume_game(self):
        if self.enabled and not self.muted:
            pygame.mixer.unpause()

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.stop_bgm()
        else:
            self.play_bgm()

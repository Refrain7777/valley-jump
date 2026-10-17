"""简单民谣风循环 BGM 和短音效（不使用任何正版曲库）。

网页端延后生成波形，避免一进游戏就卡很久。
"""

import array
import math
import sys

import pygame

SAMPLE_RATE = 22050


def _raw_tone(freq, ms, volume=0.18, decay=True, step=2):
    """step>1 时少算采样，再重复，显著加快 WASM 上的生成速度。"""
    n_samples = max(1, int(SAMPLE_RATE * ms / 1000))
    buf = array.array("h")
    step = max(1, int(step))
    for i in range(0, n_samples, step):
        t = i / SAMPLE_RATE
        env = 1.0 - i / n_samples if decay else 1.0
        wave = math.sin(2 * math.pi * freq * t)
        wave += 0.25 * math.sin(2 * math.pi * freq * 1.5 * t)
        sample = int(volume * env * 16000 * wave)
        sample = max(-32767, min(32767, sample))
        for _ in range(min(step, n_samples - i)):
            buf.append(sample)
    return buf


def _tone(freq, ms, volume=0.18, decay=True, step=2):
    return pygame.mixer.Sound(buffer=_raw_tone(freq, ms, volume, decay, step))


class Audio:
    def __init__(self, lazy=True):
        self.enabled = True
        self.muted = False
        self.bgm = None
        self.sfx = {}
        self._ready = False
        self._want_bgm = False
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(SAMPLE_RATE, -16, 1, 512)
        except (pygame.error, Exception):
            self.enabled = False
            return
        if not lazy:
            self.ensure_ready()

    def ensure_ready(self):
        if self._ready or not self.enabled:
            return
        try:
            # 网页用更大步长换速度；本机仍较细
            step = 4 if sys.platform == "emscripten" else 2
            notes = [262, 294, 330, 392, 440, 392, 330, 294]
            melody = array.array("h")
            for freq in notes:
                melody.extend(_raw_tone(freq, 220, 0.08, True, step=step))
            self.bgm = pygame.mixer.Sound(buffer=melody)
            self.sfx = {
                "jump": _tone(520, 70, 0.14, step=step),
                "coin": _tone(880, 90, 0.16, step=step),
                "stomp": _tone(180, 100, 0.2, step=step),
                "hurt": _tone(140, 180, 0.22, step=step),
                "shoot": _tone(700, 55, 0.14, step=step),
                "hit": _tone(240, 70, 0.16, step=step),
                "empty": _tone(110, 60, 0.12, step=step),
                "win": _tone(523, 280, 0.16, decay=False, step=step),
            }
            self._ready = True
            if self._want_bgm and not self.muted:
                self.bgm.play(loops=-1)
        except (pygame.error, Exception):
            self.enabled = False

    def play_bgm(self):
        self._want_bgm = True
        if not self._ready:
            return
        if self.enabled and not self.muted and self.bgm:
            self.bgm.play(loops=-1)

    def stop_bgm(self):
        if self.bgm:
            self.bgm.stop()

    def play(self, name):
        if not self._ready:
            self.ensure_ready()
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
            if not self._ready:
                self.ensure_ready()
            self.play_bgm()

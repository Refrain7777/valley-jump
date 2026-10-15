"""检测 Windows 是否处于中文输入。网页端始终返回 False。"""

import sys

IME_CMODE_NATIVE = 0x0001


def is_chinese_ime():
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        import pygame

        hwnd = pygame.display.get_wm_info().get("window")
        if not hwnd:
            return False
        imm32 = ctypes.WinDLL("imm32", use_last_error=True)
        imm32.ImmGetContext.argtypes = [wintypes.HWND]
        imm32.ImmGetContext.restype = wintypes.HANDLE
        imm32.ImmReleaseContext.argtypes = [wintypes.HWND, wintypes.HANDLE]
        imm32.ImmGetOpenStatus.argtypes = [wintypes.HANDLE]
        imm32.ImmGetOpenStatus.restype = wintypes.BOOL
        imm32.ImmGetConversionStatus.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        imm32.ImmGetConversionStatus.restype = wintypes.BOOL

        himc = imm32.ImmGetContext(wintypes.HWND(hwnd))
        if not himc:
            return False
        opened = bool(imm32.ImmGetOpenStatus(himc))
        conv = wintypes.DWORD()
        sent = wintypes.DWORD()
        native = False
        if imm32.ImmGetConversionStatus(himc, ctypes.byref(conv), ctypes.byref(sent)):
            native = bool(conv.value & IME_CMODE_NATIVE)
        imm32.ImmReleaseContext(wintypes.HWND(hwnd), himc)
        # 同时开着输入法且是中文模式，才提示；避免误判把游戏锁死
        return opened and native
    except Exception:
        return False

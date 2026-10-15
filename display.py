"""网页画布铺满窗口，但逻辑分辨率仍是 960x540，点击坐标与按钮一致。"""

import sys


def setup_web_page():
    if sys.platform != "emscripten":
        return
    try:
        from platform import document, window

        style = document.createElement("style")
        style.textContent = """
        html,body{
          margin:0;padding:0;width:100%;height:100%;overflow:hidden;
          background:#050608;touch-action:none;
          -webkit-user-select:none;user-select:none;
        }
        canvas,canvas.emscripten,#canvas,#pygame{
          display:block !important;
          position:fixed !important;
          left:50% !important;
          top:50% !important;
          transform:translate(-50%,-50%) !important;
          width:auto !important;
          height:auto !important;
          max-width:100vw !important;
          max-height:100vh !important;
          object-fit:contain !important;
          touch-action:none !important;
        }
        """
        document.head.appendChild(style)
        document.body.style.margin = "0"
        document.body.style.overflow = "hidden"

        def _block_scroll(ev):
            ev.preventDefault()

        document.addEventListener("touchmove", _block_scroll, {"passive": False})
        document.addEventListener("gesturestart", _block_scroll, {"passive": False})
        window.addEventListener("touchmove", _block_scroll, {"passive": False})
    except Exception:
        pass

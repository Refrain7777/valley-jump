"""网页画布按 16:9 铺满；手机竖屏时旋转成横版，触摸按旋转后的画面换算。"""

import json
import sys

GAME_W = 960
GAME_H = 540

_FIT_JS = r"""
(function () {
  if (window.__vjReady) return;
  window.__vjReady = true;
  window.__vj = { pointers: {}, json: '{"p":[]}', rotated: false };
  var GW = 960, GH = 540;

  function canvas() {
    return document.querySelector("canvas") || document.getElementById("canvas") || document.getElementById("pygame");
  }

  function viewSize() {
    var vv = window.visualViewport;
    var sw = (vv && vv.width) || window.innerWidth || document.documentElement.clientWidth;
    var sh = (vv && vv.height) || window.innerHeight || document.documentElement.clientHeight;
    return { sw: sw, sh: sh };
  }

  function fit() {
    var c = canvas();
    if (!c) return;
    var size = viewSize();
    var sw = size.sw, sh = size.sh;
    // 浏览器仍报竖屏时（手机已横过来也很常见），把 16:9 画面旋转铺满
    var rotated = sw < sh;
    window.__vj.rotated = rotated;
    var s = rotated ? Math.min(sw / GH, sh / GW) : Math.min(sw / GW, sh / GH);
    var w = Math.max(1, Math.round(GW * s));
    var h = Math.max(1, Math.round(GH * s));
    c.style.cssText = [
      "position:fixed",
      "left:" + Math.floor((sw - w) / 2) + "px",
      "top:" + Math.floor((sh - h) / 2) + "px",
      "right:auto",
      "bottom:auto",
      "margin:0",
      "width:" + w + "px",
      "height:" + h + "px",
      "max-width:none",
      "max-height:none",
      "transform:" + (rotated ? "rotate(90deg)" : "none"),
      "transform-origin:center center",
      "object-fit:fill",
      "touch-action:none",
      "z-index:20",
      "pointer-events:auto"
    ].join(";");
  }

  function toGame(ev) {
    var c = canvas();
    if (!c) return null;
    var r = c.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return null;
    var nx = (ev.clientX - r.left) / r.width;
    var ny = (ev.clientY - r.top) / r.height;
    if (window.__vj.rotated) {
      // CSS rotate(90deg)：屏幕左右对应游戏上下，屏幕上下对应游戏左右
      return { x: ny * GW, y: (1 - nx) * GH };
    }
    return { x: nx * GW, y: ny * GH };
  }

  function dump() {
    var list = [];
    var ptrs = window.__vj.pointers;
    for (var k in ptrs) {
      if (Object.prototype.hasOwnProperty.call(ptrs, k)) list.push(ptrs[k]);
    }
    window.__vj.json = JSON.stringify({ p: list });
  }

  function down(ev) {
    var p = toGame(ev);
    if (!p) return;
    if (ev.cancelable) ev.preventDefault();
    window.__vj.pointers[String(ev.pointerId)] = { id: ev.pointerId, x: p.x, y: p.y };
    dump();
  }
  function move(ev) {
    var key = String(ev.pointerId);
    if (!window.__vj.pointers[key]) return;
    var p = toGame(ev);
    if (!p) return;
    if (ev.cancelable) ev.preventDefault();
    window.__vj.pointers[key] = { id: ev.pointerId, x: p.x, y: p.y };
    dump();
  }
  function up(ev) {
    delete window.__vj.pointers[String(ev.pointerId)];
    dump();
  }

  function wrapTouch(t) {
    return { pointerId: "t" + t.identifier, clientX: t.clientX, clientY: t.clientY, cancelable: true, preventDefault: function () {} };
  }
  function touchDown(ev) {
    if (ev.cancelable) ev.preventDefault();
    for (var i = 0; i < ev.changedTouches.length; i++) down(wrapTouch(ev.changedTouches[i]));
  }
  function touchMove(ev) {
    if (ev.cancelable) ev.preventDefault();
    for (var i = 0; i < ev.changedTouches.length; i++) move(wrapTouch(ev.changedTouches[i]));
  }
  function touchUp(ev) {
    for (var i = 0; i < ev.changedTouches.length; i++) up(wrapTouch(ev.changedTouches[i]));
  }
  function tryLandscape() {
    try {
      var o = screen.orientation || screen.mozOrientation;
      if (o && o.lock) o.lock("landscape").catch(function () {});
    } catch (e) {}
  }
  document.addEventListener("pointerdown", function () { tryLandscape(); }, { capture: true });
  document.addEventListener("pointerdown", down, { passive: false, capture: true });
  document.addEventListener("pointermove", move, { passive: false, capture: true });
  document.addEventListener("pointerup", up, { passive: false, capture: true });
  document.addEventListener("pointercancel", up, { passive: false, capture: true });
  document.addEventListener("touchstart", touchDown, { passive: false, capture: true });
  document.addEventListener("touchmove", touchMove, { passive: false, capture: true });
  document.addEventListener("touchend", touchUp, { passive: false, capture: true });
  document.addEventListener("touchcancel", touchUp, { passive: false, capture: true });
  window.addEventListener("resize", fit);
  window.addEventListener("orientationchange", fit);
  function loop() {
    fit();
    dump();
    requestAnimationFrame(loop);
  }
  loop();
})();
"""


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
          -webkit-touch-callout:none;
        }
        #status,#progress,#lblstatus,.emscripten_border{
          pointer-events:none !important;
        }
        """
        document.head.appendChild(style)
        var meta = document.querySelector('meta[name="viewport"]')
        if not meta:
            meta = document.createElement("meta")
            meta.setAttribute("name", "viewport")
            document.head.appendChild(meta)
        meta.setAttribute(
            "content",
            "width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover",
        )
        document.body.style.margin = "0"
        document.body.style.overflow = "hidden"

        script = document.createElement("script")
        script.textContent = _FIT_JS
        document.body.appendChild(script)
        if hasattr(window, "eval"):
            window.eval(_FIT_JS)
    except Exception:
        pass


def poll_web_pointers():
    """浏览器里返回当前按住的指针，已换算到 960x540。本机返回空。"""
    if sys.platform != "emscripten":
        return []
    try:
        from platform import window

        raw = ""
        vj = getattr(window, "__vj", None)
        if vj is not None:
            raw = getattr(vj, "json", "") or ""
        if not raw:
            raw = getattr(window, "__vj_json", "") or ""
        text = str(raw)
        if text.startswith("'") and text.endswith("'"):
            text = text[1:-1]
        data = json.loads(text)
        out = []
        for item in data.get("p") or []:
            out.append(
                {
                    "id": item.get("id", 0),
                    "x": float(item.get("x", 0)),
                    "y": float(item.get("y", 0)),
                }
            )
        return out
    except Exception:
        return []

"""网页画布按 16:9 真实像素居中，触摸坐标用浏览器指针换算，不依赖 CSS transform。"""

import json
import sys

GAME_W = 960
GAME_H = 540

_FIT_JS = r"""
(function () {
  if (window.__vjReady) return;
  window.__vjReady = true;
  window.__vj = { pointers: {}, json: '{"p":[]}' };
  var GW = 960, GH = 540;

  function canvas() {
    return document.querySelector("canvas") || document.getElementById("canvas") || document.getElementById("pygame");
  }

  function fit() {
    var c = canvas();
    if (!c) return;
    var sw = window.innerWidth || document.documentElement.clientWidth;
    var sh = window.innerHeight || document.documentElement.clientHeight;
    var s = Math.min(sw / GW, sh / GH);
    var w = Math.max(1, Math.round(GW * s));
    var h = Math.max(1, Math.round(GH * s));
    c.style.position = "fixed";
    c.style.left = Math.floor((sw - w) / 2) + "px";
    c.style.top = Math.floor((sh - h) / 2) + "px";
    c.style.right = "auto";
    c.style.bottom = "auto";
    c.style.margin = "0";
    c.style.width = w + "px";
    c.style.height = h + "px";
    c.style.maxWidth = "none";
    c.style.maxHeight = "none";
    c.style.transform = "none";
    c.style.objectFit = "fill";
    c.style.touchAction = "none";
    c.style.zIndex = "20";
    c.style.pointerEvents = "auto";
  }

  function toGame(ev) {
    var c = canvas();
    if (!c) return null;
    var r = c.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return null;
    return {
      x: ((ev.clientX - r.left) / r.width) * GW,
      y: ((ev.clientY - r.top) / r.height) * GH
    };
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

"""手机横屏：用独立舞台旋转铺满，并挡住 pygbag 对画布的缩放。"""

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

  function ensureStage() {
    var c = canvas();
    if (!c) return null;
    var stage = document.getElementById("vj-stage");
    if (!stage) {
      stage = document.createElement("div");
      stage.id = "vj-stage";
      document.body.appendChild(stage);
    }
    if (c.parentElement !== stage) stage.appendChild(c);
    return stage;
  }

  function viewSize() {
    var sw = window.innerWidth || document.documentElement.clientWidth || 0;
    var sh = window.innerHeight || document.documentElement.clientHeight || 0;
    if (window.visualViewport && window.visualViewport.width && window.visualViewport.height) {
      sw = window.visualViewport.width;
      sh = window.visualViewport.height;
    }
    return { sw: sw, sh: sh };
  }

  function wantRotate() {
    try {
      var t = (screen.orientation && screen.orientation.type) || "";
      if (t.indexOf("landscape") >= 0) return false;
      if (t.indexOf("portrait") >= 0) return true;
    } catch (e) {}
    if (typeof window.orientation === "number") return Math.abs(window.orientation) !== 90;
    try {
      if (window.matchMedia("(orientation: landscape)").matches) return false;
      if (window.matchMedia("(orientation: portrait)").matches) return true;
    } catch (e2) {}
    var size = viewSize();
    return size.sw < size.sh;
  }

  function layout() {
    var stage = ensureStage();
    var c = canvas();
    if (!stage || !c) return;
    var size = viewSize();
    var sw = size.sw, sh = size.sh;
    var rotated = wantRotate();
    window.__vj.rotated = rotated;
    var s = rotated ? Math.min(sw / GH, sh / GW) : Math.min(sw / GW, sh / GH);
    var w = Math.max(1, Math.round(GW * s));
    var h = Math.max(1, Math.round(GH * s));
    stage.style.setProperty("position", "fixed", "important");
    stage.style.setProperty("left", "50%", "important");
    stage.style.setProperty("top", "50%", "important");
    stage.style.setProperty("width", w + "px", "important");
    stage.style.setProperty("height", h + "px", "important");
    stage.style.setProperty("margin", "0", "important");
    stage.style.setProperty("padding", "0", "important");
    stage.style.setProperty("z-index", "9999", "important");
    stage.style.setProperty("overflow", "hidden", "important");
    stage.style.setProperty(
      "transform",
      rotated ? "translate(-50%,-50%) rotate(-90deg)" : "translate(-50%,-50%)",
      "important"
    );
    stage.style.setProperty("transform-origin", "center center", "important");
    c.style.setProperty("position", "absolute", "important");
    c.style.setProperty("left", "0", "important");
    c.style.setProperty("top", "0", "important");
    c.style.setProperty("width", "100%", "important");
    c.style.setProperty("height", "100%", "important");
    c.style.setProperty("max-width", "none", "important");
    c.style.setProperty("max-height", "none", "important");
    c.style.setProperty("transform", "none", "important");
    c.style.setProperty("object-fit", "fill", "important");
    c.style.setProperty("margin", "0", "important");
    c.style.setProperty("border", "0", "important");
    c.style.setProperty("touch-action", "none", "important");
  }

  function hijackPygbag() {
    function wrap(name) {
      try {
        window[name] = function () { layout(); };
      } catch (e) {}
    }
    wrap("window_resize");
    wrap("window_resize_2d");
    wrap("window_resize_3d");
    try {
      if (window.vm && window.vm.config) window.vm.config.user_canvas_managed = 0;
    } catch (e2) {}
  }

  function toGame(ev) {
    var c = canvas();
    if (!c) return null;
    var r = c.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return null;
    var nx = (ev.clientX - r.left) / r.width;
    var ny = (ev.clientY - r.top) / r.height;
    if (window.__vj.rotated) {
      // rotate(-90deg)：手机顺时针横过来后，点的位置和画面一致
      return { x: (1 - ny) * GW, y: nx * GH };
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
  function quiet(p) {
    try {
      if (p && typeof p.catch === "function") p.catch(function () {});
    } catch (e) {}
  }
  function tryWide() {
    // Optional. Mobile denies fullscreen / orientation lock with
    // "Permissions check failed"; pygbag alerts any unhandled rejection.
    if (window.__vj.wideDone) return;
    window.__vj.wideDone = true;
    try {
      var el = document.documentElement;
      var req = el.requestFullscreen || el.webkitRequestFullscreen || el.webkitRequestFullScreen;
      if (req) quiet(req.call(el));
    } catch (e) {}
    try {
      var o = screen.orientation || screen.mozOrientation;
      if (o && o.lock) quiet(o.lock("landscape"));
    } catch (e2) {}
  }

  function clearAll() {
    window.__vj.pointers = {};
    dump();
  }
  document.addEventListener("pointerdown", function () { tryWide(); }, { capture: true });
  document.addEventListener("pointerdown", down, { passive: false, capture: true });
  document.addEventListener("pointermove", move, { passive: false, capture: true });
  document.addEventListener("pointerup", up, { passive: false, capture: true });
  document.addEventListener("pointercancel", up, { passive: false, capture: true });
  window.addEventListener("blur", clearAll);
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) clearAll();
  });
  if (!window.PointerEvent) {
    function wrapTouch(t) {
      return { pointerId: "t" + t.identifier, clientX: t.clientX, clientY: t.clientY, cancelable: true, preventDefault: function () {} };
    }
    document.addEventListener("touchstart", function (ev) {
      if (ev.cancelable) ev.preventDefault();
      for (var i = 0; i < ev.changedTouches.length; i++) down(wrapTouch(ev.changedTouches[i]));
    }, { passive: false, capture: true });
    document.addEventListener("touchmove", function (ev) {
      if (ev.cancelable) ev.preventDefault();
      for (var i = 0; i < ev.changedTouches.length; i++) move(wrapTouch(ev.changedTouches[i]));
    }, { passive: false, capture: true });
    document.addEventListener("touchend", function (ev) {
      for (var i = 0; i < ev.changedTouches.length; i++) up(wrapTouch(ev.changedTouches[i]));
    }, { passive: false, capture: true });
    document.addEventListener("touchcancel", function (ev) {
      for (var i = 0; i < ev.changedTouches.length; i++) up(wrapTouch(ev.changedTouches[i]));
    }, { passive: false, capture: true });
  }
  window.addEventListener("resize", layout);
  window.addEventListener("orientationchange", function () { setTimeout(layout, 50); setTimeout(layout, 300); });
  if (screen.orientation && screen.orientation.addEventListener) {
    screen.orientation.addEventListener("change", function () { setTimeout(layout, 50); });
  }
  hijackPygbag();
  setInterval(function () { hijackPygbag(); layout(); }, 400);
  function loop() {
    layout();
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
          margin:0 !important;padding:0 !important;
          width:100% !important;height:100% !important;
          overflow:hidden !important;background:#050608 !important;
          touch-action:none !important;
          -webkit-user-select:none !important;user-select:none !important;
          position:fixed !important;inset:0 !important;
        }
        #status,#progress,#lblstatus,#infobox,.emscripten_border,#pyconsole,#system,#transfer,#info,#box{
          display:none !important;pointer-events:none !important;
        }
        #vj-stage{
          position:fixed !important;z-index:9999 !important;
          left:50% !important;top:50% !important;
          transform:translate(-50%,-50%);
        }
        #vj-stage canvas,canvas.emscripten,#canvas,#pygame{
          position:absolute !important;left:0 !important;top:0 !important;
          width:100% !important;height:100% !important;
          max-width:none !important;max-height:none !important;
          border:0 !important;padding:0 !important;margin:0 !important;
          touch-action:none !important;
        }
        """
        document.head.appendChild(style)
        meta = document.querySelector('meta[name="viewport"]')
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
        try:
            window.vm.config.user_canvas_managed = 0
        except Exception:
            pass
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

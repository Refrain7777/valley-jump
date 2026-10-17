"""手机视口锁死时，按机身朝向把画面转正，左右横屏都能翻转。"""

import json
import sys

GAME_W = 960
GAME_H = 540

_FIT_JS = r"""
(function () {
  if (window.__vjReady) return;
  window.__vjReady = true;
  if (window.vjBootDone) window.vjBootDone();
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
    var ox = 0, oy = 0;
    var vv = window.visualViewport;
    if (vv && vv.width && vv.height) {
      sw = vv.width;
      sh = vv.height;
      ox = vv.offsetLeft || 0;
      oy = vv.offsetTop || 0;
    }
    return { sw: sw, sh: sh, ox: ox, oy: oy };
  }

  function ensureSafeProbe() {
    var probe = document.getElementById("vj-safe");
    if (!probe) {
      probe = document.createElement("div");
      probe.id = "vj-safe";
      document.body.appendChild(probe);
    }
    return probe;
  }

  function safeInsets() {
    var probe = ensureSafeProbe();
    var cs = window.getComputedStyle(probe);
    function n(v) {
      var x = parseFloat(v);
      return x > 0 && isFinite(x) ? x : 0;
    }
    return {
      l: n(cs.paddingLeft),
      t: n(cs.paddingTop),
      r: n(cs.paddingRight),
      b: n(cs.paddingBottom)
    };
  }

  function isMobile() {
    try {
      if (window.matchMedia("(pointer: coarse)").matches) return true;
    } catch (e) {}
    return (navigator.maxTouchPoints || 0) > 0;
  }

  function screenAngle() {
    try {
      var o = screen.orientation;
      if (o && typeof o.angle === "number" && isFinite(o.angle)) {
        return ((o.angle % 360) + 360) % 360;
      }
    } catch (e) {}
    // window.orientation 正值是逆时针。逆时针 90° 与 screen.orientation.angle 的 90 一致。
    if (typeof window.orientation === "number") {
      var w = window.orientation;
      if (w === -90) return 270;
      if (w < 0) w += 360;
      return ((w % 360) + 360) % 360;
    }
    return null;
  }

  function commitQuadrant(q) {
    if (q == null) return;
    var now = Date.now();
    if (q === window.__vj.q) {
      window.__vj.pendingQ = q;
      return;
    }
    if (q !== window.__vj.pendingQ) {
      window.__vj.pendingQ = q;
      window.__vj.pendingAt = now;
      return;
    }
    // 换方向要稳住大约半秒，避免手一抖就翻
    var wait = window.__vj.q == null ? 250 : 600;
    if (now - window.__vj.pendingAt >= wait) window.__vj.q = q;
  }

  function onOrient(ev) {
    if (ev.beta == null || ev.gamma == null) return;
    var b = ev.beta, g = ev.gamma;
    var ab = Math.abs(b), ag = Math.abs(g);
    if (ab < 25 && ag < 25) return;
    var q = null;
    // 0 竖屏正放，1 顺时针横屏，2 倒竖屏，3 逆时针横屏
    // 已经有方向时，阈值更宽，小幅晃动不算翻转
    var locked = window.__vj.q != null;
    var margin = locked ? 38 : 22;
    var minAxis = locked ? 58 : 42;
    if (ag > ab + margin && ag > minAxis) q = g > 0 ? 1 : 3;
    else if (ab > ag + margin && ab > minAxis) q = b > 0 ? 0 : 2;
    if (q == null) return;
    commitQuadrant(q);
  }

  function computeRot() {
    if (!isMobile()) return 0;
    var q = window.__vj.q;
    // 还没拿到机身方向时先不要转。有的浏览器一转，开始键和手指就对不上，人进不了游戏。
    if (q == null) return 0;
    var angle = screenAngle();
    if (angle == null) {
      var size2 = viewSize();
      angle = size2.sw >= size2.sh ? 90 : 0;
    }
    angle = (Math.round(angle / 90) * 90) % 360;
    var size3 = viewSize();
    var wide = size3.sw > size3.sh * 1.05;
    var tall = size3.sh > size3.sw * 1.05;
    var angleWide = angle === 90 || angle === 270;
    // 视口像素没跟着方向数字走时，按看到的宽高来补，否则翻转会被算成 0。
    if ((wide && !angleWide) || (tall && angleWide)) angle = wide ? 90 : 0;
    var sky = (360 - q * 90) % 360;
    return (sky - angle + 360) % 360;
  }

  function listenMotion() {
    if (window.__vj.motionListening) return;
    window.__vj.motionListening = true;
    window.addEventListener("deviceorientation", onOrient, true);
  }

  function enableMotion() {
    if (window.__vj.motionAsked) return;
    window.__vj.motionAsked = true;
    var D = window.DeviceOrientationEvent;
    if (D && typeof D.requestPermission === "function") {
      try {
        var p = D.requestPermission();
        if (p && typeof p.then === "function") {
          p.then(function (s) {
            if (s === "granted") listenMotion();
          }, function () {});
        }
      } catch (e) {}
      return;
    }
    listenMotion();
  }

  function layout() {
    try { layoutBody(); } catch (e) {}
  }

  function layoutBody() {
    var stage = ensureStage();
    var c = canvas();
    if (!stage || !c) return;
    var size = viewSize();
    var inset = safeInsets();
    var padL = inset.l, padR = inset.r, padT = inset.t, padB = inset.b;
    // 系统不报安全区时，横屏圆角和底部手势条仍会挡住边上的按键
    if (padL + padR < 8 && size.sw > size.sh) {
      padL += 12;
      padR += 12;
    }
    if (padB < 8) padB += 10;
    var sw = Math.max(1, size.sw - padL - padR);
    var sh = Math.max(1, size.sh - padT - padB);
    var rot = (computeRot() + (window.__vj.userFlip || 0)) % 360;
    window.__vj.rot = rot;
    var sideways = rot === 90 || rot === 270;
    var s = sideways ? Math.min(sw / GH, sh / GW) : Math.min(sw / GW, sh / GH);
    var w = Math.max(1, Math.round(GW * s));
    var h = Math.max(1, Math.round(GH * s));
    var cx = size.ox + padL + sw / 2;
    var cy = size.oy + padT + sh / 2;
    stage.style.setProperty("position", "fixed", "important");
    stage.style.setProperty("left", cx + "px", "important");
    stage.style.setProperty("top", cy + "px", "important");
    stage.style.setProperty("width", w + "px", "important");
    stage.style.setProperty("height", h + "px", "important");
    stage.style.setProperty("margin", "0", "important");
    stage.style.setProperty("padding", "0", "important");
    stage.style.setProperty("z-index", "9999", "important");
    stage.style.setProperty("overflow", "hidden", "important");
    stage.style.setProperty(
      "transform",
      "translate(-50%,-50%) rotate(" + rot + "deg)",
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
    var rot = window.__vj.rot || 0;
    if (rot === 90) return { x: ny * GW, y: (1 - nx) * GH };
    if (rot === 270) return { x: (1 - ny) * GW, y: nx * GH };
    if (rot === 180) return { x: (1 - nx) * GW, y: (1 - ny) * GH };
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

  function gestureDup(ev) {
    var now = Date.now();
    var x = ev.clientX || 0, y = ev.clientY || 0;
    var last = window.__vj.gd;
    if (last && (now - last.t) < 50 && Math.abs(last.x - x) < 12 && Math.abs(last.y - y) < 12) return true;
    window.__vj.gd = { t: now, x: x, y: y };
    return false;
  }
  function down(ev) {
    try {
      if (gestureDup(ev)) return;
      var p = toGame(ev);
      if (!p) return;
      // 只在点「翻转」时才问方向权限。一进页面就问，微信 / QQ 会白屏或直接退出。
      if (p.x >= 578 && p.x <= 650 && p.y >= 12 && p.y <= 48) enableMotion();
      if (ev.cancelable) ev.preventDefault();
      window.__vj.pointers[String(ev.pointerId)] = { id: ev.pointerId, x: p.x, y: p.y };
      dump();
    } catch (e) {}
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
  function on(el, name, fn) {
    try {
      el.addEventListener(name, fn, { passive: false, capture: true });
    } catch (e) {
      try { el.addEventListener(name, fn, true); } catch (e2) {}
    }
  }

  function clearAll() {
    window.__vj.pointers = {};
    dump();
  }
  function fromTouch(t, ev) {
    return {
      pointerId: "t" + t.identifier,
      clientX: t.clientX,
      clientY: t.clientY,
      cancelable: true,
      preventDefault: function () { if (ev.cancelable) ev.preventDefault(); }
    };
  }
  function isFinger(ev) {
    if (ev.pointerType === "mouse" || ev.pointerType === "pen") return false;
    return isMobile();
  }
  // 部分手机浏览器有 PointerEvent，但点下去没反应。手指一律走 touch。
  on(document, "pointerdown", function (ev) {
    if (isFinger(ev)) return;
    down(ev);
  });
  on(document, "pointermove", function (ev) {
    if (isFinger(ev)) return;
    move(ev);
  });
  on(document, "pointerup", function (ev) {
    if (isFinger(ev)) return;
    up(ev);
  });
  on(document, "pointercancel", function (ev) {
    if (isFinger(ev)) return;
    up(ev);
  });
  on(document, "touchstart", function (ev) {
    for (var i = 0; i < ev.changedTouches.length; i++) down(fromTouch(ev.changedTouches[i], ev));
  });
  on(document, "touchmove", function (ev) {
    for (var i = 0; i < ev.changedTouches.length; i++) move(fromTouch(ev.changedTouches[i], ev));
  });
  on(document, "touchend", function (ev) {
    for (var i = 0; i < ev.changedTouches.length; i++) up(fromTouch(ev.changedTouches[i], ev));
  });
  on(document, "touchcancel", function (ev) {
    for (var i = 0; i < ev.changedTouches.length; i++) up(fromTouch(ev.changedTouches[i], ev));
  });
  window.addEventListener("blur", clearAll);
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) clearAll();
  });
  window.addEventListener("resize", layout);
  window.addEventListener("orientationchange", function () { setTimeout(layout, 50); setTimeout(layout, 300); });
  window.addEventListener("pageshow", layout);
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", layout);
    window.visualViewport.addEventListener("scroll", layout);
  }
  if (screen.orientation && screen.orientation.addEventListener) {
    screen.orientation.addEventListener("change", function () { setTimeout(layout, 50); });
  }
  if (!(window.DeviceOrientationEvent && window.DeviceOrientationEvent.requestPermission)) {
    listenMotion();
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
          overscroll-behavior:none !important;
          -webkit-user-select:none !important;user-select:none !important;
          position:fixed !important;
          top:0 !important;right:0 !important;bottom:0 !important;left:0 !important;
        }
        #vj-safe{
          position:fixed;left:0;top:0;width:0;height:0;
          visibility:hidden;pointer-events:none;
          padding: env(safe-area-inset-top) env(safe-area-inset-right)
                   env(safe-area-inset-bottom) env(safe-area-inset-left);
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


def toggle_web_flip():
    """网页里把画面再转 180°。方向传感器不可用时，用画面上的「翻转」。"""
    if sys.platform != "emscripten":
        return
    try:
        from platform import window

        if hasattr(window, "eval"):
            window.eval("if(window.__vj){window.__vj.userFlip=window.__vj.userFlip?0:180;}")
            return
        vj = getattr(window, "__vj", None)
        if vj is None:
            return
        cur = int(getattr(vj, "userFlip", 0) or 0)
        vj.userFlip = 0 if cur else 180
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

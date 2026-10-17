#!/usr/bin/env python3
"""Copy the pygbag runtime off pygame-web.github.io into build/web.

GitHub Pages then serves the engine from the same origin as the game.
The script rewrites index.html so the browser does not request the CDN,
drops the dead browserfs script if one is still present, and records
file sizes for the Chinese loading screen.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

RUNTIME_FILES = (
    "pythons.js",
    "cpythonrc.py",
    "empty.ogg",
    "cpython312/main.js",
    "cpython312/main.wasm",
    "cpython312/main.data",
)
PARENT_FILES = (
    "vt.js",
    "vtx.js",
    "vt/xterm.js",
    "vt/xterm.css",
    "vt/xterm-addon-image.js",
)
CDN_RE = re.compile(
    r"https://pygame-web\.github\.io/cdn/(?P<version>\d+\.\d+(?:\.\d+)?)/"
)
SIZES_RE = re.compile(
    r'<script id="vj-sizes">.*?</script>',
    re.DOTALL,
)
PRELOAD = """<link rel="preload" href="vendor/runtime/cpython312/main.wasm" as="fetch" crossorigin="anonymous">
<link rel="preload" href="vendor/runtime/cpython312/main.data" as="fetch" crossorigin="anonymous">"""


def _get(url: str, dest: Path | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "valley-jump-pages"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"download failed {exc.code} {url}") from exc
    if dest is not None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    return data


def platform_tags(blob: bytes) -> list[str]:
    found = {
        match.decode("ascii", "ignore").replace("-", "_")
        for match in re.findall(rb"wasm32[-_][A-Za-z0-9_-]{0,48}emscripten", blob)
    }
    ordered = ["wasm32_bi_emscripten"]
    ordered.extend(sorted(found, key=lambda item: ("bi" not in item, -len(item))))
    seen = []
    for item in ordered:
        if item and item not in seen:
            seen.append(item)
    return seen


def resolve_wheel(index: dict, cdn_root: str, tags: list[str]) -> tuple[str, str]:
    template = index.get("pygame")
    if not template:
        raise SystemExit("package index has no pygame wheel")
    for tag in tags:
        path = template.replace("<abi>", "cp312").replace("<api>", tag)
        url = cdn_root + path
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "valley-jump-pages"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status == 200:
                    return path, url
        except urllib.error.HTTPError:
            continue
    raise SystemExit(f"could not find pygame wheel for tags {tags}: {template}")


def rewrite_index(html: str, cdn_prefix: str, sizes: dict[str, int]) -> str:
    if cdn_prefix not in html:
        raise SystemExit(f"index.html is missing CDN prefix {cdn_prefix}")
    html = re.sub(
        r"<script[^>]*browserfs\.min\.js[^>]*>\s*</script>",
        "",
        html,
        flags=re.IGNORECASE,
    )
    html = html.replace(cdn_prefix, "vendor/runtime/")
    html = html.replace(
        'src="vendor/runtime/pythons.js"',
        'src="vendor/runtime/pythons.js?PYGPI=vendor/pkg/"',
    )
    # Module imports resolve against the script URL, so the runtime base has to be absolute.
    html = html.replace(
        'cdn : "vendor/runtime/",',
        'cdn : new URL("vendor/runtime/", document.baseURI).href,',
    )
    payload = json.dumps(sizes, ensure_ascii=False, separators=(",", ":"))
    replacement = (
        '<script id="vj-sizes">window.__vjSizes='
        + payload
        + ";window.__vjPrefetch=false;</script>"
    )
    html2, count = SIZES_RE.subn(replacement, html, count=1)
    if count != 1:
        raise SystemExit("index.html is missing the vj-sizes script")
    html = html2.replace("<!-- vj-preload -->", PRELOAD, 1)
    return html


def assert_index(html: str) -> None:
    if re.search(r"browserfs\.min\.js", html, flags=re.IGNORECASE):
        raise SystemExit("browserfs script is still in index.html")
    if "pygame-web.github.io" in html:
        raise SystemExit("index.html still points at pygame-web.github.io")
    if "PYGPI=vendor/pkg/" not in html:
        raise SystemExit("PYGPI was not added to pythons.js")
    if "vj-boot" not in html and "vjBootStage" not in html:
        raise SystemExit("Chinese loader is missing from index.html")
    if 'src="vendor/runtime//"' in html or "cdn//" in html:
        raise SystemExit("double-slash CDN path is still present")
    for src in re.findall(r'\ssrc="([^"]+)"', html):
        if src.startswith("about:"):
            continue
        path = src.split("?", 1)[0]
        if path.startswith("https://") or path.startswith("http://"):
            raise SystemExit(f"unexpected remote script {src}")
        if "//" in path:
            raise SystemExit(f"double slash in src {src}")


def self_test() -> None:
    sample = """<html lang="zh-CN"><!-- vj-preload --><script id="vj-sizes">window.__vjSizes={};window.__vjPrefetch=false;</script><script src="https://pygame-web.github.io/cdn/0.9.3/pythons.js" type=module id="site"></script>
cdn : "https://pygame-web.github.io/cdn/0.9.3/",
function vjBootStage(msg) {}
<script src="https://pygame-web.github.io/cdn/0.9.3//browserfs.min.js"></script>
"""
    html = rewrite_index(sample, "https://pygame-web.github.io/cdn/0.9.3/", {"cpython312/main.wasm": 10})
    assert_index(html)
    if "vendor/runtime/cpython312/main.wasm" not in html:
        raise SystemExit("preload was not inserted")
    if 'new URL("vendor/runtime/", document.baseURI).href' not in html:
        raise SystemExit("runtime CDN was not made absolute")
    if '"cpython312/main.wasm":10' not in html:
        raise SystemExit("sizes were not inserted")
    print("vendor_pages self-test ok")


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        self_test()
        return
    if len(sys.argv) != 2:
        raise SystemExit("usage: vendor_pages.py build/web | --self-test")

    web = Path(sys.argv[1])
    index_path = web / "index.html"
    html = index_path.read_text(encoding="utf-8")
    match = CDN_RE.search(html)
    if not match:
        raise SystemExit("could not find pygame-web CDN version in index.html")
    version = match.group("version")
    cdn_prefix = f"https://pygame-web.github.io/cdn/{version}/"
    cdn_root = "https://pygame-web.github.io/cdn/"

    runtime = web / "vendor" / "runtime"
    for rel in RUNTIME_FILES:
        dest = runtime / rel
        print(f"fetch {cdn_prefix}{rel}")
        _get(cdn_prefix + rel, dest)

    parent = web / "vendor"
    for rel in PARENT_FILES:
        print(f"fetch {cdn_root}{rel}")
        _get(cdn_root + rel, parent / rel)

    pythons = (runtime / "pythons.js").read_text(encoding="utf-8")
    old = """    elems = url.rsplit('?',1)
    url = elems.shift()

    if (url.endsWith(module_name)) {
        url = url + (window.location.search || "?") + ( window.location.hash || "#" )
        console.log("Location of",module_name,"overrides script", old_url ,'=>', url )
    }"""
    new = """    elems = url.rsplit('?',1)
    url = elems.shift()
    var script_query = elems.length ? elems[0] : ""

    if (url.endsWith(module_name)) {
        var page_query = window.location.search || ""
        if (page_query && script_query) page_query = page_query + "&" + script_query
        else page_query = page_query || (script_query ? ("?" + script_query) : "?")
        url = url + page_query + ( window.location.hash || "#" )
        console.log("Location of",module_name,"overrides script", old_url ,'=>', url )
    }"""
    if old not in pythons:
        raise SystemExit("pythons.js query parser did not match; cannot pass PYGPI")
    (runtime / "pythons.js").write_text(pythons.replace(old, new, 1), encoding="utf-8")

    data = (runtime / "cpython312" / "main.data").read_bytes()
    wasm = (runtime / "cpython312" / "main.wasm").read_bytes()
    if not wasm.startswith(b"\x00asm"):
        raise SystemExit("main.wasm is not a wasm binary")
    if len(data) < 1_000_000:
        raise SystemExit("main.data looks truncated")

    index_url = f"{cdn_root}index-{version}-cp312.json"
    print(f"fetch {index_url}")
    index = json.loads(_get(index_url))
    wheel_rel, wheel_url = resolve_wheel(index, cdn_root, platform_tags(data))
    wheel_dest = web / "vendor" / "pkg" / wheel_rel
    print(f"fetch {wheel_url}")
    _get(wheel_url, wheel_dest)
    index["-CDN-"] = "vendor/pkg/"
    pkg_index = web / "vendor" / "pkg" / f"index-{version}-cp312.json"
    pkg_index.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sizes: dict[str, int] = {}
    for path in (web / "vendor").rglob("*"):
        if not path.is_file() or path.stat().st_size < 100_000:
            continue
        rel = path.relative_to(web / "vendor").as_posix()
        if rel.startswith("runtime/cpython312/"):
            sizes["cpython312/" + path.name] = path.stat().st_size
        else:
            sizes[path.name] = path.stat().st_size
    for archive in list(web.glob("*.tar.gz")) + list(web.glob("*.apk")):
        sizes[archive.name] = archive.stat().st_size

    html = rewrite_index(html, cdn_prefix, sizes)
    assert_index(html)
    index_path.write_text(html, encoding="utf-8")

    total = sum(path.stat().st_size for path in (web / "vendor").rglob("*") if path.is_file())
    print(f"vendored {total / (1024 * 1024):.1f} MB into {web / 'vendor'}")
    for key, size in sorted(sizes.items(), key=lambda item: -item[1]):
        print(f"  {size / (1024 * 1024):6.1f} MB  {key}")


if __name__ == "__main__":
    main()

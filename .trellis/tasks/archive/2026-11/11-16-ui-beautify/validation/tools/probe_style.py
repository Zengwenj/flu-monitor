"""A4 视觉度量探针：计算样式 + WCAG 对比度 + 关键元素位置（file:// 同源 iframe）。

与 probe_narrow.py 的分工：那边只量「有没有横向溢出」，这边量「是否可读、
是否突出」，即字号/字重/前景底色/对比度/元素纵向位置。

用法：
  python -X utf8 .tmp_a4/probe_style.py audit 360
  python -X utf8 .tmp_a4/probe_style.py audit 1280
  python -X utf8 .tmp_a4/probe_style.py json 360 .tmp_a4/style-360.json
"""
import json
import re
import subprocess
import sys
from pathlib import Path

def _find_root():
    p = Path(__file__).resolve()
    for cand in p.parents:
        if (cand / 'CONTEXT.md').exists() and (cand / 'src' / 'build_site.py').exists():
            return cand
    raise SystemExit('repo root not found from ' + str(p))


ROOT = _find_root()
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SITE = ROOT / "site"
PROBE_DIR = SITE / ".probe"

OUTER = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>outer</title>
<style>html,body{margin:0;padding:0;background:#fff}
iframe{border:0;width:__W__px;height:__H__px;display:block}</style>
</head><body><iframe id="f" src="__SRC__"></iframe>
<pre id="out">PENDING</pre>
<script>
(function(){
  var f = document.getElementById('f');
  function px(v){ var n = parseFloat(v); return isFinite(n) ? n : 0; }
  function rgba(s){
    if(!s || s === 'transparent') return [0,0,0,0];
    var m = s.match(/rgba?\\(([^)]+)\\)/);
    if(!m) return [0,0,0,0];
    var p = m[1].split(',').map(function(x){ return parseFloat(x); });
    return [p[0]||0, p[1]||0, p[2]||0, p.length > 3 ? p[3] : 1];
  }
  function effBg(el, win){
    // 逐级上溯直到不透明，按 alpha 合成（近似：从底往上叠）
    var layers = [], node = el;
    while(node && node.nodeType === 1){
      var bg = rgba(win.getComputedStyle(node).backgroundColor);
      if(bg[3] > 0){ layers.push(bg); if(bg[3] >= 0.999) break; }
      node = node.parentElement;
    }
    if(!layers.length) return [255,255,255,1];
    var acc = layers[layers.length - 1].slice();
    for(var i = layers.length - 2; i >= 0; i--){
      var t = layers[i], a = t[3];
      acc[0] = t[0]*a + acc[0]*(1-a);
      acc[1] = t[1]*a + acc[1]*(1-a);
      acc[2] = t[2]*a + acc[2]*(1-a);
      acc[3] = 1;
    }
    return acc;
  }
  function collect(){
    try{
      var win = f.contentWindow, doc = win.document, de = doc.documentElement;
      var rows = [], all = doc.body.querySelectorAll('*');
      for(var i = 0; i < all.length; i++){
        var el = all[i];
        if(/^(SCRIPT|STYLE|TEMPLATE|NOSCRIPT)$/.test(el.tagName)) continue;
        var own = '';
        for(var k = 0; k < el.childNodes.length; k++){
          var c = el.childNodes[k];
          if(c.nodeType === 3) own += c.nodeValue;
        }
        own = own.replace(/\\s+/g, ' ').trim();
        if(!own) continue;
        var cs = win.getComputedStyle(el);
        if(cs.display === 'none' || cs.visibility === 'hidden') continue;
        var fs = px(cs.fontSize);
        if(fs <= 0) continue;
        var r = el.getBoundingClientRect();
        if(r.width <= 0 && r.height <= 0) continue;
        // SVG 文本用 fill 上色，HTML 文本用 color；不区分会拿继承来的 color 假通过
        var isSvg = (el.namespaceURI && el.namespaceURI.indexOf('svg') >= 0)
                    || !!(el.closest && el.closest('svg'));
        var fg, fgsrc;
        if(isSvg){
          fg = rgba(cs.fill);
          fgsrc = 'fill';
          if(fg[3] === 0) fgsrc = 'fill-none';   // fill:none 不绘制，不计入对比度
        } else {
          fg = rgba(cs.color);
          fgsrc = 'color';
        }
        var clsTxt = (el.getAttribute && el.getAttribute('class')) || '';
        if(!clsTxt && typeof el.className === 'string') clsTxt = el.className;
        var bg = effBg(el, win);
        rows.push({
          tag: el.tagName,
          cls: clsTxt.slice(0, 46),
          txt: own.slice(0, 34),
          fs: Math.round(fs * 10) / 10,
          fw: cs.fontWeight,
          fg: fg,
          fgsrc: fgsrc,
          bg: bg,
          top: Math.round(r.top),
          left: Math.round(r.left),
          w: Math.round(r.width),
          h: Math.round(r.height)
        });
      }
      // 关键锚点位置（供首屏断言）
      function topOf(sel, idx){
        var n = doc.querySelectorAll(sel);
        if(n.length <= (idx || 0)) return null;
        return Math.round(n[idx || 0].getBoundingClientRect().top);
      }
      var info = {
        iw: win.innerWidth, sw: de.scrollWidth, sh: de.scrollHeight,
        dpr: win.devicePixelRatio,
        top: {
          h1: topOf('.wrap h1'),
          first_h2: topOf('.card h2'),
          first_big: topOf('.big'),
          second_big: topOf('.big', 1),
          first_card: topOf('.card')
        },
        cards: doc.querySelectorAll('.card').length,
        bigs: doc.querySelectorAll('.big').length,
        rows: rows
      };
      document.getElementById('out').textContent = JSON.stringify(info);
    } catch(e){
      document.getElementById('out').textContent = 'ERR:' + e.message;
    }
  }
  // 初始 about:blank 也可能 readyState=complete，必须等真实 load 并确认已渲染
  var tries = 0;
  function kick(){
    tries++;
    try {
      var doc = f.contentDocument;
      var ok = doc && doc.querySelectorAll('.card').length > 0;
      if(ok || tries > 40){ collect(); return; }
    } catch(e){}
    setTimeout(kick, 100);
  }
  f.addEventListener('load', kick);
  window.addEventListener('load', kick);
})();
</script></body></html>"""


def write_outer(width, height, page=None):
    PROBE_DIR.mkdir(exist_ok=True)
    src = (page or (SITE / "index.html")).resolve().as_uri()
    html = (OUTER.replace("__W__", str(width)).replace("__H__", str(height))
            .replace("__SRC__", src))
    p = PROBE_DIR / f"style-{width}.html"
    p.write_text(html, encoding="utf-8", newline="\n")
    return p


def dump(width, page=None, height=3400):
    outer = write_outer(width, height, page)
    out = subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--allow-file-access-from-files",
         f"--window-size={max(width, 560)},{height}",
         "--virtual-time-budget=5000", "--dump-dom", outer.as_uri()],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r'<pre id="out">(.*?)</pre>', out.stdout, re.S)
    if not m:
        print("FAIL: 未取到度量输出")
        print(out.stderr[-500:])
        raise SystemExit(1)
    raw = (m.group(1).replace("&quot;", '"').replace("&lt;", "<")
           .replace("&gt;", ">").replace("&amp;", "&"))
    if raw.startswith("ERR:"):
        print("JS FAIL:", raw[:300])
        raise SystemExit(1)
    return json.loads(raw)


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def lum(rgb):
    return 0.2126 * _lin(rgb[0]) + 0.7152 * _lin(rgb[1]) + 0.0722 * _lin(rgb[2])


def ratio(fg, bg):
    a, b = lum(fg), lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def audit(width):
    d = dump(width)
    rows = [r for r in d["rows"] if r.get("fgsrc") != "fill-none"]
    for r in rows:
        r["cr"] = round(ratio(r["fg"], r["bg"]), 2)
        r["need"] = 3.0 if (r["fs"] >= 24 or (r["fs"] >= 18.66 and int(r["fw"]) >= 700)) else 4.5
    bad = sorted([r for r in rows if r["cr"] < r["need"]], key=lambda x: x["cr"])
    small = sorted([r for r in rows if r["fs"] < 12], key=lambda x: x["fs"])
    by_fill = [r for r in rows if r.get("fgsrc") == "fill"]
    print(f"== {width}px ==  inner={d['iw']} scrollW={d['sw']} scrollH={d['sh']} "
          f"cards={d['cards']} bigs={d['bigs']}")
    print("   top:", json.dumps(d["top"], ensure_ascii=False))
    print(f"   文本节点={len(rows)}  低于 AA={len(bad)}  <12px={len(small)}  "
          f"按 fill 计={len(by_fill)}")
    if by_fill:
        worst = sorted(by_fill, key=lambda x: x["cr"])[:5]
        print("   -- SVG 文本（fill）worst 5 --")
        for r in worst:
            print(f"   {r['cr']:>5} / 需{r['need']}  {r['fs']:>5}px {r['cls'][:26]:<26} {r['txt']}")
    if bad:
        print("   -- 对比度不足（worst 18） --")
        for r in bad[:18]:
            print(f"   {r['cr']:>5} / 需{r['need']}  {r['fs']:>5}px {r['fw']:>3}  "
                  f"{r['cls'][:26]:<26} {r['txt']}")
    if small:
        print("   -- 字号 <12px --")
        for r in small[:10]:
            print(f"   {r['fs']:>5}px {r['cls'][:26]:<26} {r['txt']}")
    return d


SELFTEST = """<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="background:#fff;color:#000000">
<svg width="200" height="40" viewBox="0 0 200 40">
  <text x="0" y="20" font-size="12" fill="#000000">dark</text>
  <text x="90" y="20" font-size="12" fill="#767676">mid</text>
</svg>
</body></html>"""


def selftest():
    """探针自检：同一 color 继承下两个 fill 不同的 SVG 文本必须测得不同对比度。"""
    PROBE_DIR.mkdir(exist_ok=True)
    page = PROBE_DIR / "selftest.html"
    page.write_text(SELFTEST, encoding="utf-8", newline="\n")
    d = dump(900, page=page, height=200)
    rows = [r for r in d["rows"] if r["txt"] in ("dark", "mid")]
    if len(rows) != 2:
        print(f"SELFTEST FAIL: 期望 2 个 SVG 文本节点，实得 {len(rows)}")
        return 1
    for r in rows:
        r["cr"] = round(ratio(r["fg"], r["bg"]), 2)
    dark = next(r for r in rows if r["txt"] == "dark")
    mid = next(r for r in rows if r["txt"] == "mid")
    ok = True
    if dark.get("fgsrc") != "fill" or mid.get("fgsrc") != "fill":
        print(f"SELFTEST FAIL: fgsrc 非 fill（dark={dark.get('fgsrc')} mid={mid.get('fgsrc')}）")
        ok = False
    if dark["cr"] == mid["cr"]:
        print(f"SELFTEST FAIL: 两个 fill 测得相同对比度 {dark['cr']}（探针未读 fill）")
        ok = False
    if abs(dark["cr"] - 21.0) > 0.2:
        print(f"SELFTEST FAIL: #000000 on #fff 应为 21.0，实得 {dark['cr']}")
        ok = False
    if abs(mid["cr"] - 4.54) > 0.35:
        print(f"SELFTEST FAIL: #767676 on #fff 应约 4.54，实得 {mid['cr']}")
        ok = False
    print(f"SELFTEST {'PASS' if ok else 'FAIL'}: dark={dark['cr']} ({dark.get('fgsrc')}) "
          f"mid={mid['cr']} ({mid.get('fgsrc')})")
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "audit"
    if cmd == "--selftest":
        raise SystemExit(selftest())
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 360
    if cmd == "audit":
        audit(w)
    elif cmd == "json":
        dest = Path(sys.argv[3])
        dest.write_text(json.dumps(dump(w), ensure_ascii=False, indent=1),
                        encoding="utf-8")
        print(f"wrote {dest}")

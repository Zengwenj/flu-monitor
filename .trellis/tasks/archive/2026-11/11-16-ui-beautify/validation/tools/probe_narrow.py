"""A4 窄屏度量 / 截图（file:// 同源版）。

headless Chrome 的 --window-size 有 ~500px 下限，直接截图拿到的不是真实
360/320 布局。用同源 iframe 承载被测页（媒体查询按 iframe 宽度生效），
配合 --allow-file-access-from-files 让外层页能读 iframe 内部度量。

用法：
  python -X utf8 .tmp_a4/probe_narrow.py measure 360
  python -X utf8 .tmp_a4/probe_narrow.py shot 360 .tmp_a4/shots/x.png [height]
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
<script>
(function(){
  var f = document.getElementById('f');
  function measure(){
    try {
      var win = f.contentWindow, doc = win.document, de = doc.documentElement;
      var over = [], all = doc.body.querySelectorAll('*');
      for (var i=0;i<all.length;i++){
        var el = all[i], r = el.getBoundingClientRect();
        if (r.width>0 && r.right > de.clientWidth + 1){
          over.push({tag: el.tagName, cls: (el.className||'').toString().slice(0,44),
                     right: Math.round(r.right), w: Math.round(r.width)});
          if (over.length>14) break;
        }
      }
      document.title = 'PROBE' + JSON.stringify({iw: win.innerWidth, cw: de.clientWidth,
        sw: de.scrollWidth, sh: de.scrollHeight, bodyW: doc.body.scrollWidth, over: over});
    } catch(e) { document.title = 'PROBEERR' + e.message; }
  }
  if (f.contentDocument && f.contentDocument.readyState === 'complete') { measure(); }
  else { f.addEventListener('load', measure); }
})();
</script></body></html>"""


def write_outer(width, height, page=None):
    PROBE_DIR.mkdir(exist_ok=True)
    src = (page or (SITE / "index.html")).resolve().as_uri()
    html = (OUTER.replace("__W__", str(width)).replace("__H__", str(height))
            .replace("__SRC__", src))
    p = PROBE_DIR / f"outer-{width}.html"
    p.write_text(html, encoding="utf-8", newline="\n")
    return p


def measure(width, page=None):
    outer = write_outer(width, 2400, page)
    out = subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--allow-file-access-from-files", "--window-size=1100,2500",
         "--virtual-time-budget=4000", "--dump-dom", outer.as_uri()],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"<title>PROBE(\{.*?\})</title>", out.stdout, re.S)
    if not m:
        err = re.search(r"<title>PROBEERR(.*?)</title>", out.stdout, re.S)
        print("FAIL", err.group(1)[:300] if err else out.stderr[-300:])
        return 1
    print(json.dumps(json.loads(m.group(1).replace("&quot;", '"')),
                     ensure_ascii=False, indent=1))
    return 0


def shot(width, dest, height=2400, page=None):
    outer = write_outer(width, height, page)
    dest_abs = Path(dest).resolve()
    dest_abs.parent.mkdir(parents=True, exist_ok=True)
    # Chrome 窗口宽度有 ~560px 下限：截图会带上右侧空白画布，需按 iframe 实际宽度裁切
    chrome_w = max(width, 560)
    raw = dest_abs.with_name(dest_abs.stem + ".raw" + dest_abs.suffix)
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--allow-file-access-from-files",
         f"--window-size={chrome_w},{height}", "--virtual-time-budget=4000",
         f"--screenshot={raw}", outer.as_uri()],
        capture_output=True, text=True)
    try:
        from PIL import Image
        with Image.open(raw) as im:
            need_crop = im.width > width
            if need_crop:
                im.crop((0, 0, width, im.height)).save(dest_abs)
        if need_crop:
            raw.unlink()
        else:
            raw.replace(dest_abs)
    except ImportError:
        raw.replace(dest_abs)
    print(f"wrote {dest_abs}")



if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "measure"
    page = Path(sys.argv[5]) if len(sys.argv) > 5 else None
    if cmd == "measure":
        raise SystemExit(measure(int(sys.argv[2]), page))
    elif cmd == "shot":
        shot(int(sys.argv[2]), sys.argv[3],
             int(sys.argv[4]) if len(sys.argv) > 4 else 2400, page)

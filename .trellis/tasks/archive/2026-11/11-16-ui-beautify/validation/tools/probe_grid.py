# -*- coding: utf-8 -*-
"""A4 断点验证：比对 #default-view 在 899/900/1024/1280 下的 computed
display / grid-template-columns / 各卡片 grid-column span，确认
①<900 单列（等同现状）②≥900 双列（12 栅格 :has() 定位）③断点无半生效状态。
用法：python -X utf8 .tmp_a4\\probe_grid.py
"""
import json
import re
import subprocess
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
PROBE = SITE / ".probe"
PROBE.mkdir(parents=True, exist_ok=True)

OUTER = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>o</title>
<style>html,body{margin:0;background:#fff}iframe{border:0;width:__W__px;height:3000px;display:block}</style>
</head><body><iframe id="f" src="__SRC__"></iframe><script>
(function(){
 var f=document.getElementById('f');
 function kick(){ if(!f.contentDocument||!f.contentDocument.querySelector('.card')){return setTimeout(kick,100);} measure(); }
 function measure(){
  try{
   var d=f.contentDocument, dv=d.getElementById('default-view');
   var cs=f.contentWindow.getComputedStyle(dv);
   var cards=[].map.call(dv.querySelectorAll(':scope > .card'),function(c){
     var s=f.contentWindow.getComputedStyle(c);
     var h2=c.querySelector('h2'), sig='?';
     if(c.querySelector('.adv'))sig='sc';
     else if(c.querySelector('.hist-tbl'))sig='hist';
     else if(c.querySelector('.kv'))sig='flu';
     else if(c.querySelector('.rank'))sig='rank';
     else if(c.querySelector('.trendrow'))sig='trend';
     else if(c.querySelector('.childg'))sig='child';
     return {sig:sig,gc:s.gridColumnStart+'/'+s.gridColumnEnd,w:Math.round(c.getBoundingClientRect().width),
             top:Math.round(c.getBoundingClientRect().top)};
   });
   document.title='P'+JSON.stringify({w:f.contentWindow.innerWidth,display:cs.display,
     cols:cs.gridTemplateColumns,cards:cards});
  }catch(e){document.title='E'+e.message;}
 }
 f.addEventListener('load',kick); if(f.contentDocument&&f.contentDocument.readyState==='complete')kick();
})();
</script></body></html>"""

src = (SITE / "index.html").resolve().as_uri()
for w in (899, 900, 1024, 1280):
    p = PROBE / f"grid-{w}.html"
    p.write_text(OUTER.replace("__W__", str(w)).replace("__SRC__", src),
                 encoding="utf-8", newline="\n")
    out = subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--allow-file-access-from-files", "--window-size=1400,3200",
         "--virtual-time-budget=5000", "--dump-dom", p.as_uri()],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"<title>P(\{.*?\})</title>", out.stdout, re.S)
    if not m:
        e = re.search(r"<title>E(.*?)</title>", out.stdout, re.S)
        print(w, "FAIL", e.group(1)[:200] if e else out.stderr[-200:])
        continue
    d = json.loads(m.group(1).replace("&quot;", '"'))
    print(f"\n== {w}px == display={d['display']} cols={d['cols']}")
    for c in d["cards"]:
        print(f"   {c['sig']:6s} gc={c['gc']:8s} w={c['w']:4d} top={c['top']}")

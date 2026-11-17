"""A4 V5b 验收：搜索视图切换不泄漏（headless 驱动真实 SEARCH_JS）。

背景（A4-PLAN-01）：#default-view{display:grid} 是作者级规则，会覆盖 UA 的
[hidden]{display:none}；若缺 `#default-view[hidden]{display:none}` 守卫，
≥900px 查询其他地区后成都六卡会与查询结果同屏。本脚本在 1280px 同源
iframe 里驱动页面真实内联 JS，断言三条契约：
  A 查询非成都并显式选中候选 → #default-view computed display 为 none，
    #query-view 单独可见且非空；
  B 点「回成都」→ 默认视图恢复可见（computed display 不为 none）；
  C 已呈现查询结果时点「清空」→ 只清输入与候选，结果视图不动
    （childElementCount 不变、仍可见）。

用法：python -X utf8 .tmp_a4\\check_view_toggle.py
退出码 0=全过；1=有失败项。
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

WIDTH = 1280
HEIGHT = 1600

INNER_JS = r"""
(function(){
  var f = document.getElementById('f');
  function done(obj){
    document.getElementById('out').textContent = JSON.stringify(obj);
  }
  function visible(win, el){
    var cs = win.getComputedStyle(el);
    return cs.display !== 'none' && cs.visibility !== 'hidden';
  }
  function fire(el, type, opts){
    var o = opts || {bubbles:true, cancelable:true};
    el.dispatchEvent(type === 'mousedown' ? new MouseEvent('mousedown', o)
                                          : new Event(type, o));
  }
  function step(win){
    var doc = win.document;
    var q = doc.getElementById('q'), go = doc.getElementById('q-go'),
        clear = doc.getElementById('q-clear'), home = doc.getElementById('q-home'),
        list = doc.getElementById('q-list'), status = doc.getElementById('q-status'),
        dv = doc.getElementById('default-view'), qv = doc.getElementById('query-view');
    var R = {init_ready: !q.disabled, steps: []};
    function rec(name, ok, detail){
      R.steps.push({name: name, ok: !!ok, detail: detail});
    }
    if(!R.init_ready){ done(R); return; }

    // ---- A. 查询哈尔滨并显式选中第一个候选 ----
    q.value = '哈尔滨';
    fire(q, 'input');
    var opts = list.querySelectorAll('li.q-item');
    if(!opts.length){ rec('A-open-list', false, 'no candidates'); done(R); return; }
    fire(opts[0], 'mousedown');
    var a_hidden = dv.hidden === true;
    var a_display_none = win.getComputedStyle(dv).display === 'none';
    var a_qv_visible = qv.hidden === false && visible(win, qv) && qv.childElementCount > 0;
    rec('A-default-hidden-attr', a_hidden, 'dv.hidden=' + dv.hidden);
    rec('A-default-display-none', a_display_none,
        'computed display=' + win.getComputedStyle(dv).display);
    rec('A-query-visible-nonempty', a_qv_visible,
        'qv.hidden=' + qv.hidden + ' kids=' + qv.childElementCount);
    var a_kids = qv.childElementCount;

    // ---- B. 回成都 ----
    fire(home, 'click');
    rec('B-default-restored',
        dv.hidden === false && win.getComputedStyle(dv).display !== 'none',
        'dv.hidden=' + dv.hidden +
        ' display=' + win.getComputedStyle(dv).display);
    rec('B-query-hidden', qv.hidden === true, 'qv.hidden=' + qv.hidden);

    // ---- C. 再查询广东 → 清空不动结果 ----
    q.value = '广东';
    fire(q, 'input');
    var opts2 = list.querySelectorAll('li.q-item');
    if(opts2.length){ fire(opts2[0], 'mousedown'); }
    var c_shown = qv.hidden === false && qv.childElementCount > 0;
    var c_kids_before = qv.childElementCount;
    fire(clear, 'click');
    var c_still = qv.hidden === false && qv.childElementCount === c_kids_before
                  && visible(win, qv);
    var c_dv_still_hidden = dv.hidden === true;
    rec('C-query-shown-first', c_shown, 'kids=' + c_kids_before);
    rec('C-clear-keeps-result', c_still,
        'after clear: qv.hidden=' + qv.hidden +
        ' kids=' + qv.childElementCount + ' (before ' + c_kids_before + ')');
    rec('C-clear-keeps-default-hidden', c_dv_still_hidden, 'dv.hidden=' + dv.hidden);
    rec('C-clear-empties-input', q.value === '', 'q.value="' + q.value + '"');
    done(R);
  }
  var tries = 0;
  function kick(){
    tries++;
    try{
      var doc = f.contentDocument;
      var q = doc && doc.getElementById('q');
      var ok = q && !q.disabled && doc.querySelectorAll('.card').length > 0;
      if(ok || tries > 40){ step(f.contentWindow); return; }
    }catch(e){}
    setTimeout(kick, 100);
  }
  f.addEventListener('load', kick);
  window.addEventListener('load', kick);
})();
"""

OUTER_TMPL = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>outer</title>
<style>html,body{margin:0;padding:0;background:#fff}
iframe{border:0;width:%dpx;height:%dpx;display:block}</style>
</head><body><iframe id="f" src="%s"></iframe>
<pre id="out">PENDING</pre>
<script>%s</script></body></html>"""


def run():
    PROBE_DIR.mkdir(exist_ok=True)
    src = (SITE / "index.html").resolve().as_uri()
    outer = PROBE_DIR / "toggle-1280.html"
    outer.write_text(OUTER_TMPL % (WIDTH, HEIGHT, src, INNER_JS),
                     encoding="utf-8", newline="\n")
    out = subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--allow-file-access-from-files",
         f"--window-size={WIDTH},{HEIGHT}",
         "--virtual-time-budget=6000", "--dump-dom", outer.as_uri()],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r'<pre id="out">(.*?)</pre>', out.stdout, re.S)
    if not m:
        print("FAIL: 未取到输出（页面未就绪或脚本异常）")
        print(out.stderr[-400:])
        return 1
    raw = (m.group(1).replace("&quot;", '"').replace("&lt;", "<")
           .replace("&gt;", ">").replace("&amp;", "&"))
    if raw == "PENDING" or raw.startswith("ERR"):
        print("FAIL: 输出未就绪 ->", raw[:200])
        return 1
    data = json.loads(raw)
    print(f"init_ready={data.get('init_ready')}")
    fails = 0
    for s in data.get("steps", []):
        mark = "PASS" if s["ok"] else "FAIL"
        if not s["ok"]:
            fails += 1
        print(f"  [{mark}] {s['name']}  ({s['detail']})")
    if not data.get("steps"):
        print("FAIL: 无断言执行")
        return 1
    print("RESULT:", "PASS" if fails == 0 and data.get("init_ready") else "FAIL")
    return 0 if fails == 0 and data.get("init_ready") else 1


if __name__ == "__main__":
    sys.exit(run())

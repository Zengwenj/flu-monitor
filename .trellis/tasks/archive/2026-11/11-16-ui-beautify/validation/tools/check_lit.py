# -*- coding: utf-8 -*-
"""A4 验收 V4（Step 8 完整版）：字面保全 + 结构断言 + 夹具三态 +
SVG 片段 hex 计数对照 before-product + st 类源码断言 + sc 卡实时态一致性。

用法：python -X utf8 .tmp_a4\\check_lit.py
退出码 0=全部通过；1=有失败项。
"""
import re
import sys
from pathlib import Path

def _find_root():
    p = Path(__file__).resolve()
    for cand in p.parents:
        if (cand / 'CONTEXT.md').exists() and (cand / 'src' / 'build_site.py').exists():
            return cand
    raise SystemExit('repo root not found from ' + str(p))


ROOT = _find_root()
PAGE = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
SRC = (ROOT / "src" / "build_site.py").read_text(encoding="utf-8")
BEFORE = (Path(__file__).resolve().parent / "before-product.html").read_text(encoding="utf-8")

fails = []


def chk(ok, label):
    print(f"{'OK ' if ok else 'FAIL'} {label}")
    if not ok:
        fails.append(label)


# ---- 1) 产物字面（Q5/Q1/Q10/Q11 契约）----
LITS = [
    "min-height:44px",
    "font-size:16px",
    "focus-visible",
    '  <div class="card">',
    '<div id="default-view">\n  <div class="banner">',
    "已恢复成都默认",
    "请从列表中选择",
    "未找到匹配的省市",
    "个单位",
]
for lit in LITS:
    chk(lit in PAGE, f"字面存在: {lit[:44]!r}")

# ---- 2) 源码字面（_sc_body empty 态文案，A4-PLAN-09：对象=源码）----
chk("官方分级未获取 · 状态未知" in SRC, "源码字面存在: '官方分级未获取 · 状态未知'")

# ---- 3) 脚手架 id ----
for i in ["q", "q-list", "q-status", "query-view", "default-view"]:
    chk(f'id="{i}"' in PAGE, f"id 存在: {i}")

# ---- 4) 计数断言 ----
n_sc = PAGE.count("四川官方流感分级")
chk(n_sc == 1, f"四川官方流感分级 计数==1（实际 {n_sc}）")
m = re.search(r'<div class="big">([\d.]+)<span class="unit">', PAGE)
chk(bool(m), f".big 数值+unit 结构字面（goldstein={m.group(1) if m else '无'}）")
n_script = len(re.findall(r"<script(?:\s|>)", PAGE))
chk(n_script == 3, f"script 段数==3（实际 {n_script}）")
n_rail = PAGE.count('<div class="rail"')
chk(n_rail == 1, f"rail 恰 1（实际 {n_rail}，实施前应为 0）")

# ---- 5) SVG 锚 hex 存在（属性选择器锚点，<style> 内选择器不算）----
for h in ["#999", "#6b7280", "#e5e7eb"]:
    chk(h in PAGE, f"SVG 锚 hex 存在: {h}")

# ---- 6) SVG 片段 hex 计数对照 before-product（A4-PLAN-08）----
def svg_hex_counts(text):
    frag = "".join(re.findall(r"<svg\b.*?</svg>", text, re.S))
    out = {}
    for h in ["#c0392b", "#7f8c8d", "#8e44ad", "#1f4e79", "#999",
              "#6b7280", "#e5e7eb", "#eef0f2", "#4b5563", "#f3f4f6"]:
        out[h] = frag.count(h)
    return out


b_cnt, a_cnt = svg_hex_counts(BEFORE), svg_hex_counts(PAGE)
for h in b_cnt:
    chk(b_cnt[h] == a_cnt[h],
        f"SVG 片段 hex 计数相等: {h}（before={b_cnt[h]} after={a_cnt[h]}）")

# ---- 7) st 四态类名定义在源码（CSS_THEME）----
for c in ["st-ok", "st-wait", "st-fail", "st-unknown"]:
    chk(f".tag.{c}" in SRC or f".q-chip.{c}" in SRC, f"源码含状态类定义: {c}")

# ---- 8) sc 卡 .tag 类与 sichuan_block() 实时态一致 ----
sys.path.insert(0, str(ROOT / "src"))
import build_site  # noqa: E402

live = build_site.sichuan_block()
if live.get("state") == "ok":
    line = live.get("line", "")
    expect = "st-ok" if line.startswith("数据正常") else (
        "st-wait" if "本月待更新" in line else "st-unknown")
else:
    expect = "st-unknown"
chk(f'class="tag {expect}"' in PAGE,
    f"sc 卡 .tag 实时态一致（sichuan_block → {expect}）")

# ---- 9) 夹具三态（Step 5.4，A4-PLAN-06/09）----
fix_now = {"state": "ok", "level": "IV", "level_name": "活跃期",
           "year": "2026", "month": "11",
           "line": "数据正常 · 11月 · 来源发布 2026-11-05",
           "advice": ["通风"], "source_url": "https://example.invalid/"}
fix_old = dict(fix_now, month="10", line="10月已确认等级 · 本月待更新")
fix_empty = {"state": "empty"}

h = build_site._sc_body(fix_now)
chk('class="tag st-ok"' in h and '<div class="rail"' in h
    and "st-wait" not in h and "st-unknown" not in h,
    "夹具当月: st-ok + rail，无 st-wait/st-unknown")
h = build_site._sc_body(fix_old)
chk('class="tag st-wait"' in h and '<div class="rail"' in h
    and 'class="tag st-ok"' not in h,
    "夹具过月: st-wait + rail，无 st-ok")
h = build_site._sc_body(fix_empty)
chk('class="tag st-unknown"' in h and "nodata" in h
    and "官方分级未获取 · 状态未知" in h and '<div class="rail"' not in h,
    "夹具 empty: st-unknown + nodata + 官方文案，无 rail")

# ---- 10) 四禁串不在产物 ----
for b in ["<script src", "fetch(", "@import", "url(http"]:
    chk(b not in PAGE, f"禁串不在: {b!r}")

print(f"\n== {len(fails)} 项失败 == {fails}")
sys.exit(1 if fails else 0)

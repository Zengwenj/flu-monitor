# -*- coding: utf-8 -*-
"""渲染分块证据页 site/index.html（M3b 阶段二仪表盘）。

契约（M2 r3 + M3b design）：
- 方式 A：字符串插值直接渲染进 HTML（无独立 JSON、无 fetch），file:// 可离线打开
- 零外部依赖：趋势图为纯 Python 生成的内联 SVG（无 JS/Canvas/图表库）
- 分块不合成总分（D14）；状态文案只用枚举；口径标注齐全（D15）
- 页面取数规则 3：流感数值/指数取最新 status=ok 行；更晚失败行 → 失败横幅
"""
import csv
import math
import sys
from datetime import date, timedelta
from html import escape as _esc
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from compute_index import child_rank, pathogen_ranking, pathogen_trend  # noqa: E402

FLU_CSV = ROOT / "data" / "flu_south.csv"
SC_CSV = ROOT / "data" / "sichuan_monthly.csv"
RUN_STATUS = ROOT / "data" / "run_status.json"
OUT = ROOT / "site" / "index.html"


def run_banner(local: bool = False) -> str:
    """M4b/momus B1：读本次运行状态——chinacdc 源本次 skipped/failed 时显诚实横幅，
    避免"旧数据被标数据正常"。
    本地模式（--local）忽略该文件：bot 回写会把云端上一轮状态带回仓库，
    本地构建若读它会误报/漏报（trellis-check 中等项）。"""
    import json
    if local or not RUN_STATUS.exists():
        return ""
    try:
        st = json.loads(RUN_STATUS.read_text(encoding="utf-8"))
    except Exception:
        return ""
    srcs = st.get("sources", {})
    names = {"flu_south": "流感周报", "sentinel": "哨点周报"}
    bad = [names[k] for k in names if srcs.get(k) in ("skipped", "failed")]
    if not bad:
        return ""
    return (f'<div class="banner">⚠ 本次更新未能获取最新数据（{"、".join(bad)}） · '
            f'当前展示为上次成功的存量数据 · 运行时间 {st.get("run_at", "?")}</div>')

SC_LV4_ADVICE = [
    "（1）勤洗手，打喷嚏或咳嗽时用纸巾或袖子遮住口、鼻；",
    "（2）避免带病上课上班；",
    "（3）尽量避免接触流感样病例患者；如需接触应佩戴口罩；",
    "（4）鼓励市民接种流感疫苗；",
    "（5）加强学校托幼机构因病缺勤监测和晨午检。",
]
LEVEL_ADVICE = {"IV": SC_LV4_ADVICE, "V": [
    "（1）保持室内空气流通，注意环境卫生；",
    "（2）保持充足睡眠，健康饮食，坚持适量运动；",
    "（3）注意天气变化，添减衣物，避免着凉。",
]}


def read_csv(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ---------------- A1b：南方片流感视图（数据契约） ----------------

def _iso_week_valid(y: int, w: int) -> bool:
    try:
        date.fromisocalendar(y, w, 1)
        return True
    except ValueError:
        return False


def _num(s):
    """转有限非负 float；非法/NaN/inf/负数 → None。"""
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v) or v < 0:
        return None
    return v


def valid_url(s):
    """仅 http/https 且带主机名才算有效来源链接。"""
    if not s:
        return None
    try:
        u = urlsplit(s)
    except ValueError:
        return None
    if u.scheme not in ("http", "https") or not u.hostname:
        return None
    return u


def build_flu_view(rows: list) -> dict:
    """把 flu_south.csv 行规范化为周键视图（A1b design §2）。

    - 周键 (iso_year, iso_week) 经 ISO 历法校验（2025W53 这类非法周只计数不建模）。
    - 同周多条 ok：数值解析全部有效且数值一致 → 合并为一个点，代表行按
      (fetched_at, source_pubdate, source_url, week_start, 三个数值原文) 取最大；
      任何一条解析失败或数值不一致 → 该周 conflict（"数据异常"，绝不静默择值）。
    - 仅 fail 行的周 state=fail；ok 行永不被 fail 行覆盖。
    - anchor=有 ok 行的最大周键（数值过滤之前锚定：锚周异常不回退到更早周）。
    """
    grouped, invalid = {}, 0
    for r in rows or []:
        try:
            y, w = int(r.get("iso_year", "")), int(r.get("iso_week", ""))
            monday = date.fromisocalendar(y, w, 1)
        except (ValueError, TypeError):
            invalid += 1
            continue
        grouped.setdefault((y, w), []).append(r)

    def rep_key(r):
        return (r.get("fetched_at") or "", r.get("source_pubdate") or "",
                r.get("source_url") or "", r.get("week_start") or "",
                r.get("goldstein_index") or "", r.get("south_ili_pct") or "",
                r.get("south_flu_positive_pct") or "")

    weeks, anchor = {}, None
    for k, grp in grouped.items():
        y, w = k
        oks = [r for r in grp if (r.get("status") or "") == "ok"]
        monday = date.fromisocalendar(y, w, 1)
        wk = {"has_ok": bool(oks), "state": "fail", "monday": monday,
              "vals": None, "disp": None, "rep": None,
              "week_start_mismatch": False,
              "pub": "", "url": None, "fetched_at": ""}
        if oks:
            if anchor is None or k > anchor:
                anchor = k
            parsed = []
            for r in oks:
                g = _num(r.get("goldstein_index"))
                ili = _num(r.get("south_ili_pct"))
                pos = _num(r.get("south_flu_positive_pct"))
                if (g is None or g > 10000 or ili is None or ili > 100
                        or pos is None or pos > 100):
                    parsed.append(None)
                else:
                    parsed.append((g, ili, pos))
            rep = max(oks, key=rep_key)
            wk["rep"], wk["pub"], wk["url"] = rep, rep.get("source_pubdate") or "", rep.get("source_url") or None
            wk["fetched_at"] = rep.get("fetched_at") or ""
            if all(p is not None for p in parsed) and all(
                    p == parsed[0] for p in parsed):
                wk["state"] = "ok"
                wk["vals"] = parsed[0]
                wk["disp"] = (rep.get("goldstein_index") or "",
                              rep.get("south_ili_pct") or "",
                              rep.get("south_flu_positive_pct") or "")
                wk["week_start_mismatch"] = (rep.get("week_start") or "") != monday.isoformat()
            else:
                wk["state"] = "conflict"
        weeks[k] = wk
    return {"weeks": weeks, "anchor": anchor, "invalid_week_rows": invalid}


def flu_block(model: dict = None) -> dict:
    """流感卡数据：环比按 ISO 周一差精确 7 天（不借更早周），历史失败不再误报横幅。"""
    v = model if model is not None else build_flu_view(read_csv(FLU_CSV))
    if v["anchor"] is None:
        return {"state": "empty", "banner": "",
                "invalid_rows": v["invalid_week_rows"],
                "empty_note": "存在未成功获取的记录" if v["weeks"] else ""}
    y, w = v["anchor"]
    wk = v["weeks"][(y, w)]
    later_bad = [k for k, x in v["weeks"].items()
                 if k > (y, w) and x["state"] in ("fail", "conflict")]
    rep = wk.get("rep") or {}
    src = rep.get("source_url") or ""
    if wk["state"] != "ok":  # 锚周有 ok 行但数值异常：不静默回退
        # S4-B04：异常锚周绝不被称为"上次成功数据"；更晚失败仍如实提示
        banner = (f"最新一期获取失败 · {y}年第{w}周数据异常，未采用 · 请人工核对官网"
                  if later_bad else "")
        return {"state": "ok", "banner": banner, "anchor_bad": True,
                "invalid_rows": v["invalid_week_rows"],
                "iso_year": str(y), "iso_week": str(w),
                "goldstein_index": "—", "south_ili_pct": "—",
                "south_flu_positive_pct": "—", "source_url": src,
                "source_pubdate": rep.get("source_pubdate") or "未提供",
                "line": f"{y}年第{w}周 · 数据异常，未采用 · 请人工核对官网",
                "mom": f"{y}年第{w}周数据异常，未比较"}
    prev_monday = wk["monday"] - timedelta(days=7)
    pk = (prev_monday.isocalendar()[0], prev_monday.isocalendar()[1])
    prev = v["weeks"].get(pk)
    if prev is None or prev["state"] == "fail":
        mom = "较上周 · 上周数据缺失"
    elif prev["state"] == "conflict":
        mom = "较上周 · 上周数据异常"
    else:
        g_prev, g_now = prev["vals"][0], wk["vals"][0]
        mom = f"较上周 {'↑' if g_now > g_prev else ('↓' if g_now < g_prev else '→')}"
    g_s, ili_s, pos_s = wk["disp"]
    return {"state": "ok", "banner": (f"最新一期获取失败 · 显示上次成功数据（{y}年第{w}周）"
                                      if later_bad else ""),
            "invalid_rows": v["invalid_week_rows"],
            "iso_year": str(y), "iso_week": str(w), "goldstein_index": g_s,
            "south_ili_pct": ili_s, "south_flu_positive_pct": pos_s,
            "source_url": src,
            "source_pubdate": rep.get("source_pubdate") or "未提供",
            "week_start": rep.get("week_start") or "",
            "fetched_at": rep.get("fetched_at") or "",
            "line": f"数据正常 · {y}年第{w}周 · 来源发布 {rep.get('source_pubdate') or '未提供'}",
            "mom": mom}


def history_data(v: dict) -> dict:
    """A1b design §4：锚周所在自然年 + 前三年窗口的年度序列与覆盖统计。"""
    if v["anchor"] is None:
        return {"empty": True, "anchor": None, "years": [], "single_year": False}
    ay, aw = v["anchor"]
    years = []
    for yy in range(ay, ay - 4, -1):
        yw = {k: x for k, x in v["weeks"].items() if k[0] == yy}
        if not yw:
            continue
        ok_wks = sorted(k[1] for k, x in yw.items() if x["state"] == "ok")
        ok_set = set(ok_wks)
        gaps = 0
        if len(ok_wks) > 1:
            gaps = sum(1 for k in range(ok_wks[0] + 1, ok_wks[-1])
                       if _iso_week_valid(yy, k) and k not in ok_set)
        ank = yw.get((yy, aw))
        note = None
        if ank is None and aw == 53 and not _iso_week_valid(yy, 53):
            note = "no_w53"
        years.append({
            "year": yy, "n_ok": len(ok_wks),
            "first": ok_wks[0] if ok_wks else None,
            "last": ok_wks[-1] if ok_wks else None,
            "gaps": gaps,
            "points": [(k, yw[(yy, k)]["vals"][0]) for k in ok_wks],
            "anchor_state": ank["state"] if ank else None,
            "anchor_val": ank["vals"][0] if ank and ank["state"] == "ok" else None,
            "anchor_disp": ank["disp"] if ank and ank["state"] == "ok" else None,
            "anchor_meta": ({"url": ank["url"], "pub": ank["pub"],
                             "ws": (ank.get("rep") or {}).get("week_start", "")}
                            if ank and ank.get("rep") else None),
            "anchor_note": note})
    return {"empty": False, "anchor": v["anchor"], "years": years,
            "single_year": len(years) == 1}


# ---------------- A1b：历年同周对比渲染（design §5 视觉规格） ----------------

def nice_axis(maxval: float) -> tuple:
    """统一纵轴 1-2-5 刻度，返回 (step, n, top)。

    target=max(10, maxval*1.06)；step 按升序遍历 {1,2,5}×10^k（k 从 0 起），
    取首个使 ceil(target/step)≤5 者；n=ceil(target/step)；top=n*step。"""
    if not math.isfinite(maxval) or maxval < 0:
        maxval = 0.0
    target = max(10.0, maxval * 1.06)
    k = 0
    while True:
        for m in (1, 2, 5):
            step = m * 10 ** k
            n = math.ceil(target / step - 1e-9)  # 容忍浮点误差
            if n <= 5:
                return step, n, n * step
        k += 1


# 相对锚年的年度样式：线型/粗细/标记形状三者共同区分，不单靠颜色。
# size 为标记整体宽度（SVG 单位）：历史年 7 大、锚年 5.5 小并压在最上层，
# 两年数值近似（如 82.27 与 75.72）时仍可辨认。颜色只区分年度，不是风险色。
_HIST_STYLES = {
    0: dict(color="#c0392b", width=2.6, dash="", cap="butt",
            shape="circle", size=5.5, halo=True),
    1: dict(color="#1f4e79", width=1.6, dash="", cap="butt",
            shape="square", size=7, halo=False),
    2: dict(color="#4f86b8", width=1.6, dash="6 3", cap="butt",
            shape="diamond", size=7, halo=False),
    3: dict(color="#6b7280", width=2, dash="1 4", cap="round",
            shape="triangle", size=7, halo=False),
}


def _hist_plot_years(h: dict) -> list:
    """入图年份：至少有一个有效点（降序，锚年在前）。"""
    return [y for y in h.get("years", []) if y["n_ok"] > 0]


def _hist_table_years(h: dict) -> list:
    """表行年份：窗口内有记录的年份全部列出（S4-B03：仅异常/仅失败的年份
    也不静默丢弃，行内如实标注"该周缺失/数据异常，未采用"）。"""
    return list(h.get("years", []))


def _hist_segments(points: list) -> list:
    """按相邻整数周切段：周序差恰为 1 才连线，缺口处断开（不跨接、不补零）。"""
    segs, cur = [], []
    for w, g in points:
        if cur and w - cur[-1][0] != 1:
            segs.append(cur)
            cur = []
        cur.append((w, g))
    if cur:
        segs.append(cur)
    return segs


def _hist_marker(shape: str, x: float, y: float, size: float, color: str,
                 halo: bool = False) -> str:
    half = size / 2
    st = ' stroke="#fff" stroke-width="1.5"' if halo else ""
    if shape == "circle":
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{half:g}" fill="{color}"{st}/>'
    if shape == "square":
        return (f'<rect x="{x - half:.1f}" y="{y - half:.1f}" width="{size:g}" '
                f'height="{size:g}" fill="{color}"{st}/>')
    if shape == "diamond":
        d = size * 0.72
        pts = f"{x:.1f},{y - d:.1f} {x + d:.1f},{y:.1f} {x:.1f},{y + d:.1f} {x - d:.1f},{y:.1f}"
    else:  # triangle：外接圆圆心即视觉中心
        r = size * 0.62
        pts = f"{x:.1f},{y - r:.1f} {x + r * 0.866:.1f},{y + r / 2:.1f} {x - r * 0.866:.1f},{y + r / 2:.1f}"
    return f'<polygon points="{pts}" fill="{color}"{st}/>'


def _hist_swatch(st: dict) -> str:
    """表内线样小样（兼作图例）：与图中同线型、同标记。"""
    dash = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
    return (f'<svg width="28" height="12" viewBox="0 0 28 12" aria-hidden="true" focusable="false">'
            f'<line x1="1" y1="6" x2="27" y2="6" stroke="{st["color"]}" '
            f'stroke-width="{st["width"]:g}" stroke-linecap="{st["cap"]}"{dash}/>'
            f'{_hist_marker(st["shape"], 14, 6, st["size"], st["color"], st["halo"])}</svg>')


def _hist_axis_label(v) -> str:
    # ≥1000 用 k 缩写，保证左边距 26 内放得下（真实数据 top=800 不触发）
    return f"{v / 1000:g}k" if v >= 1000 else f"{v:g}"


def _hist_nodata(h: dict) -> str:
    extra = ""
    if h.get("anchor"):  # 有锚周但无任何有效点：只能是锚周数据异常，不误称等待回补
        y, w = h["anchor"]
        extra = f" · {y}年第{w}周数据异常，未采用"
    return f'<div class="nodata">暂无可用的南方片历史数据{extra}</div>'


def _hist_src_cell(meta, yy: int, aw: int) -> str:
    url = ((meta or {}).get("url") or "").strip()
    if valid_url(url):
        return (f'<td><a href="{_esc(url, quote=True)}" target="_blank" rel="noopener" '
                f'aria-label="{yy}年第{aw}周周报原文">当期</a></td>')
    return '<td class="hist-na">来源未提供</td>'


def history_svg(h: dict) -> str:
    """多年度同周曲线：横轴固定 ISO 周 1–53，纵轴各年统一（从 0 起的 1-2-5 刻度）。
    历史年画全年，本年只画到锚周；缺口断线，孤立点按年度形状单独标出。"""
    plot = _hist_plot_years(h)
    if h.get("empty") or not plot:
        return ""
    ay, aw = h["anchor"]
    W, H, L, R, T, B = 280, 192, 26, 10, 16, 26
    pw, ph = W - L - R, H - T - B          # 绘图区 244×150
    base = T + ph
    step, n, top = nice_axis(max(g for y in plot for _, g in y["points"]))

    def X(w):
        return L + (w - 1) / 52 * pw

    def Y(v):  # 夹在 [T+1, base-1]：防描边裁切，不改变表中的真实值（含真 0）
        return min(max(T + (1 - v / top) * ph, T + 1), base - 1)

    xa = X(aw)
    bg, grid, axis, ylab, xlab, lines, marks = [], [], [], [], [], [], []
    if aw < 53:  # 灰底：本年尚无观测的周次
        bg.append(f'<rect x="{xa:.1f}" y="{T}" width="{L + pw - xa:.1f}" height="{ph}" fill="#f3f4f6"/>')
    for k in range(n + 1):
        val = k * step
        yy = T + (1 - val / top) * ph
        ylab.append(f'<text x="{L - 3}" y="{yy + 4:.1f}" font-size="12" text-anchor="end" '
                    f'fill="#6b7280">{_hist_axis_label(val)}</text>')
        if 0 < k < n:
            grid.append(f'<line x1="{L}" y1="{yy:.1f}" x2="{L + pw}" y2="{yy:.1f}" stroke="#e5e7eb"/>')
    for w in (1, 14, 27, 40, 53):
        x = X(w)
        if w not in (1, 53):
            grid.append(f'<line x1="{x:.1f}" y1="{T}" x2="{x:.1f}" y2="{base}" stroke="#eef0f2"/>')
        axis.append(f'<line x1="{x:.1f}" y1="{base}" x2="{x:.1f}" y2="{base + 3}" stroke="#9ca3af"/>')
        anc = "start" if w == 1 else ("end" if w == 53 else "middle")
        xlab.append(f'<text x="{x:.1f}" y="{base + 17}" font-size="12" text-anchor="{anc}" '
                    f'fill="#6b7280">{w}</text>')
    axis.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{base}" stroke="#d1d5db"/>')
    axis.append(f'<line x1="{L}" y1="{base}" x2="{L + pw}" y2="{base}" stroke="#9ca3af"/>')
    # 锚周竖虚线 + “第W周”：靠右时右对齐向内，靠左时左对齐，不越界
    right = xa > L + pw / 2
    axis.append(f'<line x1="{xa:.1f}" y1="{T}" x2="{xa:.1f}" y2="{base}" stroke="#9ca3af" '
                f'stroke-dasharray="3 3"/>')
    axis.append(f'<text x="{xa + (-4 if right else 4):.1f}" y="12" font-size="12" '
                f'text-anchor="{"end" if right else "start"}" fill="#4b5563">第{aw}周</text>')

    for y in reversed(plot):  # 先历史后锚年：锚年线与标记压在最上层
        st = _HIST_STYLES[ay - y["year"]]
        stroke = (f'stroke="{st["color"]}" stroke-width="{st["width"]:g}" '
                  f'stroke-linejoin="round" stroke-linecap="{st["cap"]}"'
                  + (f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""))
        for seg in _hist_segments(y["points"]):
            if len(seg) >= 2:
                pts = " ".join(f"{X(w):.1f},{Y(g):.1f}" for w, g in seg)
                lines.append(f'<polyline fill="none" {stroke} points="{pts}"/>')
            elif seg[0][0] != aw:  # 孤立点（锚周点由下方锚周标记负责）
                marks.append(_hist_marker(st["shape"], X(seg[0][0]), Y(seg[0][1]),
                                          st["size"], st["color"], st["halo"]))
        if y["anchor_val"] is not None:
            marks.append(_hist_marker(st["shape"], xa, Y(y["anchor_val"]),
                                      st["size"], st["color"], st["halo"]))

    vals = "；".join(f'{y["year"]}年 {_esc((y["anchor_disp"][0] or "").strip())}'
                     for y in plot if y["anchor_state"] == "ok" and y["anchor_disp"])
    desc = ("横轴为 ISO 周序号 1 至 53，纵轴为 Goldstein 相对强度指数，各年统一。"
            + (f"第{aw}周：{vals}。" if vals else f"第{aw}周：本年无可用数值。")
            + "本年曲线截至最新已收录周，往年为该年已收录周的曲线，均不是预测。")
    return (f'<svg viewBox="0 0 {W} {H}" style="display:block;width:100%;max-width:{W}px;height:auto" '
            f'role="img" aria-labelledby="hist-title hist-desc" focusable="false">'
            f'<title id="hist-title">南方片流感指数 · 历年同周对比</title>'
            f'<desc id="hist-desc">{desc}</desc>'
            + "".join(bg + grid + axis + ylab + lines + marks + xlab) + '</svg>')


def history_table(h: dict) -> str:
    """同周对照表（图的文字替代，兼作图例）：6 列；锚年行灰底；
    表包在唯一横向滚动容器内，窄屏只表格滚动、页面不溢出。"""
    plot = _hist_plot_years(h)
    if h.get("empty") or not plot:
        return _hist_nodata(h)
    ay, aw = h["anchor"]
    cur = next(y for y in h["years"] if y["year"] == ay)
    hist_only = [y for y in plot if y["year"] != ay]

    notice = ""
    if not hist_only:
        notice = f"仅 {ay} 年有有效观测，暂无可对比的往年同周数据"
    elif not any(y["anchor_val"] is not None for y in hist_only):
        notice = "往年该周暂无可用观测"

    body, mismatch = [], False
    for y in _hist_table_years(h):
        yy, off = y["year"], ay - y["year"]
        st, meta, state = _HIST_STYLES[off], y["anchor_meta"], y["anchor_state"]
        subs = (f'<span class="hist-sub2">截至第{aw}周</span>'
                f'<span class="hist-sub2">不是预测</span>' if off == 0 else "")
        subs += f'<span class="hist-sub2">已收录{y["n_ok"]}周</span>'
        if y["gaps"]:
            subs += f'<span class="hist-sub2">内部缺{y["gaps"]}周</span>'
        th = (f'<th scope="row"><span class="hist-yl">{_hist_swatch(st)}'
              f'<span>{yy}</span></span>{subs}</th>')
        if y["anchor_note"] == "no_w53" or not _iso_week_valid(yy, aw):
            tds = '<td colspan="5" class="hist-na">该年无第53周</td>'
        else:
            d = date.fromisocalendar(yy, aw, 1)
            ds = d.strftime("%m-%d") if d.year == yy else d.isoformat()
            if meta is not None and (meta.get("ws") or "").strip() != d.isoformat():
                ds += "*"
                mismatch = True
            wcell = f"<td>{ds}</td>"
            if state == "ok" and y["anchor_disp"]:
                g, ili, pos = (_esc((s or "").strip()) for s in y["anchor_disp"])
                tds = (wcell + f'<td class="hist-g">{g}</td><td>{ili}</td><td>{pos}</td>'
                       + _hist_src_cell(meta, yy, aw))
            else:
                txt = "该周缺失" if state in (None, "fail") else "数据异常，未采用"
                if meta is not None:  # 冲突周仍有代表行：保留来源核对入口
                    tds = (wcell + f'<td colspan="3" class="hist-na">{txt}</td>'
                           + _hist_src_cell(meta, yy, aw))
                else:
                    tds = wcell + f'<td colspan="4" class="hist-na">{txt}</td>'
        body.append(f'<tr class="hist-cur">{th}{tds}</tr>' if off == 0 else f"<tr>{th}{tds}</tr>")

    cmeta = cur["anchor_meta"] or {}
    pub = _esc((cmeta.get("pub") or "").strip() or "未提供")
    latest = (f"最新已收录：{ay}年第{aw}周（来源发布 {pub}）" if cur["anchor_state"] == "ok"
              else f"最新一期：{ay}年第{aw}周数据异常，未采用（来源发布 {pub}）")
    foot = f"{latest} · 表中周起日按 ISO 周序对齐，逐年略有错位；灰底行为本年（截至第{aw}周）"
    if mismatch:
        foot += "<br>* 原周起标注缺失或与 ISO 周序不一致，已按 ISO 周序对齐"
    return (
        (f'<div class="hist-notice">{notice}</div>' if notice else "")
        + '<div class="hist-scroll-hint">↔ 左右滑动查看完整对照</div>'
        + '<div class="hist-scroll" tabindex="0" role="region" '
          'aria-label="南方片历年同周对照表，可左右滑动查看">'
        + f'<table class="hist-tbl"><caption>{ay}年第{aw}周与往年同周对照</caption>'
        + '<thead><tr><th scope="col">年份</th><th scope="col">ISO周起</th>'
          '<th scope="col">指数<span class="hist-sub2">Goldstein</span></th>'
          '<th scope="col">ILI%</th><th scope="col">阳性率%</th>'
          '<th scope="col">来源</th></tr></thead>'
        + f'<tbody>{"".join(body)}</tbody></table></div>'
        + f'<div class="src hist-note">{foot}</div>')


def history_block(model: dict = None) -> str:
    """「南方片流感指数 · 历年同周对比」卡正文：曲线 + 图外说明 + 同周表 + 来源。"""
    v = model if model is not None else build_flu_view(read_csv(FLU_CSV))
    h = history_data(v)
    plot = _hist_plot_years(h)
    if h["empty"] or not plot:
        return _hist_nodata(h)
    ay, aw = h["anchor"]
    has_hist = any(y["year"] != ay for y in plot)
    years = "、".join(str(y["year"]) for y in plot)
    total = sum(y["n_ok"] for y in plot)
    y0, w0 = min((y["year"], y["first"]) for y in plot)
    y1, w1 = max((y["year"], y["last"]) for y in plot)
    kind = "历史年为该年已收录周的曲线，本年截至最新已收录周，不是预测" if has_hist else "本年截至最新已收录周，不是预测"
    band = "；灰底为本年尚无观测的周次" if aw < 53 else ""
    return (
        f'<div class="hist-sub">南方片 · Goldstein 相对强度指数（ILI%×流感阳性率）'
        f'· {years} 年 · 按 ISO 周序号对齐</div>'
        + history_svg(h)
        + f'<div class="src hist-note">指数为相对强度（南方片哨点口径）· {kind}{band}。</div>'
        + '<div class="src hist-note">横轴为 ISO 周序号 1–53，刻度约对应 1 月初、4 月初、'
          '7 月初、10 月初、年末；纵轴各年统一，低位波动请看下表。</div>'
        + history_table(h)
        + f'<div class="src hist-note">来源：国家流感中心《中国流感监测周报》（南方片）· '
          f'图中共 {total} 周有效数据（{y0}年第{w0}周–{y1}年第{w1}周）· '
          f'指数为相对强度，非风险等级、感染概率或百分位。</div>')


def sichuan_block() -> dict:
    rows = read_csv(SC_CSV)
    if not rows:
        return {"state": "empty"}
    latest = max(rows, key=lambda r: (int(r["year"]), int(r["month"])))
    today = date.today()
    if (today.year, today.month) == (int(latest["year"]), int(latest["month"])):
        line = f"数据正常 · {latest['month']}月 · 来源发布 {latest['source_pubdate']}"
    else:
        line = f"{latest['month']}月已确认等级 · 本月待更新"
    advice = LEVEL_ADVICE.get(latest["level"], [])
    return {"state": "ok", **latest, "line": line, "advice": advice}


# ---------------- M3b：SVG 趋势图 ----------------

def _adjacent_week(a: int, b: int) -> bool:
    """线性周序 a→b 是否相邻（跨年 W52→次年W1 连续；lin=y*53+wk）。"""
    ya, wa = divmod(a, 53)
    yb, wb = divmod(b, 53)
    if ya == yb:
        return wb - wa == 1
    if yb - ya == 1 and wb == 1 and wa >= 51:  # 年末（W51/52）→ 次年 W1 连续
        return True
    return False


def svg_sparkline(series: list, w: int = 300, h: int = 70,
                  color: str = "#3a6ea5") -> str:
    """series: [((year,week), pct)] 升序。生成内联 SVG 折线（无 JS/无外部依赖）。
    周序跳变（缺周）→ 分段 polyline 断点，不画 0。"""
    if not series:
        return '<div class="nodata">暂无数据</div>'
    lin = [(y * 53 + wk, v) for (y, wk), v in series]  # 线性周序
    xmin, xmax = lin[0][0], lin[-1][0]
    ymax = max(v for _, v in lin)
    top = max(ymax * 1.15, 1.0)
    pad_l, pad_r, pad_t, pad_b = 4, 30, 8, 12
    iw, ih = w - pad_l - pad_r, h - pad_t - pad_b

    def X(x): return pad_l + (x - xmin) / max(xmax - xmin, 1) * iw

    def Y(v): return pad_t + (1 - v / top) * ih

    segs, cur = [], [lin[0]]
    for a, b in zip(lin, lin[1:]):
        if not _adjacent_week(a[0], b[0]):  # 缺周断点（跨年 W52→W1 视为连续）
            segs.append(cur)
            cur = []
        cur.append(b)
    segs.append(cur)
    polys = "".join(
        f'<polyline points="{" ".join(f"{X(x):.1f},{Y(v):.1f}" for x, v in seg)}" '
        f'fill="none" stroke="{color}" stroke-width="1.6"/>' for seg in segs)
    lastx, lastv = lin[-1]
    y0, w0 = divmod(xmin, 53)
    y1, w1 = divmod(xmax, 53)
    return (f'<svg viewBox="0 0 {w} {h}" style="width:100%;max-width:{w}px" role="img">'
            f'{polys}'
            f'<circle cx="{X(lastx):.1f}" cy="{Y(lastv):.1f}" r="2.6" fill="{color}"/>'
            f'<text x="{X(lastx)+5:.1f}" y="{Y(lastv)+4:.1f}" font-size="11" fill="{color}">{lastv:g}%</text>'
            f'<text x="0" y="{h-2}" font-size="9" fill="#999">{y0}W{w0}</text>'
            f'<text x="{w-34}" y="{h-2}" font-size="9" fill="#999">{y1}W{w1}</text>'
            f'</svg>')


# ---------------- M3b：新块渲染 ----------------

def trend_block() -> str:
    names = [("流感病毒", "#c0392b"), ("新型冠状病毒", "#7f8c8d"), ("呼吸道合胞病毒", "#8e44ad")]
    parts = []
    for name, color in names:
        parts.append(f'<div class="trendrow"><span class="tlabel">{name}</span>'
                     f'{svg_sparkline(pathogen_trend(name), color=color)}</div>')
    return ("".join(parts) +
            '<div class="src">本年度（含开办期以来）全国哨点门急诊阳性率逐周折线 · '
            '缺周为断点不画 0 · X 轴为周次</div>')


def ranking_block() -> str:
    rk = pathogen_ranking()
    if not rk.get("available"):
        return f'<div class="big">—</div><div class="meta"><span class="tag">{rk.get("reason","暂无数据")}</span></div>'
    rows = "".join(
        f'<tr><td>{r["pathogen"]}</td><td class="num">{r["pct"]}%</td>'
        f'<td class="num">{r["arrow"]}</td></tr>' for r in rk["rows"])
    return (f'<table class="rank"><tr><th>病原体</th><th>门急诊阳性率</th><th>较上周</th></tr>{rows}</table>'
            f'<div class="meta"><span class="tag">数据正常 · 第{rk["week"]}周 · 全国哨点口径</span></div>'
            f'<div class="src">按门急诊流感样病例阳性率降序 · 箭头为较上周方向（百分点变化见数据表）</div>')


def child_block() -> str:
    c = child_rank()
    if not c.get("available"):
        return (f'<div class="big">？</div><div class="meta"><span class="tag">'
                f'{c.get("reason", "官方分级未获取 · 状态未知")}'
                f'（第{c.get("week","?")}周）</span></div>')
    groups = "".join(
        f'<div class="childg"><b>{cat}</b><span class="chain">{" ＞ ".join(trio)}</span></div>'
        for cat, trio in c["groups"].items())
    return (f'{groups}'
            f'<div class="meta"><span class="tag">数据正常 · 第{c["week"]}周 · 全国哨点门急诊</span>'
            f'<span class="tag">排序非数值</span></div>'
            f'<div class="src">来源：中疾控哨点监测周报表3 · "＞"为检出率位次 · 非成都口径</div>')


TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>成都 · 呼吸道防护参考</title>
<style>
  body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;margin:0;background:#f5f6f8;color:#222}}
  .wrap{{max-width:640px;margin:0 auto;padding:16px}}
  h1{{font-size:20px;margin:16px 0 4px}}
  .sub{{font-size:12px;color:#888;margin-bottom:12px}}
  .banner{{background:#fff3cd;border:1px solid #ffc107;color:#856404;padding:8px 12px;border-radius:8px;font-size:14px;margin-bottom:12px}}
  .card{{background:#fff;border-radius:12px;padding:16px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
  .card h2{{font-size:15px;margin:0 0 8px;color:#555}}
  .big{{font-size:34px;font-weight:700}}
  .unit{{font-size:13px;color:#888;font-weight:400}}
  .kv{{display:flex;flex-wrap:wrap;gap:6px 18px;margin-top:8px;font-size:14px}}
  .kv b{{font-size:18px}}
  .meta{{margin-top:10px;font-size:12px;color:#999}}
  .tag{{display:inline-block;font-size:11px;padding:2px 8px;border-radius:10px;background:#eef4ff;color:#3a6ea5;margin-right:6px}}
  .adv{{margin:8px 0 0;padding:0 0 0 18px;font-size:13px;color:#444;line-height:1.7}}
  .src{{font-size:12px;color:#999;margin-top:8px}}
  .rank{{width:100%;border-collapse:collapse;font-size:14px}}
  .rank th,.rank td{{padding:4px 6px;border-bottom:1px solid #eee;text-align:left}}
  .rank th{{font-size:12px;color:#888;font-weight:400}}
  .rank .num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
  .trendrow{{display:flex;align-items:center;gap:8px;margin:6px 0}}
  .tlabel{{width:72px;font-size:13px;color:#444;flex:none}}
  .childg{{margin:8px 0;font-size:14px}}
  .childg b{{display:inline-block;min-width:64px;color:#555;font-size:13px}}
  .chain{{color:#222}}
  .nodata{{color:#999;font-size:13px;padding:8px 0}}
  .foot{{font-size:11px;color:#aaa;margin:16px 0;line-height:1.6}}
  .hist-sub{{font-size:12px;color:#888;margin:0 0 8px;line-height:1.6}}
  .hist-note{{margin-top:6px;line-height:1.6}}
  .hist-notice{{font-size:13px;color:#8a6d1f;background:#fff8e6;border-left:3px solid #e0b33c;padding:6px 10px;border-radius:4px;margin:8px 0}}
  .hist-scroll-hint{{display:none;font-size:11px;color:#999;margin:6px 0 2px}}
  .hist-scroll{{width:100%;max-width:100%;overflow-x:auto;outline:none}}
  .hist-scroll:focus-visible{{box-shadow:0 0 0 2px #3a6ea5;border-radius:4px}}
  .hist-tbl{{min-width:340px;width:100%;border-collapse:collapse;font-size:12px;margin-top:4px}}
  .hist-tbl caption{{caption-side:top;text-align:left;font-size:11px;color:#888;padding:0 0 6px}}
  .hist-tbl th,.hist-tbl td{{padding:5px 6px;border-bottom:1px solid #eee;text-align:left;white-space:nowrap;font-weight:400}}
  .hist-tbl thead th{{font-size:11px;color:#888;border-bottom:1px solid #e5e7eb}}
  .hist-tbl tbody th{{color:#333}}
  .hist-tbl td{{font-variant-numeric:tabular-nums}}
  .hist-tbl .hist-g{{font-weight:700;color:#222}}
  .hist-tbl .hist-na{{color:#999}}
  .hist-tbl tbody tr.hist-cur{{background:#f6f7f9}}
  .hist-yl{{display:inline-flex;align-items:center;gap:5px}}
  .hist-sub2{{display:block;font-size:11px;color:#999;font-weight:400;margin-top:1px}}
  .hist-tbl thead .hist-sub2{{display:inline;margin-left:3px}}
  @media (max-width:420px){{ .hist-scroll-hint{{display:block}} }}
</style>
</head>
<body>
<div class="wrap">
  <h1>成都 · 呼吸道防护参考</h1>
  <div class="sub">分块证据 · 各自口径 · 不合成总分</div>
  {run_banner}
  {banner}
  <div class="card">
    <h2>四川官方流感分级（月度 · 成都=平原区）</h2>
    {sc_body}
  </div>
  <div class="card">
    <h2>南方片流感趋势（周度）</h2>
    {flu_body}
  </div>
  <div class="card">
    <h2>南方片流感指数 · 历年同周对比</h2>
    {hist_body}
  </div>
  <div class="card">
    <h2>全国多病原活跃度排行（周度）</h2>
    {rank_body}
  </div>
  <div class="card">
    <h2>流感 / 新冠 / RSV 趋势（周度 · 本年度）</h2>
    {trend_body}
  </div>
  <div class="card">
    <h2>儿童分龄高发前三（周度）</h2>
    {child_body}
  </div>
  <div class="foot">
    口径说明：四川分级为省疾控平原区（月度）；流感指数为南方片哨点（周度）；多病原排行/趋势/儿童卡均为
    全国哨点口径（非成都实测）。排序为名称非数值；箭头仅表较上周方向；Goldstein 指数为相对强度指数
    （ILI%×阳性率），非人群感染率。
    据中疾控《版权与免责声明》注明：稿件来源：中国疾病预防控制中心；WHO FluNet 数据为国家层面公开数据。
    页面生成时间：{gen} · 数据以官方发布为准。
  </div>
</div>
</body>
</html>
"""


def flu_body_html(flu: dict) -> str:
    """流感卡正文（S4-B01/B02）：动态内容全转义、URL 白名单、无效周次计数上屏。"""
    n_bad = flu.get("invalid_rows") or 0
    note = (f'<span class="tag">已忽略 {n_bad} 条无效周次记录</span>'
            if n_bad else "")
    src = flu.get("source_url") or ""
    u = valid_url(src)
    link = (f'<a href="{_esc(src, quote=True)}" target="_blank" rel="noopener">当期文章</a>'
            if u else "来源链接未提供")
    if flu.get("anchor_bad"):
        return f"""
    <div class="big">—<span class="unit"> 数据异常，未采用</span></div>
    <div class="kv"><span>{_esc(flu.get('iso_year',''))}年第<b>{_esc(flu.get('iso_week',''))}</b>周</span></div>
    <div class="meta"><span class="tag">{_esc(flu.get('line',''))}</span><span class="tag">{_esc(flu.get('mom',''))}</span>{note}</div>
    <div class="src">来源：国家流感中心《中国流感监测周报》 {link}</div>"""
    if flu["state"] == "ok":
        return f"""
    <div class="big">{_esc(flu.get('goldstein_index',''))}<span class="unit"> Goldstein 指数（相对强度）</span></div>
    <div class="kv">
      <span>ILI% <b>{_esc(flu.get('south_ili_pct',''))}%</b></span>
      <span>流感阳性率 <b>{_esc(flu.get('south_flu_positive_pct',''))}%</b></span>
      <span>{_esc(flu.get('iso_year',''))}年第<b>{_esc(flu.get('iso_week',''))}</b>周</span>
    </div>
    <div class="meta"><span class="tag">{_esc(flu.get('line',''))}</span><span class="tag">{_esc(flu.get('mom',''))}</span>{note}</div>
    <div class="src">来源：国家流感中心《中国流感监测周报》 {link}</div>"""
    if flu.get("empty_note"):
        return f"""<div class="big">—</div><div class="meta"><span class="tag">暂无可用数据 · 存在未成功获取的记录 · 请运行更新</span>{note}</div>"""
    return f"""<div class="big">—</div><div class="meta"><span class="tag">暂无数据 · 请运行更新</span>{note}</div>"""


def render() -> None:
    model = build_flu_view(read_csv(FLU_CSV))  # 一次读取：流感卡与历史卡共用同一规范化视图
    flu = flu_block(model)
    sc = sichuan_block()

    flu_body = flu_body_html(flu)

    if sc["state"] == "ok":
        advice = "".join(f"<li>{a}</li>" for a in sc["advice"])
        sc_body = f"""
    <div class="big">{sc['level']} 级 · {sc['level_name']}<span class="unit">（{sc['year']}年{sc['month']}月）</span></div>
    <div class="meta"><span class="tag">{sc['line']}</span><span class="tag">省级官方分级</span></div>
    <ol class="adv">{advice}</ol>
    <div class="src">防控建议为官方原文：四川省疾控"流感指数分级标准表" {sc['level']} 级 · <a href="{sc['source_url']}" target="_blank">当期发布</a></div>"""
    else:
        sc_body = """<div class="big">？</div><div class="meta"><span class="tag">官方分级未获取 · 状态未知</span></div>"""

    banner_html = (f'<div class="banner">⚠ {flu["banner"]}</div>'
                   if flu.get("banner") else "")
    html = TPL.format(run_banner=run_banner(local="--local" in sys.argv),
                      banner=banner_html, flu_body=flu_body,
                      hist_body=history_block(model),
                      sc_body=sc_body, rank_body=ranking_block(),
                      trend_body=trend_block(), child_body=child_block(),
                      gen=date.today().isoformat())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"已生成 {OUT}")


if __name__ == "__main__":
    render()

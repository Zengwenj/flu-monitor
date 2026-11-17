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
import os
import sys
from datetime import date, timedelta
from html import escape as _esc
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from compute_index import child_rank, pathogen_ranking, pathogen_trend  # noqa: E402

FLU_CSV = ROOT / "data" / "flu_south.csv"
FLU_NORTH_CSV = ROOT / "data" / "flu_north.csv"
HLJ_FLU_CSV = ROOT / "data" / "heilongjiang_flu.csv"
HLJ_SENT_CSV = ROOT / "data" / "heilongjiang_sentinel.csv"
RANK_CSV = ROOT / "data" / "sentinel_rank.csv"
CHANGES_LOG = ROOT / "data" / "changes.log"
SC_CSV = ROOT / "data" / "sichuan_monthly.csv"
RUN_STATUS = ROOT / "data" / "run_status.json"
RUN_STATUS_V2 = 2  # A2 design §4：v2 运行状态 schema 版本（--run-status 显式传入）
OUT = ROOT / "site" / "index.html"  # A2 搜索版：单页

# A2 design §2.1/§5：三个流感产品的字段映射与口径文案（默认南方，兼容旧调用）。
FLU_REGIONS = {
    "south": {"csv": FLU_CSV, "ili": "south_ili_pct", "pos": "south_flu_positive_pct",
              "area": "南方片", "rank_category": "南方省份",
              "source_label": "国家流感中心《中国流感监测周报》"},
    "north": {"csv": FLU_NORTH_CSV, "ili": "north_ili_pct", "pos": "north_flu_positive_pct",
              "area": "北方片", "rank_category": "北方省份",
              "source_label": "国家流感中心《中国流感监测周报》（北方片）"},
    "heilongjiang": {"csv": HLJ_FLU_CSV, "ili": "ili_pct", "pos": "flu_positive_pct",
                     "area": "黑龙江", "rank_category": "北方省份",
                     "source_label": "黑龙江省疾病预防控制中心《黑龙江省流感监测周报》"},
}


SRC_NAMES = {"flu_south": "流感周报（南方）", "flu_north": "流感周报（北方）",
             "heilongjiang_flu": "黑龙江流感周报",
             "heilongjiang_sentinel": "黑龙江哨点周报",
             "sentinel": "全国哨点周报", "flunet": "WHO FluNet"}


def _status_of(src):
    """兼容 v1（字符串）与 v2（对象）。返回 (status, 明细)。"""
    if isinstance(src, dict):
        return src.get("status"), {k: v for k, v in src.items() if k != "status"}
    return src, {}


# 各页相关数据源（复核 IMP-04：按页只显示该页卡片实际依赖的源，缺键按 unknown 提示）
# 依据卡片契约逐卡核对：flunet_china.csv 当前不渲染任何卡片（仅页脚提及），
# 故不列入任何页面的相关源；黑龙江页无北方片指数卡（只有北方片名称背景卡=哨点源）；
# A2 搜索版：单页发布，运行状态横幅只按首页相关源过滤。
PAGE_SOURCES = {
    "index": ({"flu_south", "sentinel"}, {"south"}),
}
COMPUTE_NAMES = {"south": "南方片指数", "north": "北方片指数",
                 "heilongjiang": "黑龙江指数"}


def run_banner(local: bool = False, run_id: str = None, page: str = "index",
               status=None) -> str:
    """运行状态横幅（A2 design §4：v2 本轮 / v1 历史 / local 无状态须注明）。

    - status=None：local 构建且未提供显式状态 → 注明「未提供本次运行记录」；
      云端无状态文件 → 空串（旧页面行为）。
    - v2（schema=2）：run_id 匹配才是"本轮"；不匹配标历史运行，不称本次。
      只显示与 page 相关的采集源与计算目标；相关键缺失按 unknown 提示（不静默）。
    - v1（旧扁平结构）：只能当历史运行信息，标其 run_at。
    - 坏 JSON：不作为成功，也不能凭空断定失败，按未知处理。
    """
    import json
    if status is None:
        path = RUN_STATUS
        if local:
            return ('<div class="banner">ℹ 本地构建 · 未提供本次运行记录 · '
                    '页面按各源存量数据展示</div>')
        if not path.exists():
            return ""
        try:
            status = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            status = "bad"
    if status == "bad":
        return ('<div class="banner">⚠ 运行状态文件无法解析 · '
                '当前页面数据按存量展示，未确认本轮采集结果</div>')
    st = status
    srcs = st.get("sources") or {}
    rel_fetch, rel_compute = PAGE_SOURCES.get(page, PAGE_SOURCES["index"])
    if st.get("schema") == 2:
        this_run = (run_id is not None and st.get("run_id") == run_id)
        failed, skipped, unknown = [], [], []
        for k in sorted(rel_fetch):
            if k not in srcs:
                unknown.append(SRC_NAMES.get(k, k))  # 缺键=unknown，不静默（IMP-04）
                continue
            status_v, _ = _status_of(srcs[k])
            name = SRC_NAMES.get(k, k)
            if status_v == "failed":
                failed.append(name)
            elif status_v == "skipped":
                skipped.append(name)
            elif status_v != "ok":
                unknown.append(name)
        comp = st.get("compute") or {}
        comp_failed, comp_skipped, comp_unknown = [], [], []
        for t in sorted(rel_compute):
            name = COMPUTE_NAMES.get(t, t)
            raw = comp.get(t)
            if not isinstance(raw, dict) or raw.get("status") is None:
                comp_unknown.append(name)
            elif raw.get("status") == "failed":
                comp_failed.append(name)
            elif raw.get("status") == "skipped":
                comp_skipped.append(name)  # 复核 03：skipped≠unknown，四态分列
            elif raw.get("status") != "ok":
                comp_unknown.append(name)
        parts = []
        if failed:
            parts.append(f'本次未能获取最新数据（{"、".join(failed)}）')
        if skipped:
            parts.append(f'本次未执行获取（{"、".join(skipped)}）')
        if unknown:
            parts.append(f'状态未知（{"、".join(unknown)}）')
        if comp_failed:
            parts.append(f'指数计算未完成（{"、".join(comp_failed)}）')
        if comp_skipped:
            parts.append(f'本次未执行指数计算（{"、".join(comp_skipped)}）')
        if comp_unknown:
            parts.append(f'指数计算状态未知（{"、".join(comp_unknown)}）')
        if not parts:
            return ""
        # 不再用整轮 complete 追加“未全部完成”：构建时读到的必是采集阶段快照
        # （complete 恒为 false），该后缀会把正常部分失败误报成整轮未完成；
        # 采集/计算的真实状态已由上方分列文案表达（复核 IMP-04）。
        head = "本次更新" if this_run else "历史运行（非本轮）"
        when = st.get("finished_at") or st.get("started_at") or "?"
        return (f'<div class="banner">⚠ {head} · {" · ".join(parts)} · '
                f'当前展示为各卡最新成功数据 · 运行时间 {when}</div>')
    # v1：历史运行信息
    bad = [SRC_NAMES.get(k, k) for k, v in srcs.items()
           if _status_of(v)[0] in ("failed", "skipped")]
    if not bad:
        return ""
    return (f'<div class="banner">⚠ 上次运行未能获取最新数据（{"、".join(bad)}） · '
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


def build_flu_view(rows: list, ili_field: str = "south_ili_pct",
                   pos_field: str = "south_flu_positive_pct") -> dict:
    """把流感 CSV 行规范化为周键视图（A1b design §2；A2 起按产品字段映射参数化）。

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
                r.get("goldstein_index") or "", r.get(ili_field) or "",
                r.get(pos_field) or "")

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
                ili = _num(r.get(ili_field))
                pos = _num(r.get(pos_field))
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
                              rep.get(ili_field) or "",
                              rep.get(pos_field) or "")
                wk["week_start_mismatch"] = (rep.get("week_start") or "") != monday.isoformat()
            else:
                wk["state"] = "conflict"
        weeks[k] = wk
    return {"weeks": weeks, "anchor": anchor, "invalid_week_rows": invalid}


def flu_block(model: dict = None, region: str = "south") -> dict:
    """流感卡数据：环比按 ISO 周一差精确 7 天（不借更早周），历史失败不再误报横幅。

    A2：按 region（south/north/heilongjiang）取字段映射与口径文案；
    输出键沿用该产品的字段名（south 仍为 south_ili_pct/south_flu_positive_pct）。
    """
    spec = FLU_REGIONS[region]
    ili_f, pos_f = spec["ili"], spec["pos"]
    v = model if model is not None else build_flu_view(read_csv(spec["csv"]), ili_f, pos_f)
    common = {"invalid_rows": v["invalid_week_rows"], "area": spec["area"],
              "ili_field": ili_f, "pos_field": pos_f,
              "source_label": spec["source_label"]}
    if v["anchor"] is None:
        return {"state": "empty", "banner": "", **common,
                "never_collected": not v["weeks"],
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
        return {"state": "ok", "banner": banner, "anchor_bad": True, **common,
                "iso_year": str(y), "iso_week": str(w),
                "goldstein_index": "—", ili_f: "—", pos_f: "—", "source_url": src,
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
            **common,
            "iso_year": str(y), "iso_week": str(w), "goldstein_index": g_s,
            ili_f: ili_s, pos_f: pos_s,
            "source_url": src,
            "source_pubdate": rep.get("source_pubdate") or "未提供",
            "week_start": rep.get("week_start") or "",
            "fetched_at": rep.get("fetched_at") or "",
            "sample_count": rep.get("sample_count") or "",
            "positive_count": rep.get("positive_count") or "",
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


def _hist_nodata(h: dict, area: str = "南方片") -> str:
    extra = ""
    if h.get("anchor"):  # 有锚周但无任何有效点：只能是锚周数据异常，不误称等待回补
        y, w = h["anchor"]
        extra = f" · {y}年第{w}周数据异常，未采用"
    return f'<div class="nodata">暂无可用的{_esc(area)}历史数据{extra}</div>'


def _hist_src_cell(meta, yy: int, aw: int) -> str:
    url = ((meta or {}).get("url") or "").strip()
    if valid_url(url):
        return (f'<td><a href="{_esc(url, quote=True)}" target="_blank" rel="noopener" '
                f'aria-label="{yy}年第{aw}周周报原文">当期</a></td>')
    return '<td class="hist-na">来源未提供</td>'


def history_svg(h: dict, area: str = "南方片") -> str:
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
            f'<title id="hist-title">{_esc(area)}流感指数 · 历年同周对比</title>'
            f'<desc id="hist-desc">{desc}</desc>'
            + "".join(bg + grid + axis + ylab + lines + marks + xlab) + '</svg>')


def history_table(h: dict, area: str = "南方片") -> str:
    """同周对照表（图的文字替代，兼作图例）：6 列；锚年行灰底；
    表包在唯一横向滚动容器内，窄屏只表格滚动、页面不溢出。"""
    plot = _hist_plot_years(h)
    if h.get("empty") or not plot:
        return _hist_nodata(h, area)
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
          f'aria-label="{_esc(area)}历年同周对照表，可左右滑动查看">'
        + f'<table class="hist-tbl"><caption>{ay}年第{aw}周与往年同周对照</caption>'
        + '<thead><tr><th scope="col">年份</th><th scope="col">ISO周起</th>'
          '<th scope="col">指数<span class="hist-sub2">Goldstein</span></th>'
          '<th scope="col">ILI%</th><th scope="col">阳性率%</th>'
          '<th scope="col">来源</th></tr></thead>'
        + f'<tbody>{"".join(body)}</tbody></table></div>'
        + f'<div class="src hist-note">{foot}</div>')


def history_block(model: dict = None, area: str = "南方片", source_label: str = None) -> str:
    """「{area}流感指数 · 历年同周对比」卡正文：曲线 + 图外说明 + 同周表 + 来源。"""
    v = model if model is not None else build_flu_view(read_csv(FLU_CSV))
    h = history_data(v)
    plot = _hist_plot_years(h)
    if h["empty"] or not plot:
        return _hist_nodata(h, area)
    ay, aw = h["anchor"]
    has_hist = any(y["year"] != ay for y in plot)
    years = "、".join(str(y["year"]) for y in plot)
    total = sum(y["n_ok"] for y in plot)
    y0, w0 = min((y["year"], y["first"]) for y in plot)
    y1, w1 = max((y["year"], y["last"]) for y in plot)
    kind = "历史年为该年已收录周的曲线，本年截至最新已收录周，不是预测" if has_hist else "本年截至最新已收录周，不是预测"
    band = "；灰底为本年尚无观测的周次" if aw < 53 else ""
    return (
        f'<div class="hist-sub">{_esc(area)} · Goldstein 相对强度指数（ILI%×流感阳性率）'
        f'· {years} 年 · 按 ISO 周序号对齐</div>'
        + history_svg(h, area)
        + f'<div class="src hist-note">指数为相对强度（{_esc(area)}哨点口径）· {kind}{band}。</div>'
        + '<div class="src hist-note">横轴为 ISO 周序号 1–53，刻度约对应 1 月初、4 月初、'
          '7 月初、10 月初、年末；纵轴各年统一，低位波动请看下表。</div>'
        + history_table(h, area)
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


# ---------------- A2：多页导航、片区名称卡、地方卡 ----------------

SETTINGS = [("门急诊", "门急诊"), ("住院", "住院")]


def _card(title: str, body: str) -> str:
    return f'  <div class="card">\n    <h2>{title}</h2>\n    {body}\n  </div>'


def rank_gap_cause(y, w) -> str:
    """B2：该周排名缺口在本工具侧的已知原因（读 data/changes.log 的 ranks 行）。

    只复述本工具解析/入库环节的记录，不断言官方原因；无记录返回空串。
    兼容 4 列历史契约（ts/周次/项/说明）与 5 列现行契约（ts/周次/项/旧/新）。
    """
    try:
        with CHANGES_LOG.open(encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return ""
    want = f"{y}W{w}"
    note = ""
    for line in lines:
        cols = line.split("\t")
        if len(cols) < 3 or cols[1] != want or cols[2] != "ranks":
            continue
        note = (cols[4] if len(cols) >= 5 else cols[3]).strip()
    if not note:
        return ""
    if "合并" in note:
        return "该期为月度合并版，表2/3归属周次不明"
    if "行数" in note or "版式" in note:
        return "该期表2版式差异，解析未取得"
    return note


def region_rank_block(category: str, area: str) -> str:
    """片区前三名（仅名称，无百分比）：门急诊与住院两组都必须出现。

    数据源 data/sentinel_rank.csv 的 dimension=region 行；官方只给名称次序，
    因此不排序、不补百分比；缺任一组即如实标"本工具未取得该组"。

    复核 IMP-07 修正（round-2）：
    - 官方"排名缺失"占位行的真实格式是 category=全部、setting=全部、
      status=rank_unavailable（fetch_sentinel.py:307-311）——占位行必须参与
      本组锚周判断，否则最新周占位会被过滤掉、静默回退旧周充数；
    - 门急诊/住院各自独立锚定本组最新周（含占位行），某组最新周无排名时
      如实标"本工具未取得该周前三名排名"，不写"官方未提供"（超出证据）；
    - 同组同周重复行必须全部一致，冲突判"数据异常，未采用"（不按行序取值）；
    - 两组各自保留当期来源链接（可能不同周），不再只显示第一组的；
    - 来源更正：sentinel_rank 来自中疾控《全国急性呼吸道传染病哨点监测情况》
      表2/表3（fetch_sentinel.py 抓取），不是国家流感中心流感监测周报。
    """
    rows = read_csv(RANK_CSV)
    # 占位行（category=全部/setting=全部）与该片区具体行都算候选：
    # 占位行代表"该周官方排名整体缺失"，必须能把锚周顶到最新
    cand = [r for r in rows if (r.get("dimension") or "") == "region"
            and (r.get("category") or "") in (category, "全部")]
    head = (f'<div class="meta"><span class="tag">'
            f'{_esc(area)}前三名 · 仅列名称，无百分比</span></div>')
    if not cand:
        return ('<div class="big nodata">—</div><div class="meta">'
                f'<span class="tag">本工具未取得{_esc(area)}前三名记录</span></div>'
                '<div class="src">官方周报给名称次序、不给百分比，不可用于定量比较。</div>')
    groups = []
    for setting, _label in SETTINGS:
        # 全局占位行（setting=全部）对本组同样生效
        srows = [r for r in cand if (r.get("setting") or "") in (setting, "全部")]
        if not srows:
            groups.append(f'<div class="childg"><b>{_esc(setting)}</b>'
                          '<span class="nodata">本工具未取得该组</span></div>')
            continue
        try:
            weeks = sorted({(int(r["iso_year"]), int(r["iso_week"])) for r in srows})
            target = weeks[-1]  # 本组独立最新周（不回退到旧周充数）
            tr = [r for r in srows
                  if (int(r["iso_year"]), int(r["iso_week"])) == target]
        except (KeyError, ValueError):
            groups.append(f'<div class="childg"><b>{_esc(setting)}</b>'
                          '<span class="nodata">数据异常（周次不可解析，未采用）</span></div>')
            continue
        y, w = target
        # 同周重复行一致性：任一字段不一致 = 冲突，不按行序任选（IMP-07）
        keys = {(r.get("rank1", ""), r.get("rank2", ""), r.get("rank3", ""),
                 r.get("status", "")) for r in tr}
        if len(keys) > 1:
            groups.append(f'<div class="childg"><b>{_esc(setting)}</b>'
                          f'<span class="nodata">{y}年第{w}周记录重复且不一致，'
                          '数据异常未采用</span></div>')
            continue
        r = tr[0]
        if r.get("status") == "ok" and (r.get("rank1") or r.get("rank2") or r.get("rank3")):
            names = " ＞ ".join(x for x in (r.get("rank1"), r.get("rank2"),
                                            r.get("rank3")) if x)
            link = _src_link(r.get("source_url"))
            groups.append(f'<div class="childg"><b>{_esc(setting)}</b>'
                          f'<span class="chain">{_esc(names)}</span>'
                          f'<span class="meta">{y}年第{w}周</span>{link}</div>')
        else:
            # 只陈述本工具侧事实，不断言官方原因（IMP-07 round-2）
            # B2：若 changes.log 有该周记录，附上本工具侧的具体原因（月度合并版 / 版式差异）
            cause = rank_gap_cause(y, w)
            detail = f"（{_esc(cause)}）" if cause else ""
            groups.append(f'<div class="childg"><b>{_esc(setting)}</b>'
                          f'<span class="nodata">本工具未取得{y}年第{w}周前三名排名{detail}</span></div>')
    return (head + "".join(groups)
            + '<div class="meta"><span class="tag">片区哨点 · 两组各自最新周</span>'
              '<span class="tag">排序非数值</span></div>'
            + f'<div class="src">来源：中国疾控中心《全国急性呼吸道传染病哨点监测情况》'
              f'表2（{_esc(area)}名称次序，各组链接为其当期文章）'
              ' · "＞"为检出率位次，仅列名称。</div>')


def _src_link(url: str) -> str:
    """当期文章链接（URL 白名单校验，非法则文字提示）。"""
    if not url:
        return ""
    if valid_url(url):
        return (f' <a href="{_esc(url, quote=True)}" target="_blank" '
                'rel="noopener">当期文章</a>')
    return ' <span class="unit">来源链接未提供</span>'


def hlj_sentinel_block() -> str:
    """黑龙江 B2 当期部分观测：官方正文公布的样本构成与前几位病原阳性率。

    只展示官方正文明确写出的项，不补 11 病原、不跨样本混算、不生成趋势。
    """
    rows = [r for r in read_csv(HLJ_SENT_CSV) if (r.get("status") or "") == "ok"]
    if not rows:
        return ('<div class="big">—</div><div class="meta">'
                '<span class="tag">本工具未取得黑龙江哨点监测记录</span></div>'
                '<div class="src">官方正文以文字与图片给出部分病原结果，本工具只转写文字部分。</div>')
    try:
        y, w = max((int(r["iso_year"]), int(r["iso_week"])) for r in rows)
    except (KeyError, ValueError):
        y, w = None, None
    cur = [r for r in rows if str(r.get("iso_year")) == str(y) and str(r.get("iso_week")) == str(w)]
    groups = []
    for setting, _label in SETTINGS:
        grp = [r for r in cur if (r.get("setting") or "") == setting]
        if not grp:
            groups.append(f'<div class="childg"><b>{_esc(setting)}</b>'
                          '<span class="nodata">本期未公布该组文字结果</span></div>')
            continue
        try:
            grp.sort(key=lambda r: -float(r.get("positive_pct") or 0))
        except ValueError:
            pass
        chains = " · ".join(
            f'{_esc(r.get("pathogen") or "")} {_esc(r.get("positive_pct") or "")}%' for r in grp)
        n = grp[0].get("sample_count") or ""
        tot = grp[0].get("total_samples") or ""
        cap = f'（标本 {_esc(n)} 份 / 共 {_esc(tot)} 份）' if n and tot else ""
        groups.append(f'<div class="childg"><b>{_esc(setting)}</b>'
                      f'<span class="chain">{chains}</span>'
                      f'<span class="unit">{cap}</span></div>')
    rep = cur[0] if cur else {}
    u = valid_url(rep.get("source_url") or "")
    link = (f'<a href="{_esc(rep.get("source_url") or "", quote=True)}" '
            'target="_blank" rel="noopener">当期文章</a>' if u else "来源链接未提供")
    when = f'{y}年第{w}周' if y is not None else ""
    return ("".join(groups)
            + f'<div class="meta"><span class="tag">{_esc(when)} · 官方正文部分观测</span>'
              '<span class="tag">非完整病原表</span></div>'
            + f'<div class="src">来源：黑龙江省疾病预防控制中心《急性呼吸道传染病哨点监测周报》'
              f'{link} · 官方正文只列部分病原，未提及不等于 0，本工具不补全。</div>')


def chongqing_block() -> str:
    """重庆：官方入口卡。本工具不转载其正文/数值/图，也不把南方片数值当作重庆实测。"""
    url = "https://www.cqcdc.org/index.php?a=lists&catid=209"
    return ('<div class="meta"><span class="tag">官方来源已核实 · 本工具未转成数值</span></div>'
            '<div class="kv"><span>重庆市疾控中心 · 流感/呼吸道传染病信息列表</span></div>'
            f'<div class="src">请前往官方页面查看：'
            f'<a href="{_esc(url, quote=True)}" target="_blank" rel="noopener">重庆市疾控中心</a>'
            ' · 官方声明未经许可不得复制发布，本工具只提供入口，不转载正文、数值或图片。</div>')


# A4 主题层（design r3 §2/§3）：独立原始字符串，不经 str.format（GAP-A4-01），
# 由 render() 经 PAGE_TPL 的 {css} 占位注入 <style> 尾部，后置覆盖存量规则。
# 红线：不引用任何外部资源，不含脚本标签或远程地址字样；病种识别色仅用于
# 线条与端点，不进入背景；红色总面积小于百分之一。
CSS_THEME = r"""
/* ===== A4 主题层「检验单」===== 纯呈现覆盖，后置于存量规则之上 */
:root{
  --bg:#E9EEF1; --surface:#FFF; --surface-2:#F4F7F8; --notice:#FFF6E5;
  --hair:#DDE5E8; --hair-strong:#C3D2D7; --field-border:#7B8C93;
  --ink-1:#0E1B20; --ink-2:#3D4E56; --ink-3:#56686F; --ink-4:#8C9BA2;
  --link:#0A6273; --brand:#0B5D6B; --brand-soft:#E5F0F2; --focus:#0A6B7A;
  --mono:ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace;
  --sans:-apple-system,"Segoe UI","PingFang SC","Hiragino Sans GB",
         "Microsoft YaHei UI","Microsoft YaHei","Noto Sans CJK SC",system-ui,sans-serif;
}
body{background:var(--bg);color:var(--ink-1);font-family:var(--sans)}
.wrap{counter-reset:card}
h1{font-size:21px;font-weight:600;color:var(--ink-1);letter-spacing:.01em}
.sub{color:var(--ink-3)}
a{color:var(--link)}
.banner{background:var(--notice);border-color:var(--hair-strong);border-left:3px solid #7A4E00;color:#7A4E00}
.card{background:var(--surface);border:1px solid var(--hair);border-radius:10px;padding:14px 20px 18px;box-shadow:0 1px 2px rgba(14,27,32,.04);position:relative;counter-increment:card}
.card h2{font-size:13px;font-weight:600;letter-spacing:.02em;color:var(--ink-2);padding-right:44px}
.card::before{content:counter(card,decimal-leading-zero);position:absolute;top:13px;right:16px;font-family:var(--mono);font-size:12px;color:var(--ink-4);pointer-events:none}
#default-view,#query-view{counter-reset:card}
.big{font-size:34px;font-weight:700;color:var(--ink-1);font-variant-numeric:tabular-nums;letter-spacing:-0.02em}
.big.nodata{font-size:24px;color:var(--ink-3);font-weight:400;letter-spacing:0}
.unit{font-size:13px;font-weight:500;color:var(--ink-3);white-space:nowrap}
.kv{font-size:15px;line-height:1.62;color:var(--ink-1)}
.kv b{font-size:20px;font-weight:600;font-variant-numeric:tabular-nums}
.meta{color:var(--ink-3)}
.src{color:var(--ink-3)}
.foot{font-size:12px;color:var(--ink-3)}
.q-ver{font-size:12px;color:var(--ink-3)}
.q-status{color:var(--ink-3)}
.q-chip{color:var(--ink-3)}
.adv{font-size:15px;line-height:1.62;color:var(--ink-1);max-width:68ch;list-style:none;padding-left:0;margin:8px 0 0}
/* 官方原文自带（1）…（5）序号，故去掉浏览器 decimal 序号，仅保留悬挂缩进 */
.adv li{padding-left:1.6em;text-indent:-1.6em}
.chain{font-size:15px;line-height:1.62;color:var(--ink-1)}
.tlabel{font-size:13px;color:var(--ink-2)}
.nodata{color:var(--ink-3)}
.rank{font-size:15px}
.rank th{font-size:12px;font-weight:500;letter-spacing:.08em;color:var(--ink-3)}
.childg b{color:var(--ink-2)}
.search label{color:var(--ink-2)}
#q{border-color:var(--field-border)}
#q-list{border-color:var(--field-border)}
.q-btn{border-color:var(--field-border)}
#q-list .q-item .q-sub{font-size:12px;color:var(--ink-3)}
#q-list .q-item[aria-selected="true"] .q-sub{color:#E5E7EB}
.hist-sub{color:var(--ink-3)}
.hist-sub2{font-size:12px;color:var(--ink-3)}
.hist-scroll-hint{font-size:12px;color:var(--ink-3)}
.hist-tbl caption{font-size:12px;color:var(--ink-3)}
.hist-tbl thead th{font-family:var(--mono);font-size:12px;letter-spacing:.08em;color:var(--ink-3)}
.hist-tbl .hist-na{color:var(--ink-3)}
.hist-tbl tbody tr.hist-cur{background:#F4F7F8;box-shadow:inset 2px 0 0 var(--brand)}
.eyebrow{font-family:var(--mono);font-size:12px;font-weight:600;letter-spacing:.08em;color:var(--ink-3);margin:0 0 2px}
/* 品牌短线：把视线钉在关键数字上（design §3.4 第 4 层） */
.eyebrow::before{content:"";display:inline-block;width:24px;height:3px;background:var(--brand);margin-right:8px;vertical-align:middle}
/* -- 状态四态（design §2.2/§3）-- */
.tag{font-size:12px;font-weight:500;padding:3px 10px;border-radius:11px;background:var(--brand-soft);color:var(--brand)}
.tag.st-ok{background:#E7F4EE;color:#0F6B4F}
.tag.st-wait{background:var(--notice);color:#7A4E00;border-left:3px solid #7A4E00}
.tag.st-fail{background:var(--notice);color:#A02D1E;border-left:3px solid #A02D1E}
.tag.st-unknown{background:var(--surface-2);color:var(--ink-2);border:1px dashed var(--field-border)}
.q-chip.st-ok{color:#0F6B4F}
.q-chip.st-wait{color:#7A4E00}
.q-chip.st-fail{color:#A02D1E}
.q-chip.st-unknown{color:var(--ink-2)}
/* -- 五级标尺（仅四川卡，_sc_body 未冻结）-- */
.rail{display:flex;gap:4px;margin:12px 0 0;max-width:380px}
.rail i{flex:1;height:6px;border-radius:3px;opacity:.22}
.rail i.on{opacity:1;outline:1px solid var(--hair-strong)}
.rail i.lvl-V{background:#D8E8EB}.rail i.lvl-IV{background:#AECFD6}
.rail i.lvl-III{background:#7FAEB9}.rail i.lvl-II{background:#3D7C8B}
.rail i.lvl-I{background:#14505F}
.rail-labels{display:flex;gap:4px;max-width:380px;margin:3px 0 0}
.rail-labels span{flex:1;text-align:center;font-family:var(--mono);font-size:12px;color:var(--ink-3)}
/* -- SVG：chrome 重着色 + 文字/线条边界（识别色只留折线与端点）-- */
svg text[fill="#999"],svg text[fill="#6b7280"]{fill:#3D4E56}
svg text[fill="#c0392b"],svg text[fill="#7f8c8d"],svg text[fill="#8e44ad"]{fill:#3D4E56}
svg line[stroke="#e5e7eb"],svg line[stroke="#eef0f2"]{stroke:#EFF3F4}
svg line[stroke="#9ca3af"],svg line[stroke="#d1d5db"]{stroke:#9FB0B6}
svg rect[fill="#f3f4f6"]{fill:#F4F7F8}
svg text[font-size="9"]{font-size:10px}
/* 小图右端周次标签与低值末端百分比会在底部相撞：两个周次标签共用 y=68 基线，
   一起下移 10px；溢出改为可见并由 margin-bottom 预留空间（viewBox 不变，
   冻结函数 svg_sparkline 未改）。 */
.trendrow svg{overflow:visible;margin-bottom:12px}
svg text[y="68"]{transform:translateY(10px)}
/* -- hero（四川卡）：品牌竖条 + 微网格底纹 -- */
#default-view > .card:has(.adv){
  border-left:3px solid var(--brand);
  background-image:repeating-linear-gradient(0deg,rgba(14,27,32,.035) 0 1px,transparent 1px 24px),
                   repeating-linear-gradient(90deg,rgba(14,27,32,.035) 0 1px,transparent 1px 24px);
}
#default-view > .card:has(.big.nodata){border-left:3px dashed var(--field-border)}
/* -- 焦点环统一 -- */
#q:focus-visible,.q-btn:focus-visible,.hist-scroll:focus-visible,
#query-view h2:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
#q-list .q-item:focus-visible{outline:2px solid var(--focus);outline-offset:-2px}
/* -- 账本式表格 hover（仅指针设备）-- */
@media (hover:hover){
  .rank tbody tr:hover,.hist-tbl tbody tr:hover{background:#F7FAFB}
}
/* -- 布局断点：720/900/1024 -- */
@media (min-width:720px){
  .wrap{padding:20px}
  .big{font-size:46px}
}
@media (max-width:719px){
  .card::before{display:none}
  .card h2{padding-right:0}
}
@media (min-width:900px){
  .wrap{max-width:min(1080px,100%)}
  #default-view{display:grid;grid-template-columns:repeat(12,1fr);gap:20px;align-items:start}
  #default-view[hidden]{display:none}
  #default-view > *{margin-bottom:0}
  #default-view > .banner,#default-view > .card{grid-column:1/-1}
  #default-view > .card:has(.adv){grid-column:span 7}
  #default-view > .card:has(.kv){grid-column:span 5}
  #default-view > .card:has(.hist-tbl){grid-column:span 7}
  #default-view > .card:has(.rank){grid-column:span 5}
  #default-view > .card:has(.trendrow){grid-column:span 7}
  #default-view > .card:has(.childg){grid-column:span 5}
  #query-view > .card{grid-column:1/-1}
}
@media (min-width:1024px){
  .wrap{padding:18px 32px}
}
@media (max-width:519px){
  .trendrow{flex-direction:column;align-items:stretch;gap:2px}
  .tlabel{width:auto}
}
@media print{
  .card{box-shadow:none;background-image:none}
  .banner{display:none}
  body{background:#fff}
}
"""

PAGE_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;margin:0;background:#f5f6f8;color:#222}}
  .wrap{{max-width:640px;margin:0 auto;padding:16px}}
  h1{{font-size:20px;margin:16px 0 4px}}
  .sub{{font-size:12px;color:#888;margin-bottom:12px}}
  .banner{{background:#fff3cd;border:1px solid #ffc107;color:#856404;padding:8px 12px;border-radius:8px;font-size:14px;margin-bottom:12px}}
  .card{{background:#fff;border-radius:12px;padding:16px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
  .card h2{{font-size:15px;margin:0 0 8px;color:#555}}
  .big{{font-size:34px;font-weight:700}}
  .big.nodata{{font-size:24px;color:#9ca3af;font-weight:400}}
  .unit{{font-size:13px;color:#888;font-weight:400}}
  .kv{{display:flex;flex-wrap:wrap;gap:6px 18px;margin-top:8px;font-size:14px}}
  .kv b{{font-size:18px}}
  .meta{{margin-top:10px;font-size:12px;color:#6b7280}}
  .tag{{display:inline-block;font-size:11px;padding:2px 8px;border-radius:10px;background:#eef4ff;color:#3a6ea5;margin-right:6px;margin-bottom:2px;max-width:100%;box-sizing:border-box}}
  .adv{{margin:8px 0 0;padding:0 0 0 18px;font-size:13px;color:#444;line-height:1.7}}
  .src{{font-size:12px;color:#6b7280;margin-top:8px}}
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
  .foot{{font-size:11px;color:#6b7280;margin:16px 0;line-height:1.6}}
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
  .search{{margin:0 0 12px}}
  .search label{{font-size:13px;color:#555;display:block;margin-bottom:6px}}
  #q{{width:100%;box-sizing:border-box;font-size:16px;padding:10px 12px;border:1px solid #d5dade;border-radius:8px;background:#fff}}
  #q:focus-visible{{outline:2px solid #3a6ea5;outline-offset:1px}}
  #q-list{{list-style:none;margin:4px 0 0;padding:4px;background:#fff;border:1px solid #d5dade;border-radius:8px;max-height:260px;overflow:auto}}
  #q-list .q-item{{padding:8px 10px;border-radius:6px;cursor:pointer;font-size:14px;min-height:44px;box-sizing:border-box}}
  #q-list .q-item[aria-selected="true"]{{background:#1f2937;color:#fff}}
  #q-list .q-item .q-sub{{font-size:11px;color:#999;margin-left:6px}}
  #q-list .q-item[aria-selected="true"] .q-sub{{color:#ddd}}
  .q-status{{font-size:12px;color:#6b7280;margin-top:6px;min-height:16px;line-height:1.6}}
  .q-row{{display:flex;gap:8px;align-items:stretch}}
  .q-row #q{{flex:1 1 auto;min-width:0}}
  #q[disabled]{{background:#f0f2f4;color:#6b7280;cursor:not-allowed}}
  .q-btns{{display:flex;gap:6px;flex:none}}
  .q-btn{{min-height:44px;padding:0 12px;font-size:14px;border:1px solid #d5dade;border-radius:8px;background:#f5f7f9;color:#1f2937;cursor:pointer}}
  .q-btn:hover{{background:#eef1f4}}
  .q-btn:focus-visible{{outline:2px solid #3a6ea5;outline-offset:1px}}
  .q-btn[disabled]{{opacity:.55;cursor:not-allowed}}
  .q-chip{{font-size:12px;color:#6b7280;margin:6px 0 0}}.q-chip.bad{{color:#b91c1c}}.q-chip.ok{{color:#15803d}}.q-ver{{font-size:11px;color:#9ca3af;margin-top:4px;line-height:1.6}}
  /* 结果区标题可编程聚焦（tabindex=-1），不显示焦点框 */
  #query-view h2:focus{{outline:none}}
  #query-view h2:focus-visible{{outline:2px solid #3a6ea5;outline-offset:1px}}
  @media (max-width:520px){{ .q-row{{display:block}} .q-btns{{margin-top:6px}} .q-btn{{flex:1}} }}
{css}
</style>
</head>
<body>
<div class="wrap">
  <h1>{h1}</h1>
  <div class="sub">{sub}</div>
{searchbox}
<div id="default-view">
  {run_banner}
  {banner}
{cards}
</div>
{templates}
  <div class="foot">
{foot}
    页面生成时间：{gen} · 数据以官方发布为准。
  </div>
</div>
<script type="application/json" id="catalog-data">{catalog_data}</script>
<script type="application/json" id="recipes-data">{recipes_data}</script>
{search_js}
</body>
</html>
"""


def flu_body_html(flu: dict) -> str:
    """流感卡正文（S4-B01/B02）：动态内容全转义、URL 白名单、无效周次计数上屏。

    A2：字段名与来源文案由 flu_block 的 ili_field/pos_field/source_label 参数化。
    """
    ili_f = flu.get("ili_field") or "south_ili_pct"
    pos_f = flu.get("pos_field") or "south_flu_positive_pct"
    src_label = flu.get("source_label") or "国家流感中心《中国流感监测周报》"
    n_bad = flu.get("invalid_rows") or 0
    note = (f'<span class="tag">已忽略 {n_bad} 条无效周次记录</span>'
            if n_bad else "")
    src = flu.get("source_url") or ""
    u = valid_url(src)
    link = (f'<a href="{_esc(src, quote=True)}" target="_blank" rel="noopener">当期文章</a>'
            if u else "来源链接未提供")
    if flu.get("anchor_bad"):
        return f"""
    <div class="big nodata">—<span class="unit"> 数据异常，未采用</span></div>
    <div class="kv"><span>{_esc(flu.get('iso_year',''))}年第<b>{_esc(flu.get('iso_week',''))}</b>周</span></div>
    <div class="meta"><span class="tag">{_esc(flu.get('line',''))}</span><span class="tag">{_esc(flu.get('mom',''))}</span>{note}</div>
    <div class="src">来源：{_esc(src_label)} {link}</div>"""
    if flu["state"] == "ok":
        return f"""
    <div class="eyebrow">GOLDSTEIN · { _esc(flu.get('iso_year','')) }W{ _esc(flu.get('iso_week','')) }</div>
    <div class="big">{_esc(flu.get('goldstein_index',''))}<span class="unit"> Goldstein 指数（相对强度）</span></div>
    <div class="kv">
      <span>ILI% <b>{_esc(flu.get(ili_f,''))}%</b></span>
      <span>流感阳性率 <b>{_esc(flu.get(pos_f,''))}%</b></span>
      <span>{_esc(flu.get('iso_year',''))}年第<b>{_esc(flu.get('iso_week',''))}</b>周</span>
    </div>
    <div class="meta"><span class="tag">{_esc(flu.get('line',''))}</span><span class="tag">{_esc(flu.get('mom',''))}</span>{note}</div>
    <div class="src">来源：{_esc(src_label)} {link}</div>"""
    if flu.get("empty_note"):
        return f"""<div class="big nodata">—</div><div class="meta"><span class="tag">暂无可用数据 · 存在未成功获取的记录 · 请运行更新</span>{note}</div>"""
    if flu.get("never_collected") and (flu.get("area") or "南方片") != "南方片":
        return (f"""<div class="big nodata">—</div><div class="meta"><span class="tag">本工具未取得"""
                f"""{_esc(flu.get("area") or "")}该产品的周报数据</span>{note}</div>"""
                f"""<div class="src">来源：{_esc(src_label)} {link}</div>""")
    return f"""<div class="big nodata">—</div><div class="meta"><span class="tag">暂无数据 · 请运行更新</span>{note}</div>"""


def _cli_opts(argv):
    """A2 §4：解析构建状态参数。--local 无显式状态；--run-status/--run-id 成对显式传入。"""
    opts = {"local": False, "run_status": None, "run_id": None}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--local":
            opts["local"] = True
        elif a in ("--run-status", "--run-id"):
            i += 1
            if i >= len(argv):
                print(f"{a} 缺少取值", file=sys.stderr)
                raise SystemExit(2)
            opts["run_status" if a == "--run-status" else "run_id"] = argv[i]
        else:
            print(f"未知参数：{a}\n用法：--local | --run-status <path> --run-id <id>",
                  file=sys.stderr)
            raise SystemExit(2)
        i += 1
    if (opts["run_status"] is None) != (opts["run_id"] is None):
        print("--run-status 与 --run-id 必须成对出现", file=sys.stderr)
        raise SystemExit(2)
    return opts


def _sc_body(sc: dict) -> str:
    if sc["state"] == "ok":
        advice = "".join(f"<li>{a}</li>" for a in sc["advice"])
        # A4 状态三态（design r3 §3）：line 以「数据正常」开头=st-ok；
        # 含「本月待更新」=st-wait（存量非当月）；empty=st-unknown。
        line = sc["line"]
        st_cls = "st-ok" if line.startswith("数据正常") else (
            "st-wait" if "本月待更新" in line else "st-unknown")
        # 五级标尺：Ⅴ(浅)→Ⅰ(深)，当前级实心、其余降透明（design r3 §2.5）
        order = ("V", "IV", "III", "II", "I")
        idx = order.index(sc["level"]) if sc["level"] in order else -1
        segs = "".join(
            f'<i class="lvl-{lv}{" on" if i == idx else ""}"></i>'
            for i, lv in enumerate(order))
        rail = ('<div class="rail" aria-hidden="true">' + segs + '</div>'
                '<div class="rail-labels" aria-hidden="true">'
                + "".join(f"<span>{c}</span>" for c in ("Ⅴ", "Ⅳ", "Ⅲ", "Ⅱ", "Ⅰ"))
                + "</div>")
        return f"""
    <div class="big">{sc['level']} 级 · {sc['level_name']}<span class="unit">（{sc['year']}年{sc['month']}月）</span></div>
    {rail}
    <div class="meta"><span class="tag {st_cls}">{sc['line']}</span><span class="tag">省级官方分级</span></div>
    <ol class="adv">{advice}</ol>
    <div class="src">防控建议为官方原文：四川省疾控"流感指数分级标准表" {sc['level']} 级 · <a href="{sc['source_url']}" target="_blank">当期发布</a></div>"""
    return '<div class="big nodata">？</div><div class="meta"><span class="tag st-unknown">官方分级未获取 · 状态未知</span></div>'


FOOT_COMMON = ("    本工具不合成综合风险总分，各块独立标注口径；排序为名称非数值；"
               "箭头仅表较上周方向；Goldstein 指数为相对强度指数（ILI%×阳性率），非人群感染率。\n"
               "    据中疾控《版权与免责声明》注明：稿件来源：中国疾病预防控制中心；"
               "WHO FluNet 数据为国家层面公开数据。\n")

FOOT_CD = ("    口径说明：四川分级为省疾控平原区（月度）；流感指数为南方片哨点（周度）；"
           "多病原排行/趋势/儿童卡均为全国哨点口径（非成都实测）。\n"
            "    查询结果中：黑龙江为省级官方周报口径；重庆仅官方入口；其余省市无当地数据时"
            "只展示省级/片区/全国参考，均明确标注，不冒充当地实测。\n")


CARD_TITLES = {
    "sc": "四川官方流感分级（月度 · 成都=平原区）",
    "flu_south": "南方片流感趋势（周度）",
    "flu_north": "北方片流感趋势（周度）",
    "flu_hlj": "黑龙江流感指数（省级周报 · 周度）",
    "hist_south": "南方片流感指数 · 历年同周对比",
    "names_south": "南方片门急诊 / 住院前三名（周度）",
    "names_north": "北方片门急诊 / 住院前三名（周度）",
    "hlj_sent": "黑龙江哨点监测 · 官方正文部分观测（周度）",
    "rank": "全国多病原活跃度排行（周度）",
    "trend": "流感 / 新冠 / RSV 趋势（周度 · 本年度）",
    "child": "儿童分龄高发前三（周度）",
    "cq": "重庆 · 官方入口",
}


def _build_cards(views: dict):
    """按卡片键生成正文；视图一次构建复用（搜索版：默认页与查询模板共用）。

    返回 (cards, available)：available 为「有内容可建卡」的键集合，用于裁剪空壳卡
    （display-proposal §5c：无数据不建卡）。
    """
    out = {}
    for key in ("flu_south", "flu_north", "flu_hlj"):
        out[key] = flu_body_html(views["flu_" + key.split("_")[1]])
    out["sc"] = _sc_body(sichuan_block())
    out["hist_south"] = history_block(views["flu_south_view"], area="南方片")
    drop = set()
    # 历史卡无任何可绘制年份时不建卡（north 首版常见）
    for hist_key, view_key in (("hist_south", "flu_south_view"),):
        h = history_data(views[view_key])
        if h["empty"] or not _hist_plot_years(h):
            drop.add(hist_key)
    out["names_south"] = region_rank_block("南方省份", "南方片")
    out["names_north"] = region_rank_block("北方省份", "北方片")
    out["hlj_sent"] = hlj_sentinel_block()
    out["rank"] = ranking_block()
    out["trend"] = trend_block()
    out["child"] = child_block()
    out["cq"] = chongqing_block()
    return out, drop


SEARCH_JS = ("<script>" + r"""
/* A2 省市查询（S2 内联交互）：页面不联网，全部候选来自内嵌目录 JSON。
   - 控件默认 disabled；init 全部成功（目录解析/元素绑定/事件注册/首渲染）后才启用。
     任何异常→控件保持不可点，#q-status 常驻降级说明，成都默认内容保持完整可读。
   - 只过滤目录里 q=1 的单位；港澳台占位（q=0）永不进入候选。
   - 用户输入只用于匹配；落屏一律 textContent / createTextNode / cloneNode，绝不拼 HTML。
   - 结果区按 recipes-data 的槽位顺序克隆 <template>，脚本不计算任何数值或口径。
   - 清空输入、收起候选、Esc 都不改变当前已显示的结果；只有「查询」/点选候选/「回成都」切换视图。 */
(function () {
  "use strict";

  var MAX_CANDIDATES = 8;
  var FAIL_TEXT = "搜索功能初始化失败，页面按成都默认内容展示";
  var BASE_STATUS_TAIL = " 个单位，可换用简称或上级地名。";
  /* 复核 A01：不在运行时剥行政后缀（不猜"哈尔滨市"→"哈尔滨"这类改写），
     只按 规范名/审核别名 的 精确 → 前缀 → 包含 三级匹配。"哈尔滨"作为
     "哈尔滨市"的前缀本就能命中；简称一律走目录 aliases 审核列。 */
  var TYPE_WORDS = { province: "省级", prefecture: "地级", province_direct_county: "省直辖县级" };

  function fatal() {
    var st = document.getElementById("q-status");
    if (st) { st.textContent = FAIL_TEXT; }
    var dv = document.getElementById("default-view");
    if (dv) { dv.hidden = false; }
    var qv = document.getElementById("query-view");
    if (qv) { qv.hidden = true; }
  }

  function normalize(text) {
    var out = "";
    for (var i = 0; i < text.length; i++) {
      var code = text.charCodeAt(i);
      var ch = text.charAt(i);
      if (code === 0x3000) { continue; }
      if (code >= 0xff01 && code <= 0xff5e) { ch = String.fromCharCode(code - 0xfee0); }
      if (ch === " " || ch === "\t" || ch === "\n" || ch === "\r") { continue; }
      out += ch;
    }
    return out.toLowerCase();
  }

  function init() {
    var qEl = document.getElementById("q");
    var listEl = document.getElementById("q-list");
    var statusEl = document.getElementById("q-status");
    var queryView = document.getElementById("query-view");
    var defaultView = document.getElementById("default-view");
    var goBtn = document.getElementById("q-go");
    var clearBtn = document.getElementById("q-clear");
    var homeBtn = document.getElementById("q-home");
    if (!qEl || !listEl || !statusEl || !queryView || !defaultView ||
        !goBtn || !clearBtn || !homeBtn) {
      throw new Error("search elements missing");
    }
    var catalogRaw = document.getElementById("catalog-data");
    var recipesRaw = document.getElementById("recipes-data");
    if (!catalogRaw || !recipesRaw) { throw new Error("embedded data missing"); }
    var rows = JSON.parse(catalogRaw.textContent);
    var recipes = JSON.parse(recipesRaw.textContent);
    if (!rows || typeof rows.length !== "number" || !recipes || typeof recipes !== "object") {
      throw new Error("embedded data malformed");
    }

    var units = [];
    var byId = {};
    for (var ri = 0; ri < rows.length; ri++) {
      var row = rows[ri];
      if (!row || row.q !== 1) { continue; }
      var aliases = [];
      var rawAliases = row.a || [];
      for (var ai = 0; ai < rawAliases.length; ai++) {
        var al = normalize(rawAliases[ai]);
        if (al) { aliases.push(al); }
      }
      var unit = {
        id: row.i,
        name: row.n,
        type: row.t,
        parent: row.p,
        aliases: aliases,
        norm: normalize(row.n)
      };
      units.push(unit);
      byId[unit.id] = unit;
    }
    if (!units.length) { throw new Error("catalog empty"); }

    var items = [];
    var activeIdx = -1;

    function say(text) { statusEl.textContent = text; }

    function listOpen() { return !listEl.hidden; }

    function closeList() {
      listEl.hidden = true;
      qEl.setAttribute("aria-expanded", "false");
      if (qEl.hasAttribute("aria-activedescendant")) {
        qEl.removeAttribute("aria-activedescendant");
      }
      activeIdx = -1;
    }

    function setActive(idx) {
      var kids = listEl.children;
      for (var k = 0; k < kids.length; k++) {
        kids[k].setAttribute("aria-selected", k === idx ? "true" : "false");
      }
      if (idx >= 0 && kids[idx]) {
        qEl.setAttribute("aria-activedescendant", kids[idx].id);
        activeIdx = idx;
      } else {
        if (qEl.hasAttribute("aria-activedescendant")) {
          qEl.removeAttribute("aria-activedescendant");
        }
        activeIdx = -1;
      }
    }

    function subLine(unit) {
      var parts = [];
      if (TYPE_WORDS[unit.type]) { parts.push(TYPE_WORDS[unit.type]); }
      if (unit.parent && byId[unit.parent]) { parts.push(byId[unit.parent].name); }
      return parts.join(" · ");
    }

    function optionNode(unit, idx) {
      var li = document.createElement("li");
      li.className = "q-item";
      li.id = "q-opt-" + idx;
      li.setAttribute("role", "option");
      li.setAttribute("aria-selected", "false");
      var nameSpan = document.createElement("span");
      nameSpan.textContent = unit.name;
      li.appendChild(nameSpan);
      var subSpan = document.createElement("span");
      subSpan.className = "q-sub";
      subSpan.textContent = "  " + subLine(unit);
      li.appendChild(subSpan);
      li.addEventListener("mousedown", function (ev) {
        ev.preventDefault();
        selectAt(idx);
      });
      return li;
    }

    function openList(matches) {
      while (listEl.firstChild) { listEl.removeChild(listEl.firstChild); }
      items = matches;
      if (!items.length) { closeList(); return; }
      for (var n = 0; n < items.length; n++) { listEl.appendChild(optionNode(items[n], n)); }
      listEl.hidden = false;
      qEl.setAttribute("aria-expanded", "true");
      setActive(-1); /* 复核 01：多候选必须显式选中，不默认激活第一项 */
    }

    /* 复核 A01：三级匹配，不再运行时剥后缀。
       0 精确（规范名或审核别名全等）→ 1 前缀（规范名或别名）→ 2 包含（规范名或别名）。
       同级内先短名后长名，最后按 id 稳定排序。 */
    function matchScore(unit, needle) {
      if (unit.norm === needle) { return 0; }
      var i;
      for (i = 0; i < unit.aliases.length; i++) {
        if (unit.aliases[i] === needle) { return 0; }
      }
      if (unit.norm.indexOf(needle) === 0) { return 1; }
      for (i = 0; i < unit.aliases.length; i++) {
        if (unit.aliases[i].indexOf(needle) === 0) { return 1; }
      }
      if (unit.norm.indexOf(needle) >= 0) { return 2; }
      for (i = 0; i < unit.aliases.length; i++) {
        if (unit.aliases[i].indexOf(needle) >= 0) { return 2; }
      }
      return -1;
    }

    function search(needle) {
      var hits = [];
      for (var i = 0; i < units.length; i++) {
        var score = matchScore(units[i], needle);
        if (score >= 0) { hits.push({ unit: units[i], score: score }); }
      }
      hits.sort(function (a, b) {
        if (a.score !== b.score) { return a.score - b.score; }
        if (a.unit.name.length !== b.unit.name.length) {
          return a.unit.name.length - b.unit.name.length;
        }
        return a.unit.id < b.unit.id ? -1 : (a.unit.id > b.unit.id ? 1 : 0);
      });
      var out = [];
      for (var k = 0; k < hits.length && k < MAX_CANDIDATES; k++) { out.push(hits[k].unit); }
      return out;
    }

    function clearQueryView() {
      while (queryView.firstChild) { queryView.removeChild(queryView.firstChild); }
    }

    function showDefault(msg) {
      clearQueryView();
      queryView.hidden = true;
      defaultView.hidden = false;
      if (msg) { say(msg); }
    }

    /* 先在离屏 staging 里拼好，再整体替换并一次性显示（避免半成品闪屏）。 */
    function renderResult(unit, slots) {
      var staging = document.createElement("div");
      var missing = [];
      for (var s = 0; s < slots.length; s++) {
        var slot = slots[s];
        var tpl = document.getElementById("tpl-" + slot);
        if (!tpl) { missing.push(slot); continue; }
        staging.appendChild(tpl.content.cloneNode(true));
      }
      if (missing.length) {
        /* 复核 04：缺模板即失败恢复完整成都默认视图，不半新半旧展示 */
        showDefault(unit.name + " 数据模块缺失（" + missing.join("、") +
                    "），已恢复成都默认。");
        return;
      }
      clearQueryView();
      while (staging.firstChild) { queryView.appendChild(staging.firstChild); }
      queryView.hidden = false;
      defaultView.hidden = true;
      say(unit.name + "：按该地区可用数据分块展示，各块自标口径与数据状态。");
      var heading = queryView.querySelector("h2, h3, h1");
      if (heading) {
        heading.setAttribute("tabindex", "-1");
        heading.focus();
      } else {
        queryView.setAttribute("tabindex", "-1");
        queryView.focus();
      }
    }

    function selectUnit(unit) {
      try {
        var slots = recipes[unit.id];
        if (!slots || !slots.length) {
          say("该地区暂无可查询的数据配方（" + unit.name + "）。");
          return;
        }
        if (slots.length === 1 && slots[0] === "chengdu_default") {
          closeList();
          qEl.value = "";
          showDefault("已恢复成都默认");
          return;
        }
        closeList();
        qEl.value = unit.name;
        renderResult(unit, slots);
      } catch (err) {
        /* 复核 04：查询切换入口统一捕获——克隆/渲染异常恢复成都默认 */
        showDefault("查询切换失败（" + (err && err.message ? err.message : err) +
                    "），已恢复成都默认。");
      }
    }

    function selectAt(idx) {
      if (idx >= 0 && items[idx]) { selectUnit(items[idx]); }
    }

    function noMatchText() {
      return "未找到匹配的省市。目录共 " + units.length + BASE_STATUS_TAIL;
    }

    function handleInput() {
      var needle = normalize(qEl.value);
      if (!needle) {
        items = []; /* 复核 01：手动删空输入须废弃旧候选，防 Enter 误选 */
        closeList();
        say("输入为空：候选已清空，当前显示结果保持不变。");
        return;
      }
      var matches = search(needle);
      if (!matches.length) {
        openList([]);
        say(noMatchText());
        return;
      }
      openList(matches);
      say("匹配到 " + matches.length + " 个地区，用 ↑↓ 选择、回车确认，或直接点列表项。");
    }

    function onGo() {
      var needle = normalize(qEl.value);
      if (!needle) {
        say("请先输入省市名称，再点「查询」。");
        qEl.focus();
        return;
      }
      if (listOpen() && items.length === 1) { selectAt(0); return; }
      if (listOpen() && items.length > 1) {
        say("匹配到 " + items.length + " 个地区，请从列表中选择。");
        return;
      }
      var matches = search(needle);
      if (!matches.length) { say(noMatchText()); return; }
      if (matches.length === 1) { selectUnit(matches[0]); return; }
      openList(matches);
      say("匹配到 " + matches.length + " 个地区，请从列表中选择。");
    }

    /* 清空只管输入框与候选：不切视图、不动已显示的结果。 */
    function onClear() {
      qEl.value = "";
      items = [];
      closeList();
      say("已清空输入与候选，当前显示结果未变。");
      qEl.focus();
    }

    function onHome() {
      qEl.value = "";
      items = [];
      closeList();
      showDefault("已恢复成都默认");
    }

    function onKeyDown(ev) {
      var key = ev.key;
      if (key === "ArrowDown") {
        if (!listOpen() || !items.length) { return; }
        ev.preventDefault();
        setActive(activeIdx + 1 >= items.length ? 0 : activeIdx + 1);
        return;
      }
      if (key === "ArrowUp") {
        if (!listOpen() || !items.length) { return; }
        ev.preventDefault();
        setActive(activeIdx - 1 < 0 ? items.length - 1 : activeIdx - 1);
        return;
      }
      if (key === "Enter") {
        ev.preventDefault();
        if (listOpen() && activeIdx >= 0 && items[activeIdx]) { selectAt(activeIdx); return; }
        if (items.length === 1) { selectAt(0); return; }
        onGo();
        return;
      }
      if (key === "Escape") {
        /* 分层（复核 01）：第一下收起列表；列表已收起时再按一次仅清空输入，
           不改变已显示的结果、不回成都。 */
        ev.preventDefault();
        if (listOpen()) {
          closeList();
          say("已收起候选列表，再按一次 Esc 清空输入。");
        } else {
          qEl.value = "";
          items = [];
          say("已清空输入，当前显示结果未变。");
        }
        return;
      }
      if (key === "Tab") { closeList(); }
    }

    function onDocKeyDown(ev) {
      if (ev.key !== "Escape") { return; }
      if (listOpen()) { closeList(); }
    }

    function onDocMouseDown(ev) {
      if (!listOpen()) { return; }
      if (ev.target === qEl || listEl.contains(ev.target)) { return; }
      closeList();
    }

    qEl.addEventListener("input", handleInput);
    qEl.addEventListener("keydown", onKeyDown);
    goBtn.addEventListener("click", onGo);
    clearBtn.addEventListener("click", onClear);
    homeBtn.addEventListener("click", onHome);
    document.addEventListener("keydown", onDocKeyDown);
    document.addEventListener("mousedown", onDocMouseDown);

    closeList();
    qEl.disabled = false;
    goBtn.disabled = false;
    clearBtn.disabled = false;
    homeBtn.disabled = false;
    say("已就绪：目录共 " + units.length + " 个单位，输入省市名称开始查询（页面不联网）。");
  }

  try {
    init();
  } catch (err) {
    fatal();
  }
})();
""" + "</" + "script>")  # S2 内联交互脚本；收尾标签拆写，避免字符串内出现字面结束标签


def _embed_json(obj) -> str:
    """内嵌 <script type="application/json"> 内容（S1b）。

    `<` 转义为 \\u003c，防止数据文本提前终止 script 块；调用方不再转义。
    """
    import json as _json
    txt = obj if isinstance(obj, str) else _json.dumps(
        obj, ensure_ascii=False, separators=(",", ":"))
    return txt.replace("<", "\\u003c")


def _search_scaffold() -> str:
    """搜索区静态骨架（S1b，design r4 §3）：S2 只补内联脚本，不改此结构。

    降级契约（复核 A2-SEARCH-04）：输入框与三按钮默认 disabled，初始化成功后
    才启用；脚本失败时控件保持不可点，状态区常驻说明，成都默认内容完整可读。
    """
    return """
  <section class="search" aria-label="查询其他省市">
    <label for="q">查询其他省市（本地目录 · 页面不联网）</label>
    <div class="q-row">
      <input id="q" type="text" role="combobox" aria-expanded="false"
             aria-controls="q-list" aria-autocomplete="list" autocomplete="off"
             placeholder="输入省市名称，如：哈尔滨 / 广东 / 重庆" disabled>
      <div class="q-btns">
        <button type="button" id="q-go" class="q-btn" disabled>查询</button>
        <button type="button" id="q-clear" class="q-btn" disabled>清空</button>
        <button type="button" id="q-home" class="q-btn" disabled>回成都</button>
      </div>
    </div>
    <ul id="q-list" role="listbox" aria-label="候选地区" hidden></ul>
    <div id="q-status" class="q-status" role="status" aria-live="polite">搜索组件加载中…若本提示未消失，说明内联脚本未完成初始化，搜索暂不可用；下方成都默认数据不受影响。</div>
    <p class="q-ver">目录版本：民政部 2025 年末 + CC0 areacodes（含 dmfw 补录 1 条）</p>
    <div id="query-view" hidden></div>
    <noscript><div class="q-status">浏览器脚本不可用：仅显示成都默认内容；
      查询功能需启用 JavaScript（数据已内嵌本页，不联网）。</div></noscript>
  </section>"""


def _src_chip(status, key: str) -> str:
    """A2-SEARCH-03：把本轮该源的获取状态渲染进对应模板。

    无本轮状态（本地直构建未传 --run-status）不显示 chip；状态由
    write_run_status 聚合，本函数不做任何推定。
    """
    if not isinstance(status, dict):
        return ""
    src = (status.get("sources") or {}).get(key)
    if not isinstance(src, dict):
        # 复核 03：本轮状态存在但缺该源键 = 状态未知，不静默返回空串
        return '<div class="q-chip st-unknown">本轮获取：状态未知</div>'
    st = src.get("status")
    words = {"ok": ("ok st-ok", "本轮获取：成功"),
             "skipped": ("st-wait", "本轮获取：未执行"),
             "failed": ("bad st-fail", "本轮获取：失败 · 下方为最近一次成功数据"),
             "unknown": ("st-unknown", "本轮获取：状态未知")}
    cls, txt = words.get(st, ("st-unknown", "本轮获取：状态未知"))
    return f'<div class="q-chip {cls}">{txt}</div>'


def _compute_chip(status, target: str) -> str:
    """A2-SEARCH-03 round-2：指数计算四态 chip（ok/failed/skipped/缺键=未知）。

    只读 write_run_status 聚合的 compute 段，不做推定；无本轮状态返回空串。
    """
    if not isinstance(status, dict):
        return ""
    comp = status.get("compute") or {}
    raw = comp.get(target)
    if not isinstance(raw, dict) or raw.get("status") is None:
        return '<div class="q-chip st-unknown">指数计算：状态未知</div>'
    st = raw.get("status")
    if st == "ok":
        return '<div class="q-chip ok st-ok">指数计算：已完成</div>'
    if st == "failed":
        return '<div class="q-chip bad st-fail">指数计算：未完成 · 下方为最近一次成功数据</div>'
    if st == "skipped":
        return '<div class="q-chip st-wait">指数计算：未执行</div>'
    return '<div class="q-chip st-unknown">指数计算：状态未知</div>'


def _view_banner(view: dict) -> str:
    """产品自身数据横幅（锚周异常/较新失败，来自 flu_block），注入对应模板。"""
    b = view.get("banner")
    return f'<div class="banner">⚠ {b}</div>' if b else ""


def _slot_templates(views: dict, cards: dict, status=None) -> dict:
    """A2 design r4 §3：槽位名 → 服务端预渲染卡片片段。

    JS 只按配方（recipes-data）克隆模板，不计算任何数据口径；
    槽位名与 src/search_catalog.py recipe() 白名单逐字对齐。
    """
    hlj_flu = (flu_body_html(views["flu_hlj"]) + _view_banner(views["flu_hlj"])
               + _src_chip(status, "heilongjiang_flu")
               + _compute_chip(status, "heilongjiang"))
    hlj_sent = cards["hlj_sent"] + _src_chip(status, "heilongjiang_sentinel")
    south_body = (cards["flu_south"] + _view_banner(views["flu_south"])
                  + _src_chip(status, "flu_south")
                  + _compute_chip(status, "south"))
    north_body = (cards["flu_north"] + _view_banner(views["flu_north"])
                  + _src_chip(status, "flu_north")
                  + _compute_chip(status, "north"))
    chip_sent = _src_chip(status, "sentinel")
    prov_note = '<div class="src">省级数据 · 非该市实测：</div>'
    return {
        "local_hlj_flu": _card(CARD_TITLES["flu_hlj"], hlj_flu),
        "local_hlj_sent": _card(CARD_TITLES["hlj_sent"], hlj_sent),
        "prov_hlj_flu": _card("黑龙江流感指数 · 省级参考（非该市实测）",
                              prov_note + hlj_flu),
        "prov_hlj_sent": _card("黑龙江哨点监测 · 省级参考（非该市实测）",
                               prov_note + hlj_sent),
        "zone_flu_south": _card(CARD_TITLES["flu_south"], south_body),
        "zone_flu_north": _card(CARD_TITLES["flu_north"], north_body),
        "zone_names_south": _card(CARD_TITLES["names_south"],
                                  cards["names_south"] + chip_sent),
        "zone_names_north": _card(CARD_TITLES["names_north"],
                                  cards["names_north"] + chip_sent),
        "national_rank": _card(CARD_TITLES["rank"],
                             cards["rank"] + chip_sent),
        "cq_links": _card(CARD_TITLES["cq"], cards["cq"]),
        "local_nodata": _card(
            "当地监测数据",
            '<div class="big nodata">—</div>'
            '<div class="meta"><span class="tag">本工具未取得该地区官方监测数据</span></div>'
            '<div class="src">目录覆盖不等于数据覆盖；下方省级 / 片区 / 全国块为参考，非当地实测。</div>'),
        "prov_nodata": _card(
            "省级参考",
            '<div class="big nodata">—</div>'
            '<div class="meta"><span class="tag">本工具未取得该省省级监测数据</span></div>'),
    }

def render(opts=None) -> None:
    global RUN_STATUS
    opts = opts or {"local": "--local" in sys.argv, "run_status": None, "run_id": None}
    if opts.get("run_status"):
        RUN_STATUS = Path(opts["run_status"]).resolve()
        if not RUN_STATUS.exists():
            print(f"显式状态文件不存在：{RUN_STATUS}", file=sys.stderr)
            raise SystemExit(2)
    elif not opts.get("local") and RUN_STATUS.exists():
        # 云端无显式状态：只读已保存状态作历史运行信息，绝不称"本次"
        try:
            import json as _json
            if _json.loads(RUN_STATUS.read_text(encoding="utf-8")).get("schema") == 2:
                opts = dict(opts, run_id="__history__")
        except Exception:
            pass

    # 状态一次载入（复核 IMP-04）：本地管线显式传入 pre_status 时也显示本轮横幅
    status_obj = None
    if opts.get("run_status") or (not opts.get("local") and RUN_STATUS.exists()):
        try:
            import json as _json
            status_obj = _json.loads(RUN_STATUS.read_text(encoding="utf-8"))
        except Exception:
            status_obj = "bad"
    # 显式状态完整校验（复核 IMP-04 round-3 关闭条件）：显式传入的状态
    # 必须完整满足 v2 契约——可解析 JSON 对象 + schema==2 + run_id 匹配 +
    # origin 合法 + sources 结构存在。显式状态来自同一条管线，不完整说明
    # 管线已损坏，拒绝构建而不是含糊降级出页；无显式状态的本地/云端路径
    # 不受影响（本地ℹ注明、云端坏文件按"无法解析"横幅诚实降级）。
    if opts.get("run_status"):
        if not isinstance(status_obj, dict) or status_obj == "bad":
            print("显式状态文件不可解析或不是 JSON 对象，拒绝构建", file=sys.stderr)
            raise SystemExit(2)
        if status_obj.get("schema") != RUN_STATUS_V2:
            print(f"显式状态 schema 不符（期望 {RUN_STATUS_V2}，"
                  f"得到 {status_obj.get('schema')!r}），拒绝构建", file=sys.stderr)
            raise SystemExit(2)
        if status_obj.get("run_id") != opts.get("run_id"):
            print(f"状态文件 run_id {status_obj.get('run_id')!r} 与参数 "
                  f"{opts.get('run_id')!r} 不符，拒绝构建", file=sys.stderr)
            raise SystemExit(2)
        if status_obj.get("origin") not in ("local", "cloud"):
            print(f"显式状态 origin 无效：{status_obj.get('origin')!r}，拒绝构建",
                  file=sys.stderr)
            raise SystemExit(2)
        if not isinstance(status_obj.get("sources"), dict):
            print("显式状态缺少 sources 结构，拒绝构建", file=sys.stderr)
            raise SystemExit(2)

    # 视图一次构建：index 与 south 頁共用同一南方片规范化视图（同 CSV 同锚周）
    south_view = build_flu_view(read_csv(FLU_CSV))
    north_view = build_flu_view(read_csv(FLU_NORTH_CSV),
                                "north_ili_pct", "north_flu_positive_pct")
    views = {
        "flu_south": flu_block(south_view, "south"),
        "flu_north": flu_block(north_view, "north"),
        "flu_hlj": flu_block(None, "heilongjiang"),
        "flu_south_view": south_view,
        "flu_north_view": north_view,
    }
    cards, available = _build_cards(views)

    banner_html = (f'<div class="banner">⚠ {views["flu_south"]["banner"]}</div>'
                   if views["flu_south"].get("banner") else "")
    gen = date.today().isoformat()

    # A2 搜索版（design r4 §2）：目录契约不符即构建失败（评审计数断言前置）
    import search_catalog as _scat
    by_id = _scat.load_catalog()
    recipes = {uid: _scat.recipe(uid, by_id)
               for uid, u in by_id.items() if u["queryable"]}
    templates_html = "".join(
        f'<template id="tpl-{name}">{body}</template>'
        for name, body in _slot_templates(views, cards,
                                          status_obj).items())

    outdir = OUT.parent
    outdir.mkdir(parents=True, exist_ok=True)
    # 单页版同样先暂存、整体校验、再原子替换（A2 复核 IMP-06：生成途中
    # 失败不得留下新旧混版）；暂存目录每轮唯一，finally 只清理自己的
    import shutil
    import uuid as _uuid
    stage = outdir / f".tmp_build_stage_{os.getpid()}_{_uuid.uuid4().hex[:8]}"
    stage.mkdir(parents=True)
    try:
        default_cards = "\n".join(
            _card(CARD_TITLES[k], cards[k])
            for k in ("sc", "flu_south", "hist_south", "rank", "trend", "child")
            if k not in available)
        html = PAGE_TPL.format(
            title=_esc("成都 · 呼吸道防护参考"),
            h1=_esc("成都 · 呼吸道防护参考"),
            sub=_esc("分块证据 · 各自口径 · 不合成总分"),
            searchbox=_search_scaffold(),
            run_banner=run_banner(local=opts.get("local", False),
                                  run_id=opts.get("run_id"), page="index",
                                  status=status_obj),
            banner=banner_html, cards=default_cards,
            templates=templates_html,
            catalog_data=_embed_json(_scat.embedded_json(by_id)),
            recipes_data=_embed_json(recipes),
            search_js=SEARCH_JS,
            foot=FOOT_CD + FOOT_COMMON, gen=gen,
            css=CSS_THEME)
        spath = stage / "index.html"
        spath.write_text(html, encoding="utf-8")
        _validate_pages(stage)
        os.replace(spath, OUT)
        print(f"已生成 {OUT}")
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _validate_pages(stage_dir) -> None:
    """单页完整性与资源/链接校验（A2 design r4 §5）。

    - 允许内联脚本与内嵌 JSON（S2 交互脚本），禁止外部脚本/运行时请求：
      `<script src` / `fetch(` / `@import` / `url(http` 任一出现即失败。
    - 站内链接仅限本页锚点（单页版无站内跳转；外链仍限官方来源）。
    - 目录/配方/关键模板三要素齐全，缺一即失败。
    - 复核 A2-SEARCH-04：实际解析 stage 页里的 catalog-data / recipes-data JSON，
      断言目录行数=400、模板 ID 不重复、每个配方引用的槽位都有对应模板
      （chengdu_default 例外：它就是成都默认视图本身，不需要独立模板），
      且每个模板至少被一个配方引用（防止残留/失效模板悄悄留在页面上）。
    """
    import json as _json
    import re as _re
    spath = stage_dir / "index.html"
    if not spath.exists():
        raise SystemExit("页面校验失败：暂存目录缺 index.html")
    html = spath.read_text(encoding="utf-8")
    for bad in ("<script src", "fetch(", "@import", "url(http"):
        if bad in html:
            raise SystemExit(f"页面校验失败：index.html 含禁止资源引用 {bad!r}")
    pat = _re.compile(r"""href=(["'])([^"']+)\1""")
    for _q, href in pat.findall(html):
        if "://" in href or href.startswith(("mailto:", "tel:")):
            continue
        if href.split("#")[0].strip():
            raise SystemExit(f"页面校验失败：内链 {href} 不是本页锚点（单页版无站内跳转）")
    for tid in ('id="catalog-data"', 'id="recipes-data"',
                'id="tpl-local_nodata"', 'id="tpl-zone_flu_south"',
                'id="tpl-national_rank"'):
        if tid not in html:
            raise SystemExit(f"页面校验失败：缺少 {tid}")

    def _embedded_json(element_id):
        m = _re.search(
            r'<script type="application/json" id="%s">(.*?)</script>' % element_id,
            html, _re.S,
        )
        if not m:
            raise SystemExit(f"页面校验失败：无法定位内嵌 JSON {element_id}")
        try:
            return _json.loads(m.group(1))
        except ValueError as exc:
            raise SystemExit(f"页面校验失败：{element_id} 不是合法 JSON（{exc}）")

    catalog = _embedded_json("catalog-data")
    recipes = _embedded_json("recipes-data")
    if not isinstance(catalog, list) or len(catalog) != 400:
        raise SystemExit(
            f"页面校验失败：目录行数 {len(catalog) if isinstance(catalog, list) else '非列表'}"
            f" ≠ 400"
        )
    if not isinstance(recipes, dict) or not recipes:
        raise SystemExit("页面校验失败：配方为空或结构非法")

    tpl_ids = _re.findall(r'<template id="tpl-([^"]+)">', html)
    if len(tpl_ids) != len(set(tpl_ids)):
        dup = sorted({t for t in tpl_ids if tpl_ids.count(t) > 1})
        raise SystemExit(f"页面校验失败：模板 ID 重复 {dup}")
    tpl_set = set(tpl_ids)

    used = set()
    for unit_id, slots in recipes.items():
        if not isinstance(slots, list) or not slots:
            raise SystemExit(f"页面校验失败：配方 {unit_id} 槽位为空")
        for slot in slots:
            if slot == "chengdu_default":
                continue
            used.add(slot)
            if slot not in tpl_set:
                raise SystemExit(
                    f"页面校验失败：配方 {unit_id} 引用槽位 {slot!r} 但页面无 "
                    f"tpl-{slot} 模板"
                )
    orphan = sorted(tpl_set - used)
    if orphan:
        raise SystemExit(f"页面校验失败：模板无人引用 {orphan}")


if __name__ == "__main__":
    render(_cli_opts(sys.argv[1:]))

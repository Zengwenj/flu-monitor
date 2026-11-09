# -*- coding: utf-8 -*-
"""渲染分块证据页 site/index.html（M3b 阶段二仪表盘）。

契约（M2 r3 + M3b design）：
- 方式 A：字符串插值直接渲染进 HTML（无独立 JSON、无 fetch），file:// 可离线打开
- 零外部依赖：趋势图为纯 Python 生成的内联 SVG（无 JS/Canvas/图表库）
- 分块不合成总分（D14）；状态文案只用枚举；口径标注齐全（D15）
- 页面取数规则 3：流感数值/指数取最新 status=ok 行；更晚失败行 → 失败横幅
"""
import csv
import sys
from datetime import date
from pathlib import Path

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


def flu_block() -> dict:
    rows = read_csv(FLU_CSV)
    ok = [r for r in rows if r["status"] == "ok"]
    fail = [r for r in rows if r["status"] != "ok"]
    if not ok:
        return {"state": "empty"}
    latest = max(ok, key=lambda r: (int(r["iso_year"]), int(r["iso_week"])))
    banner = ""
    later_fail = [r for r in fail
                  if (int(r["iso_year"]), int(r["iso_week"])) >
                  (int(latest["iso_year"]), int(latest["iso_week"]))]
    if later_fail:
        banner = f"最新一期获取失败 · 显示上次成功数据（{latest['iso_week']}周）"
    elif fail:
        banner = "最新一期解析失败 · 请人工核对官网"
    prev = [r for r in ok
            if (int(r["iso_year"]), int(r["iso_week"])) <
            (int(latest["iso_year"]), int(latest["iso_week"]))]
    mom = "首期数据 · 下次运行后显示环比" if not prev else \
        f"较上周 {('↑' if float(latest['goldstein_index'] or 0) > float(max(prev, key=lambda r:(int(r['iso_year']),int(r['iso_week'])))['goldstein_index'] or 0) else ('↓' if float(latest['goldstein_index'] or 0) < float(max(prev, key=lambda r:(int(r['iso_year']),int(r['iso_week'])))['goldstein_index'] or 0) else '→'))}" if prev and all(r["goldstein_index"] for r in [latest]+prev[-1:]) else "环比见多病原排行"
    return {"state": "ok", "banner": banner, **latest,
            "line": f"数据正常 · 第{latest['iso_week']}周 · 来源发布 {latest['source_pubdate']}",
            "mom": mom, "yoy": "暂无往年同期数据"}


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
    <h2>本周 vs 往年同期</h2>
    <div class="big">…</div>
    <div class="meta"><span class="tag">待历史回补后启用</span></div>
    <div class="src">需回补流感周报历史（约150期）后按周对比 · 当前不做多年曲线（数据不足且口径禁止混用）</div>
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


def render() -> None:
    flu = flu_block()
    sc = sichuan_block()

    if flu["state"] == "ok":
        flu_body = f"""
    <div class="big">{flu['goldstein_index']}<span class="unit"> Goldstein 指数（相对强度）</span></div>
    <div class="kv">
      <span>ILI% <b>{flu['south_ili_pct']}%</b></span>
      <span>流感阳性率 <b>{flu['south_flu_positive_pct']}%</b></span>
      <span>第<b>{flu['iso_week']}</b>周</span>
    </div>
    <div class="meta"><span class="tag">{flu['line']}</span><span class="tag">{flu['mom']}</span><span class="tag">{flu['yoy']}</span></div>
    <div class="src">来源：国家流感中心《中国流感监测周报》 <a href="{flu['source_url']}" target="_blank">当期文章</a></div>"""
    else:
        flu_body = """<div class="big">—</div><div class="meta"><span class="tag">暂无数据 · 请运行更新</span></div>"""

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
                      sc_body=sc_body, rank_body=ranking_block(),
                      trend_body=trend_block(), child_body=child_block(),
                      gen=date.today().isoformat())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"已生成 {OUT}")


if __name__ == "__main__":
    render()

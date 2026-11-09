# -*- coding: utf-8 -*-
"""渲染 M2 极简分块证据页 site/index.html。

r3 契约：
- 方式 A：字符串插值直接渲染进 HTML 模板（无独立 JSON、无 fetch），file:// 可离线打开
- 页面取数规则 3：流感数值/指数取最新 status=ok 行；若存在更晚周次的失败行 → 叠加失败横幅
- 状态文案只使用 design.md 附录枚举（不得自拟）；防护建议只引官方原文并标出处
"""
import csv
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLU_CSV = ROOT / "data" / "flu_south.csv"
SC_CSV = ROOT / "data" / "sichuan_monthly.csv"
OUT = ROOT / "site" / "index.html"

# 官方原文（四川流感指数分级标准表 IV 级防控建议，M1 逐字提取自
# https://www.sccdc.cn/Article/View?id=39284 附图，出处标注在页面）
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
        banner = f"最新一期解析失败 · 请人工核对官网"
    # 枚举：正常 / 首期无环比 / 无往年
    return {"state": "ok", "banner": banner, **latest,
            "line": f"数据正常 · 第{latest['iso_week']}周 · 来源发布 {latest['source_pubdate']}",
            "mom": "首期数据 · 下次运行后显示环比",
            "yoy": "暂无往年同期数据"}


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
  .foot{{font-size:11px;color:#aaa;margin:16px 0;line-height:1.6}}
</style>
</head>
<body>
<div class="wrap">
  <h1>成都 · 呼吸道防护参考</h1>
  <div class="sub">分块证据 · 各自口径 · 不合成总分</div>
  {banner}
  <div class="card">
    <h2>南方片流感趋势（周度）</h2>
    {flu_body}
  </div>
  <div class="card">
    <h2>四川官方流感分级（月度 · 成都=平原区）</h2>
    {sc_body}
  </div>
  <div class="foot">
    口径说明：流感数值为南方片哨点监测（周度，非成都市实测）；四川分级为省疾控五大区域之平原区（月度）。
    Goldstein 指数为相对强度指数（ILI%×阳性率），非人群感染率。
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
    html = TPL.format(banner=banner_html, flu_body=flu_body,
                      sc_body=sc_body,
                      gen=date.today().isoformat())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"已生成 {OUT}")


if __name__ == "__main__":
    render()

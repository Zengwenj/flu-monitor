# -*- coding: utf-8 -*-
"""计算层。

M2 部分（不动）：南方片 Goldstein 指数（ILI% × 流感阳性率，数值直乘）写回 flu_south.csv。
M3b 扩展：多病原排行 / 儿童分龄前三 / 病原趋势序列——读 M3a 产出的 CSV，
产出内存汇总结构供 build_site.py 调用（不写中间 CSV）。
契约：.trellis/tasks/11-06-disease-monitor/design.md（M3b）。
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "flu_south.csv"
RATES_CSV = ROOT / "data" / "sentinel_national_rates.csv"
RANK_CSV = ROOT / "data" / "sentinel_rank.csv"


# ---------------- M3b：多病原 / 儿童 / 趋势 汇总 ----------------

def _read(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _wk(r) -> tuple:
    return (int(r["iso_year"]), int(r["iso_week"]))


def _arrow(delta: str) -> str:
    """较上周方向（D17：箭头仅表环比）。空串=未提供。"""
    if not delta:
        return "—"
    d = float(delta)
    return "↑" if d > 0 else ("↓" if d < 0 else "→")


def pathogen_ranking() -> dict:
    """最新 ok 周的 11 病原门急诊阳性率降序排行。"""
    rows = [r for r in _read(RATES_CSV) if r["status"] == "ok"]
    if not rows:
        return {"available": False, "reason": "无数据"}
    y, w = max(_wk(r) for r in rows)
    cur = [r for r in rows if _wk(r) == (y, w) and r["setting"] == "门急诊"]
    cur.sort(key=lambda r: -float(r["positive_pct"]))
    return {"available": True, "year": y, "week": w,
            "rows": [{"pathogen": r["pathogen"],
                      "pct": r["positive_pct"],
                      "arrow": _arrow(r["delta_last_week"])} for r in cur]}


def child_rank() -> dict:
    """最新周的 0-4/5-14 岁门急诊前三。
    目标周（全表最新周）为 rank_unavailable → 返回 available:False（不静默回退更早周，B3）。"""
    rows = _read(RANK_CSV)
    ok = [r for r in rows if r["status"] == "ok" and r["dimension"] == "age"
          and r["category"] in ("0～4岁", "5～14岁") and r["setting"] == "门急诊"]
    unav = [r for r in rows if r["status"] == "rank_unavailable"]
    ok_w = max((_wk(r) for r in ok), default=None)
    unav_w = max((_wk(r) for r in unav), default=None)
    # 最新周是占位（比任何 ok 排序都晚）→ 不可用，显式返回原因
    if unav_w is not None and (ok_w is None or unav_w > ok_w):
        return {"available": False, "year": unav_w[0], "week": unav_w[1],
                "reason": "该期排序未获取（官方版式差异/月度合并版）"}
    if ok_w is None:
        return {"available": False, "reason": "无排序数据"}
    y, w = ok_w
    out = {"available": True, "year": y, "week": w, "groups": {}}
    for cat in ("0～4岁", "5～14岁"):
        g = [r for r in ok if _wk(r) == (y, w) and r["category"] == cat]
        if g:
            out["groups"][cat] = [g[0]["rank1"], g[0]["rank2"], g[0]["rank3"]]
    return out


def pathogen_trend(pathogen: str) -> list:
    """某病原逐周门急诊阳性率序列（升序），供趋势图。缺周=列表中无该周（断点）。"""
    rows = [r for r in _read(RATES_CSV)
            if r["status"] == "ok" and r["setting"] == "门急诊"
            and r["pathogen"] == pathogen]
    return sorted([(_wk(r), float(r["positive_pct"])) for r in rows])


# ---------------- M2：Goldstein（原逻辑不动） ----------------

def main() -> None:
    if not CSV_PATH.exists():
        raise SystemExit("data/flu_south.csv 不存在，先运行 fetch_flu_south.py")
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    changed = 0
    for r in rows:
        if r["status"] != "ok" or not r["south_ili_pct"] or not r["south_flu_positive_pct"]:
            if r.get("goldstein_index"):
                r["goldstein_index"] = ""
            continue
        ili = float(r["south_ili_pct"])
        pos = float(r["south_flu_positive_pct"])
        val = ili * pos
        r["goldstein_index"] = f"{val:.2f}"
        print(f"[指数] {r['iso_year']}W{r['iso_week']}: {ili} × {pos} = {val:.2f}")
        changed += 1
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"完成：{changed} 行已写回 goldstein_index")


if __name__ == "__main__":
    main()

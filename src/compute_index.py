# -*- coding: utf-8 -*-
"""计算层。

M2 部分（南方逻辑不变）：南方片 Goldstein 指数（ILI% × 流感阳性率，数值直乘）写回 flu_south.csv。
M3b 扩展：多病原排行 / 儿童分龄前三 / 病原趋势序列——读 M3a 产出的 CSV，
产出内存汇总结构供 build_site.py 调用（不写中间 CSV）。
契约：.trellis/tasks/11-06-disease-monitor/design.md（M3b）。

A2 扩展（.trellis/tasks/11-12-regional-monitor/design.md §2.1/§5）：
- compute_file(path, ili_field, positive_field) 逐产品验证+原子写；
  单文件内非法成功行 → 该文件失败原文件不动，其他目标继续
- CLI 新增 --targets south,north,heilongjiang [--result-file ... --run-id ...]；
  无参仍是仅 south（旧输出兼容）
"""
import csv
import json
import sys
from pathlib import Path

import data_io

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "flu_south.csv"
NORTH_CSV = ROOT / "data" / "flu_north.csv"
HLJ_CSV = ROOT / "data" / "heilongjiang_flu.csv"
RATES_CSV = ROOT / "data" / "sentinel_national_rates.csv"
RANK_CSV = ROOT / "data" / "sentinel_rank.csv"

# A2 计算目标注册表：名称 → (路径, ILI 字段, 阳性率字段)
TARGETS = {
    "south": (CSV_PATH, "south_ili_pct", "south_flu_positive_pct"),
    "north": (NORTH_CSV, "north_ili_pct", "north_flu_positive_pct"),
    "heilongjiang": (HLJ_CSV, "ili_pct", "flu_positive_pct"),
}


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


# ---------------- M2/A2：Goldstein ----------------

def compute_file(path: Path, ili_field: str, positive_field: str,
                 label: str = "", quiet: bool = False) -> dict:
    """单产品指数计算：验证全部行 → 原子写回。失败抛前不落盘，原文件不动。

    - 行为与旧南方 main() 一致：ok 行且两数值齐 → round(ili*pos,2) 写 goldstein_index；
      非 ok 或数值缺 → 置空 goldstein_index
    - A2 收紧：ok 行数值不可解析 / 非有限 / 越界 [0,100] → 整文件计算失败
      （design §2.1），绝不把半算好的表写回
    """
    if not path.exists():
        return {"status": "unknown", "reason": f"数据文件不存在: {path.name}",
                "target": label}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    for need in (ili_field, positive_field, "goldstein_index", "status"):
        if need not in (fields or []):
            return {"status": "failed",
                    "reason": f"{path.name} 缺列 {need}", "target": label}
    changed = 0
    for r in rows:
        if r["status"] != "ok":
            if r.get("goldstein_index"):
                r["goldstein_index"] = ""
            continue
        # ok 行 = 本工具已验证完整的数据行：两数值缺任一即整文件失败，
        # 不允许"ok 但数值空、指数置空"的静默降级（A2 复核阻塞项）
        if not r.get(ili_field) or not r.get(positive_field):
            return {"status": "failed",
                    "reason": f"{r.get('iso_year')}W{r.get('iso_week')} "
                              f"ok 行缺数值（{ili_field}/{positive_field} 有空值）",
                    "target": label}
        try:
            ili = float(r[ili_field])
            pos = float(r[positive_field])
        except ValueError as e:
            return {"status": "failed",
                    "reason": f"{r['iso_year']}W{r['iso_week']} 数值不可解析: {e}",
                    "target": label}
        for name, v in (("ILI%", ili), ("阳性率", pos)):
            if v != v or v in (float("inf"), float("-inf")) or not 0 <= v <= 100:
                return {"status": "failed",
                        "reason": f"{r['iso_year']}W{r['iso_week']} {name}={v} 非法",
                        "target": label}
        val = ili * pos
        r["goldstein_index"] = f"{val:.2f}"
        if not quiet:
            print(f"[指数]{('[' + label + ']') if label else ''} "
                  f"{r['iso_year']}W{r['iso_week']}: {ili} × {pos} = {val:.2f}")
        changed += 1
    data_io.atomic_write_csv(path, fields, rows)
    if not quiet:
        print(f"完成{('（' + label + '）') if label else ''}：{changed} 行已写回 goldstein_index")
    return {"status": "ok", "computed": changed, "target": label}


def main() -> None:
    argv = sys.argv[1:]
    if not argv:
        res = compute_file(CSV_PATH, "south_ili_pct", "south_flu_positive_pct")
        if res["status"] != "ok":
            raise SystemExit(f"[指数] south 计算失败: {res.get('reason')}")
        return
    # A2 显式目标模式：--targets south,north,heilongjiang
    if argv[0] != "--targets":
        raise SystemExit(f"未知参数: {argv[0]}（用法：无参=仅south；--targets a,b,c）")
    if len(argv) < 2 or not argv[1] or argv[1].startswith("--"):
        raise SystemExit("--targets 需要逗号分隔的目标名（south/north/heilongjiang）")
    targets, result_file, run_id = argv[1], None, None
    it = iter(argv[2:])
    for a in it:
        if a == "--result-file":
            v = next(it, "")
            result_file = Path(v) if v else None
        elif a == "--run-id":
            run_id = next(it, "")
        else:
            raise SystemExit(f"未知参数: {a}")
    names = [t.strip() for t in (targets or "").split(",") if t.strip()]
    if not names:
        raise SystemExit("--targets 需要逗号分隔的目标名（south/north/heilongjiang）")
    bad = [t for t in names if t not in TARGETS]
    if bad:
        raise SystemExit(f"未知目标: {bad}（可选 {sorted(TARGETS)}）")
    results = {}
    ok_all = True
    for name in names:
        path, ili_f, pos_f = TARGETS[name]
        # 逐目标隔离：单目标读取/IO/替换异常不阻断其余目标（A2 复核阻塞项）
        try:
            res = compute_file(path, ili_f, pos_f, label=name, quiet=False)
        except Exception as e:  # OSError / csv.Error / 原子替换失败等
            res = {"status": "failed", "reason": f"{type(e).__name__}: {e}",
                   "target": name}
        results[name] = res
        if res["status"] != "ok":
            ok_all = False
            print(f"[指数][{name}] {res['status']}: {res.get('reason', '')}",
                  file=sys.stderr)
    if result_file:
        payload = {"schema": 2, "stage": "compute", "run_id": run_id or "",
                   "targets": results}
        data_io.atomic_write_text(result_file,
                                  json.dumps(payload, indent=2, ensure_ascii=False))
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""计算南方片 Goldstein 指数（ILI% × 流感阳性率，数值直乘）并写回 flu_south.csv。

M2 r3 契约：goldstein_index 写回 data/flu_south.csv 的 goldstein_index 列（唯一产物形式，
页面只从该列读）。仅计算 status=ok 且两数值列非空的行；其余行保持为空。
指数为相对强度指数（WHO PISA Goldstein index），非人群感染率——页面侧负责标注。
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "flu_south.csv"


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

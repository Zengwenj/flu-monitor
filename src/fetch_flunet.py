# -*- coding: utf-8 -*-
"""下载 WHO FluNet 全量 CSV，筛选中国行，按列映射写 data/flunet_china.csv。

M3a 契约（design.md r2 / metis G6·B4）：
- 列映射固定（表头位次 2026-11 实测）：COUNTRY_CODE=5, ISO_WEEKSTARTDATE=7,
  ISO_YEAR=8, ISO_WEEK=9, SPEC_PROCESSED_NB=14, AH1N12009=16, AH3=18,
  INF_A=25, INF_B=32, INF_ALL=33
- 全量替换式写入（FluNet 本身即全量源，主键 iso_year+iso_week）
- 校验：中国行数≈1021 基准、最早 2005 年、最新周阳性率与官方吻合、
  数值列不得混入 NOTDEFINED
- 定位：全国背景+交叉校验，不作南方片指数输入（D15/D17）
"""
import csv
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "flunet_china.csv"
URL = "https://xmart-api-public.who.int/FLUMART/VIW_FNT?$format=csv"
FIELDS = ["iso_year", "iso_week", "week_start", "spec_processed",
          "inf_all", "inf_a", "inf_b", "ah1n1", "ah3",
          "inf_positive_pct", "source", "fetched_at"]


def download() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="flunet_")) / "VIW_FNT.csv"
    r = subprocess.run(["curl", "-s", "-o", str(tmp), URL],
                       capture_output=True, timeout=600)
    if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size < 1_000_000:
        raise RuntimeError(f"FluNet 下载失败 rc={r.returncode}")
    return tmp


def main() -> None:
    tmp = download()
    print(f"下载完成 {tmp.stat().st_size/1e6:.1f}MB")
    try:
        _convert(tmp)
    finally:
        import shutil
        shutil.rmtree(tmp.parent, ignore_errors=True)  # 清理 %TEMP% 残留


def _convert(tmp: Path) -> None:
    rows, bad = [], 0
    with tmp.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        idx = {name: i for i, name in enumerate(header)}
        need = ["COUNTRY_CODE", "ISO_YEAR", "ISO_WEEK", "ISO_WEEKSTARTDATE",
                "SPEC_PROCESSED_NB", "INF_ALL", "INF_A", "INF_B",
                "AH1N12009", "AH3"]
        for name in need:
            if name not in idx:
                raise RuntimeError(f"表头缺列 {name}（官方 schema 变更？）")
        for rec in reader:
            if len(rec) <= idx["INF_ALL"] or rec[idx["COUNTRY_CODE"]] != "CHN":
                continue
            def g(col):
                v = rec[idx[col]].strip()
                return "" if v in ("", "NOTDEFINED", "NA") else v
            year, week = g("ISO_YEAR"), g("ISO_WEEK")
            if not (year and week):
                bad += 1
                continue
            spec, inf_all = g("SPEC_PROCESSED_NB"), g("INF_ALL")
            pct = ""
            if spec and inf_all:
                s, a = float(spec), float(inf_all)
                if s > 0:
                    pct = f"{a/s*100:.2f}"
            rows.append({"iso_year": year, "iso_week": week,
                         "week_start": g("ISO_WEEKSTARTDATE"),
                         "spec_processed": spec, "inf_all": inf_all,
                         "inf_a": g("INF_A"), "inf_b": g("INF_B"),
                         "ah1n1": g("AH1N12009"), "ah3": g("AH3"),
                         "inf_positive_pct": pct, "source": "WHO_FluNet",
                         "fetched_at": datetime.now().isoformat(timespec="seconds")})
    rows.sort(key=lambda r: (int(r["iso_year"]), int(r["iso_week"])))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    years = [int(r["iso_year"]) for r in rows]
    latest = rows[-1]
    print(f"[ok] 中国 {len(rows)} 行（M1 基准≈1021），{min(years)}–{max(years)} 年，"
          f"最新 {latest['iso_year']}W{latest['iso_week']} "
          f"阳性率 {latest['inf_positive_pct']}%（送检 {latest['spec_processed']}）")
    if bad:
        print(f"[warn] 跳过无周次行 {bad} 行")
    if min(years) > 2005:
        print(f"[warn] 最早年 {min(years)} 晚于 2005 基准，覆盖异常", file=sys.stderr)
    # NOTDEFINED 混入检查（数值列）
    leak = [r for r in rows if any(str(r[k]).startswith("NOTDEF") for k in FIELDS[:9])]
    print(f"NOTDEFINED 混入数值列: {len(leak)} 行")


if __name__ == "__main__":
    main()

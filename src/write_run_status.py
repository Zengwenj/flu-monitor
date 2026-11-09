# -*- coding: utf-8 -*-
"""写 data/run_status.json：记录本次运行各数据源状态（M4b / momus B1）。

由 weekly.yml 在抓取步骤后调用，环境变量传入各 step outcome：
  SENT / FLU / FLUNET（GitHub step outcome: success/failure/skipped/cancelled）
  REACH（CHINACDC_REACHABLE: true/false）
本地 run_local 不调用本脚本（无 run_status.json → 页面不显"本次未获取"横幅）。
"""
import json
import os
from datetime import datetime
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "run_status.json"


def norm(outcome: str) -> str:
    if outcome in ("success", None) or outcome == "":
        return "ok"
    if outcome == "skipped":
        return "skipped"
    return "failed"


def main() -> None:
    reach = os.environ.get("REACH", "false")
    status = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "chinacdc_reachable": reach == "true",
        "sources": {
            "flu_south": norm(os.environ.get("FLU", "skipped" if reach != "true" else "")),
            "sentinel": norm(os.environ.get("SENT", "skipped" if reach != "true" else "")),
            "flunet": norm(os.environ.get("FLUNET", "")),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print("run_status:", json.dumps(status, ensure_ascii=False))


if __name__ == "__main__":
    main()

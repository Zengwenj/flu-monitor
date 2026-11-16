#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""聚合本轮运行状态（A2 design §4）。schema 2。

两种入口：
1) v2（新管线）：
   python -X utf8 src/write_run_status.py --run-dir .tmp_pipeline/<run_id> \
       --run-id <run_id> --origin local|cloud --out <path> [--build-exit N]
   读取 run-dir 内 manifest.json 与各子进程结果文件，逐源校验后给出
   ok / failed / skipped / unknown；无结果、坏 JSON、run_id 不符、超时终止、
   结构校验不通过一律不推定 ok。--build-exit 未提供或非 0 时 complete=false。
2) legacy（weekly.yml 旧环境变量入口）：
   保留可用，但空 outcome 不再默认为 ok（改为 unknown）。
"""
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "run_status.json"

OK, FAILED, SKIPPED, UNKNOWN = "ok", "failed", "skipped", "unknown"
SOURCE_KEYS = ["flu_south", "flu_north", "heilongjiang_flu", "heilongjiang_sentinel",
               "sentinel", "flunet"]
COMPUTE_KEYS = ["south", "north", "heilongjiang"]


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ---------------- v2 校验 ----------------

def load_json(path):
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def step_of(manifest, name):
    if not isinstance(manifest, dict):
        return None
    steps = manifest.get("steps")
    if not isinstance(steps, list):
        return None
    # 复核 IMP-14 round-3：条目非 dict → 整份 manifest 视为损坏返回 None。
    # manifest 只由本管线写入（应为全 dict 条目）；出现非 dict 说明写入中断
    # 或文件损坏，该步按"未执行"降级为 unknown，不做局部拣选。
    if not all(isinstance(s, dict) for s in steps):
        return None
    for s in steps:
        if s.get("name") == name:
            return s
    return None


def read_result(run_dir, filename, run_id, expect_stage=None, origin=None):
    """子进程结果文件必须 schema=2、run_id 匹配、stage 如约束；origin 键存在时也须匹配。

    顶层结构不是 JSON 对象（如合法 JSON 数组/字符串）一律判无效（复核 IMP-03 round-2）。
    """
    payload = load_json(Path(run_dir) / filename)
    if not isinstance(payload, dict):
        return None
    if payload.get("schema") != 2 or payload.get("run_id") != run_id:
        return None
    if expect_stage is not None and payload.get("stage") != expect_stage:
        return None
    if origin is not None and "origin" in payload and payload.get("origin") != origin:
        return None
    return payload


def check_csv(path, key_cols, min_rows=1, allow_empty=False):
    p = Path(path)
    if not p.exists():
        return False, "文件不存在"
    try:
        with p.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    except Exception as e:
        return False, f"读取失败 {e}"
    if not rows:
        if allow_empty:
            return True, "空表（本轮确认无记录）"
        # 空表曾被当作成功放过：对 flunet/sentinel 这类必须落历史的源，
        # 空表意味着本轮产物缺失，不能宣称成功
        return False, "空表（本轮无记录，不满足该源最低要求）"
    missing = [c for c in key_cols if c not in rows[0]]
    if missing:
        return False, f"缺列 {missing}"
    if len(rows) < min_rows:
        return False, f"仅 {len(rows)} 行，低于下限 {min_rows}"
    return True, f"{len(rows)} 行"


def judge_direct(manifest, run_dir, run_id, name, checks):
    """无结果文件、直接看 CSV 结构的源（flunet / sentinel）。"""
    step = step_of(manifest, name)
    if step is None:
        return {"status": UNKNOWN, "reason": "未执行"}
    if step.get("timed_out"):
        return {"status": UNKNOWN, "reason": "子进程超时被终止"}
    if step.get("exit") != 0:
        return {"status": FAILED, "reason": f"exit={step.get('exit')}"}
    notes = []
    for path, cols, min_rows in checks:
        ok, note = check_csv(path, cols, min_rows)
        notes.append(note)
        if not ok:
            return {"status": FAILED, "reason": note}
    return {"status": OK, "reason": " / ".join(notes)}


def judge_from_result(payload, key, step=None):
    """结果文件状态必须与子进程终态联合校验（A2 复核阻塞项）：
    - step 缺失 → 未执行（unknown）
    - 子进程超时/被终止 → 结果文件不采信（unknown），ok 也不保留推定
    - exit 0/1 = 正常终态（1 = 允许携带逐产品结果的部分失败），逐产品状态采信；
      exit 非 0/1（崩溃/被杀）→ 结果不采信；exit=1 在 reason 注明部分失败
    """
    if step is None:
        return {"status": UNKNOWN, "reason": "未执行"}
    if step.get("timed_out"):
        return {"status": UNKNOWN, "reason": "子进程超时被终止，结果文件不采信"}
    src = None
    if isinstance(payload, dict):
        got = (payload.get("sources") or {}).get(key) if isinstance(
            payload.get("sources"), dict) else None
        if isinstance(got, dict):
            st = got.get("status")
            if st in (OK, FAILED):
                src = {"status": st}
                for k in ("reason", "week", "rows", "target_week"):
                    if k in got:
                        src[k] = got[k]
            else:
                src = {"status": UNKNOWN, "reason": f"结果内状态异常：{st!r}"}
    if src is None:
        return {"status": UNKNOWN, "reason": "缺/坏结果文件或 run_id/stage 不符"}
    if step.get("exit") not in (0, 1):
        return {"status": UNKNOWN,
                "reason": f"子进程异常退出 exit={step.get('exit')}，结果不采信"}
    if step.get("exit") == 1:
        src = dict(src, reason=f"{src.get('reason', '')}（exit=1 部分失败）")
    return src


def aggregate(manifest, run_dir, run_id):
    """返回 (state, notes)。任何不确定都落 unknown，不推定 ok。"""
    sk = manifest.get("skipped") if isinstance(manifest, dict) else None
    skipped = set(sk) if isinstance(sk, (list, tuple)) else set()
    state = {
        "schema": 2,
        "run_id": run_id,
        "origin": manifest.get("origin"),
        "started_at": manifest.get("started_at"),
        "finished_at": now(),
        "stage": "collect",
        "complete": False,
        "sources": {},
        "compute": {},
    }
    notes = []

    # 1) WHO FluNet（真实列契约：flunet_china.csv 无 pathogen 列，
    #    病原级数据在 sentinel_national_rates.csv，此前错列导致 flunet 永远 failed）
    if "flunet" in skipped:
        state["sources"]["flunet"] = {"status": SKIPPED, "reason": "本轮按 --skip 跳过"}
    else:
        state["sources"]["flunet"] = judge_direct(
            manifest, run_dir, run_id, "flunet",
            [(DATA / "flunet_china.csv",
              ["iso_year", "iso_week", "week_start", "inf_positive_pct"], 800)])

    # 2) 全国哨点
    if "sentinel" in skipped:
        state["sources"]["sentinel"] = {"status": SKIPPED, "reason": "本轮按 --skip 跳过"}
    else:
        state["sources"]["sentinel"] = judge_direct(
            manifest, run_dir, run_id, "sentinel",
            [(DATA / "sentinel_national_rates.csv",
              ["iso_year", "iso_week", "setting", "pathogen", "positive_pct"], 22),
             (DATA / "sentinel_rank.csv",
              ["iso_year", "iso_week", "dimension", "category", "setting"], 1)])

    # 3) 南北双片（同一 PDF，区域各自成败；结果与子进程终态联合校验）
    flu_payload = read_result(run_dir, "fetch_flu.json", run_id,
                              expect_stage="fetch", origin=manifest.get("origin"))
    flu_step = step_of(manifest, "flu")
    for r in ("south", "north"):
        key = f"flu_{r}"
        if key in skipped:
            state["sources"][key] = {"status": SKIPPED, "reason": "本轮按 --skip 跳过"}
            continue
        state["sources"][key] = judge_from_result(flu_payload, key, flu_step)

    # 4) 黑龙江 B1/B2
    hlj_payload = read_result(run_dir, "fetch_hlj.json", run_id,
                              expect_stage="fetch", origin=manifest.get("origin"))
    hlj_step = step_of(manifest, "heilongjiang")
    for key in ("heilongjiang_flu", "heilongjiang_sentinel"):
        if key in skipped:
            state["sources"][key] = {"status": SKIPPED, "reason": "本轮按 --skip 跳过"}
            continue
        state["sources"][key] = judge_from_result(hlj_payload, key, hlj_step)

    # 5) 三个指数产品（计算失败≠抓取成功）
    compute_payload = read_result(run_dir, "compute.json", run_id,
                                  expect_stage="compute", origin=manifest.get("origin"))
    compute_step = step_of(manifest, "compute")
    for t in COMPUTE_KEYS:
        inputs = {"south": ["flu_south"], "north": ["flu_north"],
                  "heilongjiang": ["heilongjiang_flu"]}[t]
        if all(state["sources"].get(i, {}).get("status") == SKIPPED for i in inputs):
            state["compute"][t] = {"status": SKIPPED, "reason": "输入源本轮跳过"}
            continue
        # 计算结果同样受子进程终态约束；exit=1 部分失败时成功目标仍采信
        if compute_step is None:
            state["compute"][t] = {"status": UNKNOWN, "reason": "未执行"}
            continue
        if compute_step.get("timed_out"):
            state["compute"][t] = {"status": UNKNOWN, "reason": "子进程超时被终止，结果文件不采信"}
            continue
        if compute_step.get("exit") not in (0, 1):
            state["compute"][t] = {"status": UNKNOWN,
                                   "reason": f"子进程异常退出 exit={compute_step.get('exit')}，结果不采信"}
            continue
        if compute_payload is None:
            state["compute"][t] = {"status": UNKNOWN,
                                   "reason": "缺/坏结果文件或 run_id/stage 不符"}
            continue
        got = (compute_payload.get("targets") or {}).get(t) if isinstance(
            compute_payload.get("targets"), dict) else None
        if not isinstance(got, dict) or got.get("status") not in (OK, FAILED, UNKNOWN):
            state["compute"][t] = {"status": UNKNOWN, "reason": "结果缺该目标或状态非法"}
        else:
            state["compute"][t] = {k: v for k, v in got.items() if k != "target"}

    bad = [k for k, v in state["sources"].items() if v.get("status") in (FAILED, UNKNOWN)]
    badc = [k for k, v in state["compute"].items() if v.get("status") in (FAILED, UNKNOWN)]
    if bad:
        notes.append(f"源异常：{bad}")
    if badc:
        notes.append(f"计算异常：{badc}")
    return state, notes


def write_out(state, path):
    from data_io import atomic_write_json
    atomic_write_json(Path(path), state)


# ---------------- legacy 入口 ----------------

def norm(outcome):
    """空/未知 outcome 不再默认为 ok（A2 design §4）。"""
    if outcome == "success":
        return OK
    if outcome == "skipped":
        return SKIPPED
    if outcome in (None, ""):
        return UNKNOWN
    return FAILED


def legacy_main():
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
    return 0


# ---------------- main ----------------

def main(argv):
    if not argv:
        return legacy_main()
    run_dir = run_id = origin = out = None
    build_exit = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--run-dir", "--run-id", "--origin", "--out", "--build-exit"):
            if i + 1 >= len(argv):
                print(f"{a} 缺少取值", file=sys.stderr)
                return 2
            val = argv[i + 1]
            i += 2
            if a == "--run-dir":
                run_dir = Path(val)
            elif a == "--run-id":
                run_id = val
            elif a == "--origin":
                origin = val
            elif a == "--out":
                out = Path(val)
            else:
                try:
                    build_exit = int(val)
                except ValueError:
                    print("--build-exit 必须是整数", file=sys.stderr)
                    return 2
        else:
            print(f"未知参数：{a}", file=sys.stderr)
            return 2
    if not (run_dir and run_id and origin and out):
        print("需要 --run-dir --run-id --origin --out", file=sys.stderr)
        return 2
    if origin not in ("local", "cloud"):
        print("--origin 只能是 local 或 cloud", file=sys.stderr)
        return 2
    manifest = load_json(Path(run_dir) / "manifest.json")
    if not isinstance(manifest, dict):
        print(f"读不到或 manifest 非对象：{Path(run_dir) / 'manifest.json'}", file=sys.stderr)
        return 2
    if manifest.get("schema") != 2:
        print(f"manifest schema 非 2：{manifest.get('schema')!r}", file=sys.stderr)
        return 2
    if manifest.get("run_id") != run_id:
        print(f"manifest run_id {manifest.get('run_id')!r} 与参数 {run_id!r} 不符",
              file=sys.stderr)
        return 2
    if manifest.get("origin") != origin:
        print(f"manifest origin {manifest.get('origin')!r} 与参数 {origin!r} 不符",
              file=sys.stderr)
        return 2
    state, notes = aggregate(manifest, run_dir, run_id)
    if build_exit is None:
        state["stage"] = "collect"
        state["complete"] = False
    elif build_exit == 0:
        state["stage"] = "build"
        state["complete"] = True
    else:
        state["stage"] = "build_failed"
        state["complete"] = False
        notes.append(f"构建失败 exit={build_exit}")
    write_out(state, out)
    print("[状态] " + " ".join(
        [f"{k}={v['status']}" for k, v in state["sources"].items()] +
        [f"compute.{k}={v['status']}" for k, v in state["compute"].items()] +
        [f"complete={state['complete']}"]))
    for n in notes:
        print("[状态] " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

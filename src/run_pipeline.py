#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""FluMonitor 统一运行管线（A2 design §4/§6）。

把现有抓取/计算/构建脚本按固定顺序串起来，供本地 run_local.bat 与云端 weekly.yml
共用；不引入新调度服务。设计约束：

- 仓库级更新锁：第二个管线实例明确拒绝（不覆盖、不等待）。锁只保护管线，
  不阻止绕过管线的独立进程（设计要求明确提示该边界）。
- 运行目录 .tmp_pipeline/<run_id>/：manifest.json 记录每步退出码/超时/耗时，
  抓取与计算子进程另写各自结果文件（带同一 run_id）。状态聚合与校验由
  write_run_status.py 完成；缺结果/坏 JSON/run_id 不符/异常退出 → unknown，不推定 ok。
- 单源失败继续；退出码 0=全部成功 1=部分失败（仍建诚实降级页）2=管线/构建失败。
- 云端才写 data/run_status.json；本地不写，构建走 --local 只读存量。
- 构建失败不上传、不自动打开旧页（site_ready=false）。

用法：
  python -X utf8 src/run_pipeline.py --local
  python -X utf8 src/run_pipeline.py --cloud [--timeout 1800]
  python -X utf8 src/run_pipeline.py --local --skip flunet,sentinel
  python -X utf8 src/run_pipeline.py --local --open      # 成功后打开页面（bat 用）
  python -X utf8 src/run_pipeline.py --local --force-unlock
"""
import contextlib
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from uuid import uuid4 as _uuid4

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SITE = ROOT / "site"
DATA = ROOT / "data"
RUN_DIR_BASE = ROOT / ".tmp_pipeline"
# 锁必须是 .tmp_pipeline/ 目录内的文件：.gitignore 的 `.tmp_*/` 是目录模式，
# 裸文件 .tmp_pipeline.lock 不被忽略，崩溃遗留会污染 git status（S5 验证发现）。
LOCK = RUN_DIR_BASE / "lock"
RUN_STATUS = DATA / "run_status.json"

PY = sys.executable
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

OK, FAILED, SKIPPED, UNKNOWN = "ok", "failed", "skipped", "unknown"
FETCH_KEYS = ["flu_south", "flu_north", "heilongjiang_flu", "heilongjiang_sentinel",
              "sentinel", "flunet"]


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def say(msg, file=sys.stdout):
    print(msg, file=file, flush=True)


# ---------------- 锁 ----------------

def _pid_alive(pid):
    if pid <= 0:
        return False
    if os.name == "nt":
        # tasklist 输出是本地代码页（GBK），只按字节找 PID，避免解码歧义
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True)
        return str(pid).encode() in (out.stdout or b"")
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_lock(force=False):
    # 先建父目录：全新 checkout（含 GitHub runner 首跑）没有 .tmp_pipeline/，
    # 裸 write_text 会 FileNotFoundError
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    # 清理恢复者崩溃遗留的 .dead.* 残片：残片不参与锁竞争，删除无竞害——
    # 并发恢复者对自己 token 的 unlink 已容 FileNotFoundError（复核 IMP-01 round-3）
    for _stale in LOCK.parent.glob(f"{LOCK.name}.dead.*"):
        with contextlib.suppress(OSError):
            _stale.unlink()
    while True:
        # O_CREAT|O_EXCL 排他创建：两个进程同时通过检查时只有一个能建锁文件，
        # 消除 exists()→write_text 之间的竞态窗口
        try:
            fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                raw = LOCK.read_text(encoding="utf-8")
                info = json.loads(raw)
                if not isinstance(info, dict):
                    raise ValueError("lock is not a json object")
            except Exception:
                # 无法辨认持有者（含"已创建但 PID 尚未写完"的空锁窗口、损坏锁）：
                # 一律不当成死锁删除，交人工处理——误删活锁会破坏单写者保护
                # （复核 IMP-01 round-2）
                say(f"[锁] 锁文件存在但无法辨认持有者（可能另一实例正在创建，或内容损坏）。")
                say(f"[锁] 为避免误删活锁，本次拒绝；确认无其它管线后可手动删除 {LOCK} 重跑。")
                return False
            pid = int(info.get("pid", 0) or 0)
            if pid <= 0:
                say(f"[锁] 锁文件 pid 非法（{pid}），无法判定持有者，本次拒绝；"
                    f"确认无其它管线后可手动删除 {LOCK} 重跑。")
                return False
            alive = _pid_alive(pid)
            # IMP-01 终版策略（复核 round-3 后定案）：任何情况下都不自动删除
            # 他人创建的锁——死锁恢复一律人工执行（手动删除锁文件后重跑），
            # 从根上消除"两个恢复者并发夺取同一把锁"的删除竞态；单写者
            # 不变量由此绝对成立，不再依赖 rename 复核窗口。
            if alive:
                say(f"[锁] 已有管线在运行（pid={pid}，started={info.get('started_at', '?')}），本次拒绝。")
                say("[锁] 注意：该锁只覆盖本管线，不覆盖单独运行的抓取/回补 CLI。")
            else:
                say(f"[锁] 存在遗留锁（原 pid={pid} 已不在运行）。")
                say(f"[锁] 恢复方式：确认无其它管线实例后，手动删除 {LOCK} 再重跑。")
                say("[锁] --force-unlock 不自动清除锁（防并发恢复误删活锁）。")
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps({"pid": os.getpid(), "started_at": now()}))
        return True


def release_lock():
    """只释放属于本进程的锁，避免误删他人持有的锁。"""
    try:
        info = json.loads(LOCK.read_text(encoding="utf-8"))
    except Exception:
        info = {}
    if int(info.get("pid", 0) or 0) == os.getpid():
        LOCK.unlink(missing_ok=True)


# ---------------- 子进程 ----------------

def run_step(manifest, run_dir, name, args, timeout):
    """跑一个子进程并把结果记进 manifest。返回 (exit, timed_out)。"""
    log_path = run_dir / f"{name}.log"
    say(f"[{name}] {' '.join(args)}")
    t0 = time.time()
    timed_out = False
    cp = None
    try:
        cp = subprocess.run([PY, "-X", "utf8"] + args, cwd=str(ROOT), env=ENV,
                            capture_output=True, timeout=timeout)
        code = cp.returncode
    except subprocess.TimeoutExpired as e:
        timed_out = True
        code = 124
        partial = (e.stdout or b"") if isinstance(e.stdout, bytes) else b""
        log_path.write_text(partial.decode("utf-8", "replace") +
                            f"\n[超时] 超过 {timeout}s 被终止\n", encoding="utf-8")
        say(f"[{name}] 超时（>{timeout}s），已终止")
    except Exception as e:                       # 启动失败也算 unresolved
        code = 125
        log_path.write_text(f"[启动失败] {e}\n", encoding="utf-8")
        say(f"[{name}] 启动失败：{e}")
    if cp is not None:
        out = (cp.stdout or b"").decode("utf-8", "replace")
        err = (cp.stderr or b"").decode("utf-8", "replace")
        log_path.write_text(out + ("\n--- stderr ---\n" + err if err else ""),
                            encoding="utf-8")
        if out:
            print(out.rstrip(), flush=True)
        if err:
            print(err.rstrip(), file=sys.stderr, flush=True)
    manifest["steps"].append({"name": name, "args": args, "exit": code,
                              "timed_out": timed_out,
                              "seconds": round(time.time() - t0, 1)})
    save_manifest(run_dir, manifest)
    say(f"[{name}] exit={code} 用时 {time.time() - t0:.1f}s")
    return code, timed_out


def save_manifest(run_dir, manifest):
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def call_status(run_dir, run_id, origin, out_path, build_exit=None):
    """调用 write_run_status.py 做 v2 聚合与校验。返回是否成功。"""
    args = [str(SRC / "write_run_status.py"), "--run-dir", str(run_dir),
            "--run-id", run_id, "--origin", origin, "--out", str(out_path)]
    if build_exit is not None:
        args += ["--build-exit", str(build_exit)]
    cp = subprocess.run([PY, "-X", "utf8"] + args, cwd=str(ROOT), env=ENV,
                        capture_output=True)
    out = (cp.stdout or b"").decode("utf-8", "replace")
    err = (cp.stderr or b"").decode("utf-8", "replace")
    (run_dir / "status.log").write_text(out + ("\n" + err if err else ""),
                                        encoding="utf-8")
    if out:
        print(out.rstrip(), flush=True)
    if err:
        print(err.rstrip(), file=sys.stderr, flush=True)
    return cp.returncode == 0


# ---------------- 主流程 ----------------

def main(argv):
    origin = None
    timeout = 1800
    skip = set()
    force = False
    do_open = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--local":
            origin = "local"
        elif a == "--cloud":
            origin = "cloud"
        elif a == "--timeout":
            i += 1
            if i >= len(argv) or not argv[i].isdigit() or int(argv[i]) <= 0:
                print("--timeout 必须为正整数秒", file=sys.stderr)
                return 2
            timeout = int(argv[i])
        elif a == "--skip":
            i += 1
            skip |= {s.strip() for s in (argv[i] if i < len(argv) else "").split(",") if s.strip()}
        elif a == "--force-unlock":
            force = True
        elif a == "--open":
            do_open = True
        else:
            print(f"未知参数：{a}\n用法：--local|--cloud [--timeout N] [--skip a,b] "
                  "[--open] [--force-unlock]", file=sys.stderr)
            return 2
        i += 1
    if origin is None:
        print("必须指定 --local 或 --cloud", file=sys.stderr)
        return 2
    if not acquire_lock(force=force):
        return 2
    try:
        return _run(origin, timeout, skip, do_open)
    finally:
        release_lock()


def _run(origin, timeout, skip, do_open):
    run_id = datetime.now().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    run_dir = RUN_DIR_BASE / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": 2, "run_id": run_id, "origin": origin,
        "started_at": now(), "skipped": sorted(skip), "steps": [],
    }
    save_manifest(run_dir, manifest)
    (RUN_DIR_BASE / "last_run.json").unlink(missing_ok=True)  # 防上一轮 site_ready 被误用
    say(f"[管线] run_id={run_id} origin={origin} timeout={timeout}s skip={sorted(skip) or '无'}")

    # ---- 1. WHO FluNet ----
    if "flunet" in skip:
        say("[源] flunet: 本轮按 --skip 跳过")
    else:
        run_step(manifest, run_dir, "flunet", [str(SRC / "fetch_flunet.py")], timeout)

    # ---- 2. 全国哨点 ----
    if "sentinel" in skip:
        say("[源] sentinel: 本轮按 --skip 跳过")
    else:
        run_step(manifest, run_dir, "sentinel", [str(SRC / "fetch_sentinel.py")], timeout)

    # ---- 3. 南北双片流感（同一 PDF 只下载一次，区域各自成败）----
    regions = [r for r in ("south", "north") if f"flu_{r}" not in skip]
    if not regions:
        say("[源] flu_south/flu_north: 本轮按 --skip 跳过")
    else:
        run_step(manifest, run_dir, "flu",
                 [str(SRC / "fetch_flu_south.py"),
                  "--regions", ",".join(regions),
                  "--result-file", str(run_dir / "fetch_flu.json"),
                  "--run-id", run_id], timeout)

    # ---- 4. 黑龙江 B1/B2（可按产品单独跳过）----
    hlj_keys = {"heilongjiang_flu", "heilongjiang_sentinel"}
    if hlj_keys <= skip:
        say("[源] 黑龙江: 本轮按 --skip 跳过")
    else:
        hlj_args = [str(SRC / "fetch_heilongjiang.py")]
        # 只跳过一个产品时必须传 --products，否则另一产品会被重复抓取
        # 而聚合状态却标 skipped（状态与写入不一致）
        if "heilongjiang_flu" not in skip and "heilongjiang_sentinel" in skip:
            hlj_args += ["--products", "b1"]
        elif "heilongjiang_sentinel" not in skip and "heilongjiang_flu" in skip:
            hlj_args += ["--products", "b2"]
        hlj_args += ["--result-file", str(run_dir / "fetch_hlj.json"),
                     "--run-id", run_id]
        run_step(manifest, run_dir, "heilongjiang", hlj_args, timeout)

    # ---- 5. 三个指数计算 ----
    compute_inputs = {"south": "flu_south", "north": "flu_north",
                      "heilongjiang": "heilongjiang_flu"}
    targets = [t for t, src in compute_inputs.items() if src not in skip]
    if not targets:
        say("[计算] 无可用输入源，跳过")
    else:
        run_step(manifest, run_dir, "compute",
                 [str(SRC / "compute_index.py"),
                  "--targets", ",".join(targets),
                  "--result-file", str(run_dir / "compute.json"),
                  "--run-id", run_id], timeout)

    # ---- 6. 采集结束的运行状态快照（构建输入）----
    pre_status = run_dir / "run_status.collect.json"
    status_ok = call_status(run_dir, run_id, origin, pre_status)
    if not status_ok or not pre_status.exists():
        # 复核 IMP-05 round-2：预聚合失败 = 本轮证据链不完整。
        # 不允许退回"无状态构建"再靠最终聚合恢复成功把发布门重新打开——
        # 那样生成的页面没有本轮成败信息却可能被部署。直接按管线失败收尾：
        # 不构建、不上传、不打开旧页。
        say("[状态] 采集后状态聚合失败：本轮证据链不完整，按管线失败处理"
            "（不构建、不上传、不打开旧页）", file=sys.stderr)
        manifest["steps"].append({"name": "build", "args": [],
                                  "exit": None, "timed_out": False,
                                  "skipped_reason": "pre-status aggregation failed"})
        save_manifest(run_dir, manifest)
        (run_dir / "site_ready.json").write_text(
            json.dumps({"site_ready": False, "exit": None, "pipeline_exit": 2},
                       ensure_ascii=False), encoding="utf-8")
        (RUN_DIR_BASE / "last_run.json").write_text(
            json.dumps({"run_id": run_id, "origin": origin, "exit": 2,
                        "build_exit": None, "site_ready": False,
                        "run_dir": str(run_dir), "finished_at": now(),
                        "reason": "pre-status aggregation failed"},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        return 2

    # ---- 7. 构建单页 ----
    build_args = [str(SRC / "build_site.py")]
    if origin == "cloud":
        build_args += ["--run-status", str(pre_status), "--run-id", run_id]
    else:
        # 本地也传本轮 v2 状态：本地管线同样要在页面横幅如实反映本轮成败
        # （走到这里 pre_status 必然存在）
        build_args += ["--local",
                       "--run-status", str(pre_status), "--run-id", run_id]
    code, timed_out = run_step(manifest, run_dir, "build", build_args, timeout)

    # ---- 7b. 发布隔离（A2-SEARCH-05 round-2）：site/ 中的非受管文件
    # （历史旧页等）原样保留、绝不清理；云端把验证过的 index.html 复制进
    # 独立发布目录 site_publish/，部署 artifact 只来自该目录。复制失败 =
    # 发布证据链不完整 → 按构建失败处理（关门）。
    publish_ok = True
    if code == 0 and not timed_out and SITE.is_dir():
        stray = sorted(p.name for p in SITE.iterdir() if p.name != "index.html")
        if stray:
            say(f"[隔离] site/ 含非受管文件 {stray}（保留不动，不进发布产物）")
        if origin == "cloud":
            try:
                pub = publish_isolate()
                say(f"[隔离] 发布目录已就绪：{pub}（仅含本轮验证过的 index.html）")
            except Exception as exc:
                say(f"[隔离] 发布目录复制失败：{exc}，按构建失败处理", file=sys.stderr)
                publish_ok = False
                code = 2

    # ---- 8. 最终状态先落盘，再据此决定指针与退出码 ----
    # 状态写失败 = 本轮证据链不完整，不得宣称可发布（site_ready 关闭）
    final_path = RUN_STATUS if origin == "cloud" else (run_dir / "run_status.json")
    final_ok = call_status(run_dir, run_id, origin, final_path, build_exit=code)
    state = {}
    if final_ok:
        try:
            state = json.loads(final_path.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    bad = [k for k, v in (state.get("sources") or {}).items()
           if v.get("status") in (FAILED, UNKNOWN)]
    badc = [k for k, v in (state.get("compute") or {}).items()
            if v.get("status") in (FAILED, UNKNOWN)]
    if code != 0 or timed_out:
        pipeline_exit = 2   # 构建失败
    elif not final_ok or not state:
        pipeline_exit = 2   # 状态聚合/写入失败：证据链不完整
    elif bad or badc:
        pipeline_exit = 1   # 部分失败（已生成诚实降级页）
    else:
        pipeline_exit = 0
    site_ready = (code == 0 and not timed_out and final_ok and bool(state))
    (run_dir / "site_ready.json").write_text(
        json.dumps({"site_ready": site_ready, "exit": code,
                    "pipeline_exit": pipeline_exit}, ensure_ascii=False),
        encoding="utf-8")
    # 供外部（weekly.yml / bat）读取的稳定指针：不随 run_id 变化，且位于被忽略的 .tmp_*/
    # exit = 管线最终退出码（0 全成功/1 部分失败仍可部署/2 不可部署）；build_exit 另记
    (RUN_DIR_BASE / "last_run.json").write_text(
        json.dumps({"run_id": run_id, "origin": origin, "exit": pipeline_exit,
                    "build_exit": code, "site_ready": site_ready,
                    "run_dir": str(run_dir), "finished_at": now()},
                   ensure_ascii=False, indent=2),
        encoding="utf-8")
    say(f"[构建] build_exit={code} pipeline_exit={pipeline_exit} "
        f"site_ready={str(site_ready).lower()}")

    if not site_ready:
        say("[终止] 构建或状态落盘失败：不上传、不自动打开旧页", file=sys.stderr)
        return 2
    if pipeline_exit == 1:
        say(f"[终止] 部分失败：源 {bad} 计算 {badc}（已生成诚实降级页）")
        if do_open:
            open_site()
        return 1
    say("[完成] 全部采集与计算成功")
    if do_open:
        open_site()
    return 0


def publish_isolate():
    """A2-SEARCH-05 round-2：本轮独立发布目录。

    只把验证过的 site/index.html 原子复制到 site_publish/：
    先写临时目录、校验字节一致，再整体替换；site/ 中其他文件一律
    保留在原地、绝不进入发布产物。任何失败向上抛出，由调用方关门。
    """
    import shutil
    import uuid as _uuid
    src = SITE / "index.html"
    if not src.exists():
        raise RuntimeError(f"缺少 {src}")
    pub = ROOT / "site_publish"
    tmp = pub.parent / f".site_publish.tmp.{os.getpid()}.{_uuid.uuid4().hex[:8]}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    try:
        shutil.copy2(src, tmp / "index.html")
        if (tmp / "index.html").read_bytes() != src.read_bytes():
            raise RuntimeError("复制结果与源文件字节不一致")
        if pub.exists():
            shutil.rmtree(pub)
        tmp.rename(pub)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
    return pub


def open_site():
    target = SITE / "index.html"
    if not target.exists():
        say(f"[打开] 未找到 {target}，跳过")
        return
    say(f"[打开] {target}")
    try:
        if os.name == "nt":
            os.startfile(str(target))          # noqa: S606
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except Exception as e:
        say(f"[打开] 失败：{e}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

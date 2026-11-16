# -*- coding: utf-8 -*-
"""共享原子写助手（A2 design §4）。

所有权威 CSV/JSON 的整表写入统一走这里：
目标父目录下 `.tmp_writes/` 内创建唯一临时文件 → 逐行写出（每行 flush）→
fsync → os.replace 原子替换。异常路径 finally 清理临时文件；硬终止（kill -9 /
TerminateProcess）没有 finally，遗留的半成品留在 `.tmp_writes/` 内——
本助手绝不读取、复用或清理他人遗留文件，后续运行各建各的唯一名临时文件。

`.tmp_writes/` 目录名被仓库 .gitignore 的 `.tmp_*/` 规则覆盖（gitignore 目录
模式不锚定时匹配任意层级），因此 data/ 下的暂存不会被 git 收入；沙箱验证
见 validation/check_regional.py C1 组。

契约来源：.trellis/tasks/11-12-regional-monitor/design.md §4（A2-LEGACY-WRITE-PROTECTION）。
"""
import csv
import json
import os
from uuid import uuid4


def _tmp_path(path) -> "tuple":
    """目标同卷唯一临时文件路径：父目录/.tmp_writes/<name>.<pid>.<uuid8>.tmp"""
    tmp_dir = path.parent / ".tmp_writes"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir, tmp_dir / f"{path.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp"


def atomic_write_csv(path, fields, rows) -> None:
    """CSV 整表原子写入（保持 utf-8 / newline='' 约定）。

    逐行 writerow + flush：正常场景开销可忽略，同时给沙箱中断实验提供
    真实的「临时文件已存在且含部分行」观察窗口（不靠 raise 模拟硬终止）。
    """
    tmp_dir, tmp = _tmp_path(path)
    try:
        with tmp.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow(r)
                f.flush()
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # 同卷 rename：权威文件要么旧要么新，无半成品
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def atomic_write_text(path, text: str) -> None:
    """UTF-8 文本原子写入（运行状态 JSON 等）。"""
    tmp_dir, tmp = _tmp_path(path)
    try:
        with tmp.open("w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def atomic_write_json(path, obj) -> None:
    """JSON 原子写入（ensure_ascii=False，缩进 2，与 run_status 形态一致）。"""
    atomic_write_text(path, json.dumps(obj, indent=2, ensure_ascii=False))

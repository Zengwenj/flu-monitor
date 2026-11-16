#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A2 S5 正式验证套件（任务 11-12-regional-monitor）。

运行：python -X utf8 .trellis/tasks/11-12-regional-monitor/validation/check_regional.py
U3（A1b 51 项回归）为独立入口：
    python -X utf8 .trellis/tasks/11-12-regional-monitor/validation/check_history_compat.py --check

覆盖组（implement.md S5）：
- D1/D2  南北双片 parse_issue 契约（表1分母/括号互校/自算/守卫）
- H1/H2  黑龙江 B1/B2 解析与 upsert 守卫
- C1     写入保护：真实子进程强杀沙箱（原子写/旧采集器 save/双表部分完成/暂存被 git 忽略）
- R1/R2  管线锁（并发拒绝/遗留锁）与跳过聚合（本地 skip-all 全链）
- U1/U2/U4  五页结构契约 / run_banner v2 文案 / 导航与名称卡无数值
- E1     构建零改动 data/

契约来源：design.md §2-§7、implement.md S1-S5、复核 A2-LEGACY-WRITE-PROTECTION。
全部沙箱化：不联网；除 R 组真实跑 run_pipeline --local --skip <全部源>（只写 site/ 与
.tmp_pipeline/，二者均被 .gitignore 覆盖）与 C1_4 调 git check-ignore 外，全在临时目录。
"""
import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

_here = Path(__file__).resolve()
ROOT = _here
while not ((ROOT / "CONTEXT.md").exists() and (ROOT / "src" / "build_site.py").exists()):
    if ROOT.parent == ROOT:
        raise SystemExit("找不到仓库根（需同时存在 CONTEXT.md 与 src/build_site.py）")
    ROOT = ROOT.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import build_site as bs            # noqa: E402
import fetch_flu_south as ffs      # noqa: E402
import fetch_heilongjiang as fhj   # noqa: E402
import data_io                     # noqa: E402
import run_pipeline as rp          # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKIP_ALL = ("--local", "--skip",
            "flunet,sentinel,flu_south,flu_north,heilongjiang_flu,heilongjiang_sentinel")
SIX_SOURCES = {"flu_south", "flu_north", "heilongjiang_flu",
               "heilongjiang_sentinel", "sentinel", "flunet"}


def _iso_root(tmp: Path) -> Path:
    """隔离仓库根（复核 IMP-14）：复制 src、建空 data/。

    R 组在此运行 run_pipeline，锁/运行目录/site 全落临时区，
    绝不读写真实仓库的 .tmp_pipeline/lock（旧实现会删真实锁，已被复核否决）。
    """
    import shutil
    root = Path(tmp)
    shutil.copytree(SRC, root / "src")
    (root / "data").mkdir()
    return root


def _quiet(fn, *a, **kw):
    """静音被测函数内部的 print（解析来源等）。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return fn(*a, **kw)


# ---------------- D 组：南北双片解析契约 ----------------

def _flu_body(week_line, south_den, north_den, total, ili_line, pos_line, extra=""):
    tbl = f"南方省份 北方省份 合计\n检测数 {south_den} {north_den} {total}\n"
    return (f"中国流感监测周报（摘要）\n{week_line}\n第 900 期\n"
            f"{tbl}{ili_line}\n{pos_line}\n{extra}")


class D1(unittest.TestCase):
    """south/north 基本解析：表 1 分母、括号互校、自算、字段名随区域。"""

    W44 = "2026年第44周（2026年10月26日-11月1日）"
    W45 = "2026年第45周（2026年11月2日-11月8日）"

    def test_01_south_bracket(self):
        txt = _flu_body(self.W44, "10,481", "10,041", "20,522",
                        "南方省份哨点医院报告的 ILI% 为 4.8%",
                        "南方省份检测到 1796(17.14%)份流感病毒阳性标本")
        row, warns = _quiet(ffs.parse_issue, txt, title="2026 第44周")
        self.assertEqual(row["south_ili_pct"], "4.8")
        self.assertEqual(row["south_flu_positive_pct"], "17.14")
        self.assertEqual((row["iso_year"], row["iso_week"]), (2026, 44))
        self.assertEqual(row["week_start"], "2026-10-26")
        self.assertIn("south_ili_pct", row)
        self.assertNotIn("north_ili_pct", row)
        self.assertEqual(warns, [])

    def test_02_south_self_calc(self):
        txt = _flu_body(self.W45, "10837", "9971", "20808",
                        "南方省份哨点医院报告的 ILI% 为 4.6%",
                        "南方省份检测到 1940 份流感病毒阳性标本，其中 A 型占多数")
        row, _ = _quiet(ffs.parse_issue, txt)
        self.assertEqual(row["south_flu_positive_pct"], "17.90")  # 1940/10837

    def test_03_north_self_calc_with_south_present(self):
        # north 必须取北方列分母，同页南方句不得串扰
        txt = _flu_body(self.W45, "10837", "10041", "20878",
                        "南方省份哨点医院报告的 ILI% 为 4.6%",
                        "南方省份检测到 1940 份流感病毒阳性标本\n"
                        "北方省份哨点医院报告的 ILI% 为 3.8%\n"
                        "北方省份检测到 1171 份流感病毒阳性标本")
        row, _ = _quiet(ffs.parse_issue, txt, region="north")
        self.assertEqual(row["north_ili_pct"], "3.8")
        self.assertEqual(row["north_flu_positive_pct"], "11.66")  # 1171/10041
        self.assertNotIn("south_ili_pct", row)

    def test_04_north_spaced_fallback(self):
        # 2023W32 实测形态：北方句被 pdftotext 排出字间空白
        txt = _flu_body("2023年第32周（2023年8月7日-8月13日）", "4977", "4486", "9463",
                        "南 方 省 份 哨 点 医 院 报 告 的 ILI% 为 2.2%",
                        "南 方 省 份 检 测 到 109 份流感病毒阳性标本\n"
                        "北 方 省 份 哨 点 医 院 报 告 的 ILI% 为 1.5%\n"
                        "北 方 省 份 检 测 到 12 份流感病毒阳性标本")
        row, _ = _quiet(ffs.parse_issue, txt, region="north")
        self.assertEqual(row["north_ili_pct"], "1.5")
        self.assertEqual(row["north_flu_positive_pct"], "0.27")  # 12/4486

    def test_05_missing_table1_fails(self):
        txt = ("2026年第44周（2026年10月26日-11月1日）\n"
               "南方省份哨点医院报告的 ILI% 为 4.8%\n"
               "南方省份检测到 1796 份流感病毒阳性标本")
        with self.assertRaises(RuntimeError) as cm:
            _quiet(ffs.parse_issue, txt)
        self.assertIn("表 1", str(cm.exception))

    def test_06_north_column_check_fail(self):
        # 南北列加总偏差 > 0.2% → 判失败（防列错位）
        txt = _flu_body(self.W45, "10837", "10041", "18878",
                        "北方省份哨点医院报告的 ILI% 为 3.8%",
                        "北方省份检测到 1171 份流感病毒阳性标本")
        with self.assertRaises(RuntimeError) as cm:
            _quiet(ffs.parse_issue, txt, region="north")
        self.assertIn("列校验失败", str(cm.exception))


class D2(unittest.TestCase):
    """守卫：括号互校、表合计笔误容差、计数域、标题一致、合并版/封面残留。"""

    W44 = "2026年第44周（2026年10月26日-11月1日）"

    def test_01_bracket_mismatch_fails(self):
        txt = _flu_body(self.W44, "10,481", "10,041", "20,522",
                        "南方省份哨点医院报告的 ILI% 为 4.8%",
                        "南方省份检测到 1796(50.00%)份流感病毒阳性标本")
        with self.assertRaises(RuntimeError) as cm:
            _quiet(ffs.parse_issue, txt)
        self.assertIn("bracket_mismatch", str(cm.exception))

    def test_02_table_sum_typo_warns(self):
        # 2025W33 实测：上游合计笔误 0.07% ≤ 0.2% → 告警照存
        txt = _flu_body(self.W44, "10043", "2995", "13029",
                        "南方省份哨点医院报告的 ILI% 为 3.4%",
                        "南方省份检测到 189(1.88%)份流感病毒阳性标本")
        row, warns = _quiet(ffs.parse_issue, txt)
        self.assertEqual(row["south_flu_positive_pct"], "1.88")
        self.assertTrue(any("table_sum_check" in w for w in warns), warns)

    def test_03_num_over_den_fails(self):
        txt = _flu_body(self.W44, "10,481", "10,041", "20,522",
                        "南方省份哨点医院报告的 ILI% 为 4.8%",
                        "南方省份检测到 99999 份流感病毒阳性标本")
        with self.assertRaises(RuntimeError) as cm:
            _quiet(ffs.parse_issue, txt)
        self.assertIn("阳性数", str(cm.exception))

    def test_04_title_mismatch_fails(self):
        txt = _flu_body(self.W44, "10,481", "10,041", "20,522",
                        "南方省份哨点医院报告的 ILI% 为 4.8%",
                        "南方省份检测到 1796 份流感病毒阳性标本")
        with self.assertRaises(RuntimeError) as cm:
            _quiet(ffs.parse_issue, txt, title="2025 第44周")
        self.assertIn("issue_mismatch", str(cm.exception))

    def test_05_merged_issue_fails(self):
        extra = "第 895 期\n" * 3 + "第 900 期\n" * 3
        txt = _flu_body(self.W44, "10,481", "10,041", "20,522",
                        "南方省份哨点医院报告的 ILI% 为 4.8%",
                        "南方省份检测到 1796 份流感病毒阳性标本", extra=extra)
        with self.assertRaises(RuntimeError) as cm:
            _quiet(ffs.parse_issue, txt)
        self.assertIn("merged_issue", str(cm.exception))

    def test_06_cover_leftover_warns(self):
        # 主期号 ≥3 次、残留期号 ≤2 次（2026W11 实测）→ 告警照存
        extra = "第 895 期\n" * 2 + "第 900 期\n" * 4
        txt = _flu_body(self.W44, "10,481", "10,041", "20,522",
                        "南方省份哨点医院报告的 ILI% 为 4.8%",
                        "南方省份检测到 1796 份流感病毒阳性标本", extra=extra)
        row, warns = _quiet(ffs.parse_issue, txt)
        self.assertEqual(row["iso_week"], 44)
        self.assertTrue(any("cover_leftover_issue" in w for w in warns), warns)


# ---------------- H 组：黑龙江 B1/B2 ----------------

def _b1_body(week, rng, ili, sample_line, rate_line):
    return (f"黑龙江省流感监测周报\n{week}（{rng}）\n"
            f"全省哨点监测：ILI%（门急诊就诊病例）为 {ili}%。\n"
            f"{sample_line}。本期流感病毒核酸检测阳性率 {rate_line}%。")


class H1(unittest.TestCase):
    """B1：三种 SAMPLE_PAT 版式、周次守卫、upsert 守卫。"""

    def _b1(self, week="2026年第45周", rng="2026.11.2-2026.11.8", ili="3.01",
            sample="共采集ILI标本751份，其中36份标本流感病毒阳性", rate="4.79",
            title_week="2026年第45周"):
        title = f"{title_week}{fhj.B1_TITLE}"
        body = _b1_body(week, rng, ili, sample, rate)
        return title, fhj.parse_b1(title, body)

    def test_01_normal(self):
        title, r = self._b1()
        self.assertEqual((r["iso_year"], r["iso_week"], r["week_start"]),
                         (2026, 45, "2026-11-02"))
        self.assertEqual(r["ili_pct"], "3.01")
        self.assertEqual(r["flu_positive_pct"], "4.79")
        self.assertEqual((r["sample_count"], r["positive_count"]), ("751", "36"))
        self.assertEqual(r["status"], "ok")

    def test_02_all_negative_variant(self):
        # 「核酸检测均为阴性」= 阳性 0（官方阳性率 0%）
        _, r = self._b1(sample="共采集ILI标本197份，核酸检测均为阴性", rate="0")
        self.assertEqual((r["sample_count"], r["positive_count"]), ("197", "0"))
        self.assertEqual(r["flu_positive_pct"], "0")

    def test_03_no_qizhong_variant(self):
        # 7108 实测：无「其中」前缀
        _, r = self._b1(week="2026年第24周", rng="2026.6.8-2026.6.14", ili="2.38",
                        sample="共采集ILI标本196份，10份标本流感病毒阳性", rate="5.10",
                        title_week="2026年第24周")
        self.assertEqual((r["sample_count"], r["positive_count"]), ("196", "10"))
        self.assertEqual(r["flu_positive_pct"], "5.10")

    def test_04_range_not_seven_days(self):
        # 2025W2 上游年份笔误（2024.01.06-2025.01.12）→ 判失败
        with self.assertRaises(RuntimeError) as cm:
            self._b1(week="2025年第2周", rng="2024.01.06-2025.01.12", ili="3.5",
                     sample="共采集ILI标本120份，其中2份标本流感病毒阳性", rate="1.67",
                     title_week="2025年第2周")
        self.assertIn("7 天", str(cm.exception))

    def test_05_title_body_conflict(self):
        with self.assertRaises(RuntimeError) as cm:
            self._b1(title_week="2026年第43周")
        self.assertIn("conflict", str(cm.exception))

    def test_06_upsert_guards(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            old_csv, old_log = fhj.B1_CSV, fhj.CHANGES_LOG
            fhj.B1_CSV, fhj.CHANGES_LOG = d / "b1.csv", d / "changes.log"
            try:
                base = {"iso_year": "2026", "iso_week": "45", "week_start": "2026-11-02",
                        "ili_pct": "3.01", "flu_positive_pct": "4.79", "goldstein_index": "",
                        "sample_count": "751", "positive_count": "36",
                        "source_url": "", "source_pubdate": "", "fetched_at": "t0",
                        "status": "ok"}
                self.assertEqual(fhj.upsert_b1(dict(base, fetched_at="t1"), "u1", "d1"), "ok_new")
                self.assertEqual(fhj.upsert_b1(dict(base, fetched_at="t2"), "u2", "d2"), "ok_same")
                rows = fhj.load_csv(fhj.B1_CSV, fhj.B1_FIELDS)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["fetched_at"], "t2")
                self.assertEqual(rows[0]["source_url"], "u2")
                self.assertEqual(rows[0]["status"], "ok")
                # 变值 → changes.log 留痕后覆盖
                st = fhj.upsert_b1(dict(base, ili_pct="9.99", fetched_at="t3"), "u3", "d3")
                self.assertEqual(st, "ok_new")
                rows = fhj.load_csv(fhj.B1_CSV, fhj.B1_FIELDS)
                self.assertEqual(rows[0]["ili_pct"], "9.99")
                self.assertIn("heilongjiang_flu",
                              fhj.CHANGES_LOG.read_text(encoding="utf-8"))
            finally:
                fhj.B1_CSV, fhj.CHANGES_LOG = old_csv, old_log


def _b2_body(groups=("门急诊 ILI 病例中检测到的病原体主要为鼻病毒（阳性率 8%）、"
                     "人偏肺病毒（阳性率 6.67%）、副流感病毒（与腺病毒并列，阳性率 6.67%）；",
                     "住院 SARI 病例中检测到的病原体主要为鼻病毒（阳性率 13.89%）、"
                     "博卡病毒（阳性率 6.94%）、流感病毒（与人偏肺病毒并列，阳性率 5.56%）。"),
             total="222 份标本，其中门急诊 ILI 病例 150 份，住院 SARI 病例 72 份"):
    return ("黑龙江省急性呼吸道传染病哨点监测周报\n"
            "2026年第45周（2026.11.2-2026.11.8）\n"
            f"共采集 {total}。\n" + "\n".join(groups))


class H2(unittest.TestCase):
    """B2：整期校验、并列展开、构成校验、缺组拒绝。"""

    TITLE = "2026年第45周黑龙江省急性呼吸道传染病哨点监测周报"

    def test_01_normal_with_tie_expansion(self):
        rows = fhj.parse_b2(self.TITLE, _b2_body())
        got = {(r["setting"], r["pathogen"]): r["positive_pct"] for r in rows}
        self.assertEqual(got[("门急诊", "鼻病毒")], "8")
        self.assertEqual(got[("门急诊", "副流感病毒")], "6.67")
        # 并列伙伴同率成行
        self.assertEqual(got[("门急诊", "腺病毒")], "6.67")
        self.assertEqual(got[("住院", "流感病毒")], "5.56")
        self.assertEqual(got[("住院", "人偏肺病毒")], "5.56")
        # 已在先的 (住院,人偏肺病毒)? 本夹具住院并列伙伴人偏肺病毒未先出现 → 应成行
        # 样本框按组
        bykey = {(r["setting"], r["pathogen"]): r for r in rows}
        self.assertEqual(bykey[("门急诊", "鼻病毒")]["sample_count"], "150")
        self.assertEqual(bykey[("住院", "鼻病毒")]["sample_count"], "72")
        self.assertEqual(bykey[("门急诊", "鼻病毒")]["total_samples"], "222")
        for r in rows:
            # parse_b2 返回 int 周键（写 CSV 时才转字符串）
            self.assertEqual((r["iso_year"], r["iso_week"]), (2026, 45))
            self.assertEqual(r["status"], "ok")

    def test_02_total_mismatch_fails(self):
        body = _b2_body(total="222 份标本，其中门急诊 ILI 病例 150 份，住院 SARI 病例 73 份")
        with self.assertRaises(RuntimeError) as cm:
            fhj.parse_b2(self.TITLE, body)
        self.assertIn("两组标本", str(cm.exception))

    def test_03_missing_group_fails(self):
        body = _b2_body(groups=("门急诊 ILI 病例中检测到的病原体主要为鼻病毒（阳性率 8%）；",))
        with self.assertRaises(RuntimeError) as cm:
            fhj.parse_b2(self.TITLE, body)
        self.assertIn("未同时找到", str(cm.exception))

    def test_04_rate_out_of_range_fails(self):
        body = _b2_body(groups=("门急诊 ILI 病例中检测到的病原体主要为鼻病毒（阳性率 8%）；",
                                "住院 SARI 病例中检测到的病原体主要为鼻病毒（阳性率 150%）。"))
        with self.assertRaises(RuntimeError) as cm:
            fhj.parse_b2(self.TITLE, body)
        self.assertIn("越界", str(cm.exception))

    def test_09_sample_count_revision_is_logged(self):
        # 复核 IMP-13 round-3 / IMP-14：仅标本数修订（阳性率全同）也必须留痕——
        # 签名涵盖 sample_count/total_samples，不得无痕覆盖
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            saved = (fhj.B2_CSV, fhj.CHANGES_LOG)
            fhj.B2_CSV = d / "b2.csv"
            fhj.CHANGES_LOG = d / "changes.log"
            try:
                fhj.replace_b2(fhj.parse_b2(self.TITLE, _b2_body()),
                               "http://fake/a.html", "2026-11-12")
                # 仅改标本数：门急诊 150→160（总数 222→232），率不变
                body2 = _b2_body(
                    total="232 份标本，其中门急诊 ILI 病例 160 份，住院 SARI 病例 72 份")
                with contextlib.redirect_stdout(io.StringIO()):
                    fhj.replace_b2(fhj.parse_b2(self.TITLE, body2),
                                   "http://fake/a.html", "2026-11-12")
                log = fhj.CHANGES_LOG.read_text(encoding="utf-8")
                self.assertIn("heilongjiang_sentinel", log,
                              "仅标本数修订也必须写变化日志")
                rows = fhj.load_csv(fhj.B2_CSV, fhj.B2_FIELDS)
                self.assertTrue(any(r["sample_count"] == "160" for r in rows),
                                "新标本数应已写入")
            finally:
                (fhj.B2_CSV, fhj.CHANGES_LOG) = saved

    def test_05_same_setting_twice_fails(self):
        # 复核 IMP-08：两组都写成门急诊 → setting 集合校验拒绝
        body = _b2_body(groups=(
            "门急诊 ILI 病例中检测到的病原体主要为鼻病毒（阳性率 8%）；",
            "门急诊 ILI 病例中检测到的病原体主要为博卡病毒（阳性率 6.94%）。"))
        with self.assertRaises(RuntimeError) as cm:
            fhj.parse_b2(self.TITLE, body)
        self.assertIn("门急诊", str(cm.exception))

    def test_06_unparseable_fragment_fails(self):
        # 复核 IMP-08：段内出现无法解析的病原片段（含"阳性率"字样）→ 整期失败，
        # 不允许 findall 静默跳过
        body = _b2_body(groups=(
            "门急诊 ILI 病例中检测到的病原体主要为鼻病毒（阳性率 8%）、"
            "某种新病原检出情况表述异常阳性率 5%；",
            "住院 SARI 病例中检测到的病原体主要为鼻病毒（阳性率 13.89%）。"))
        with self.assertRaises(RuntimeError) as cm:
            fhj.parse_b2(self.TITLE, body)
        self.assertIn("无法解析的病原条目", str(cm.exception))

    def test_07_tie_partner_rate_conflict_fails(self):
        # 复核 IMP-08：并列伙伴已在库但率不同 → 冲突拒绝
        body = _b2_body(groups=(
            "门急诊 ILI 病例中检测到的病原体主要为鼻病毒（阳性率 8%）、"
            "人偏肺病毒（阳性率 6.67%）、副流感病毒（与人偏肺病毒并列，阳性率 7.5%）；",
            "住院 SARI 病例中检测到的病原体主要为鼻病毒（阳性率 13.89%）。"))
        with self.assertRaises(RuntimeError) as cm:
            fhj.parse_b2(self.TITLE, body)
        self.assertIn("不一致", str(cm.exception))

    def test_08_tie_partner_same_rate_ok(self):
        # 伙伴先出现、并列者同率 → 正常成行（与 test_01 互为镜像）
        body = _b2_body(groups=(
            "门急诊 ILI 病例中检测到的病原体主要为人偏肺病毒（阳性率 6.67%）、"
            "副流感病毒（与人偏肺病毒并列，阳性率 6.67%）；",
            "住院 SARI 病例中检测到的病原体主要为鼻病毒（阳性率 13.89%）。"))
        rows = fhj.parse_b2(self.TITLE, body)
        got = {(r["setting"], r["pathogen"]): r["positive_pct"] for r in rows}
        self.assertEqual(got[("门急诊", "人偏肺病毒")], "6.67")
        self.assertEqual(got[("门急诊", "副流感病毒")], "6.67")


# ---------------- C 组：写入保护强杀沙箱（A2-LEGACY-WRITE-PROTECTION） ----------------

FIELDS8 = [f"f{i}" for i in range(8)]

_CHILD_ATOMIC = r'''
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import data_io
class SlowDict(dict):
    def get(self, k, d=None):
        time.sleep(0.002)
        return super().get(k, d)
rows = [SlowDict({f: f"{i}-{j}" for j, f in enumerate(%FIELDS%)} ) for i in range(600)]
data_io.atomic_write_csv(Path(sys.argv[2]), %FIELDS%, rows)
print("CHILD_DONE", flush=True)
'''.replace("%FIELDS%", repr(FIELDS8))

_CHILD_SENTINEL = r'''
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import fetch_sentinel as fs
rates, rank = Path(sys.argv[2]), Path(sys.argv[3])
fs.save(rates, [{"a": "9", "b": "NEW"}], ["a", "b"])   # 第一表：完整新版（先完成）
class SlowDict(dict):
    def get(self, k, d=None):
        time.sleep(0.002)
        return super().get(k, d)
rows = [SlowDict({"a": str(i), "b": "x"}) for i in range(600)]
fs.save(rank, rows, ["a", "b"])                        # 第二表：写入中被强杀
print("CHILD_DONE", flush=True)
'''

_CHILD_FLUNET = r'''
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import data_io, fetch_flunet as fnet
# 复核 IMP-14 round-2：必须走 fetch_flunet._convert() 真实生产出口——
# 它内部调用 data_io.atomic_write_csv(OUT, FIELDS, rows)（src/fetch_flunet.py:86）。
# 慢化点注入在 data_io.atomic_write_csv 的行迭代上：_convert 换回直写本测试会失败。
fnet.OUT = Path(sys.argv[2])
_real = data_io.atomic_write_csv
class Slow(list):
    def __iter__(self):
        for r in list.__iter__(self):
            time.sleep(0.002)
            yield r
def slow_write(path, fields, rows):
    _real(path, fields, Slow(rows))
data_io.atomic_write_csv = slow_write
fnet._convert(Path(sys.argv[3]))
print("CHILD_DONE", flush=True)
'''


def _flunet_fixture_csv(path, n=600):
    """构造 _convert 可消费的 WHO FluNet 原始 CSV（CHN 行 × n）。"""
    need = ["COUNTRY_CODE", "ISO_YEAR", "ISO_WEEK", "ISO_WEEKSTARTDATE",
            "SPEC_PROCESSED_NB", "INF_ALL", "INF_A", "INF_B",
            "AH1N12009", "AH3"]
    lines = [",".join(need)]
    for i in range(n):
        lines.append(f"CHN,{2002 + i % 25},{i % 53 + 1},2026-01-01,100,{i % 90},1,2,3,4")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def _spawn(code, *args):
    return subprocess.Popen(
        [sys.executable, "-c", code, str(SRC), *(str(a) for a in args)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _await_partial_write(tmp_dir: Path, timeout: float = 25.0):
    """轮询暂存目录：出现 *.tmp 且有部分行、仍在增长 → 返回该 tmp 路径。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if tmp_dir.exists():
            for c in tmp_dir.glob("*.tmp"):
                if c.stat().st_size > 80:
                    s1 = c.stat().st_size
                    time.sleep(0.3)
                    if c.exists() and c.stat().st_size > s1:
                        return c
        time.sleep(0.05)
    return None


class C1(unittest.TestCase):
    """真实子进程 + TerminateProcess 强杀（不以 raise 模拟）。"""

    def test_01_atomic_write_kill_keeps_target(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            target = d / "t" / "table.csv"
            target.parent.mkdir()
            old_rows = [{"f0": str(i), "f1": "old", "f2": "x", "f3": "x",
                         "f4": "x", "f5": "x", "f6": "x", "f7": "x"} for i in range(5)]
            data_io.atomic_write_csv(target, FIELDS8, old_rows)
            before = target.read_bytes()
            p = _spawn(_CHILD_ATOMIC, target)
            tmp = _await_partial_write(target.parent / ".tmp_writes")
            if tmp is None:
                p.kill()
                self.fail("未观察到暂存写入窗口（测试环境异常）")
            p.kill()
            p.wait(timeout=10)
            self.assertEqual(target.read_bytes(), before, "强杀后权威文件被改动")
            self.assertTrue(tmp.exists(), "应停在暂存半成品（证明击中写入窗口）")
            self.assertNotEqual(p.returncode, 0)

    def test_02_legacy_sentinel_save_kill_two_tables(self):
        # 复核关闭条件：第一表完整新 + 第二表完整旧
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            rates, rank = d / "rates.csv", d / "rank.csv"
            for pth, seed in ((rates, "R"), (rank, "K")):
                data_io.atomic_write_csv(pth, ["a", "b"],
                                         [{"a": str(i), "b": seed} for i in range(3)])
            old_rank = rank.read_bytes()
            p = _spawn(_CHILD_SENTINEL, rates, rank)
            tmp = _await_partial_write(rank.parent / ".tmp_writes")
            if tmp is None:
                p.kill()
                self.fail("未观察到第二表写入窗口")
            p.kill()
            p.wait(timeout=10)
            self.assertEqual(rates.read_text(encoding="utf-8"), "a,b\n9,NEW\n",
                             "第一表应为完整新版")
            self.assertEqual(rank.read_bytes(), old_rank, "第二表必须保持完整旧版")

    def test_03_tmp_writes_ignored_by_git(self):
        git = shutil_which_git()
        if git is None:
            self.skipTest("git 不可用")
        for rel in ("data/.tmp_writes/flu_south.csv.123.abcd1234.tmp",
                    ".tmp_pipeline/lock", ".tmp_a2/anything.txt"):
            r = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", rel],
                               capture_output=True)
            self.assertEqual(r.returncode, 0, f"{rel} 未被 .gitignore 覆盖")

    def test_04_flunet_save_kill_keeps_target(self):
        # 复核 IMP-14 round-2：经 fetch_flunet._convert() 真实保存出口写入中被
        # 强杀 → 权威 flunet_china.csv 逐字节不变
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            import fetch_flunet as fnet
            target = d / "flunet_china.csv"
            data_io.atomic_write_csv(target, fnet.FIELDS,
                                     [{f: "old" for f in fnet.FIELDS}])
            before = target.read_bytes()
            raw = d / "raw.csv"
            _flunet_fixture_csv(raw)
            p = _spawn(_CHILD_FLUNET, target, raw)
            tmp = _await_partial_write(target.parent / ".tmp_writes")
            if tmp is None:
                p.kill()
                self.fail("未观察到 flunet 保存写入窗口（测试环境异常）")
            p.kill()
            p.wait(timeout=10)
            self.assertEqual(target.read_bytes(), before, "强杀后 flunet 表被改动")
            self.assertNotEqual(p.returncode, 0)

    def test_05_tmp_writes_not_staged_by_git_add(self):
        # 冻结计划 r2:213：临时仓库里 git add data/ 后，暂存清单不得含 .tmp_writes
        git = shutil_which_git()
        if git is None:
            self.skipTest("git 不可用")
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            subprocess.run(["git", "init", "-q", str(d)], check=True,
                           capture_output=True)
            subprocess.run(["git", "-C", str(d), "config", "user.email", "t@t"],
                           check=True, capture_output=True)
            subprocess.run(["git", "-C", str(d), "config", "user.name", "t"],
                           check=True, capture_output=True)
            (d / ".gitignore").write_text(
                (ROOT / ".gitignore").read_text(encoding="utf-8"), encoding="utf-8")
            (d / "data").mkdir()
            (d / "data" / "flu_south.csv").write_text("year,week\n2026,45\n",
                                                      encoding="utf-8")
            (d / "data" / ".tmp_writes").mkdir()
            (d / "data" / ".tmp_writes" / "x.tmp").write_text("partial", encoding="utf-8")
            r = subprocess.run(["git", "-C", str(d), "add", "data/"],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            staged = subprocess.run(["git", "-C", str(d), "diff", "--cached",
                                     "--name-only"], capture_output=True,
                                    text=True, encoding="utf-8").stdout
            self.assertIn("data/flu_south.csv", staged)
            self.assertNotIn(".tmp_writes", staged,
                             "暂存清单不得包含 .tmp_writes 半成品")


def shutil_which_git():
    from shutil import which
    return which("git")


# ---------------- R 组：管线锁与聚合 ----------------

class R1(unittest.TestCase):
    """单写者锁：并发第二实例必须拒绝；skip-all 本地全链 exit 0。

    复核 IMP-14：全部在隔离根运行，绝不触碰真实仓库 .tmp_pipeline/lock。
    """

    def _run(self, root: Path, *extra, timeout=300):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(root / "src" / "run_pipeline.py"),
             *SKIP_ALL, *extra],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout)

    def test_01_concurrent_second_refused(self):
        # 用测试进程自身 PID（存活）持隔离锁：确定性覆盖「活锁拒绝」路径。
        # 双子进程方案在慢机上不可靠——skip-all 全链约 2 秒，p1 可能在 p2
        # 启动前就完成并释放锁，导致 p2 合法获锁 exit 0（时序竞态，非缺陷）。
        with tempfile.TemporaryDirectory() as d:
            root = _iso_root(Path(d))
            lock = root / ".tmp_pipeline" / "lock"
            lock.parent.mkdir(exist_ok=True)
            lock.write_text(json.dumps({"pid": os.getpid(),
                                        "started_at": "concurrent-test"}),
                            encoding="utf-8")
            r = self._run(root, timeout=120)
            self.assertNotEqual(r.returncode, 0, "持锁期间第二实例必须非零退出")
            self.assertIn("锁", r.stdout + r.stderr)

    def test_02_skip_all_local_exit_zero(self):
        with tempfile.TemporaryDirectory() as d:
            root = _iso_root(Path(d))
            r = self._run(root)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
            last = json.loads((root / ".tmp_pipeline" / "last_run.json")
                              .read_text(encoding="utf-8"))
            self.assertTrue(last["site_ready"])
            self.assertEqual(last["exit"], 0)
            run_dir = Path(last["run_dir"])
            st = json.loads((run_dir / "run_status.json").read_text(encoding="utf-8"))
            self.assertEqual(set(st.get("sources") or {}), SIX_SOURCES)
            for k, v in st["sources"].items():
                self.assertEqual(bs._status_of(v)[0], "skipped", f"{k} 应为 skipped")


class R2(unittest.TestCase):
    """遗留锁（原进程已死）：拒绝并提示 --force-unlock；活锁强制解锁被拒；强制解锁后可跑。

    复核 IMP-14：隔离根运行，不触碰真实仓库锁。
    """

    def _run(self, root: Path, *extra, timeout=300):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(root / "src" / "run_pipeline.py"),
             *SKIP_ALL, *extra],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout)

    def test_01_stale_lock_refused_then_force_unlock(self):
        with tempfile.TemporaryDirectory() as d:
            root = _iso_root(Path(d))
            lock = root / ".tmp_pipeline" / "lock"
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text(json.dumps({"pid": 999999,
                                        "started_at": "2026-01-01T00:00:00"}),
                            encoding="utf-8")
            r = self._run(root, timeout=120)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("已不在运行", r.stdout + r.stderr)
            r2 = self._run(root, "--force-unlock")
            self.assertEqual(r2.returncode, 0, r2.stdout[-2000:])
            self.assertFalse(lock.exists(), "跑完应释放锁")

    def test_02_live_lock_force_unlock_refused(self):
        # 活锁 + --force-unlock 必须拒绝（复核 IMP-01：强制解锁不得绕过活跃写者）
        with tempfile.TemporaryDirectory() as d:
            root = _iso_root(Path(d))
            lock = root / ".tmp_pipeline" / "lock"
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text(json.dumps({"pid": os.getpid(),
                                        "started_at": "live-lock-test"}),
                            encoding="utf-8")
            r = self._run(root, "--force-unlock", timeout=120)
            self.assertNotEqual(r.returncode, 0, "活锁强制解锁必须被拒绝")
            self.assertTrue(lock.exists(), "活锁不得被删除")


# ---------------- U 组：页面与状态文案 ----------------

def _render_to(tmpdir: Path):
    out = bs.OUT
    argv = sys.argv[:]
    bs.OUT = tmpdir / "index.html"
    sys.argv = ["build_site.py", "--local"]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            bs.render()
    finally:
        bs.OUT = out
        sys.argv = argv
    pages = {"index": tmpdir / "index.html"}
    for slug in bs.PAGES:
        pages[slug] = tmpdir / f"{slug}.html"
    for name, p in pages.items():
        assert p.exists(), f"缺页 {name}"
        pages[name] = p.read_text(encoding="utf-8")
    return pages


class U1(unittest.TestCase):
    """五页结构：无外部资源、黑/渝无四川卡、口径标注、重庆只链接。"""

    def test_01_pages_and_no_external_resources(self):
        with tempfile.TemporaryDirectory() as d:
            pages = _render_to(Path(d))
            self.assertEqual(set(pages), {"index", "south", "north", "heilongjiang", "chongqing"})
            for name, text in pages.items():
                for bad in ("<script", "fetch(", "@import", "url(http",
                            'img src="http', 'link href="http'):
                    self.assertNotIn(bad, text, f"{name}:{bad}")

    def test_02_hlj_cq_no_sichuan_card(self):
        with tempfile.TemporaryDirectory() as d:
            pages = _render_to(Path(d))
            for name in ("heilongjiang", "chongqing"):
                text = pages[name]
                self.assertNotIn("平原区", text)
                self.assertNotIn("流感分级", text)
                self.assertIn("全国哨点", text, f"{name} 全国卡须标全国哨点口径")
            self.assertIn("黑龙江", pages["heilongjiang"])
            self.assertIn("cqcdc.org", pages["chongqing"])
            self.assertIn("官方来源已核实", pages["chongqing"])
            # 成都页保留四川卡与 A1b 历史卡
            self.assertIn("流感分级", pages["index"])
            self.assertIn("历年同周对比", pages["index"])
            self.assertIn("历年同周对比", pages["south"])
            # 复核 BLOCKER-1：south 页不得再出现自引链接
            self.assertNotIn("查看南方片页", pages["south"])
            self.assertIn("查看南方片页", pages["index"])


class U2(unittest.TestCase):
    """run_banner v2 文案：failed/skipped/unknown 分开、run_id、local、坏 JSON。"""

    def _banner(self, status_obj, local=False, run_id="R1", page="index"):
        with tempfile.TemporaryDirectory() as d:
            old = bs.RUN_STATUS
            bs.RUN_STATUS = Path(d) / "rs.json"
            try:
                bs.RUN_STATUS.write_text(json.dumps(status_obj, ensure_ascii=False),
                                         encoding="utf-8")
                return bs.run_banner(local=local, run_id=run_id, page=page)
            finally:
                bs.RUN_STATUS = old

    def test_01_v2_partial_wording(self):
        st = {"schema": 2, "run_id": "R1", "complete": False, "finished_at": "2026-11-13T09:00:00",
              "sources": {"flu_south": "ok", "flu_north": "failed",
                          "heilongjiang_flu": "skipped", "heilongjiang_sentinel": {"status": "x"},
                          "sentinel": "failed", "flunet": "ok"},
              "compute": {"south": {"status": "ok"}, "north": {"status": "failed"},
                          "heilongjiang": {"status": "ok"}}}
        # heilongjiang 页：相关源全聚合，分列文案齐全（IMP-04 关闭条件）；
        # 北方流感不是本页卡片依赖，不得出现（按页相关性）
        b = self._banner(st, page="heilongjiang")
        self.assertIn("本次未能获取最新数据（全国哨点周报）", b)
        self.assertIn("本次未执行获取（黑龙江流感周报）", b)
        self.assertIn("状态未知（黑龙江哨点周报）", b)
        self.assertNotIn("流感周报（北方）", b)
        self.assertNotIn("本轮采集计算未全部完成", b,
                         "整轮 complete 后缀已删（构建前快照恒 false，误报）")
        self.assertIn("本次更新", b)
        self.assertNotIn("上次运行", b)
        # north 页：北方流感失败 + 北方指数失败都聚合（键序 sorted，稳定）
        bn = self._banner(st, page="north")
        self.assertIn("本次未能获取最新数据（流感周报（北方）、全国哨点周报）", bn)
        self.assertIn("指数计算未完成（北方片指数）", bn)
        self.assertNotIn("黑龙江流感周报", bn)

    def test_02_run_id_mismatch_is_history(self):
        st = {"schema": 2, "run_id": "OTHER", "complete": True,
              "sources": {"flu_south": "failed"}}
        b = self._banner(st, run_id="R1")
        self.assertIn("历史运行（非本轮）", b)
        self.assertNotIn("本次更新", b)

    def test_03_local_without_status_is_noted(self):
        # IMP-04：本地构建未提供显式状态 → 必须注明，不得静默（旧断言"恒空"作废）
        with tempfile.TemporaryDirectory() as d:
            old = bs.RUN_STATUS
            bs.RUN_STATUS = Path(d) / "rs.json"
            try:
                b = bs.run_banner(local=True, run_id="R1")
            finally:
                bs.RUN_STATUS = old
        self.assertIn("本地构建", b)
        self.assertIn("未提供本次运行记录", b)

    def test_04_all_ok_no_banner(self):
        st = {"schema": 2, "run_id": "R1", "complete": True,
              "sources": {k: "ok" for k in SIX_SOURCES},
              "compute": {"south": {"status": "ok"}, "north": {"status": "ok"},
                          "heilongjiang": {"status": "ok"}}}
        self.assertEqual(self._banner(st, page="heilongjiang"), "")

    def test_05_bad_json_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            old = bs.RUN_STATUS
            bs.RUN_STATUS = Path(d) / "rs.json"
            try:
                bs.RUN_STATUS.write_text("{not json", encoding="utf-8")
                b = bs.run_banner(run_id="R1")
            finally:
                bs.RUN_STATUS = old
        self.assertIn("无法解析", b)

    def test_06_per_page_relevance_filtering(self):
        # IMP-04：无关源的失败不得出现在别页（黑龙江失败不上重庆页）
        st = {"schema": 2, "run_id": "R1", "complete": False,
              "sources": {"flu_south": "ok", "flu_north": "failed",
                          "heilongjiang_flu": "failed", "heilongjiang_sentinel": "ok",
                          "sentinel": "ok", "flunet": "ok"},
              "compute": {"south": {"status": "ok"}, "north": {"status": "ok"},
                          "heilongjiang": {"status": "ok"}}}
        cq = self._banner(st, page="chongqing")
        self.assertEqual(cq, "", "重庆页与黑龙江/北方源无关，应为空横幅")
        hj = self._banner(st, page="heilongjiang")
        self.assertIn("黑龙江流感周报", hj)
        self.assertNotIn("流感周报（北方）", hj,
                         "黑龙江页无片区指数卡，北方流感失败不上本页")

    def test_07_compute_states(self):
        base = {"schema": 2, "run_id": "R1", "complete": True,
                "sources": {k: "ok" for k in SIX_SOURCES}}
        st1 = dict(base, compute={"south": {"status": "failed"}, "north": {"status": "ok"}})
        self.assertIn("指数计算未完成（南方片指数）", self._banner(st1))
        st2 = dict(base, compute={})  # 缺键 → unknown，不静默
        self.assertIn("指数计算状态未知（北方片指数）", self._banner(st2, page="north"))

    def test_08_missing_fetch_key_unknown(self):
        st = {"schema": 2, "run_id": "R1", "complete": True,
              "sources": {"flu_south": "ok", "sentinel": "ok", "flunet": "ok"},
              "compute": {"south": {"status": "ok"}}}
        # north 页相关键 flu_north 缺失 → 状态未知
        self.assertIn("状态未知（流感周报（北方））", self._banner(st, page="north"))


class U4(unittest.TestCase):
    """导航契约与片区名称卡（只名称、两组、无百分比）。"""

    def test_01_nav_contract(self):
        with tempfile.TemporaryDirectory() as d:
            pages = _render_to(Path(d))
            for name, text in pages.items():
                self.assertEqual(text.count('aria-current="page"'), 1, name)
                for href in re.findall(r'href="([^"]+)"', text):
                    self.assertFalse(href.startswith("/"), f"{name} 站内绝对路径 {href}")
                    if not href.startswith("http"):
                        self.assertTrue(href.endswith(".html"), f"{name} 相对链接 {href}")
                for must in ("成都", "南方片"):
                    self.assertIn(must, text, f"{name} 缺导航项 {must}")

    def test_02_region_names_cards_no_values(self):
        with tempfile.TemporaryDirectory() as d:
            pages = _render_to(Path(d))
            # south/north/chongqing 页不含 child_block，chain span 只来自
            # region_rank_block（名称链）。heilongjiang 页的 B2 卡也用 chain
            # 展示官方百分比（省级哨点实测，允许），故不入数字断言。
            for name in ("south", "north", "chongqing"):
                text = pages[name]
                chains = re.findall(r'<span class="chain">([^<]*)</span>', text)
                self.assertGreaterEqual(len(chains), 2, f"{name} 须有门急诊+住院两组")
                for c in chains:
                    self.assertNotRegex(c, r"[\d.%]")
                    self.assertIn("＞", c)
                self.assertIn("门急诊", text, name)
                self.assertIn("住院", text, name)
                self.assertIn("仅列名称", text, name)
            # 黑龙江页：背景名称卡存在且 B2 卡带官方百分比（两组都在）
            hj = pages["heilongjiang"]
            self.assertIn("仅列名称", hj)
            self.assertIn("门急诊", hj)
            self.assertIn("住院", hj)
            self.assertIn("非完整病原表", hj)
            self.assertIn("未提及不等于 0", hj)


# ---------------- D3 组：复核补充单元/沙箱（IMP-02/03/10/11/12） ----------------

class D3(unittest.TestCase):
    """结果联合校验、compute 整文件失败、hlj CLI 参数、缓存来源绑定。"""

    def test_01_judge_from_result_joint_checks(self):
        # 复核 IMP-03：结果文件状态必须与子进程终态联合校验
        import write_run_status as wrs
        ok_payload = {"run_id": "R1", "sources": {
            "flu_south": {"status": "ok", "week": "2026W45"}}}
        # step 缺失 → 未执行
        r = wrs.judge_from_result(ok_payload, "flu_south", None)
        self.assertEqual(r["status"], wrs.UNKNOWN)
        self.assertIn("未执行", r["reason"])
        # 超时 → ok 也不采信
        r = wrs.judge_from_result(ok_payload, "flu_south",
                                  {"exit": 0, "timed_out": True})
        self.assertEqual(r["status"], wrs.UNKNOWN)
        self.assertIn("超时", r["reason"])
        # 异常退出（exit=2 崩溃/被杀）→ 不采信
        r = wrs.judge_from_result(ok_payload, "flu_south", {"exit": 2})
        self.assertEqual(r["status"], wrs.UNKNOWN)
        self.assertIn("异常退出", r["reason"])
        # exit=1 部分失败 → 逐产品状态采信但 reason 注明（批量隔离成功者）
        mixed = {"run_id": "R1", "sources": {
            "heilongjiang_flu": {"status": "failed", "reason": "parse_error"},
            "heilongjiang_sentinel": {"status": "ok"}}}
        r = wrs.judge_from_result(mixed, "heilongjiang_flu", {"exit": 1})
        self.assertEqual(r["status"], wrs.FAILED)
        self.assertIn("exit=1 部分失败", r["reason"])
        r = wrs.judge_from_result(mixed, "heilongjiang_sentinel", {"exit": 1})
        self.assertEqual(r["status"], wrs.OK)
        # 正常成功
        r = wrs.judge_from_result(ok_payload, "flu_south", {"exit": 0})
        self.assertEqual(r["status"], wrs.OK)
        self.assertEqual(r["week"], "2026W45")
        # 结果文件缺该键 / 坏结构 → unknown
        r = wrs.judge_from_result({"sources": {}}, "flu_south", {"exit": 0})
        self.assertEqual(r["status"], wrs.UNKNOWN)

    def test_01b_read_result_and_step_of_branches(self):
        # 复核 IMP-03 round-3 / IMP-14：read_result 与 step_of 的新校验分支
        # 必须被直接覆盖（顶层类型/stage/origin/manifest 结构）
        import write_run_status as wrs
        with tempfile.TemporaryDirectory() as d:
            rd = Path(d)
            good = {"schema": 2, "run_id": "R1", "stage": "fetch",
                    "origin": "local", "sources": {}}
            (rd / "good.json").write_text(json.dumps(good), encoding="utf-8")
            (rd / "arr.json").write_text("[1,2]", encoding="utf-8")   # 合法 JSON 数组
            (rd / "str.json").write_text('"hello"', encoding="utf-8")  # 合法 JSON 字符串
            (rd / "bad.json").write_text("not-json", encoding="utf-8")
            # 顶层非 dict / 坏 JSON / 缺文件 → None（不抛异常）
            for fn in ("arr.json", "str.json", "bad.json", "missing.json"):
                self.assertIsNone(wrs.read_result(rd, fn, "R1"), fn)
            # run_id 不符 / schema 不符 / stage 不符 / origin 不符 → None
            self.assertIsNone(wrs.read_result(rd, "good.json", "OTHER"))
            g2 = dict(good, schema=1); (rd / "s1.json").write_text(json.dumps(g2), encoding="utf-8")
            self.assertIsNone(wrs.read_result(rd, "s1.json", "R1"))
            self.assertIsNone(wrs.read_result(rd, "good.json", "R1", expect_stage="compute"))
            g3 = dict(good, origin="cloud"); (rd / "oc.json").write_text(json.dumps(g3), encoding="utf-8")
            self.assertIsNone(wrs.read_result(rd, "oc.json", "R1", origin="local"))
            # 匹配 origin 与 stage → payload
            self.assertEqual(
                wrs.read_result(rd, "good.json", "R1", expect_stage="fetch",
                                origin="local"), good)
            # origin 键缺失时不强校验（旧结果文件兼容）
            g4 = {k: v for k, v in good.items() if k != "origin"}
            (rd / "noorigin.json").write_text(json.dumps(g4), encoding="utf-8")
            self.assertEqual(wrs.read_result(rd, "noorigin.json", "R1",
                                             origin="local"), g4)
        # step_of：manifest 非 dict / steps 非 list / 条目非 dict → None
        m = {"steps": [{"name": "flu_south", "exit": 0}]}
        self.assertIsNone(wrs.step_of(None, "flu_south"))
        self.assertIsNone(wrs.step_of({"steps": "x"}, "flu_south"))
        self.assertIsNone(wrs.step_of({"steps": [42, {"name": "flu_south"}]}, "flu_south"))
        self.assertIsNone(wrs.step_of(m, "nope"))
        self.assertEqual(wrs.step_of(m, "flu_south"), {"name": "flu_south", "exit": 0})

    def test_02_flunet_columns_contract(self):
        # 复核 IMP-02：聚合判据必须匹配真实 flunet_china.csv 表头（无 pathogen 列）
        import write_run_status as wrs
        with (ROOT / "data" / "flunet_china.csv").open(
                encoding="utf-8-sig") as f:
            head = f.readline().strip().split(",")
        for col in ("iso_year", "iso_week", "week_start", "inf_positive_pct"):
            self.assertIn(col, head, f"flunet 真实表头缺 {col}（判据需同步）")
        self.assertNotIn("pathogen", head, "flunet 无 pathogen 列，判据不得要求它")

    def test_03_compute_ok_row_empty_value_fails_file(self):
        # 复核 IMP-10：ok 行数值空 → 整文件失败，原文件不动
        import compute_index as ci
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.csv"
            fields = ["iso_year", "iso_week", "ili", "pos", "goldstein_index", "status"]
            rows = [{"iso_year": "2026", "iso_week": "45", "ili": "4.6",
                     "pos": "17.90", "goldstein_index": "", "status": "ok"},
                    {"iso_year": "2026", "iso_week": "44", "ili": "",
                     "pos": "17.14", "goldstein_index": "82.27", "status": "ok"}]
            data_io.atomic_write_csv(p, fields, rows)
            before = p.read_bytes()
            res = _quiet(ci.compute_file, p, "ili", "pos", label="t")
            self.assertEqual(res["status"], "failed")
            self.assertIn("空值", res["reason"])
            self.assertEqual(p.read_bytes(), before, "失败不得写回")

    def test_04_hlj_cli_arg_validation(self):
        # 复核 IMP-11（round-2 补强）：非法参数必须在联网/写入前拒绝（return 2）
        for argv in (["--products", "b9"], ["--products", ""],
                     ["--from", "2024W50"], ["--from", "garbage"],
                     ["--from", "2025W53"],  # round-2：不存在的 ISO 周不能只靠大小放行
                     ["--bogus"], ["--limit", "0"],
                     ["--write-url"],        # round-2：缺值不得静默落入默认抓取
                     ["--result-file"], ["--run-id"],
                     # round-3：缺值且下一 token 是选项时，不得把选项当值放行
                     ["--result-file", "--force"], ["--from", "--force"],
                     ["--products", "--force"], ["--run-id", "--backfill"]):
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                rc = fhj.main(list(argv))
            self.assertEqual(rc, 2, f"{argv} 应被拒绝")

    def test_04b_hlj_products_alias_offline(self):
        # 复核 IMP-11 round-2：冻结计划 flu/sentinel 别名必须被接受。
        # 离线验证技巧：别名解析通过后参数循环才会走到后面的 --bogus——
        # 若别名被拒，报错应是 "--products 用法"而非"未知参数"
        for prods in ("flu", "sentinel", "flu,b2"):
            with contextlib.redirect_stdout(io.StringIO()) as out, \
                    contextlib.redirect_stderr(io.StringIO()) as err:
                rc = fhj.main(["--products", prods, "--bogus"])
            self.assertEqual(rc, 2)
            self.assertIn("未知参数", err.getvalue() + out.getvalue(),
                          f"--products {prods} 别名应被接受（报错应来自 --bogus）")

    def test_05_cache_full_binding(self):
        # 复核 IMP-12 round-2：完整来源绑定——元数据须含 article_url/pdf_url/title/
        # week/sha256 且全部与本轮事实一致才可复用；篡改/缺字段/坏 JSON/URL 不符/
        # 周次不符 → 重下并留痕 cache_invalid；旧裸 txt → 一次性候选后补建绑定留痕
        body = _flu_body("2023年第1周（2023年1月2日-1月8日）", "4522", "3982", "8504",
                         "南方省份哨点医院报告的 ILI% 为 3.6%",
                         "南方省份检测到 2 份流感病毒阳性标本")
        art = 'x <a href="./P0.pdf">2023年第1周第848期中国流感监测周报.pdf</a> y'
        calls = {"n": 0, "pdf": 0}

        def fake_http(url):
            calls["n"] += 1
            if url.endswith(".html"):
                return art.encode("utf-8")
            calls["pdf"] += 1
            return b"PDFBYTES"

        def fake_pdf(raw):
            return body

        def _good_meta(url="http://fake/a.html"):
            # 摘要按原始字节算（与生产 read_bytes() 同口径；read_text 会把
            # CRLF 归一化导致摘要永远不符）
            raw = (txt_dir / "2023_W1.txt").read_bytes()
            return {"article_url": url, "pdf_url": "http://fake/P0.pdf",
                    "title": "2023年第1周中国流感监测周报", "week": "2023W1",
                    "anchor": "2023年第1周第848期中国流感监测周报.pdf",
                    "sha256": hashlib.sha256(raw).hexdigest()}

        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            txt_dir = d / "txt"
            txt_dir.mkdir()
            csv_p = d / "flu_south.csv"
            chlog = d / "changes.log"
            saved = (ffs.TXT_DIR, ffs.CHANGES_LOG, ffs.RATE_LIMIT,
                     ffs.REGIONS["south"]["csv"], ffs.http_get,
                     ffs.pdf_to_text, ffs.enumerate_archive)
            ffs.TXT_DIR = txt_dir
            ffs.CHANGES_LOG = chlog
            ffs.RATE_LIMIT = 0
            ffs.REGIONS["south"]["csv"] = csv_p
            ffs.http_get = fake_http
            ffs.pdf_to_text = fake_pdf
            ffs.enumerate_archive = lambda: (
                {(2023, 1): ("2023年第1周中国流感监测周报",
                             "http://fake/a.html", "2023-01-09")}, {})
            try:
                # A：首轮下载（文章页+PDF），meta 完整落盘
                with contextlib.redirect_stdout(io.StringIO()):
                    ffs.backfill(region="south", from_w=(2023, 1), to_w=(2023, 1))
                self.assertEqual(calls["n"], 2, "首轮应下载文章页+PDF")
                meta = json.loads((txt_dir / "2023_W1.json").read_text(encoding="utf-8"))
                for k in ("article_url", "pdf_url", "title", "week", "sha256"):
                    self.assertIn(k, meta, f"meta 缺 {k}")
                # B：meta 完整但 article_url 不符 → 重下 + cache_invalid 留痕
                csv_p.unlink()
                (txt_dir / "2023_W1.json").write_text(json.dumps(
                    _good_meta("http://fake/OTHER.html")), encoding="utf-8")
                calls["n"] = 0
                with contextlib.redirect_stdout(io.StringIO()):
                    ffs.backfill(region="south", from_w=(2023, 1), to_w=(2023, 1))
                self.assertEqual(calls["n"], 2, "meta URL 不匹配必须重新下载")
                log = chlog.read_text(encoding="utf-8")
                self.assertIn("cache_invalid", log)
                self.assertIn("文章 URL 不符", log)
                meta = json.loads((txt_dir / "2023_W1.json").read_text(encoding="utf-8"))
                self.assertEqual(meta["article_url"], "http://fake/a.html")
                # C：meta 完全匹配 → 零网络请求直接复用
                csv_p.unlink()
                calls["n"] = 0
                with contextlib.redirect_stdout(io.StringIO()):
                    ffs.backfill(region="south", from_w=(2023, 1), to_w=(2023, 1))
                self.assertEqual(calls["n"], 0, "meta 匹配应直接复用缓存")
                rows = ffs.load_rows(csv_p)
                self.assertEqual(rows[0]["south_flu_positive_pct"], "0.04")
                # D：缓存文本被篡改（sha256 不符）→ 重下 + 留痕，缓存恢复
                csv_p.unlink()
                chlog.write_text("", encoding="utf-8")
                (txt_dir / "2023_W1.txt").write_text("TAMPERED", encoding="utf-8")
                calls["n"] = 0
                with contextlib.redirect_stdout(io.StringIO()):
                    ffs.backfill(region="south", from_w=(2023, 1), to_w=(2023, 1))
                self.assertEqual(calls["n"], 2, "摘要不符必须重新下载")
                log = chlog.read_text(encoding="utf-8")
                self.assertIn("cache_invalid", log)
                self.assertIn("摘要不符", log)
                self.assertEqual((txt_dir / "2023_W1.txt").read_text(encoding="utf-8"),
                                 body, "重下后缓存应恢复为真实内容")
                # E：旧裸 txt（无 meta 文件）→ 一次性候选：解析复用缓存文本，
                #    但补全绑定需重取文章页学 pdf_url（复核 IMP-12 round-3：
                #    pdf_url 无效不构成完整绑定，不允许零请求永久信任）
                csv_p.unlink()
                chlog.write_text("", encoding="utf-8")
                (txt_dir / "2023_W1.json").unlink()
                calls["n"] = 0
                calls["pdf"] = 0
                with contextlib.redirect_stdout(io.StringIO()):
                    ffs.backfill(region="south", from_w=(2023, 1), to_w=(2023, 1))
                self.assertEqual(calls["n"], 1,
                                 "旧裸 txt 复用缓存文本，但补全绑定须取文章页 1 次")
                self.assertEqual(calls["pdf"], 0, "复用路径不得下载 PDF")
                self.assertIn("cache_legacy_bind", chlog.read_text(encoding="utf-8"))
                meta = json.loads((txt_dir / "2023_W1.json").read_text(encoding="utf-8"))
                self.assertEqual(meta["article_url"], "http://fake/a.html",
                                 "补建绑定必须记录本轮验证过的文章 URL")
                self.assertEqual(meta["pdf_url"], "http://fake/P0.pdf",
                                 "补全绑定必须取到有效 pdf_url（http）")
                # E2：补全后的 meta 构成完整绑定 → 再次运行零网络
                csv_p.unlink()
                calls["n"] = 0
                with contextlib.redirect_stdout(io.StringIO()):
                    ffs.backfill(region="south", from_w=(2023, 1), to_w=(2023, 1))
                self.assertEqual(calls["n"], 0)
                # F：补建的 meta 若 pdf_url 缺失（文章页取失败）→ 仍按 legacy
                #    一次性候选处理，不升级为零请求信任（每轮重试绑定）
                csv_p.unlink()
                chlog.write_text("", encoding="utf-8")
                meta["pdf_url"] = ""
                (txt_dir / "2023_W1.json").write_text(
                    json.dumps(meta, ensure_ascii=False), encoding="utf-8")
                calls["n"] = 0
                with contextlib.redirect_stdout(io.StringIO()):
                    ffs.backfill(region="south", from_w=(2023, 1), to_w=(2023, 1))
                self.assertEqual(calls["n"], 1,
                                 "pdf_url 无效的 meta 仍须每轮重取文章页补全")
            finally:
                (ffs.TXT_DIR, ffs.CHANGES_LOG, ffs.RATE_LIMIT,
                 ffs.REGIONS["south"]["csv"], ffs.http_get,
                 ffs.pdf_to_text, ffs.enumerate_archive) = saved


# ---------------- E 组：构建零改动 data/ ----------------

class E1(unittest.TestCase):
    def test_01_render_leaves_data_untouched(self):
        data_dir = ROOT / "data"
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(data_dir.glob("*")) if p.is_file()}
        with tempfile.TemporaryDirectory() as d:
            _render_to(Path(d))
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(data_dir.glob("*")) if p.is_file()}
        self.assertEqual(before, after)

    def test_02_validate_pages_rejects_incomplete_set(self):
        # 复核 IMP-06 关闭条件之一：暂存校验必须拦住不完整五页（缺页 → SystemExit）
        with tempfile.TemporaryDirectory() as d:
            stage = Path(d)
            for slug in ("index", "south", "north", "heilongjiang"):  # 缺 chongqing
                (stage / f"{slug}.html").write_text("<html>x</html>", encoding="utf-8")
            with self.assertRaises(SystemExit):
                bs._validate_pages(stage)

    def test_03_validate_pages_rejects_bad_links(self):
        # 暂存页含绝对路径站内链接 / 指向不存在页的相对链接 → SystemExit
        with tempfile.TemporaryDirectory() as d:
            stage = Path(d)
            for slug in ("index", "south", "north", "heilongjiang", "chongqing"):
                body = '<a href="index.html">home</a>'
                if slug == "south":
                    body = '<a href="/missing.html">abs</a>'
                (stage / f"{slug}.html").write_text(f"<html>{body}</html>",
                                                    encoding="utf-8")
            with self.assertRaises(SystemExit):
                bs._validate_pages(stage)
        with tempfile.TemporaryDirectory() as d:
            stage = Path(d)
            for slug in ("index", "south", "north", "heilongjiang", "chongqing"):
                body = '<a href="nosuch.html">missing</a>'
                (stage / f"{slug}.html").write_text(f"<html>{body}</html>",
                                                    encoding="utf-8")
            with self.assertRaises(SystemExit):
                bs._validate_pages(stage)

    def test_04_validate_pages_accepts_valid_set(self):
        with tempfile.TemporaryDirectory() as d:
            stage = Path(d)
            for slug in ("index", "south", "north", "heilongjiang", "chongqing"):
                body = (f'<a href="index.html">home</a>'
                        f'<a href="https://www.chinacdc.cn/x.html">off</a>')
                (stage / f"{slug}.html").write_text(f"<html>{body}</html>",
                                                    encoding="utf-8")
            self.assertIsNone(bs._validate_pages(stage))


# ---------------- R3 组：管线故障矩阵（复核 IMP-05/14 round-2）----------------

class R3(unittest.TestCase):
    """受控故障注入（隔离根，全部在真实 run_pipeline.py 入口）：
    预聚合失败 → exit 2 不构建；构建失败 → 发布门关闭；单源 fetch 失败 → exit 1
    仍出诚实降级页；fetch 超时 → unknown 且管线正常收尾不挂死。
    """

    def _run(self, root: Path, *extra, timeout=300):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(root / "src" / "run_pipeline.py"),
             *extra],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout)

    def _last_run(self, root):
        return json.loads((root / ".tmp_pipeline" / "last_run.json")
                          .read_text(encoding="utf-8"))

    def test_01_preagg_failure_exit2_no_build(self):
        with tempfile.TemporaryDirectory() as d:
            root = _iso_root(Path(d))
            # 受控故障：聚合器自身退出非零（预聚合失败 = 证据链不完整）
            (root / "src" / "write_run_status.py").write_text(
                "import sys\nsys.exit(3)\n", encoding="utf-8")
            r = self._run(root, *SKIP_ALL, timeout=180)
            self.assertEqual(r.returncode, 2,
                             r.stdout[-1500:] + r.stderr[-1500:])
            last = self._last_run(root)
            self.assertEqual(last["exit"], 2)
            self.assertIsNone(last["build_exit"])
            self.assertFalse(last["site_ready"])
            self.assertIn("reason", last)
            self.assertFalse((root / "site" / "index.html").exists(),
                             "预聚合失败不得构建页面")

    def test_02_build_failure_closes_gate(self):
        with tempfile.TemporaryDirectory() as d:
            root = _iso_root(Path(d))
            (root / "src" / "build_site.py").write_text(
                "import sys\nsys.exit(3)\n", encoding="utf-8")
            r = self._run(root, *SKIP_ALL, timeout=180)
            self.assertEqual(r.returncode, 2,
                             r.stdout[-1500:] + r.stderr[-1500:])
            last = self._last_run(root)
            self.assertEqual(last["exit"], 2)
            self.assertEqual(last["build_exit"], 3)
            self.assertFalse(last["site_ready"], "构建失败必须关发布门")
            gate = json.loads((Path(last["run_dir"]) / "site_ready.json")
                              .read_text(encoding="utf-8"))
            self.assertFalse(gate["site_ready"])

    def test_03_partial_fetch_failure_exit1_still_builds(self):
        with tempfile.TemporaryDirectory() as d:
            root = _iso_root(Path(d))
            # 受控故障：flu_south 步骤 exit 1 且不写结果文件（→ unknown）
            (root / "src" / "fetch_flu_south.py").write_text(
                "import sys\nsys.exit(1)\n", encoding="utf-8")
            skip4 = ("--local", "--skip",
                     "flunet,sentinel,heilongjiang_flu,heilongjiang_sentinel")
            r = self._run(root, *skip4, timeout=180)
            self.assertEqual(r.returncode, 1,
                             r.stdout[-1500:] + r.stderr[-1500:])
            last = self._last_run(root)
            self.assertEqual(last["exit"], 1)
            self.assertTrue((root / "site" / "index.html").exists(),
                            "部分失败仍须产出诚实降级页")
            st = json.loads((Path(last["run_dir"]) / "run_status.json")
                            .read_text(encoding="utf-8"))
            self.assertNotEqual(bs._status_of(st["sources"]["flu_south"])[0],
                                "ok", "无结果文件的失败源不得标 ok")

    def test_04_fetch_timeout_marks_unknown_pipeline_finishes(self):
        with tempfile.TemporaryDirectory() as d:
            root = _iso_root(Path(d))
            (root / "src" / "fetch_flu_south.py").write_text(
                "import time\ntime.sleep(60)\n", encoding="utf-8")
            skip4 = ("--local", "--skip",
                     "flunet,sentinel,heilongjiang_flu,heilongjiang_sentinel")
            t0 = time.time()
            r = self._run(root, *skip4, "--timeout", "3", timeout=180)
            elapsed = time.time() - t0
            self.assertLess(elapsed, 120, "超时后管线必须正常收尾，不得挂死")
            self.assertNotEqual(r.returncode, 0)
            last = self._last_run(root)
            self.assertEqual(last["exit"], r.returncode)
            st = json.loads((Path(last["run_dir"]) / "run_status.json")
                            .read_text(encoding="utf-8"))
            self.assertEqual(bs._status_of(st["sources"]["flu_south"])[0],
                             "unknown", "超时源必须标 unknown（不采信也不猜失败）")

    def test_05_final_status_write_failure_closes_gate(self):
        # 复核 IMP-05 round-3 / IMP-14：构建成功但最终状态聚合失败 →
        # 证据链不完整，发布门必须关闭（页面可已生成，但不得宣称可发布）
        with tempfile.TemporaryDirectory() as d:
            root = _iso_root(Path(d))
            # 受控故障：预聚合（无 --build-exit）写最小合法 v2 后成功；
            # 最终聚合（带 --build-exit）注入失败
            wrapper = (
                "import sys, json\n"
                "args = sys.argv[1:]\n"
                "if '--build-exit' in args:\n"
                "    sys.stderr.write('injected final-status failure\\n')\n"
                "    sys.exit(3)\n"
                "out = args[args.index('--out') + 1]\n"
                "rid = args[args.index('--run-id') + 1]\n"
                "org = args[args.index('--origin') + 1]\n"
                "with open(out, 'w', encoding='utf-8') as f:\n"
                "    f.write(json.dumps({'schema': 2, 'run_id': rid, 'origin': org,"
                " 'run_at': '2026-11-13T00:00:00', 'sources': {},"
                " 'complete': False}))\n"
                "sys.exit(0)\n")
            (root / "src" / "write_run_status.py").write_text(wrapper, encoding="utf-8")
            r = self._run(root, *SKIP_ALL, timeout=180)
            self.assertEqual(r.returncode, 2,
                             r.stdout[-1500:] + r.stderr[-1500:])
            last = self._last_run(root)
            self.assertEqual(last["exit"], 2, "状态落盘失败 = 不可部署")
            self.assertEqual(last["build_exit"], 0, "构建本身成功（页面已生成）")
            self.assertFalse(last["site_ready"], "状态写失败必须关发布门")
            gate = json.loads((Path(last["run_dir"]) / "site_ready.json")
                              .read_text(encoding="utf-8"))
            self.assertFalse(gate["site_ready"])


# ---------------- R4 组：锁不可辨认窗口（复核 IMP-01 round-2）----------------

class R4(unittest.TestCase):
    """空锁/坏 JSON/pid 非法：一律拒绝且不删除（不得误删正在建立的活锁）。"""

    def _run(self, root: Path, *extra, timeout=180):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(root / "src" / "run_pipeline.py"),
             *SKIP_ALL, *extra],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout)

    def _assert_refused_and_kept(self, root, lock, label):
        r = self._run(root)
        self.assertNotEqual(r.returncode, 0, f"{label} 必须拒绝")
        self.assertTrue(lock.exists(), f"{label} 不得被删除（可能是正在建立的活锁）")
        self.assertTrue(("无法辨认" in r.stdout + r.stderr)
                        or ("拒绝" in r.stdout + r.stderr)
                        or ("手动删除" in r.stdout + r.stderr),
                        f"{label} 应提示交人工处理")

    def test_01_empty_lock_refused(self):
        # 排他创建与写入 PID 之间的空锁窗口：他人不得当作死锁删除
        with tempfile.TemporaryDirectory() as d:
            root = _iso_root(Path(d))
            lock = root / ".tmp_pipeline" / "lock"
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text("", encoding="utf-8")
            self._assert_refused_and_kept(root, lock, "空锁")

    def test_02_broken_json_lock_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = _iso_root(Path(d))
            lock = root / ".tmp_pipeline" / "lock"
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text("not-json{{", encoding="utf-8")
            self._assert_refused_and_kept(root, lock, "坏 JSON 锁")

    def test_03_pid_zero_lock_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = _iso_root(Path(d))
            lock = root / ".tmp_pipeline" / "lock"
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text(json.dumps({"pid": 0, "started_at": "x"}),
                            encoding="utf-8")
            self._assert_refused_and_kept(root, lock, "pid=0 锁")

    def test_04_force_unlock_still_refuses_unrecognizable_locks(self):
        # 复核 IMP-01 round-3：--force-unlock 只适用于"可辨认且已死"的锁；
        # 空锁/坏锁/pid 非法即使带 force 也必须拒绝且不删（force 不是万能钥匙）
        for content, label in (("", "空锁+force"), ("not-json{{", "坏JSON锁+force"),
                               (json.dumps({"pid": 0}), "pid0锁+force")):
            with tempfile.TemporaryDirectory() as d:
                root = _iso_root(Path(d))
                lock = root / ".tmp_pipeline" / "lock"
                lock.parent.mkdir(parents=True, exist_ok=True)
                lock.write_text(content, encoding="utf-8")
                r = self._run(root, "--force-unlock")
                self.assertNotEqual(r.returncode, 0, f"{label} 必须拒绝")
                self.assertTrue(lock.exists(), f"{label} 不得删除锁文件")
                self.assertTrue(("无法辨认" in r.stdout + r.stderr)
                                or ("拒绝" in r.stdout + r.stderr)
                                or ("手动删除" in r.stdout + r.stderr),
                                f"{label} 应提示交人工处理")

    def test_05_two_recoverers_cannot_both_delete_lock(self):
        # 复核 IMP-01 round-3 关闭条件：两个 --force-unlock 恢复者竞态。
        # rename 原子夺取协议：rename 成功者独占删除权；失败者重新竞争创建。
        # 恒言：恰一个成功持锁，另一拒绝，且锁文件最终属于胜者（无第三人锁被误删）。
        import threading
        with tempfile.TemporaryDirectory() as d:
            lock_dir = Path(d) / ".tmp_pipeline"
            lock_dir.mkdir(parents=True)
            lock = lock_dir / "lock"
            lock.write_text(json.dumps({"pid": 999999, "started_at": "x"}),
                            encoding="utf-8")
            saved = rp.LOCK
            rp.LOCK = lock
            real_stdout = sys.stdout
            sys.stdout = io.StringIO()  # 共享缓冲：避免两线程嵌套 redirect_stdout 互相恢复错位
            try:
                barrier = threading.Barrier(2)
                results = []

                def recover():
                    barrier.wait()
                    results.append(rp.acquire_lock(force=True))

                t1 = threading.Thread(target=recover)
                t2 = threading.Thread(target=recover)
                t1.start(); t2.start(); t1.join(); t2.join()
                self.assertEqual(sorted(results), [False, True],
                                 "两个恢复者必须恰一个成功持锁")
                self.assertTrue(lock.exists(), "胜者的锁必须在场")
                info = json.loads(lock.read_text(encoding="utf-8"))
                self.assertEqual(info["pid"], os.getpid(),
                                 "锁必须属于胜者（本测试进程），不得残留死 pid")
                leftovers = list(lock_dir.glob("lock.dead.*"))
                self.assertEqual(leftovers, [],
                                 "rename 夺取后残片必须被清理")
            finally:
                sys.stdout = real_stdout
                rp.LOCK = saved


# ---------------- H3 组：B2 同周多篇规范化（复核 IMP-08 round-2）----------------

def _b2_item(aid, week, date):
    return {"id": aid, "title": f"2026年第{week}周黑龙江省急性呼吸道哨点监测周报",
            "date": date, "kind": "b2",
            "url": f"http://fake/{aid}.html", "page": 1}


def _b2_rows(rate="4.00", n_opd="150", n_inp="72", week="45"):
    total = str(int(n_opd) + int(n_inp))
    base = {"iso_year": "2026", "iso_week": week, "week_start": "2026-11-02",
            "source_url": "", "source_pubdate": "", "fetched_at": "", "status": "ok"}
    return [
        {"setting": "门急诊", "pathogen": "鼻病毒", "positive_pct": rate,
         "sample_count": n_opd, "total_samples": total, **base},
        {"setting": "住院", "pathogen": "博卡病毒", "positive_pct": rate,
         "sample_count": n_inp, "total_samples": total, **base},
    ]


class H3(unittest.TestCase):
    """_pick_b2 / _fetch_latest_b2：等值确定性代表；异值冲突保全旧表；
    只解析最新标题周；全部解析失败如实报。
    """

    def setUp(self):
        self.saved = (fhj.CHANGES_LOG, fhj.B1_CSV, fhj.B2_CSV,
                      fhj.parse_one, fhj.replace_b2)
        fd = tempfile.TemporaryDirectory()
        self._fd = fd
        d = Path(fd.name)
        fhj.CHANGES_LOG = d / "changes.log"
        fhj.B1_CSV = d / "b1.csv"
        fhj.B2_CSV = d / "b2.csv"

    def tearDown(self):
        (fhj.CHANGES_LOG, fhj.B1_CSV, fhj.B2_CSV,
         fhj.parse_one, fhj.replace_b2) = self.saved
        self._fd.cleanup()

    def test_01_equal_multidoc_deterministic_rep(self):
        calls = []
        rows = _b2_rows()

        def fake_parse(it):
            calls.append(it["id"])
            return {"kind": "b2", "rows": [dict(r) for r in rows],
                    "title": it["title"], "pubdate": it["date"]}
        fhj.parse_one = fake_parse
        pick = fhj._pick_b2([_b2_item("a", 45, "2026-11-12"),
                             _b2_item("b", 45, "2026-11-11")])
        self.assertEqual(pick["status"], "ok")
        self.assertEqual(pick["n"], 2)
        self.assertEqual(pick["rep"]["item"]["id"], "b",
                         "同值多篇必须按 (pubdate,url) 确定性代表，不按列表序")

    def test_02_conflict_multidoc_no_write(self):
        rates = {"a": "4.00", "b": "5.00"}
        fhj.parse_one = lambda it: {
            "kind": "b2", "rows": _b2_rows(rate=rates[it["id"]]),
            "title": it["title"], "pubdate": it["date"]}
        writes = []
        fhj.replace_b2 = lambda *a, **k: writes.append(a) or 0
        results = {"heilongjiang_sentinel": {}}
        fhj._fetch_latest_b2([_b2_item("a", 45, "2026-11-12"),
                              _b2_item("b", 45, "2026-11-11")], results)
        self.assertEqual(results["heilongjiang_sentinel"]["status"], "failed")
        self.assertIn("数值冲突", results["heilongjiang_sentinel"]["reason"])
        self.assertEqual(writes, [], "冲突周不得覆盖旧成功表")

    def test_03_only_newest_title_week_parsed(self):
        calls = []
        fhj.parse_one = lambda it: calls.append(it["id"]) or {
            "kind": "b2", "rows": _b2_rows(week=it["title"][6:8].rstrip("周")),
            "title": it["title"], "pubdate": it["date"]}
        pick = fhj._pick_b2([_b2_item("a", 45, "2026-11-12"),
                             _b2_item("b", 44, "2026-11-05")])
        self.assertEqual(pick["status"], "ok")
        self.assertEqual(calls, ["a"], "旧周候选不解析（不抓正文）")

    def test_04_all_parse_fail_reported(self):
        def boom(it):
            raise RuntimeError("parse_error: 未解析到标本总数/两组构成")
        fhj.parse_one = boom
        results = {"heilongjiang_sentinel": {}}
        fhj._fetch_latest_b2([_b2_item("a", 45, "2026-11-12")], results)
        self.assertEqual(results["heilongjiang_sentinel"]["status"], "failed")
        self.assertIn("全部解析失败", results["heilongjiang_sentinel"]["reason"])

    def test_05_unparseable_title_mixed_weeks_no_false_conflict(self):
        """复核修正回归：标题不可解析 + 不同周文章混合，不得伪冲突。

        真实故障：全量枚举 16 篇 B2 中 1 篇标题不匹配 TITLE_WEEK，
        旧实现走"保守全解析"把不同周文章放同一集合比签名 → 必然伪冲突，
        2026W45 被误判「多篇 B2 数值冲突」。修正后按正文周次分组。
        """
        rows_by_week = {"a": _b2_rows(week="45"),
                        "b": _b2_rows(rate="9.00", week="43"),
                        "c": _b2_rows(rate="8.00", week="42")}
        items = [
            _b2_item("a", 45, "2026-11-12"),
            _b2_item("b", 43, "2026-10-29"),
            {"id": "c", "title": "黑龙江省呼吸道哨点监测情况（转载汇编）",
             "date": "2026-10-22", "kind": "b2",
             "url": "http://fake/c.html", "page": 3},  # 标题周次不可解析
        ]
        fhj.parse_one = lambda it: {
            "kind": "b2", "rows": rows_by_week[it["id"]],
            "title": it["title"], "pubdate": it["date"]}
        pick = fhj._pick_b2(items)
        self.assertEqual(pick["status"], "ok")
        self.assertEqual(pick["week"], (2026, 45))
        self.assertEqual(pick["rep"]["item"]["id"], "a")
        self.assertEqual(pick["n"], 1,
                         "不同正文周次不得进同一签名集合（伪冲突源头）")

    def test_06_unparseable_title_same_content_week_conflict_still_caught(self):
        """标题不可解析但正文同周异值：真冲突仍必须被抓住。"""
        rows_by_id = {"a": _b2_rows(week="45"),
                      "b": _b2_rows(rate="5.00", week="45")}
        items = [
            _b2_item("a", 45, "2026-11-12"),
            {"id": "b", "title": "黑龙江省急性呼吸道传染病哨点监测情况",
             "date": "2026-11-13", "kind": "b2",
             "url": "http://fake/b.html", "page": 1},  # 标题不可解析，正文 W45
        ]
        fhj.parse_one = lambda it: {
            "kind": "b2", "rows": rows_by_id[it["id"]],
            "title": it["title"], "pubdate": it["date"]}
        pick = fhj._pick_b2(items)
        self.assertEqual(pick["status"], "conflict")
        self.assertEqual(pick["week"], (2026, 45))

    def test_07_newest_title_fail_not_downgraded_to_older_week(self):
        """复核 IMP-08 round-3 NEW-BY-FIX：标题 W46 候选解析失败 + 标题不可解析
        （正文 W45）候选成功 → 不得从成功集合倒退选 W45 宣称成功，必须整期失败保全。
        """
        def fake_parse(it):
            if it["id"] == "a":
                raise RuntimeError("parse_error: 未解析到标本总数/两组构成")
            return {"kind": "b2", "rows": _b2_rows(week="45"),
                    "title": it["title"], "pubdate": it["date"]}
        fhj.parse_one = fake_parse
        items = [
            _b2_item("a", 46, "2026-11-13"),   # 最新标题周，解析失败
            {"id": "b", "title": "黑龙江省呼吸道哨点监测情况（转载汇编）",
             "date": "2026-11-12", "kind": "b2",
             "url": "http://fake/b.html", "page": 2},  # 标题不可解析，正文 W45
        ]
        pick = fhj._pick_b2(items)
        self.assertEqual(pick["status"], "failed")
        self.assertIn("保全", pick["reason"])

    def test_08_same_title_week_one_fail_one_ok_preserves(self):
        """复核 IMP-08 round-3：同标题周一篇失败一篇成功 → 无法确认该周真相，
        整期失败保全，不得静默采用成功那篇。
        """
        def fake_parse(it):
            if it["id"] == "bad":
                raise RuntimeError("parse_error: 未解析到标本总数/两组构成")
            return {"kind": "b2", "rows": _b2_rows(week="45"),
                    "title": it["title"], "pubdate": it["date"]}
        fhj.parse_one = fake_parse
        pick = fhj._pick_b2([_b2_item("bad", 45, "2026-11-13"),
                             _b2_item("ok", 45, "2026-11-12")])
        self.assertEqual(pick["status"], "failed")
        self.assertIn("候选解析失败", pick["reason"])


# ---------------- D6 组：黑龙江单产品写域（复核 IMP-11 round-2）----------------

class D6(unittest.TestCase):
    """--products b2 的回补：不做 B1 遍历/解析/写入（B1 表逐字节不变）。"""

    def test_01_b2_only_backfill_skips_b1_entirely(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            saved = (fhj.CHANGES_LOG, fhj.B1_CSV, fhj.B2_CSV,
                     fhj.list_items, fhj.parse_one, fhj.replace_b2)
            fhj.CHANGES_LOG = d / "changes.log"
            fhj.B1_CSV = d / "b1.csv"
            fhj.B2_CSV = d / "b2.csv"
            fhj.B1_CSV.write_text("header-only", encoding="utf-8")
            before = fhj.B1_CSV.read_bytes()
            fhj.list_items = lambda pageno: [_b2_item("a", 45, "2026-11-12")]
            fhj.parse_one = lambda it: {
                "kind": "b2", "rows": _b2_rows(), "title": it["title"],
                "pubdate": it["date"]}
            fhj.replace_b2 = lambda *a, **k: 2
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    res = fhj.backfill(products=("b2",))
                self.assertEqual(res["heilongjiang_sentinel"]["status"], "ok")
                self.assertEqual(res["heilongjiang_flu"]["status"], "unknown")
                self.assertIn("请求范围", res["heilongjiang_flu"].get("reason", ""))
                self.assertEqual(fhj.B1_CSV.read_bytes(), before,
                                 "b2-only 回补不得触碰 B1 表")
            finally:
                (fhj.CHANGES_LOG, fhj.B1_CSV, fhj.B2_CSV,
                 fhj.list_items, fhj.parse_one, fhj.replace_b2) = saved

    def test_02_result_file_contains_only_requested_products(self):
        # 复核 IMP-11 round-3：--result-file 只表达本次请求的产品，
        # 未请求产品不得出现在结果文件（会误导状态聚合方）
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            rf = d / "result.json"
            saved = (fhj.CHANGES_LOG, fhj.B1_CSV, fhj.B2_CSV,
                     fhj.list_items, fhj.parse_one, fhj.replace_b2)
            fhj.CHANGES_LOG = d / "changes.log"
            fhj.B1_CSV = d / "b1.csv"
            fhj.B2_CSV = d / "b2.csv"
            fhj.list_items = lambda pageno: [_b2_item("a", 45, "2026-11-12")]
            fhj.parse_one = lambda it: {
                "kind": "b2", "rows": _b2_rows(), "title": it["title"],
                "pubdate": it["date"]}
            fhj.replace_b2 = lambda *a, **k: 2
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = fhj.main(["--products", "b2", "--result-file", str(rf),
                                   "--run-id", "T1"])
                self.assertEqual(rc, 0)
                payload = json.loads(rf.read_text(encoding="utf-8"))
                self.assertIn("heilongjiang_sentinel", payload["sources"])
                self.assertNotIn("heilongjiang_flu", payload["sources"],
                                 "未请求产品不得写入结果文件")
            finally:
                (fhj.CHANGES_LOG, fhj.B1_CSV, fhj.B2_CSV,
                 fhj.list_items, fhj.parse_one, fhj.replace_b2) = saved


# ---------------- U5 组：片区前三名占位与独立锚周（复核 IMP-07 round-2）----------------

def _rank_csv_write(path, rows):
    fields = ["iso_year", "iso_week", "dimension", "category", "setting",
              "rank1", "rank2", "rank3", "source_url", "fetched_at", "status"]
    data_io.atomic_write_csv(path, fields, rows)


def _rank_row(y, w, category, setting, r1="", r2="", r3="",
              status="ok", url="https://www.chinacdc.cn/jksj/jksj04_14275/x.html"):
    return {"iso_year": str(y), "iso_week": str(w), "dimension": "region",
            "category": category, "setting": setting,
            "rank1": r1, "rank2": r2, "rank3": r3, "source_url": url,
            "fetched_at": "2026-11-13T00:00:00", "status": status}


class U5(unittest.TestCase):
    """真实占位行（category=全部/setting=全部/rank_unavailable）必须把锚周顶到
    最新周并如实标"本工具未取得"；两组独立锚周；同周冲突判异常。
    """

    def test_01_placeholder_anchors_latest_week(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "rank.csv"
            _rank_csv_write(p, [
                _rank_row(2026, 43, "南方省份", "门急诊", "流感病毒", "鼻病毒", "人偏肺病毒"),
                _rank_row(2026, 43, "南方省份", "住院", "鼻病毒", "流感病毒", "博卡病毒"),
                _rank_row(2026, 45, "全部", "全部", status="rank_unavailable"),
            ])
            saved = bs.RANK_CSV
            bs.RANK_CSV = p
            try:
                html = bs.region_rank_block("南方省份", "南方片")
            finally:
                bs.RANK_CSV = saved
            self.assertIn("2026年第45周", html, "锚周必须顶到占位行的 45 周")
            self.assertIn("本工具未取得", html)
            self.assertNotIn("官方未提供", html, "不得把解析缺失说成官方缺失")
            self.assertNotIn('class="chain"', html,
                             "占位周不得静默回退 43 周的旧排名")
            self.assertNotIn("流感病毒", html, "43 周的具体病名不得漏出")

    def test_02_two_settings_independent_weeks(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "rank.csv"
            _rank_csv_write(p, [
                _rank_row(2026, 44, "南方省份", "门急诊", "A病毒", "B病毒", "C病毒"),
                _rank_row(2026, 43, "南方省份", "住院", "D病毒", "E病毒", "F病毒"),
            ])
            saved = bs.RANK_CSV
            bs.RANK_CSV = p
            try:
                html = bs.region_rank_block("南方省份", "南方片")
            finally:
                bs.RANK_CSV = saved
            self.assertIn("2026年第44周", html)
            self.assertIn("2026年第43周", html, "两组必须各自锚定自己的最新周")
            self.assertIn("A病毒", html)
            self.assertIn("D病毒", html)

    def test_03_same_week_conflict_marks_anomaly(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "rank.csv"
            _rank_csv_write(p, [
                _rank_row(2026, 44, "南方省份", "门急诊", "A病毒", "B病毒", "C病毒"),
                _rank_row(2026, 44, "南方省份", "门急诊", "X病毒", "B病毒", "C病毒"),
            ])
            saved = bs.RANK_CSV
            bs.RANK_CSV = p
            try:
                html = bs.region_rank_block("南方省份", "南方片")
            finally:
                bs.RANK_CSV = saved
            self.assertIn("数据异常", html, "同周重复行不一致必须判异常，不按行序取值")

    def test_04_source_labels_table2_only(self):
        # 复核 IMP-07 round-3 非阻塞：片区名称卡数据来自哨点周报表 2，
        # 不得笼统写"表2/表3"（表 3 是年龄分组，与本卡无关）
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "rank.csv"
            _rank_csv_write(p, [
                _rank_row(2026, 44, "南方省份", "门急诊", "A病毒", "B病毒", "C病毒"),
            ])
            saved = bs.RANK_CSV
            bs.RANK_CSV = p
            try:
                html = bs.region_rank_block("南方省份", "南方片")
            finally:
                bs.RANK_CSV = saved
            self.assertIn("哨点监测情况", html)
            self.assertIn("表2", html)
            self.assertNotIn("表2/表3", html)


# ---------------- U6 组：按页来源与显式身份（复核 IMP-04 round-2）----------------

class U6(unittest.TestCase):
    def test_01_page_sources_match_actual_cards(self):
        # 重庆页只有哨点名称卡（sentinel）；黑龙江页无片区指数卡；
        # 南北两片的指数页才含 flu_south/flu_north 与对应 compute
        self.assertEqual(bs.PAGE_SOURCES["chongqing"], ({"sentinel"}, set()))
        self.assertEqual(bs.PAGE_SOURCES["heilongjiang"],
                         ({"heilongjiang_flu", "heilongjiang_sentinel", "sentinel"},
                          {"heilongjiang"}))
        self.assertEqual(bs.PAGE_SOURCES["south"],
                         ({"flu_south", "sentinel"}, {"south"}))
        self.assertEqual(bs.PAGE_SOURCES["north"],
                         ({"flu_north", "sentinel"}, {"north"}))

    def test_02_render_rejects_run_id_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            st = d / "status.json"
            st.write_text(json.dumps({"schema": 2, "run_id": "RID-A",
                                      "origin": "cloud", "sources": {}}),
                          encoding="utf-8")
            with self.assertRaises(SystemExit) as cm:
                bs.render({"run_status": str(st), "run_id": "RID-B"})
            self.assertEqual(cm.exception.code, 2, "错 run_id 必须拒绝构建")


# ---------------- E2 组：构建失败保全与门（复核 IMP-06/14 round-2）----------------

class E2(unittest.TestCase):
    def test_01_render_failure_keeps_old_pages(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            # 预置旧五页
            old = {}
            names = ["index"] + list(bs.PAGES)
            for n in names:
                p = d / f"{n}.html"
                p.write_text(f"OLD-{n}", encoding="utf-8")
                old[n] = p.read_bytes()
            saved_val = bs._validate_pages
            out = bs.OUT
            argv = sys.argv[:]
            bs._validate_pages = lambda sd: (_ for _ in ()).throw(SystemExit(2))
            bs.OUT = d / "index.html"
            sys.argv = ["build_site.py", "--local"]
            try:
                with self.assertRaises(SystemExit):
                    with contextlib.redirect_stdout(io.StringIO()):
                        bs.render()
            finally:
                bs._validate_pages = saved_val
                bs.OUT = out
                sys.argv = argv
            for n in names:
                self.assertEqual((d / f"{n}.html").read_bytes(), old[n],
                                 f"校验失败不得替换旧页 {n}")

    def test_02_replace_phase_failure_propagates(self):
        # 复核 IMP-06 round-3 / IMP-14：替换阶段故障必须让构建失败外显
        # （管线据此关发布门），不得吞掉后宣称成功。设计不承诺目录级原子：
        # 已替换页保持新内容、未替换页保持旧内容，均须可辨认。
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            names = ["index"] + list(bs.PAGES)
            for n in names:
                (d / f"{n}.html").write_text(f"OLD-{n}", encoding="utf-8")
            real_replace = os.replace
            state = {"n": 0}

            def flaky(src, dst):
                state["n"] += 1
                if state["n"] == 2:
                    raise OSError("injected replace failure")
                return real_replace(src, dst)

            out = bs.OUT
            argv = sys.argv[:]
            bs.OUT = d / "index.html"
            sys.argv = ["build_site.py", "--local"]
            try:
                with mock.patch("os.replace", side_effect=flaky):
                    with self.assertRaises(OSError, msg="替换失败必须外显，不得吞掉"):
                        with contextlib.redirect_stdout(io.StringIO()):
                            bs.render()
            finally:
                bs.OUT = out
                sys.argv = argv
            # 无目录级原子承诺：部分页可能已换新（含 NEW 内容/长度变化），
            # 但绝不允许"五页全旧却无人知道失败"——异常已外显即受控
            self.assertGreaterEqual(state["n"], 2)
            replaced_new = sum(
                1 for n in names
                if (d / f"{n}.html").read_text(encoding="utf-8") != f"OLD-{n}")
            self.assertLess(replaced_new, len(names), "失败点之后的页必须保持旧内容")


if __name__ == "__main__":
    unittest.main(verbosity=2)

# -*- coding: utf-8 -*-
"""A1b 验证脚本：数据契约 / 环比 / 历史选择 / 回归 / 端到端。

用法：
  python -X utf8 check_history.py --capture-baseline   # 修改功能前记录基线
  python -X utf8 check_history.py --check              # 运行全部测试
  python -X utf8 check_history.py --check Reg          # 只跑名称含 Reg 的用例

设计要点：
- 仅标准库（unittest/importlib/tempfile/hashlib/subprocess）。
- 回归基线从 git 基线 commit a94591753f763351cb095fd3a813cfa69607ac1b 提取
  src/build_site.py 源码，在隔离模块中与当前实现 A/B 对比：非目标函数
  源码逐字节相等 + 相同输入输出相等。
- S2（图表渲染）落地前，图表/表格相关用例自动 skip；落地后自动生效。
"""
import csv
import hashlib
import html
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TMP = ROOT / ".tmp_a1b"
BASE_COMMIT = "a94591753f763351cb095fd3a813cfa69607ac1b"
FIELDS = ["iso_year", "iso_week", "week_start", "south_ili_pct",
          "south_flu_positive_pct", "goldstein_index", "source_url",
          "source_pubdate", "fetched_at", "status"]

_cur = None
_base = None


def cur():
    """加载当前 src/build_site.py（每进程一次）。"""
    global _cur
    if _cur is None:
        sys.path.insert(0, str(ROOT / "src"))
        spec = importlib.util.spec_from_file_location(
            "build_site_cur", ROOT / "src" / "build_site.py")
        _cur = importlib.util.module_from_spec(spec)
        sys.modules["build_site_cur"] = _cur
        spec.loader.exec_module(_cur)
    return _cur


def base(tmp: Path):
    """从 git 基线 commit 提取 build_site 源码并加载为隔离模块。"""
    global _base
    if _base is None:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{BASE_COMMIT}:src/build_site.py"],
            capture_output=True, check=True)
        p = tmp / "build_site_base.py"
        p.write_bytes(out.stdout)
        sys.path.insert(0, str(ROOT / "src"))
        spec = importlib.util.spec_from_file_location("build_site_base", p)
        _base = importlib.util.module_from_spec(spec)
        sys.modules["build_site_base"] = _base
        spec.loader.exec_module(_base)
        # 修正其 ROOT 派生路径，指向真实数据
        _base.SC_CSV = ROOT / "data" / "sichuan_monthly.csv"
        _base.RUN_STATUS = ROOT / "data" / "run_status.json"
        _base.OUT = tmp / "out_base.html"
    return _base


def row(y, w, ili, pos, g, status="ok", ws=None, url="https://ivdc.example/t.html",
        pub="2026-11-05", fat="2026-11-09T08:00:00"):
    return dict(zip(FIELDS, [str(y), str(w), ws or f"{y}-01-02", str(ili),
                            str(pos), str(g), url, pub, fat, status]))


def view_of(rows):
    return cur().build_flu_view(rows)


class Reg(unittest.TestCase):
    """非目标面回归：源码逐字节 + 输出 A/B 对比（真实数据）。"""

    FUNCS = ["_adjacent_week", "svg_sparkline", "trend_block", "ranking_block",
             "child_block", "sichuan_block", "run_banner"]

    def test_01_source_identical(self):
        import inspect
        m, b = cur(), base(TMP)
        for f in self.FUNCS:
            self.assertEqual(inspect.getsource(getattr(m, f)),
                             inspect.getsource(getattr(b, f)), f)

    def test_02_outputs_identical_real_data(self):
        m, b = cur(), base(TMP)
        m.SC_CSV, b.SC_CSV = ROOT / "data" / "sichuan_monthly.csv", ROOT / "data" / "sichuan_monthly.csv"
        for name in ["trend_block", "ranking_block", "child_block", "sichuan_block"]:
            self.assertEqual(getattr(m, name)(), getattr(b, name)(), name)

    def test_03_run_banner(self):
        import tempfile
        m, b = cur(), base(TMP)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            st = d / "run_status.json"
            st.write_text(json.dumps({"run_at": "2026-11-13T02:00:00",
                                      "sources": {"flu_south": "failed",
                                                  "sentinel": "skipped"}}), encoding="utf-8")
            for mod in (m, b):
                mod.RUN_STATUS = st
            self.assertEqual(m.run_banner(local=False), b.run_banner(local=False))
            self.assertIn("未能获取", m.run_banner(local=False))
            self.assertEqual(m.run_banner(local=True), b.run_banner(local=True))
            self.assertEqual(m.run_banner(local=True), "")


class D1(unittest.TestCase):
    """周键解析、重复周、失败行。"""

    def test_01_order_independent(self):
        r1 = [row(2026, 43, 4.5, 18.03, 81.14), row(2026, 44, 4.8, 17.14, 82.27)]
        r2 = list(reversed(r1))
        v1, v2 = view_of(r1), view_of(r2)
        self.assertEqual(v1["anchor"], (2026, 44))
        self.assertEqual(v1["weeks"], v2["weeks"])

    def test_02_invalid_iso_week_ignored_counted(self):
        v = view_of([row(2025, 53, 1, 1, 1), row(2025, 52, 1, 1, 2)])
        self.assertNotIn((2025, 53), v["weeks"])
        self.assertEqual(v["invalid_week_rows"], 1)
        self.assertEqual(v["anchor"], (2025, 52))

    def test_03_w53_valid_in_long_year(self):
        v = view_of([row(2026, 53, 1, 1, 5)])
        self.assertIn((2026, 53), v["weeks"])
        self.assertEqual(v["anchor"], (2026, 53))

    def test_04_duplicate_same_value_merged(self):
        v = view_of([row(2026, 44, 4.8, 17.14, 82.27, fat="2026-11-09T08:00:00"),
                     row(2026, 44, 4.8, 17.14, 82.27, fat="2026-11-10T08:00:00",
                         pub="2026-11-06")])
        wk = v["weeks"][(2026, 44)]
        self.assertEqual(wk["state"], "ok")
        self.assertEqual(wk["vals"], (82.27, 4.8, 17.14))
        # 代表行取元数据排序最大者（pub 更晚）
        self.assertEqual(wk["rep"]["source_pubdate"], "2026-11-06")

    def test_05_duplicate_conflict_marks_week(self):
        v = view_of([row(2026, 44, 4.8, 17.14, 82.27),
                     row(2026, 44, 4.9, 17.14, 83.00)])
        self.assertEqual(v["weeks"][(2026, 44)]["state"], "conflict")
        self.assertIsNone(v["weeks"][(2026, 44)]["vals"])

    def test_06_bad_value_in_one_ok_row_conflicts(self):
        v = view_of([row(2026, 44, 4.8, 17.14, 82.27),
                     row(2026, 44, 4.8, 17.14, "nan")])
        self.assertEqual(v["weeks"][(2026, 44)]["state"], "conflict")

    def test_07_fail_row_does_not_override_ok(self):
        v = view_of([row(2026, 44, 4.8, 17.14, 82.27),
                     row(2026, 44, 1, 1, 1, status="fail")])
        self.assertEqual(v["weeks"][(2026, 44)]["state"], "ok")

    def test_08_fail_only_week_is_fail(self):
        v = view_of([row(2026, 43, 1, 1, 1, status="fail"),
                     row(2026, 44, 4.8, 17.14, 82.27)])
        self.assertEqual(v["weeks"][(2026, 43)]["state"], "fail")
        self.assertEqual(v["anchor"], (2026, 44))

    def test_09_rep_tiebreak_raw_strings(self):
        # 数值等价（0 与 0.00）、元数据相同 → 原字符串参与最终排序，乱序结果一致
        r1 = [row(2026, 44, 0, 0, 0, pub="2026-11-05", fat="2026-11-09T08:00:00"),
              row(2026, 44, 0, 0, "0.00", pub="2026-11-05", fat="2026-11-09T08:00:00")]
        r2 = list(reversed(r1))
        w1 = view_of(r1)["weeks"][(2026, 44)]
        w2 = view_of(r2)["weeks"][(2026, 44)]
        self.assertEqual(w1["state"], "ok")
        self.assertEqual(w1["disp"], w2["disp"])
        self.assertEqual(w1["rep"]["goldstein_index"], w2["rep"]["goldstein_index"])


class D2(unittest.TestCase):
    """数值有效性：真零有效，缺失/非法不转 0。"""

    BAD = ["", "abc", "nan", "inf", "-inf", "-1", "101", "10000.01"]

    def test_01_bad_values_rejected(self):
        for bad in self.BAD:
            with self.subTest(bad=bad):
                field = "goldstein_index" if bad not in ("101",) else "south_ili_pct"
                r = row(2026, 44, 4.8, 17.14, 82.27)
                r[field] = bad
                v = view_of([r])
                self.assertEqual(v["weeks"][(2026, 44)]["state"], "conflict", bad)

    def test_02_zero_valid(self):
        for z in ("0", "0.00"):
            v = view_of([row(2026, 44, "0.0", "0.00", z)])
            self.assertEqual(v["weeks"][(2026, 44)]["state"], "ok")
            self.assertEqual(v["weeks"][(2026, 44)]["vals"][0], 0.0)
            self.assertEqual(v["weeks"][(2026, 44)]["disp"][0], z)

    def test_03_latest_bad_value_no_silent_fallback(self):
        v = view_of([row(2026, 43, 4.5, 18.03, 81.14),
                     row(2026, 44, 4.8, 17.14, "bad")])
        self.assertEqual(v["anchor"], (2026, 44))
        self.assertEqual(v["weeks"][(2026, 44)]["state"], "conflict")
        blk = cur().flu_block(v)
        self.assertEqual(blk["iso_week"], "44")
        self.assertIn("数据异常", blk["mom"])

    def test_04_bad_metadata_keeps_value_with_note(self):
        r = row(2026, 44, 4.8, 17.14, 82.27, ws="2026-11-11")  # 非周一
        v = view_of([r])
        wk = v["weeks"][(2026, 44)]
        self.assertEqual(wk["state"], "ok")
        self.assertTrue(wk["week_start_mismatch"])

    def test_05_url_validation(self):
        m = cur()
        self.assertIsNone(m.valid_url("javascript:alert(1)"))
        self.assertIsNone(m.valid_url("data:text/html,x"))
        self.assertIsNone(m.valid_url(""))
        self.assertIsNone(m.valid_url("ftp://x/y"))
        u = m.valid_url("https://ivdc.chinacdc.cn/a/b.html")
        self.assertTrue(u.scheme.startswith("http"))


class M(unittest.TestCase):
    """环比：精确上一自然周，不借更早周。"""

    def mom(self, rows):
        m = cur()
        return m.flu_block(m.build_flu_view(rows))["mom"]

    def test_01_up_down_flat(self):
        self.assertIn("↑", self.mom([row(2026, 43, 4.5, 18.03, 81.14),
                                     row(2026, 44, 4.8, 17.14, 82.27)]))
        self.assertIn("↓", self.mom([row(2026, 43, 4.5, 18.03, 81.14),
                                     row(2026, 44, 4.0, 17.14, 70.00)]))
        self.assertIn("→", self.mom([row(2026, 43, 4.5, 18.03, 81.14),
                                     row(2026, 44, 4.5, 18.03, 81.14)]))

    def test_02_gap_no_compare(self):
        # W43 缺、W42 在：不得用 W42 冒充上周
        txt = self.mom([row(2026, 42, 4.5, 18.03, 81.14),
                        row(2026, 44, 4.8, 17.14, 82.27)])
        self.assertIn("上周数据缺失", txt)
        self.assertNotIn("↑", txt)

    def test_03_w1_cross_year(self):
        # 2026W1 的上一周是 2025W52
        txt = self.mom([row(2025, 52, 6.1, 41.9, 255.79),
                        row(2026, 1, 5.4, 35.82, 193.43)])
        self.assertIn("↓", txt)

    def test_04_w1_prev_year_w53(self):
        # 2021W1 的上一周是 2020W53（2020 是 53 周年）
        txt = self.mom([row(2020, 53, 6.0, 40.0, 240.0),
                        row(2021, 1, 5.0, 30.0, 150.0)])
        self.assertIn("↓", txt)

    def test_05_w51_jump_w1_not_adjacent(self):
        txt = self.mom([row(2025, 51, 6.0, 40.0, 240.0),
                        row(2026, 1, 5.0, 30.0, 150.0)])
        self.assertIn("上周数据缺失", txt)

    def test_06_prev_anomalous_vs_missing(self):
        miss = self.mom([row(2026, 42, 4.5, 18.03, 81.14),
                         row(2026, 44, 4.8, 17.14, 82.27)])
        anom = self.mom([row(2026, 43, 4.5, 18.03, "bad"),
                         row(2026, 44, 4.8, 17.14, 82.27)])
        self.assertIn("上周数据缺失", miss)
        self.assertIn("上周数据异常", anom)

    def test_07_single_week_is_missing(self):
        txt = self.mom([row(2026, 44, 4.8, 17.14, 82.27)])
        self.assertIn("上周数据缺失", txt)

    def test_08_banner_later_fail_and_no_false_history_fail(self):
        m = cur()
        blk = m.flu_block(m.build_flu_view(
            [row(2026, 42, 4.5, 18.03, 81.14),
             row(2026, 43, 1, 1, 1, status="fail"),
             row(2026, 44, 4.8, 17.14, 82.27)]))
        self.assertEqual(blk["banner"], "")  # 历史失败不再误报最新失败
        blk2 = m.flu_block(m.build_flu_view(
            [row(2026, 44, 4.8, 17.14, 82.27),
             row(2026, 45, 1, 1, 1, status="fail")]))
        self.assertIn("最新一期获取失败", blk2["banner"])
        # 正常锚周（最新 ok、有更晚失败）横幅完整原文，防文案回归
        self.assertIn("显示上次成功数据（2026年第44周）", blk2["banner"])

    def test_11_anomalous_anchor_with_later_fail_banner(self):
        """S4-B04：异常锚周+更晚失败——横幅不得称"上次成功数据"。"""
        m = cur()
        blk = m.flu_block(m.build_flu_view(
            [row(2026, 43, 4.5, 18.03, 81.14),
             row(2026, 44, 4.8, 17.14, "bad"),
             row(2026, 45, 1, 1, 1, status="fail")]))
        self.assertTrue(blk.get("anchor_bad"))
        self.assertEqual(blk["iso_week"], "44")  # 不回退 W43
        self.assertIn("最新一期获取失败", blk["banner"])
        self.assertIn("数据异常", blk["banner"])
        self.assertNotIn("成功数据", blk["banner"])
        blk_nofail = m.flu_block(m.build_flu_view(
            [row(2026, 43, 4.5, 18.03, 81.14),
             row(2026, 44, 4.8, 17.14, "bad")]))
        self.assertEqual(blk_nofail["banner"], "")

    def test_09_zero_participates(self):
        txt = self.mom([row(2026, 43, 0, 0, 0),
                        row(2026, 44, 4.8, 17.14, 82.27)])
        self.assertIn("↑", txt)

    def test_10_no_yoy_key(self):
        m = cur()
        blk = m.flu_block(m.build_flu_view([row(2026, 44, 4.8, 17.14, 82.27)]))
        self.assertNotIn("yoy", blk)


class H(unittest.TestCase):
    """历史年选择与覆盖统计。"""

    def test_01_anchor_from_data_not_clock(self):
        m = cur()
        rows = [row(y, w, 4, 10, 40) for y in (2023, 2024, 2025)
                for w in range(1, 11)] + [row(2025, 10, 4, 10, 41)]
        h = m.history_data(m.build_flu_view(rows))
        self.assertEqual(h["anchor"], (2025, 10))
        self.assertEqual([y["year"] for y in h["years"]], [2025, 2024, 2023])

    def test_02_window_three_prior_years_only(self):
        m = cur()
        rows = [row(y, w, 4, 10, 40) for y in (2020, 2021, 2022, 2023, 2024, 2025)
                for w in (1, 5)]
        h = m.history_data(m.build_flu_view(rows))
        self.assertEqual([y["year"] for y in h["years"]], [2025, 2024, 2023, 2022])

    def test_03_single_year_honest_note(self):
        m = cur()
        rows = [row(2026, w, 4, 10, 40) for w in range(1, 5)]
        h = m.history_data(m.build_flu_view(rows))
        self.assertTrue(h["single_year"])

    def test_04_empty_view(self):
        m = cur()
        h = m.history_data(m.build_flu_view([]))
        self.assertTrue(h["empty"])

    def test_05_internal_gaps_only(self):
        m = cur()
        rows = [row(2025, w, 4, 10, 40) for w in (1, 2, 3, 5, 8, 9)]
        rows += [row(2026, w, 4, 10, 40) for w in range(1, 45)]
        h = m.history_data(m.build_flu_view(rows))
        y25 = [y for y in h["years"] if y["year"] == 2025][0]
        self.assertEqual(y25["n_ok"], 6)
        self.assertEqual(y25["gaps"], 3)  # 缺 4、6、7；锚周后与首周前不算
        y26 = [y for y in h["years"] if y["year"] == 2026][0]
        self.assertEqual(y26["gaps"], 0)

    def test_06_anchor_week_bad_but_year_kept(self):
        m = cur()
        rows = [row(2025, 44, 4.6, 16.46, 75.72),
                row(2026, 44, 4.8, 17.14, "bad"),
                row(2026, 43, 4.5, 18.03, 81.14)]
        h = m.history_data(m.build_flu_view(rows))
        y26 = [y for y in h["years"] if y["year"] == 2026][0]
        self.assertEqual(y26["n_ok"], 1)
        self.assertIsNone(y26["anchor_val"])
        self.assertEqual(h["years"][0]["year"], 2026)

    def test_07_w53_anchor_vs_52_week_years(self):
        m = cur()
        rows = [row(y, 52, 4, 10, 40) for y in (2023, 2024, 2025)]
        rows += [row(2026, 53, 5, 20, 100)]
        h = m.history_data(m.build_flu_view(rows))
        for y in h["years"]:
            if y["year"] != 2026:
                self.assertEqual(y["anchor_note"], "no_w53")

    def test_08_fail_anchor_week_is_missing_not_anomalous(self):
        """S4-B03：历史年锚周 fail=缺失，conflict=异常，两者文案必须分开。"""
        m = cur()
        rows = [row(2025, 10, 4, 10, 40),
                row(2025, 44, 1, 1, 1, status="fail"),
                row(2024, 44, 4, 10, 40),
                row(2026, 44, 4.8, 17.14, 82.27)]
        tbl = m.history_table(m.history_data(m.build_flu_view(rows)))
        y25 = tbl[tbl.find(">2025<"):tbl.find(">2024<")]
        self.assertIn("该周缺失", y25)
        self.assertNotIn("数据异常", y25)
        rows2 = [row(2025, 44, 4, 10, 40), row(2025, 44, 5, 10, 41),
                 row(2024, 44, 4, 10, 40),
                 row(2026, 44, 4.8, 17.14, 82.27)]
        tbl2 = m.history_table(m.history_data(m.build_flu_view(rows2)))
        y25b = tbl2[tbl2.find(">2025<"):tbl2.find(">2024<")]
        self.assertIn("数据异常，未采用", y25b)

    def test_09_invalid_rows_counted_and_surfaced(self):
        """S4-B02：非法周次记录计数上屏，不静默丢弃（含仅非法/真空输入）。"""
        m = cur()
        rows = [row(2025, 53, 1, 1, 1), row(2025, 52, 6.1, 41.9, 255.79),
                row(2026, 44, 4.8, 17.14, 82.27)]
        blk = m.flu_block(m.build_flu_view(rows))
        self.assertEqual(blk["invalid_rows"], 1)
        body = m.flu_body_html(blk)
        self.assertIn("已忽略 1 条无效周次记录", body)
        # 仅一条非法周次（round-2 漏洞：最终纯空态分支曾不带计数）
        only1 = m.flu_body_html(m.flu_block(m.build_flu_view([row(2025, 53, 1, 1, 1)])))
        self.assertIn("已忽略 1 条无效周次记录", only1)
        # 仅多条非法周次
        only2 = m.flu_body_html(m.flu_block(m.build_flu_view(
            [row(2025, 53, 1, 1, 1), row(2026, 54, 1, 1, 1)])))
        self.assertIn("已忽略 2 条无效周次记录", only2)
        # 真空输入：无非法记录则不显示该提示
        empty = m.flu_body_html(m.flu_block(m.build_flu_view([])))
        self.assertNotIn("无效周次记录", empty)


class B(unittest.TestCase):
    """S4-B01：流感卡 URL 白名单与转义。"""

    def _ok_flu(self, **kw):
        base = {"state": "ok", "banner": "", "invalid_rows": 0,
                "iso_year": "2026", "iso_week": "44",
                "goldstein_index": "82.27", "south_ili_pct": "4.8",
                "south_flu_positive_pct": "17.14",
                "source_url": "https://ivdc.example/t.html",
                "line": "数据正常 · 2026年第44周 · 来源发布 2026-11-05",
                "mom": "较上周 ↑"}
        base.update(kw)
        return base

    def test_01_javascript_url_no_link(self):
        body = cur().flu_body_html(self._ok_flu(source_url="javascript:alert(1)"))
        self.assertNotIn("<a href", body)
        self.assertIn("来源链接未提供", body)

    def test_02_bad_url_anchor_branch_too(self):
        flu = self._ok_flu(anchor_bad=True, source_url="data:text/html,x",
                           goldstein_index="—", line="异常", mom="异常")
        body = cur().flu_body_html(flu)
        self.assertNotIn("<a href", body)
        self.assertIn("来源链接未提供", body)

    def test_03_url_attribute_escaped(self):
        u = 'https://x.example/a"onmouseover="alert(1)'
        body = cur().flu_body_html(self._ok_flu(source_url=u))
        self.assertNotIn('"onmouseover="alert', body)
        self.assertIn(html.escape(u, quote=True), body)
        self.assertIn('rel="noopener"', body)

    def test_04_line_html_escaped(self):
        body = cur().flu_body_html(self._ok_flu(
            line="数据正常 · <script>alert(1)</script> · 2026"))
        self.assertNotIn("<script", body)
        self.assertIn("&lt;script&gt;", body)

    def test_05_block_level_no_injection(self):
        """块级注入回归（flu_block→flu_body_html）；整页 render 由 E 组真数据覆盖。"""
        m = cur()
        rows = [row(2026, 44, 4.8, 17.14, 82.27, pub="<b>x</b>",
                    url="javascript:alert(1)")]
        blk = m.flu_block(m.build_flu_view(rows))
        body = m.flu_body_html(blk)
        self.assertNotIn("<a href", body)
        self.assertNotIn("<b>x</b>", body)
        self.assertIn("来源链接未提供", body)


class G(unittest.TestCase):
    """图形几何（S2 落地后生效）。"""

    def setUp(self):
        if not hasattr(cur(), "history_svg"):
            self.skipTest("S2 渲染未落地")

    def test_01_axis_domain_fixed(self):
        m = cur()
        rows = [row(y, w, 4, 10, 40) for y in (2025,) for w in (1, 52)]
        rows += [row(2026, w, 4, 10, 40) for w in range(1, 45)]
        svg = m.history_svg(m.history_data(m.build_flu_view(rows)))
        self.assertIn("viewBox=\"0 0 280 192\"", svg)

    def test_02_scale_algorithm(self):
        m = cur()
        self.assertEqual(m.nice_axis(604.84), (200, 4, 800))
        self.assertEqual(m.nice_axis(9.43), (2, 5, 10))
        self.assertEqual(m.nice_axis(0.0), (2, 5, 10))
        self.assertEqual(m.nice_axis(82.27), (20, 5, 100))

    def test_03_single_point_visible(self):
        m = cur()
        rows = [row(2026, w, 4, 10, 40) for w in range(1, 45)]
        rows += [row(2025, 20, 4, 10, 41)]
        svg = m.history_svg(m.history_data(m.build_flu_view(rows)))
        # Y-1=2025 是 #1f4e79：孤立点必须画标记（无折线段也可见）
        self.assertIn("#1f4e79", svg)
        # 孤立点不产生折线：2025 年不应有 polyline
        segs = re.findall(r'<polyline[^>]*stroke="#1f4e79"', svg)
        self.assertEqual(len(segs), 0)
        marks = re.findall(r'fill="#1f4e79"', svg)
        self.assertGreaterEqual(len(marks), 1)


class T(unittest.TestCase):
    """同周表内容（S2 落地后生效）。"""

    def setUp(self):
        if not hasattr(cur(), "history_table"):
            self.skipTest("S2 渲染未落地")

    def test_01_real_w44_matches_csv(self):
        from html.parser import HTMLParser

        class Rows(HTMLParser):
            def __init__(self):
                super().__init__()
                self.rows, self._row, self._cell = [], None, None

            def handle_starttag(self, tag, attrs):
                if tag == "tr":
                    self._row = []
                elif tag in ("td", "th") and self._row is not None:
                    self._cell = []

            def handle_endtag(self, tag):
                if tag == "tr" and self._row is not None:
                    self.rows.append(self._row)
                    self._row = None
                elif tag in ("td", "th") and self._cell is not None:
                    self._row.append("".join(self._cell).strip())
                    self._cell = None

            def handle_data(self, data):
                if self._cell is not None:
                    self._cell.append(data)

        m = cur()
        h = m.history_data(m.build_flu_view(m.read_csv(m.FLU_CSV)))
        tbl = m.history_table(h)
        self.assertIn("年份", tbl)
        self.assertIn("ISO周起", tbl)
        self.assertIn("指数", tbl)
        self.assertIn("ILI%", tbl)
        self.assertIn("阳性率%", tbl)
        self.assertIn("来源", tbl)
        p = Rows()
        p.feed(tbl)
        by_year = {}
        for r in p.rows:
            if r and r[0][:4].isdigit():
                by_year[r[0][:4]] = r
        self.assertEqual(by_year["2026"][1:5], ["10-26", "82.27", "4.8", "17.14"])
        self.assertEqual(by_year["2025"][1:5], ["10-27", "75.72", "4.6", "16.46"])
        self.assertEqual(by_year["2024"][1:5], ["10-28", "16.49", "3.4", "4.85"])
        self.assertEqual(by_year["2023"][1:5], ["10-30", "128.36", "5.7", "22.52"])
        # 每个数据行恰 6 列；来源列（本行片段内）指向官方文章页——限定到本行 </tr> 防跨行假阳性
        for y, r in by_year.items():
            self.assertEqual(len(r), 6, f"{y} 行列数 {len(r)} ≠ 6")
            start = tbl.find(f">{y}<")
            seg = tbl[start:tbl.find("</tr>", start)]
            self.assertIn("chinacdc.cn", seg, f"{y} 来源列缺失")

    def test_02_escaping(self):
        m = cur()
        rows = [row(2025, 44, 4, 10, 40, url="https://x.example/a<b&c=d"),
                row(2026, 44, 4.8, 17.14, 82.27)]
        tbl = m.history_table(m.history_data(m.build_flu_view(rows)))
        self.assertNotIn("<b&", tbl)
        self.assertIn(html.escape("https://x.example/a<b&c=d", quote=True), tbl)


class E(unittest.TestCase):
    """端到端：render 只写 site、data 不变、无外部资源、无旧占位。"""

    def test_01_render_isolated_no_data_write(self):
        m = cur()
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            m.OUT = d / "index.html"
            argv = sys.argv[:]
            sys.argv = ["build_site.py", "--local"]
            try:
                m.render()
            finally:
                sys.argv = argv
            self.assertTrue(m.OUT.exists())
            text = m.OUT.read_text(encoding="utf-8")
            data_dir = ROOT / "data"
            # data 字节不变由外部 --check 夹带；此处断言 HTML 形态
            self.assertNotIn("<script", text)
            self.assertNotIn("fetch(", text)
            self.assertNotIn("@import", text)
            self.assertNotIn("url(http", text)
            self.assertNotIn('img src="http', text)
            self.assertNotIn('link href="http', text)
            if hasattr(m, "history_block"):  # S2 后：旧占位必须消失
                for old in ("暂无往年同期数据", "待历史回补", "约150期"):
                    self.assertNotIn(old, text, old)
            else:
                for old in ("待历史回补后启用", "约150期"):
                    self.assertIn(old, text, old)

    def test_02_data_bytes_unchanged(self):
        data_dir = ROOT / "data"
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(data_dir.glob("*")) if p.is_file()}
        m = cur()
        with tempfile.TemporaryDirectory() as d:
            m.OUT = Path(d) / "index.html"
            argv = sys.argv[:]
            sys.argv = ["build_site.py", "--local"]
            try:
                m.render()
            finally:
                sys.argv = argv
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(data_dir.glob("*")) if p.is_file()}
        self.assertEqual(before, after)


def capture_baseline():
    TMP.mkdir(exist_ok=True)
    bdir = TMP / "baseline"
    bdir.mkdir(exist_ok=True)
    src = subprocess.run(["git", "-C", str(ROOT), "show",
                          f"{BASE_COMMIT}:src/build_site.py"],
                         capture_output=True, check=True).stdout
    (bdir / "build_site_base.py").write_bytes(src)
    shas = {}
    for p in sorted((ROOT / "data").glob("*")):
        if p.is_file():
            shas[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (bdir / "data_sha256.json").write_text(
        json.dumps(shas, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"基线已记录：{bdir}（源码来自 {BASE_COMMIT[:7]}，data 文件 {len(shas)} 个）")
    return 0


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--capture-baseline":
        return capture_baseline()
    if len(sys.argv) >= 2 and sys.argv[1] == "--check":
        pattern = sys.argv[2] if len(sys.argv) > 2 else None
        suite = unittest.defaultTestLoader.loadTestsFromModule(
            sys.modules[__name__])
        if pattern:
            suite = unittest.defaultTestLoader.loadTestsFromName(
                f"{__name__}.{pattern}")
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return 0 if result.wasSuccessful() else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())

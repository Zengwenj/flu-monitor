# -*- coding: utf-8 -*-
"""A2 搜索版验证套件（Q1–Q13，implement.md §S5 + round-4 补正）。

用法：python -X utf8 .trellis/tasks/11-12-regional-monitor/validation/check_search_query.py
全部通过输出 `Q-SUITE OK n/n` 且退出码 0；任一失败退出码 1。
设 `A2_SKIP_BUILD=1` 可跳过前置构建，复用 site/ 现有产物做静态检查。

旧套件（同目录 `check_history_compat.py` / `check_regional.py`）仍在库、仍
可跑；单页迁移后只有五页入口类断言预期失败（逐条去向见
`history-case-map.md`）。需要只跑其中**仍有效**的部分时：

  # 来源 A：自带 --check <类名>，只加载该类
  python -X utf8 .trellis/tasks/11-12-regional-monitor/validation/check_history_compat.py --check M
  python -X utf8 .trellis/tasks/11-12-regional-monitor/validation/check_history_compat.py --check T

  # 来源 B：裸 unittest.main，用 -k 按类名过滤（可重复，OR 语义）
  python -X utf8 .trellis/tasks/11-12-regional-monitor/validation/check_regional.py -k "D1"
  python -X utf8 .trellis/tasks/11-12-regional-monitor/validation/check_regional.py -k "H1" -k "H2"

排除五页入口/逻辑已变类的预期失败项后，可得到全绿的旧套件子集。
当前实测（2026-11-16）预期失败项共 19 条：

  来源 A（1 条）：`E.test_01_render_isolated_no_data_write`
  来源 B（18 条）：`E1.test_01_render_leaves_data_untouched`、
  `E1.test_04_validate_pages_accepts_valid_set`、`E2.test_01_*`、`E2.test_02_*`、
  `U1.test_01_*`、`U1.test_02_*`、`U4.test_01_nav_contract`、
  `U4.test_02_region_names_cards_no_values`、`U6.test_01_*`、
  `R1.test_02_skip_all_local_exit_zero`、
  `R2.test_01_stale_lock_refused_then_force_unlock`、
  `R3.test_03_partial_fetch_failure_exit1_still_builds`、
  `R3.test_05_final_status_write_failure_closes_gate`、
  `R4.test_05_two_recoverers_cannot_both_delete_lock`、
  `U2.test_01_v2_partial_wording`、`U2.test_06_per_page_relevance_filtering`、
  `U2.test_07_compute_states`、`U2.test_08_missing_fetch_key_unknown`

（`R3.test_03`/`R3.test_05` 的语义已由本套件 Q13 恢复；它们在旧套件里仍失败
是因为旧夹具的隔离根 data/ 为空，与单页构建前置不符。逐条去向见
`history-case-map.md`。）

Q5 中真实键盘序列已在 Chromium 无头 file:// 实测留档
（`.trellis/tasks/11-12-regional-monitor/research/q6-behavior-log.md`）；
读屏播报、触屏手势、IME、窄屏与人工验收仍为人工项，本套件只覆盖其可静态
验证的结构等价物（角色/ARIA/触控目标/降级提示/字号）。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
import build_site as bs          # noqa: E402
import search_catalog as scat    # noqa: E402

# 复核 A2-SEARCH-06：先构建本轮产物再断言——全局对象必须来自本轮构建，
# 而不是上次构建留在 site/ 的旧页（除非显式 A2_SKIP_BUILD=1 做静态检查）。
if os.environ.get("A2_SKIP_BUILD") != "1":
    _r = subprocess.run([sys.executable, "-X", "utf8",
                         str(ROOT / "src" / "build_site.py"), "--local"],
                        capture_output=True, text=True)
    if _r.returncode != 0:
        print(_r.stdout, _r.stderr)
        raise SystemExit("套件前置构建失败")
PAGE = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
BY_ID = scat.load_catalog()
REC = json.loads(re.search(
    r'<script type="application/json" id="recipes-data">(.*?)</script>',
    PAGE, re.S).group(1).replace("\\u003c", "<"))
CAT = json.loads(re.search(
    r'<script type="application/json" id="catalog-data">(.*?)</script>',
    PAGE, re.S).group(1).replace("\\u003c", "<"))
TPL = set(re.findall(r'<template id="tpl-([a-z_]+)"', PAGE))
SLOTS_USED = {s for r in REC.values() for s in r}


class Q1(unittest.TestCase):
    """查询交互要素与配方行为。"""

    def test_dom_scaffold(self):
        for i in ('id="q"', 'id="q-list"', 'id="q-status"',
                  'id="query-view"', 'id="default-view"'):
            self.assertIn(i, PAGE)
        self.assertIn("<noscript>", PAGE)

    def test_chengdu_default_and_clear(self):
        self.assertEqual(REC["510100"], ["chengdu_default"])
        self.assertIn("已恢复成都默认", PAGE)  # JS 状态文案存在

    def test_unique_and_multi_candidate_guard(self):
        # 多候选必须选中：JS 存在防直提护栏与候选清空修复（designer 实测项的静态锚点）
        self.assertIn("请从列表中选择", PAGE)

    def test_no_match_wording(self):
        # 无匹配文案与总数说明为动态文案（计数由 JS 从目录实时计算）
        self.assertIn("未找到匹配的省市", PAGE)
        self.assertIn("个单位", PAGE)

    def test_catalog_counts(self):
        self.assertEqual(len(CAT), 400)
        self.assertEqual(sum(1 for r in CAT if r["q"] == 1), 397)


class Q2(unittest.TestCase):
    """地区口径：不误套成都分级、黑省分层、重庆仅链接、普通省市参考。"""

    def test_sichuan_not_chengdu(self):
        # 四川省与四川地市不得恢复成都默认，也不得携带任何成都专属槽位
        for uid in ("510000", "510700", "513200"):
            self.assertNotIn("chengdu_default", REC[uid], uid)
            self.assertEqual(REC[uid][0], "local_nodata", uid)
        # 成都平原区分级卡只出现在默认视图（全文唯一）
        self.assertEqual(PAGE.count("四川官方流感分级"), 1)

    def test_hlj_layering(self):
        self.assertEqual(REC["230000"],
                         ["local_hlj_flu", "local_hlj_sent",
                          "zone_flu_north", "zone_names_north", "national_rank"])
        self.assertEqual(REC["230100"][:3],
                         ["local_nodata", "prov_hlj_flu", "prov_hlj_sent"])
        self.assertIn("省级参考（非该市实测）", PAGE)

    def test_chongqing_links_only(self):
        self.assertEqual(REC["500000"],
                         ["cq_links", "zone_flu_south",
                          "zone_names_south", "national_rank"])
        body = re.search(r'<template id="tpl-cq_links">(.*?)</template>',
                         PAGE, re.S).group(1)
        self.assertIn("cqcdc.org", body)
        self.assertNotIn("Goldstein", body)

    def test_generic_province_reference(self):
        self.assertEqual(REC["440000"],
                         ["local_nodata", "zone_flu_south",
                          "zone_names_south", "national_rank"])


class Q3(unittest.TestCase):
    """双产品片区映射独立、unknown 不猜、全国参考不冒充当地。"""

    def test_zone_follows_flu_region(self):
        for uid, slots in REC.items():
            if slots == ["chengdu_default"]:
                continue  # 成都：恢复默认页（默认页已含南方片卡），不走槽位配方
            f = BY_ID[uid]["flu_region"]
            s = BY_ID[uid]["sentinel_region"]
            # A2-SEARCH-02：两产品独立——流感卡跟 flu_region、名称卡跟 sentinel_region
            if f == "south":
                self.assertIn("zone_flu_south", slots, uid)
            elif f == "north":
                self.assertIn("zone_flu_north", slots, uid)
            else:
                self.assertNotIn("zone_flu_south", slots, uid)
                self.assertNotIn("zone_flu_north", slots, uid)
            if s == "south":
                self.assertIn("zone_names_south", slots, uid)
            elif s == "north":
                self.assertIn("zone_names_north", slots, uid)
            else:
                self.assertNotIn("zone_names_south", slots, uid)
                self.assertNotIn("zone_names_north", slots, uid)
            self.assertEqual(slots[-1], "national_rank", uid)

    def test_sentinel_independence_in_memory(self):
        # 内存夹具：sentinel 与 flu 分离时，名称卡跟随 sentinel 区（真实数据无此组合）
        fake = dict(BY_ID)
        fake["440000"] = dict(BY_ID["440000"], sentinel_region="north")
        r = scat.recipe("440000", fake)
        self.assertIn("zone_flu_south", r)
        self.assertIn("zone_names_north", r)
        self.assertNotIn("zone_names_south", r)
        fake["440000"] = dict(BY_ID["440000"], sentinel_region="unknown")
        r2 = scat.recipe("440000", fake)
        self.assertFalse(any(x.startswith("zone_names") for x in r2))

    def test_nine_region_combinations_in_memory(self):
        """(flu_region, sentinel_region) ∈ {south,north,unknown}² 九组合全覆盖。

        内存夹具：直接复制真实目录并按需覆盖两个 region 字段，不读改任何 CSV。
        断言：流感卡只跟 flu_region、名称卡只跟 sentinel_region、unknown 不猜，
        且末槽恒为 national_rank。
        """
        regions = ("south", "north", "unknown")
        # 广东省：local_nodata 起步（无本地绑定），便于观察片区槽位
        base_uid = "440000"
        flu_map = {"south": "zone_flu_south", "north": "zone_flu_north"}
        names_map = {"south": "zone_names_south", "north": "zone_names_north"}
        seen = set()
        for fr in regions:
            for sr in regions:
                with self.subTest(flu_region=fr, sentinel_region=sr):
                    fake = dict(BY_ID)
                    fake[base_uid] = dict(BY_ID[base_uid],
                                          flu_region=fr, sentinel_region=sr)
                    slots = scat.recipe(base_uid, fake)
                    self.assertEqual(slots[0], "local_nodata")
                    self.assertEqual(slots[-1], "national_rank",
                                     "national_rank 必须在末槽")

                    flu_slots = [s for s in slots if s.startswith("zone_flu")]
                    names_slots = [s for s in slots if s.startswith("zone_names")]
                    if fr in flu_map:
                        self.assertEqual(flu_slots, [flu_map[fr]],
                                         f"流感卡必须只由 flu_region={fr} 派生")
                    else:
                        self.assertEqual(flu_slots, [],
                                         "flu_region=unknown 不得出现片区流感卡")
                    if sr in names_map:
                        self.assertEqual(names_slots, [names_map[sr]],
                                         f"名称卡必须只由 sentinel_region={sr} 派生")
                    else:
                        self.assertEqual(names_slots, [],
                                         "sentinel_region=unknown 不得出现名称卡")
                    # 槽位顺序：flu 卡在 names 卡之前，两者都在 national_rank 之前
                    if flu_slots and names_slots:
                        self.assertLess(slots.index(flu_slots[0]),
                                        slots.index(names_slots[0]))
                    seen.add((fr, sr))
        self.assertEqual(len(seen), 9)

    def test_nine_combinations_change_nothing_for_province_self(self):
        """省级单位自身（无本地绑定的普通省）九组合同样成立。"""
        flu_map = {"south": "zone_flu_south", "north": "zone_flu_north"}
        names_map = {"south": "zone_names_south", "north": "zone_names_north"}
        for fr in ("south", "north", "unknown"):
            for sr in ("south", "north", "unknown"):
                with self.subTest(flu_region=fr, sentinel_region=sr):
                    fake = dict(BY_ID)
                    fake["530000"] = dict(BY_ID["530000"],
                                          flu_region=fr, sentinel_region=sr)
                    slots = scat.recipe("530000", fake)
                    self.assertNotIn("prov_nodata", slots)
                    want = ([flu_map[fr]] if fr in flu_map else []) + \
                           ([names_map[sr]] if sr in names_map else []) + \
                           ["national_rank"]
                    self.assertEqual(slots, ["local_nodata"] + want)

    def test_alias_exact_outranks_name_contains(self):
        """别名精确（0）必须优先于规范名包含（2），且不再运行时剥后缀。

        直接抽取生产 SEARCH_JS 里的 matchScore 到 node 里跑，避免用 Python
        重写一份逻辑造成"测的不是页面上那段代码"。
        """
        node = shutil.which("node")
        if not node:
            self.skipTest("未找到 node，跳过 JS 级匹配优先级验证")
        js = bs.SEARCH_JS
        m = re.search(r"(function matchScore\(unit, needle\) \{)", js)
        self.assertIsNotNone(m, "SEARCH_JS 中找不到 matchScore")
        # 大括号配对截出整个函数体
        start = m.start(1)
        depth, i = 0, start
        while i < len(js):
            if js[i] == "{":
                depth += 1
            elif js[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        fn = js[start:i + 1]
        self.assertNotIn("coreOf", js, "不应再有运行时剥后缀")
        self.assertNotIn("SUFFIXES", js, "后缀表应已移除")

        cases = [
            # 别名精确 0
            ({"norm": "哈尔滨市", "aliases": ["哈尔滨"]}, "哈尔滨", 0),
            # 规范名精确 0
            ({"norm": "哈尔滨市", "aliases": []}, "哈尔滨市", 0),
            # 规范名前缀 1（不剥"市"靠前缀命中）
            ({"norm": "哈尔滨市", "aliases": []}, "哈尔滨", 1),
            # 规范名包含 2
            ({"norm": "哈尔滨市", "aliases": []}, "滨市", 2),
            # 别名包含 2
            ({"norm": "长春市", "aliases": ["吉林长春"]}, "长春", 1),
            # 完全不匹配
            ({"norm": "成都市", "aliases": []}, "哈尔滨", -1),
        ]
        script = (
            fn + "\nvar cases = " + json.dumps(cases, ensure_ascii=False) + ";\n"
            "var out = cases.map(function (c) { return matchScore(c[0], c[1]); });\n"
            "process.stdout.write(JSON.stringify(out));\n")
        cp = subprocess.run([node, "-e", script], capture_output=True,
                            text=True, encoding="utf-8", timeout=60)
        self.assertEqual(cp.returncode, 0, cp.stderr[-800:])
        got = json.loads(cp.stdout)
        want = [c[2] for c in cases]
        self.assertEqual(got, want,
                         "matchScore 三级结果与预期不符："
                         f"{list(zip([c[1] for c in cases], want, got))}")
        # 关键语义单独再断一次：别名精确严格优于规范名包含
        self.assertLess(got[0], got[3])

    def test_national_card_labeled_national(self):
        self.assertIn("全国多病原活跃度排行", PAGE)
        # 当地未取得卡必须声明参考非实测
        self.assertIn("非当地实测", PAGE)


class Q4(unittest.TestCase):
    """注入与外部加载静态检查。"""

    def test_no_dynamic_html_or_network(self):
        for bad in ("fetch(", "XMLHttpRequest", "eval(", "new Function",
                    "innerHTML", "insertAdjacentHTML", "document.write",
                    "<script src", "@import", "url(http"):
            self.assertNotIn(bad, PAGE, bad)

    def test_script_tags_paired_no_close_in_data(self):
        self.assertEqual(PAGE.count("<script"), PAGE.count("</script>"))
        self.assertEqual(PAGE.count("<script"), 3)  # 目录 + 配方 + 交互

    def test_every_slot_has_template(self):
        slots_used = SLOTS_USED - {"chengdu_default"}  # 恢复默认无模板，由 JS 切换默认视图
        self.assertEqual(slots_used - TPL, set())
        self.assertEqual(TPL - slots_used, set())


class Q5(unittest.TestCase):
    """可访问性与窄屏结构（浏览器行为由 designer 实测留档）。"""

    def test_aria_roles(self):
        for i in ('role="combobox"', 'role="listbox"', 'role="status"',
                  'aria-live="polite"', 'aria-autocomplete="list"',
                  'aria-expanded="false"', 'aria-controls="q-list"'):
            self.assertIn(i, PAGE)

    def test_touch_and_font(self):
        self.assertIn("min-height:44px", PAGE)     # 候选项触控目标
        self.assertIn("font-size:16px", PAGE)      # 输入框防 iOS 缩放
        self.assertIn("focus-visible", PAGE)

    def test_noscript_fallback(self):
        self.assertIn("仅显示成都默认内容", PAGE)


class Q6(unittest.TestCase):
    """data/ 冻结基线核验（A2-SEARCH-06 修正后恢复强基线）。

    plan-freeze-r4.md:51-62 含十个 data/ 文件完整 SHA-256（绝对路径形式，
    原正则匹配不到属探测错误）。九个文件逐字节钉冻结哈希；changes.log
    = 冻结内容 + 恰好三条 S0 目录留痕追加（locations_catalog ×2 +
    location_product_map ×1，S0 基线记录在案）；两个新目录 CSV 钉
    impl-baseline-s0 的 SHA-256 前 16 位。
    """

    FREEZE = (ROOT / ".trellis/tasks/11-12-regional-monitor"
              / "research/plan-freeze-r4.md").read_text(encoding="utf-8")
    BASELINE_S0 = (ROOT / ".trellis/tasks/11-12-regional-monitor"
                   / "research/impl-baseline-s0.md").read_text(encoding="utf-8")
    CL_PINS = {"locations_catalog", "location_product_map"}

    def _freeze_pins(self):
        pins = {}
        for m in re.finditer(r"`([^`]*\\data\\[^`]+)`\s+SHA256\s+`([0-9a-f]{64})`",
                             self.FREEZE):
            pins[Path(m.group(1)).name] = m.group(2)
        self.assertEqual(len(pins), 10, "冻结 data 哈希表应为 10 项")
        return pins

    @staticmethod
    def _sha(path):
        import hashlib
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_freeze_pins_nine_files(self):
        for name, want in self._freeze_pins().items():
            if name == "changes.log":
                continue
            p = ROOT / "data" / name
            self.assertTrue(p.exists(), name)
            self.assertEqual(self._sha(p), want, f"{name} 偏离冻结 r4 基线")

    def test_changeslog_freeze_plus_catalog_appends(self):
        raw = (ROOT / "data/changes.log").read_bytes()
        lines = raw.splitlines(keepends=True)
        extra = [l for l in lines if any(k in l.decode("utf-8", "ignore")
                                         for k in self.CL_PINS)]
        self.assertEqual(len(extra), 3, "目录留痕应恰为三条 S0 追加")
        kept = [l for l in lines if l not in extra]
        self.assertEqual(
            self.__class__._sha_bytes(b"".join(kept)),
            self._freeze_pins()["changes.log"],
            "changes.log 除三条目录留痕外偏离冻结 r4 内容")

    @staticmethod
    def _sha_bytes(b):
        import hashlib
        return hashlib.sha256(b).hexdigest()

    def test_new_catalog_pins(self):
        for name in ("locations.csv", "location_product_map.csv"):
            m = re.search(re.escape(name) + r".*?([0-9a-f]{16})",
                          self.BASELINE_S0, re.S)
            self.assertIsNotNone(m, f"impl-baseline-s0.md 缺 {name} 哈希")
            self.assertTrue(self._sha(ROOT / "data" / name)
                            .startswith(m.group(1)), f"{name} 与 S0 基线不符")

    @staticmethod
    def _data_hashes():
        return {p.name: Q6._sha(p) for p in (ROOT / "data").iterdir() if p.is_file()}

    def test_build_keeps_data(self):
        before = self._data_hashes()
        r = subprocess.run([sys.executable, "-X", "utf8",
                            str(ROOT / "src/build_site.py"), "--local"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._data_hashes(), before, "build --local 改动了 data/")

    def test_changeslog_format(self):
        lines = [l for l in (ROOT / "data/changes.log")
                 .read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertGreater(len(lines), 20)
        for i, l in enumerate(lines):
            parts = l.split("\t")
            # 历史 A1a 行有 4 列变体（旧 log_change 契约），新行一律 5 列
            self.assertIn(len(parts), (4, 5),
                          f"第{i+1}行破坏 tab 列契约: {l[:40]}")
            self.assertRegex(parts[0], r"^\d{4}-\d{2}-\d{2}T", f"第{i+1}行缺时间戳")

    def test_no_unexpected_data_files(self):
        tracked = set(subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "data"],
            capture_output=True, text=True).stdout.split())
        tracked = {Path(t).name for t in tracked}
        # A2a 轮已产出的三个新 CSV（未提交但属本任务数据层，S0 基线已记 ??）
        allowed = tracked | {"locations.csv", "location_product_map.csv",
                             "flu_north.csv", "heilongjiang_flu.csv",
                             "heilongjiang_sentinel.csv"}
        extra = {p.name for p in (ROOT / "data").iterdir()
                 if p.is_file() and p.name not in allowed}
        self.assertEqual(extra, set(), f"data/ 出现未声明文件 {extra}")

    def test_build_failure_keeps_old_page(self):
        old = bs.OUT.read_bytes()
        with mock.patch.object(bs, "_validate_pages",
                               side_effect=SystemExit(2)):
            with self.assertRaises(SystemExit):
                bs.render()
        self.assertEqual(bs.OUT.read_bytes(), old, "构建失败替换了旧首页")


class Q7(unittest.TestCase):
    """发布门：单页产物、旧四页不复活。"""

    def test_site_dir_single_page(self):
        names = {p.name for p in (ROOT / "site").glob("*.html")}
        self.assertEqual(names, {"index.html"})

    def test_no_five_page_code_paths(self):
        src = (ROOT / "src/build_site.py").read_text(encoding="utf-8")
        for bad in ('f"{slug}.html"', "PAGES = ", "nav_html"):
            self.assertNotIn(bad, src, bad)

    def test_index_contains_validated_content(self):
        self.assertIn("成都 · 呼吸道防护参考", PAGE)
        self.assertIn("Goldstein", PAGE)


class Q8(unittest.TestCase):
    """A2-SEARCH-07：load_catalog 拒绝契约（沙箱 CSV 注入，六类坏输入必须抛错）。"""

    def _sandbox(self):
        import csv
        import shutil
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="cat_rej_"))
        shutil.copy(ROOT / "data/locations.csv", tmp / "locations.csv")
        shutil.copy(ROOT / "data/location_product_map.csv",
                    tmp / "location_product_map.csv")
        self.addCleanup(shutil.rmtree, tmp, True)

        def read(p):
            with open(p, encoding="utf-8", newline="") as f:
                return list(csv.DictReader(f))

        def put(p, rs, fields):
            with open(p, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                w.writerows(rs)
        return tmp, read, put

    def _expect_reject(self, name, mut):
        import csv as _csv
        tmp, read, put = self._sandbox()
        locs = read(tmp / "locations.csv")
        pmap = read(tmp / "location_product_map.csv")
        mut(locs, pmap)
        lf = list(locs[0].keys())
        mf = list(pmap[0].keys())
        with mock.patch.object(scat, "LOCATIONS_CSV", tmp / "locations.csv"), \
             mock.patch.object(scat, "PRODUCT_MAP_CSV",
                               tmp / "location_product_map.csv"):
            put(tmp / "locations.csv", locs, lf)
            put(tmp / "location_product_map.csv", pmap, mf)
            with self.assertRaises(scat.CatalogError, msg=name):
                scat.load_catalog()

    @staticmethod
    def _idx(rs, t):
        return next(i for i, r in enumerate(rs) if r["type"] == t)

    def test_map_duplicate_row(self):
        self._expect_reject("重复映射行", lambda l, p: p.append(dict(p[0])))

    def test_province_with_parent(self):
        self._expect_reject("省级带父级",
                            lambda l, p: l.__setitem__(
                                0, dict(l[0], parent_id="110000")))

    def test_prefecture_missing_parent(self):
        def m(l, p):
            i = self._idx(l, "prefecture")
            l[i] = dict(l[i], parent_id="")
        self._expect_reject("地级缺父级", m)

    def test_prefecture_parent_not_province(self):
        def m(l, p):
            i = self._idx(l, "prefecture")
            l[i] = dict(l[i], parent_id=l[i + 1]["id"])
        self._expect_reject("父级非省级", m)

    def test_direct_county_parent_not_province(self):
        def m(l, p):
            i = self._idx(l, "province_direct_county")
            l[i] = dict(l[i], parent_id=l[self._idx(l, "prefecture")]["id"])
        self._expect_reject("省直辖县级父级非省级", m)

    def test_nonunknown_mapping_empty_source(self):
        self._expect_reject("映射无来源",
                            lambda l, p: p.__setitem__(
                                0, dict(p[0], flu_region_source="")))


class Q9(unittest.TestCase):
    """IMP-01 终版锁策略：死锁/活锁一律拒绝 + 人工恢复指引；--force-unlock
    永不自动删锁（消除并发恢复竞态）。隔离根内运行，不碰真实仓库锁。"""

    @staticmethod
    def _iso_root(tmp):
        import shutil
        root = tmp / "repo"
        shutil.copytree(ROOT / "src", root / "src")
        (root / "data").mkdir()
        return root

    def _run(self, root, *extra):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(root / "src/run_pipeline.py"),
             "--local", "--skip",
             "flu_south,flu_north,heilongjiang,heilongjiang_sentinel,"
             "sentinel,flunet,south,north", *extra],
            capture_output=True, text=True, timeout=120)

    def test_stale_lock_refused_with_manual_guidance(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = self._iso_root(Path(d))
            lock = root / ".tmp_pipeline" / "lock"
            lock.parent.mkdir(parents=True)
            lock.write_text('{"pid": 999999, "started_at": "t"}',
                            encoding="utf-8")
            for args in ((), ("--force-unlock",)):
                r = self._run(root, *args)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("手动删除", r.stdout + r.stderr)
                self.assertTrue(lock.exists(), "任何路径都不得自动删锁")

    def test_live_lock_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = self._iso_root(Path(d))
            lock = root / ".tmp_pipeline" / "lock"
            lock.parent.mkdir(parents=True)
            lock.write_text('{"pid": %d, "started_at": "live"}' % os.getpid(),
                            encoding="utf-8")
            r = self._run(root)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("拒绝", r.stdout + r.stderr)
            self.assertTrue(lock.exists())

    def test_no_dead_token_files_left(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = self._iso_root(Path(d))
            base = root / ".tmp_pipeline"
            base.mkdir(parents=True)
            (base / "lock.dead.1.abc").write_text("{}", encoding="utf-8")
            lock = base / "lock"
            lock.write_text('{"pid": 999999, "started_at": "t"}',
                            encoding="utf-8")
            self._run(root)
            self.assertFalse(list(base.glob("lock.dead.*")),
                             "遗留 .dead.* 残片应被清理")


class Q10(unittest.TestCase):
    """A2-SEARCH-06：A1b 实质断言等价迁移（数值从 data/flu_south.csv 动态推导）。

    断言必须落在**默认视图内对应卡片块**，不能全文包含式检查——否则错误年份
    配对、只在隐藏模板里出现的数值都会被误判通过。
    """

    def _flu_rows(self):
        rows = [r for r in bs.read_csv(bs.FLU_CSV) if r.get("status") == "ok"]
        rows.sort(key=lambda r: (int(r["iso_year"]), int(r["iso_week"])))
        return rows

    @staticmethod
    def _default_view():
        i = PAGE.find('<div id="default-view">')
        self_ok = i >= 0
        j = PAGE.find('<template id=')
        if not self_ok or j < 0 or j <= i:
            raise AssertionError("默认视图区域定位失败")
        return PAGE[i:j]

    def _card_block(self, marker):
        """默认视图内、标题含 marker 的卡片块（<div class="card"> → 下一个）。"""
        seg = self._default_view()
        pos = seg.find(marker)
        if pos < 0:
            raise AssertionError(f"默认视图内找不到卡片：{marker}")
        start = seg.rfind('  <div class="card">', 0, pos)
        if start < 0:
            raise AssertionError(f"卡片块起点定位失败：{marker}")
        end = seg.find('  <div class="card">', pos)
        return seg[start:(end if end >= 0 else len(seg))]

    def test_flu_card_numbers_match_csv(self):
        card = self._card_block("南方片流感趋势")
        last = self._flu_rows()[-1]
        # 三个数值必须出现在这张卡里，且各自带渲染格式（避免"数字碰巧在别处"）
        self.assertIn(f'<div class="big">{last["goldstein_index"]}<span class="unit">',
                      card, "指数未落在流感卡内")
        self.assertIn(f'ILI% <b>{last["south_ili_pct"]}%</b>', card)
        self.assertIn(f'流感阳性率 <b>{last["south_flu_positive_pct"]}%</b>', card)
        self.assertIn(f'第<b>{last["iso_week"]}</b>周', card)
        self.assertIn(f'{last["iso_year"]}年第', card)

    def test_wow_direction_from_csv(self):
        """环比方向必须由 CSV 相邻两个 ISO 周的实际指数推出。"""
        from datetime import date, timedelta
        rows = self._flu_rows()
        last = rows[-1]
        prev_monday = date.fromisoformat(last["week_start"]) - timedelta(days=7)
        target = str(prev_monday)
        prev = [r for r in rows
                if r["week_start"] == target and r is not last]
        card = self._card_block("南方片流感趋势")
        if not prev:
            # 上一自然周无 ok 行：不得凭空给出方向
            self.assertNotRegex(card, r"较上周 [↑↓→]")
            return
        g_prev = float(prev[-1]["goldstein_index"])
        g_now = float(last["goldstein_index"])
        arrow = "↑" if g_now > g_prev else ("↓" if g_now < g_prev else "→")
        self.assertIn(f"较上周 {arrow}", card)
        for other in ("↑", "↓", "→"):
            if other != arrow:
                self.assertNotIn(f"较上周 {other}", card)

    def test_history_card_same_week_values(self):
        """历史同周表逐行校验：年份→该年同周指数，与 CSV 同周数据集比对。"""
        card = self._card_block("历年同周对比")
        last = self._flu_rows()[-1]
        ay, aw = int(last["iso_year"]), int(last["iso_week"])
        window = set(range(ay, ay - 4, -1))
        expected = {int(r["iso_year"]): r["goldstein_index"]
                    for r in self._flu_rows()
                    if int(r["iso_week"]) == aw and int(r["iso_year"]) in window}
        self.assertTrue(expected, "CSV 无同周数据，测试前提不成立")

        got = {}
        for body in re.findall(r"<tr[^>]*>(.*?)</tr>", card, re.S):
            if "hist-yl" not in body:
                continue
            ym = re.search(r"<span>(\d{4})</span>", body)
            if not ym:
                self.fail(f"历史行缺年份：{body[:200]}")
            year = int(ym.group(1))
            self.assertIn(year, window, f"{year} 不在锚年窗口内")
            gm = re.search(r'<td class="hist-g">([^<]+)</td>', body)
            if gm:
                got[year] = gm.group(1)

        # 每个有数据的年份必须出现，且数值必须是**该年份**的值
        for year, gold in expected.items():
            self.assertIn(year, got, f"{year} 年同周行缺失")
            self.assertEqual(got[year], gold,
                             f"{year} 年同周指数错配（疑似年份/数值错位）")
        # 反向：页面出现的数值不得来自其他年份
        for year, gold in got.items():
            self.assertEqual(gold, expected[year],
                             f"{year} 年行显示的 {gold} 不属于该年份数据集")

    def test_history_semantics_markers(self):
        card = self._card_block("历年同周对比")
        self.assertIn("不是预测", card)
        self.assertIn("历年同周对比", card)
        self.assertIn("Goldstein 相对强度指数", card)

    def test_source_link_and_locality(self):
        rows = self._flu_rows()
        card = self._card_block("南方片流感趋势")
        self.assertIn(rows[-1]["source_url"], card,
                      "来源链接必须落在流感卡内")
        self.assertIn("当期文章", card)


class Q11(unittest.TestCase):
    """oracle round-2 定向故障回归（A2-SEARCH-03/04/05 关键场景）。"""

    @staticmethod
    def _fake_status(fetch=None, compute=None):
        st = {"schema": 2, "run_id": "RID-T", "origin": "cloud",
              "sources": fetch or {}, "compute": compute or {}}
        return st

    def _templates(self, status):
        south = bs.build_flu_view(bs.read_csv(bs.FLU_CSV))
        north = bs.build_flu_view(bs.read_csv(bs.FLU_NORTH_CSV),
                                  "north_ili_pct", "north_flu_positive_pct")
        views = {"flu_south": bs.flu_block(south, "south"),
                 "flu_north": bs.flu_block(north, "north"),
                 "flu_hlj": bs.flu_block(None, "heilongjiang"),
                 "flu_south_view": south, "flu_north_view": north}
        cards, _ = bs._build_cards(views)
        return bs._slot_templates(views, cards, status)

    def test_chip_failed_and_compute_failed(self):
        t = self._templates(self._fake_status(
            fetch={"flu_north": {"status": "failed"}},
            compute={"north": {"status": "failed"}}))
        self.assertIn("本轮获取：失败", t["zone_flu_north"])
        self.assertIn("指数计算：未完成", t["zone_flu_north"])
        # 其他产品不受串扰
        self.assertNotIn("指数计算：未完成", t["zone_flu_south"])

    def test_chip_missing_key_is_unknown_not_silent(self):
        t = self._templates(self._fake_status(fetch={}, compute={}))
        self.assertIn("本轮获取：状态未知", t["zone_flu_south"])
        self.assertIn("指数计算：状态未知", t["zone_flu_south"])

    def test_chip_skipped_fetch_and_compute(self):
        t = self._templates(self._fake_status(
            fetch={"flu_south": {"status": "skipped"}},
            compute={"south": {"status": "skipped"}}))
        self.assertIn("本轮获取：未执行", t["zone_flu_south"])
        self.assertIn("指数计算：未执行", t["zone_flu_south"])

    def test_banner_compute_skipped_wording(self):
        st = self._fake_status(compute={"south": {"status": "skipped"}})
        html = bs.run_banner(local=False, run_id="RID-T", page="index",
                             status=st)
        self.assertIn("本次未执行指数计算", html)

    def test_js_round2_fixes_present(self):
        # 01：多候选不默认激活；二次 Esc 清输入；手动删空清候选
        self.assertIn("setActive(-1)", PAGE)
        self.assertIn("再按一次 Esc 清空输入", PAGE)
        self.assertIn("候选已清空", PAGE)
        # 04：静态常驻说明 + 缺模板回成都 + 切换入口捕获
        self.assertIn("说明内联脚本未完成初始化", PAGE)
        self.assertIn("已恢复成都默认。", PAGE)
        self.assertIn("查询切换失败", PAGE)
        # 03：成都横幅在默认视图内
        self.assertIn('<div id="default-view">\n  <div class="banner">', PAGE
                      or '<div class="banner">')

    def test_publish_isolate_copies_only_index(self):
        import run_pipeline as rp
        import shutil as _sh
        with mock.patch.object(rp, "ROOT") as _:
            pass  # 占位：ROOT 为模块常量，下面用真实临时树 + 属性替换
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        try:
            site = tmp / "site"; site.mkdir()
            (site / "index.html").write_text("NEW-PAGE", encoding="utf-8")
            (site / "south.html").write_text("OLD", encoding="utf-8")  # 历史残留
            old_root, old_site = rp.ROOT, rp.SITE
            rp.ROOT, rp.SITE = tmp, site
            try:
                pub = rp.publish_isolate()
                self.assertEqual((pub / "index.html").read_text(encoding="utf-8"),
                                 "NEW-PAGE")
                self.assertEqual([p.name for p in pub.iterdir()], ["index.html"])
                # 历史残留原样保留
                self.assertEqual((site / "south.html").read_text(encoding="utf-8"),
                                 "OLD")
            finally:
                rp.ROOT, rp.SITE = old_root, old_site
        finally:
            _sh.rmtree(tmp, ignore_errors=True)

    def test_publish_isolate_failure_raises(self):
        import run_pipeline as rp
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        try:
            old_root, old_site = rp.ROOT, rp.SITE
            rp.ROOT, rp.SITE = tmp, tmp / "site"  # site 不存在 → 缺 index.html
            try:
                with self.assertRaises(Exception):
                    rp.publish_isolate()
            finally:
                rp.ROOT, rp.SITE = old_root, old_site
        finally:
            import shutil as _sh2
            _sh2.rmtree(tmp, ignore_errors=True)


class Q12(unittest.TestCase):
    """A2-SEARCH-05 round-3 补口：发布隔离**复制阶段**失败必须关门。

    与 Q11 的"源文件缺失"不同，这里源 index.html 存在且构建成功，失败发生在
    复制/落位阶段（目标被同名非目录占位）。验收：管线 exit=2、
    last_run.site_ready=false、site/ 旧文件原样。
    """

    SKIP_ALL = ("flunet,sentinel,flu_south,flu_north,"
                "heilongjiang_flu,heilongjiang_sentinel")

    def test_copy_stage_failure_closes_publish_gate(self):
        import shutil
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        root = tmp / "root"
        try:
            root.mkdir()
            shutil.copytree(ROOT / "src", root / "src")
            (root / "data").mkdir()
            # 最小目录数据：构建阶段需要（不复制任何真实指标 CSV）
            for name in ("locations.csv", "location_product_map.csv"):
                shutil.copy2(ROOT / "data" / name, root / "data" / name)
            (root / "site").mkdir()
            (root / "site" / "index.html").write_text("OLD-PAGE",
                                                      encoding="utf-8")
            (root / "site" / "south.html").write_text("OLD-SOUTH",
                                                      encoding="utf-8")
            # 注入：site_publish 位置被普通文件占住 → 复制/落位阶段必然失败
            (root / "site_publish").write_text("BLOCKER", encoding="utf-8")

            cp = subprocess.run(
                [sys.executable, "-X", "utf8",
                 str(root / "src" / "run_pipeline.py"),
                 "--cloud", "--timeout", "180", "--skip", self.SKIP_ALL],
                capture_output=True, text=True, timeout=300)

            self.assertEqual(cp.returncode, 2,
                             f"复制失败必须关门（exit=2），实际 {cp.returncode}")
            self.assertIn("发布目录复制失败", cp.stderr)
            last = json.loads((root / ".tmp_pipeline" / "last_run.json")
                              .read_text(encoding="utf-8"))
            self.assertFalse(last["site_ready"], "复制失败后 site_ready 必须为 false")
            self.assertEqual(last["exit"], 2)
            # 旧文件原样保留
            self.assertEqual((root / "site" / "south.html")
                             .read_text(encoding="utf-8"), "OLD-SOUTH")
            self.assertEqual((root / "site_publish").read_text(encoding="utf-8"),
                             "BLOCKER")
            run_dirs = list((root / ".tmp_pipeline").glob("*/site_ready.json"))
            self.assertEqual(len(run_dirs), 1)
            self.assertFalse(json.loads(run_dirs[0].read_text(encoding="utf-8"))
                             ["site_ready"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Q13(unittest.TestCase):
    """round-4 补口：管线两条行为门 + 片区名称卡无数值。

    旧套件 R3 组原本覆盖这两条管线路径，但它的隔离根只有空 data/，单页构建
    需要 data/locations.csv 才能起来，于是被误判为"已失效"。这里补最小目录
    数据后重跑同样的注入，恢复这两条语义的自动化。
    """

    SKIP_ALL = ("flunet,sentinel,flu_south,flu_north,"
                "heilongjiang_flu,heilongjiang_sentinel")

    @staticmethod
    def _iso_root(tmp):
        """隔离根：src + 最小目录数据（不含任何真实指标 CSV）。"""
        import shutil
        root = tmp / "root"
        root.mkdir()
        shutil.copytree(ROOT / "src", root / "src")
        (root / "data").mkdir()
        for name in ("locations.csv", "location_product_map.csv"):
            shutil.copy2(ROOT / "data" / name, root / "data" / name)
        return root

    @staticmethod
    def _last_run(root):
        return json.loads((root / ".tmp_pipeline" / "last_run.json")
                          .read_text(encoding="utf-8"))

    def test_partial_fetch_failure_exit1_still_builds(self):
        """某 fetch 源失败但构建成功 → pipeline exit=1，页面仍生成。"""
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        try:
            root = self._iso_root(tmp)
            # 注入：flu_south 抓取必然失败（其余源 skip 掉）
            (root / "src" / "fetch_flu_south.py").write_text(
                "import sys\nsys.exit(1)\n", encoding="utf-8")
            cp = subprocess.run(
                [sys.executable, "-X", "utf8",
                 str(root / "src" / "run_pipeline.py"),
                 "--local", "--timeout", "180",
                 "--skip", "flunet,sentinel,heilongjiang_flu,"
                           "heilongjiang_sentinel"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=300)
            self.assertEqual(cp.returncode, 1,
                             f"部分失败应是 exit=1（页面仍生成），实际 "
                             f"{cp.returncode}\n{cp.stdout[-800:]}\n{cp.stderr[-500:]}")
            self.assertIn("[构建] build_exit=0 pipeline_exit=1", cp.stdout)
            last = self._last_run(root)
            self.assertEqual(last["exit"], 1)
            self.assertEqual(last["build_exit"], 0)
            self.assertTrue(last["site_ready"], "降级页仍应算发布就绪")
            self.assertTrue((root / "site" / "index.html").exists(),
                            "部分失败也必须生成诚实降级页")
        finally:
            import shutil as _sh
            _sh.rmtree(tmp, ignore_errors=True)

    def test_final_status_write_failure_closes_gate(self):
        """最终状态落盘失败 → exit=2 且 site_ready=false（宁可不发布）。"""
        import tempfile
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
            "    f.write(json.dumps({'schema': 2, 'run_id': rid,"
            " 'origin': org, 'run_at': '2026-11-13T00:00:00',"
            " 'sources': {}, 'complete': False}))\n"
            "sys.exit(0)\n")
        tmp = Path(tempfile.mkdtemp())
        try:
            root = self._iso_root(tmp)
            (root / "src" / "write_run_status.py").write_text(
                wrapper, encoding="utf-8")
            cp = subprocess.run(
                [sys.executable, "-X", "utf8",
                 str(root / "src" / "run_pipeline.py"),
                 "--local", "--timeout", "180", "--skip", self.SKIP_ALL],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=300)
            self.assertEqual(cp.returncode, 2,
                             f"状态落盘失败必须关门（exit=2），实际 "
                             f"{cp.returncode}\n{cp.stdout[-800:]}\n{cp.stderr[-500:]}")
            self.assertIn("injected final-status failure", cp.stderr)
            last = self._last_run(root)
            self.assertEqual(last["exit"], 2)
            self.assertEqual(last["build_exit"], 0)
            self.assertFalse(last["site_ready"],
                             "状态落盘失败后 site_ready 必须为 false")
            gate = json.loads(
                (Path(last["run_dir"]) / "site_ready.json")
                .read_text(encoding="utf-8"))
            self.assertFalse(gate["site_ready"])
        finally:
            import shutil as _sh
            _sh.rmtree(tmp, ignore_errors=True)

    def test_zone_names_templates_carry_no_percentages(self):
        """片区名称卡模板只列名称：不得出现任何百分比数值。"""
        for slot in ("zone_names_south", "zone_names_north"):
            self.assertIn(slot, TPL, f"缺少模板 {slot}")
            body = re.search(r'<template id="tpl-%s">(.*?)</template>' % slot,
                             PAGE, re.S).group(1)
            self.assertIsNotNone(
                re.search(r'<span class="chain">.*?</span>', body),
                f"{slot} 缺少名次链（class=\"chain\"）")
            self.assertIsNone(
                re.search(r'\d+(?:\.\d+)?\s*%', body),
                f"{slot} 出现了百分比数值，违背「仅列名称」口径")
            # 对照：同类数值卡确实带百分比 —— 证明上面的正则不是恒不命中
            rank = re.search(r'<template id="tpl-national_rank">(.*?)'
                             r'</template>', PAGE, re.S).group(1)
            self.assertIsNotNone(re.search(r'\d+(?:\.\d+)?\s*%', rank),
                                 "对照卡 national_rank 应含百分比数值")


if __name__ == "__main__":
    v = unittest.main(verbosity=1, exit=False).result
    n = v.testsRun
    ok = n - len(v.failures) - len(v.errors)
    print(f"Q-SUITE {'OK' if ok == n else 'FAIL'} {ok}/{n}")
    sys.exit(0 if ok == n else 1)

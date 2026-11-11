# -*- coding: utf-8 -*-
"""抓取国家流感中心《中国流感监测周报》，解析南方片 ILI% 与流感阳性率。

M2 r3 契约（.trellis/tasks/11-06-disease-monitor/design.md）：
- 成功才覆盖：同周新 ok 数据覆盖旧行（幂等）
- 失败永不覆盖成功：失败时若该周已有 ok 行则不动，仅记日志；该周无行才写失败行
- goldstein_index 列由 compute_index.py 写回，本脚本留空

A1a 契约（.trellis/tasks/11-11-flu-south-backfill/design.md）：
- 阳性率分母一律取 PDF 表 1「检测数 南方省份」列（旧实现误用全国合计，阳性率被稀释 21%–50%）
- 回补走 ivdc 档案 https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/，--from 下界硬校验 2023W1
  （2016–2018 扫描件无文本层；2019–2021 第三代版式；2022 缺南方分母——见 design §0 版式分代）
- 整表写入中断安全：先写 .tmp_flu_backfill/ 临时文件，fsync 后 os.replace 原子替换（design §4.0）

用法：
  python -X utf8 src/fetch_flu_south.py            # 正常流程：抓最新一期，写 CSV
  python -X utf8 src/fetch_flu_south.py <文章URL>  # 抽验模式：只解析打印，不写 CSV（用于跨年格式抽验）
  python -X utf8 src/fetch_flu_south.py --backfill [--from 2023W1] [--to 2026W44]
                                                   [--force] [--limit N]  # 历史回补
"""
import csv
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "flu_south.csv"
CHANGES_LOG = ROOT / "data" / "changes.log"
# 回补缓存与临时文件统一放 .tmp_flu_backfill/（.gitignore 的 .tmp_*/ 已覆盖）。
# 临时 CSV 必须以 ROOT 为锚：相对路径会跟随进程工作目录，跨卷后 os.replace 失去原子性（design §4.0）。
TMP_DIR = ROOT / ".tmp_flu_backfill"
TXT_DIR = TMP_DIR / "txt"
TMP_CSV = TMP_DIR / "flu_south.csv.tmp"
IVDC_BASE = "https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/"
BACKFILL_MIN = (2023, 1)  # design §0：现行版式起点，--from 不允许更早
RATE_LIMIT = 2.5          # 单期间隔（沿用 fetch_sentinel.py 的礼貌限速）
# pdftotext 跨平台（M4a）：Windows 优先本机 anaconda 绝对路径，兜底/非 Windows 用 PATH 中的 pdftotext
# （GitHub Ubuntu runner 由 workflow 安装 poppler-utils 提供）。找不到则报明确错误。
_WIN_PDFTOTEXT = r"C:/Users/zengw/anaconda3/Library/bin/pdftotext.exe"
if sys.platform == "win32" and Path(_WIN_PDFTOTEXT).exists():
    PDFTOTEXT = _WIN_PDFTOTEXT
else:
    PDFTOTEXT = shutil.which("pdftotext") or ""
if not PDFTOTEXT:
    raise RuntimeError("未找到 pdftotext：Windows 请确认 anaconda 路径，Linux/macOS 请安装 poppler-utils")
LIST_URL = "https://www.chinacdc.cn/jksj/jksj04_14249/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
FIELDS = ["iso_year", "iso_week", "week_start", "south_ili_pct",
          "south_flu_positive_pct", "goldstein_index", "source_url",
          "source_pubdate", "fetched_at", "status"]


def http_get(url: str) -> bytes:
    """urllib 优先；403/空响应切 curl 子进程（G8）。"""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        if data:
            return data
    except Exception:
        pass
    r = subprocess.run(["curl", "-s", "-A", UA["User-Agent"], url],
                       capture_output=True, timeout=120)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f"HTTP 获取失败: {url}")
    return r.stdout


def pick_latest_article(html: str) -> tuple:
    """从列表页选发布日期最新的文章。返回 (绝对URL, 发布日期, 标题)。"""
    pat = re.compile(
        r'<a href="(\./(\d{6})/t\d+_\d+\.html?)"[^>]*>([^<]+)<span>\s*([\d-]+)',
        re.S)
    best = None
    for m in pat.finditer(html):
        rel, _, title, pub = m.groups()
        url = LIST_URL + rel[2:]  # ./202611/x.html -> https://.../202611/x.html
        try:
            pd = datetime.strptime(pub.strip(), "%Y-%m-%d").date()
        except ValueError:
            continue
        if best is None or pd > best[1]:
            best = (url, pd, title.strip())
    if not best:
        raise RuntimeError("列表页未解析到任何文章链接")
    return best


def find_pdf_link(article_html: str, art_url: str) -> str:
    m = re.search(r'href="([^"]+\.pdf)"', article_html, re.I)
    if not m:
        raise RuntimeError("文章页未找到 PDF 链接")
    return urljoin(art_url, m.group(1))


def pdf_to_text(pdf_bytes: bytes) -> str:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "issue.pdf"
        p.write_bytes(pdf_bytes)
        out = Path(td) / "issue.txt"
        r = subprocess.run([PDFTOTEXT, "-layout", str(p), str(out)],
                           capture_output=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError("pdftotext 失败: " + r.stderr.decode("utf-8", "replace"))
        return out.read_text(encoding="utf-8")  # G7: 显式 utf-8


def parse_issue(txt: str, title: str = "") -> tuple:
    """解析南方片 ILI%、流感阳性率、周次与周起始日。返回 (行字典, 告警列表)。

    A1a 解析契约（design §2/§3.3）：
    - 分母一律取表 1「检测数 南方省份」列；表 1 缺失或列自洽性（南方+北方=合计）失败 → 判失败，
      绝不回退全国合计（旧 bug：阳性率被稀释 21%–50%）
    - 括号版式（官方百分比）与表 1 分母互校，相对偏差 > 1.5% → bracket_mismatch 判失败
    - 标题（列表条目，如「2026 第44周」）与 PDF 内年/周不一致 → issue_mismatch 判失败
    - PDF 内出现 ≥2 个不同期号 → merged_issue 判失败（实测正常期全篇只用一个期号）
    - 合并版范围式周次只看标题/锚文本，绝不做 PDF 正文范围匹配（13/27 正常期正文含累计区间）
    - 数值域 [0,100] 越界判失败；week_start 与 ISO 周一不一致照存解析值、仅告警
    """
    warns = []
    week = re.search(r"(\d{4})\s*年\s*第\s*(\d+)\s*周(?:\s*第\s*(\d+)\s*期)?", txt)
    if not week:
        raise RuntimeError("parse_error: 未解析到期号")
    iso_year, iso_week = int(week.group(1)), int(week.group(2))

    # 表 1 分母：锚定「南方省份 北方省份 合计」表头，限 40 字符内出现「检测数」，再取三列
    m_tab = re.search(
        r"南方省份\s+北方省份\s+合计[\s\S]{0,40}?检测数\s+(\d[\d,]*)\s+(\d[\d,]*)\s+(\d[\d,]*)", txt)
    if not m_tab:
        raise RuntimeError("parse_error: 表 1（检测数分省表）缺失，无法取南方分母")
    den_s = int(m_tab.group(1).replace(",", ""))
    den_n = int(m_tab.group(2).replace(",", ""))
    den_all = int(m_tab.group(3).replace(",", ""))
    if den_s <= 0:
        raise RuntimeError(f"parse_error: 表 1 南方检测数 {den_s} 非正数")
    if den_s + den_n != den_all:
        # 2025W33 实测：上游把合计印错（南方 10043+北方 2995=13038，表印合计 13029，差 9≈0.07%），
        # 南方列本身有官方括号佐证（189(1.9%)）。列错位/错抓会产生百分之几级偏差；
        # 故偏差 ≤0.2% 按上游笔误处理（告警照存），>0.2% 仍判失败。
        if abs(den_s + den_n - den_all) / den_all > 0.002:
            raise RuntimeError(
                f"parse_error: 表 1 列校验失败 南方{den_s}+北方{den_n}≠合计{den_all}")
        warns.append(f"table_sum_check: 南方{den_s}+北方{den_n}≠合计{den_all}"
                     f"（偏差≤0.2%，按上游笔误照存）")

    # 合并版守卫：PDF 内出现 ≥2 个不同期号。2026W11 实测发现封面会残留上一期模板行
    # （全角数字「２０２６年第６周总第８９５期」出现 1 次，正文 10 处均为半角「第 900 期」）。
    # 真合并版里每个期号都会随各自页码页眉多次出现；故主期号 ≥3 次且其余期号 ≤2 次
    # 时按「封面残留」告警照存，否则仍判 merged_issue。
    cnt = Counter(int(x) for x in re.findall(r"第\s*(\d{2,4})\s*期", txt))
    if len(cnt) >= 2:
        dom, dom_n = cnt.most_common(1)[0]
        minors = {k: v for k, v in cnt.items() if k != dom}
        if dom_n >= 3 and all(v <= 2 for v in minors.values()):
            warns.append(f"cover_leftover_issue: 主期号第{dom}期×{dom_n}，"
                         f"封面残留期号 {minors}（照存）")
        else:
            raise RuntimeError(f"merged_issue: PDF 内出现多个期号 {sorted(cnt)}")

    # 标题（列表条目）与 PDF 年/周硬校验；标题解析不出年/周则跳过（不硬杀）
    if title:
        mt = re.match(r"\s*(\d{4})\s*年?\s*第\s*(\d+)\s*周", title)
        if mt and (int(mt.group(1)), int(mt.group(2))) != (iso_year, iso_week):
            raise RuntimeError(
                f"issue_mismatch: 标题「{title.strip()}」与 PDF 内 {iso_year}W{iso_week} 不一致")

    m_ili = re.search(r"南方省份哨点医院报告的\s*ILI%\s*为\s*([\d.]+)\s*%", txt)
    if not m_ili:
        raise RuntimeError("parse_error: 未解析到南方 ILI%")

    # 阳性率两种版式（G2 跨年抽验发现）：
    # 2026 式：南方省份检测到 1796(17.14%)份流感病毒阳性标本  -> 官方括号百分比，与表 1 分母互校
    # 2025 式：南方省份检测到 75 份流感病毒阳性标本（无百分比）-> 分子 ÷ 表 1 南方列自算
    # 2023W32 上游漏字：「南方省份检测到 181 流感病毒阳性标本」——数字与「流感病毒阳性」之间没有「份」，
    # 故分子正则里的「份」必须可选（该期 181/4977=3.64%，与 W31 2.52%/W33 3.82% 邻期一致）。
    m_pos = re.search(r"南方省份检测到\s*([\d,]+)\s*\(([\d.]+)%\)", txt)
    if m_pos:
        num = int(m_pos.group(1).replace(",", ""))
        pos = m_pos.group(2)
        calc = num / den_s * 100
        # 分母用 max() 防 0% 零除（括号 0% 且分子 0 时 calc=0 → 偏差 0，正常互校通过）
        if abs(calc - float(pos)) / max(float(pos), 1e-9) > 0.015:
            raise RuntimeError(
                f"bracket_mismatch: 官方括号 {pos}% 与 {num}/{den_s}={calc:.2f}% 偏差超 1.5%")
        pos_src = f"官方括号（互校 {num}/{den_s}={calc:.2f}%）"
    else:
        m_num = re.search(r"南方省份检测到\s*([\d,]+)\s*份?\s*流感病毒阳性", txt)
        if not m_num:
            raise RuntimeError("parse_error: 未解析到南方流感阳性分子")
        num = int(m_num.group(1).replace(",", ""))
        pos = f"{num / den_s * 100:.2f}"
        pos_src = f"自算 {num}/{den_s}（表1南方列）"
    print(f"[解析] 阳性率来源: {pos_src}")

    # 数值域
    for name, v in (("ILI%", float(m_ili.group(1))), ("阳性率", float(pos))):
        if not 0 <= v <= 100:
            raise RuntimeError(f"parse_error: {name}={v} 越界 [0,100]")

    # week_start：优先「第N周（YYYY年M月D日」，兜底全文首个日期；与 ISO 周一不一致仅告警（照存解析值）
    m_ws = re.search(r"第\s*%d\s*周（(\d{4})\s*年\s*(\d+)\s*月\s*(\d+)\s*日" % iso_week, txt) \
        or re.search(r"(\d{4})\s*年\s*(\d+)\s*月\s*(\d+)\s*日", txt)
    week_start = ""
    if m_ws:
        g = m_ws.groups()
        try:
            week_start = date(int(g[-3]), int(g[-2]), int(g[-1])).isoformat()
        except ValueError:
            pass
    try:
        iso_mon = date.fromisocalendar(iso_year, iso_week, 1).isoformat()
    except ValueError:
        warns.append(f"iso_invalid: {iso_year}W{iso_week} 不是合法 ISO 周")
    else:
        if week_start and week_start != iso_mon:
            warns.append(f"week_start_check: 解析值 {week_start} ≠ ISO 周一 {iso_mon}")

    return ({"iso_year": iso_year, "iso_week": iso_week, "week_start": week_start,
             "south_ili_pct": m_ili.group(1), "south_flu_positive_pct": pos}, warns)


def load_rows() -> list:
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save_rows(rows: list) -> None:
    """中断安全的整表写入（design §4.0）：写临时文件 → fsync → os.replace 原子替换。

    upsert 每成功一期都会整表重写一次；若直接以 "w" 打开权威 CSV，
    Ctrl-C 落在"已截断、未写完"窗口会丢掉此前全部成功行。
    临时文件与 CSV 同卷（都在仓库 ROOT 内），os.replace 保持原子性。
    """
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    TMP_CSV.parent.mkdir(parents=True, exist_ok=True)
    with TMP_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
        f.flush()
        os.fsync(f.fileno())
    os.replace(TMP_CSV, CSV_PATH)


def upsert(new: dict) -> None:
    """r3 写入规则：成功才覆盖；失败永不覆盖成功（该周无行才写失败行）。"""
    rows = load_rows()
    key = lambda r: (int(r["iso_year"]), int(r["iso_week"]))
    same = [r for r in rows if key(r) == (new["iso_year"], new["iso_week"])]
    if new["status"] == "ok":
        rows = [r for r in rows if key(r) != (new["iso_year"], new["iso_week"])]
        rows.append({**{k: "" for k in FIELDS}, **new})
        save_rows(rows)
        print(f"[ok] {new['iso_year']}W{new['iso_week']} ILI%={new['south_ili_pct']} "
              f"阳性率={new['south_flu_positive_pct']}%（覆盖/写入成功行）")
    else:
        if same and same[0]["status"] == "ok":
            print(f"[{new['status']}] 该周已有成功数据，保留不动（失败不覆盖成功）")
            return
        if same:  # 该周已有失败行 → 覆盖为最新失败信息；无行 → 追加
            rows = [r for r in rows if key(r) != (new["iso_year"], new["iso_week"])]
        rows.append({**{k: "" for k in FIELDS}, **new})
        save_rows(rows)
        print(f"[{new['status']}] {new['iso_year']}W{new['iso_week']} 写入失败状态行")


def fetch_latest() -> None:
    now = datetime.now().isoformat(timespec="seconds")
    base = {"fetched_at": now, "status": "ok"}
    try:
        html = http_get(LIST_URL).decode("utf-8", "replace")
        art_url, pub, title = pick_latest_article(html)
        print(f"最新一期: {title} ({pub}) {art_url}")
        art = http_get(art_url).decode("utf-8", "replace")
        pdf_url = find_pdf_link(art, art_url)
        print(f"PDF: {pdf_url}")
        txt = pdf_to_text(http_get(pdf_url))
        parsed, warns = parse_issue(txt, title=title)
        for w in warns:
            code, _, detail = w.partition(": ")
            log_change(f"{parsed['iso_year']}W{parsed['iso_week']}", code or "warn", detail, "")
        upsert({**base, **parsed,
                "source_url": art_url, "source_pubdate": pub.isoformat()})
    except Exception as e:
        print(f"[失败] {e}", file=sys.stderr)
        # r3：失败行仅在能定位目标周次时才有意义。列表页都失败时连周次都未知，
        # 只报错退出，不写占位垃圾行（避免 iso_week=0 类无效主键）。
        sys.exit(1)


def log_change(week: str, which: str, old: str, new: str) -> None:
    """changes.log 追加一行（格式同 fetch_sentinel.py：时间戳\t周次\twhich\told\tnew）。"""
    ts = datetime.now().isoformat(timespec="seconds")
    CHANGES_LOG.parent.mkdir(parents=True, exist_ok=True)
    with CHANGES_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\t{week}\t{which}\t{old}\t{new}\n")


# ivdc 档案列表（A1a 回补源）。条目正则实测覆盖 30 页 600 条（design §3.1）。
IVDC_ITEM = re.compile(
    r'<span class="span_01">\s*<a href="([^"]*t\d+_\d+\.htm[l]?)"[^>]*>([^<]*)</a>\s*</span>'
    r'\s*<span class="span_02">\s*\(([\d-]+)\)', re.S)
TITLE_WEEK = re.compile(r"^\s*(\d{4})\s*年?\s*第\s*(\d+)\s*周")
RANGE_TITLE = re.compile(r"^\s*(\d{4})\s*年?\s*第\s*(\d+)\s*[-–~至]\s*(\d+)\s*周")  # 「第14-22周」
WEEK_RANGE = re.compile(r"第\s*\d+\s*[-–~至]\s*\d+\s*周")  # 范围式周次=合并版（只看标题/锚文本）


def _anchor_is_merged(anchor: str) -> bool:
    """锚文本含范围式周次/期号 → 合并版（design §3.4）。

    散置期号不在此判：实测锚文本期号不可靠（2024W26 锚文本 811 vs PDF 内 810、
    2016W10 锚文本为 0.pdf），真合并由 PDF 内期号频次守卫（parse_issue）兜底。
    """
    if not anchor:
        return False
    return bool(WEEK_RANGE.search(anchor)
                or re.search(r"第\s*\d+\s*[-–~至]\s*\d+\s*期", anchor))


def enumerate_archive() -> tuple:
    """枚举 ivdc 周报档案。

    返回 ({(iso_year, iso_week): (标题, 文章URL, 列表日期)},  # 单周条目
          {(iso_year, iso_week): (标题, 文章URL, 列表日期)})  # 范围式标题覆盖的周（合并版）

    页数取页内 JS 变量 countPage（越界页返回 HTTP 200 的"找不到"伪页，不能靠空页判断）；
    同周重复保留列表靠前（较新发布）的一条并留痕。
    范围式标题（如「2025 第14-22周」）不匹配 TITLE_WEEK，须单独捕获为合并版覆盖，
    否则这些周会被误报 list_missing（复核 B1）。
    """
    html = http_get(IVDC_BASE).decode("utf-8", "replace")
    m = re.search(r"var\s+countPage\s*=\s*(\d+)", html)
    if not m:
        raise RuntimeError("ivdc 列表页未解析到 countPage")
    pages = int(m.group(1))
    items: dict = {}
    merged: dict = {}
    dups = []
    for i in range(pages):
        url = IVDC_BASE if i == 0 else f"{IVDC_BASE}index_{i}.htm"
        page = http_get(url).decode("utf-8", "replace")
        for rel, title, pub in IVDC_ITEM.findall(page):
            t = title.strip()
            mr = RANGE_TITLE.match(t)
            if mr:
                y, w1, w2 = int(mr.group(1)), int(mr.group(2)), int(mr.group(3))
                if w1 <= w2:
                    for wk in _expected_weeks((y, w1), (y, w2)):
                        merged.setdefault(wk, (t, urljoin(IVDC_BASE, rel), pub.strip()))
                continue
            mt = TITLE_WEEK.match(t)
            if not mt:
                continue  # 非周报条目
            k = (int(mt.group(1)), int(mt.group(2)))
            if k in items:
                dups.append(f"{k[0]}W{k[1]}")
                continue
            items[k] = (t, urljoin(IVDC_BASE, rel), pub.strip())
        if i < pages - 1:
            time.sleep(0.5)
    if dups:
        log_change("ivdc-list", "dup_list_entry", f"丢弃 {len(dups)} 条",
                   "; ".join(sorted(set(dups))[:10]))
    return items, merged


def _expected_weeks(from_w: tuple, hi: tuple) -> list:
    """从 from_w 到 hi（含）的全部 ISO 周键，升序。"""
    out, yw = [], from_w
    while yw <= hi:
        out.append(yw)
        d = date.fromisocalendar(yw[0], yw[1], 1) + timedelta(days=7)
        yw = (d.isocalendar()[0], d.isocalendar()[1])
    return out


def _final_class(k: tuple, csv_ok: set, proc: dict) -> str:
    """最终状态三分类（design §6.4）：以收尾 CSV 为准，互斥且可重演。

    - CSV 已有 ok 行 → ok（含 force 重抓失败但旧行保留的情况）
    - 过程结果为合并版（范围标题/锚文本/PDF 多期号）且无 ok 行 → merged_skip
    - 其余 → pending_fail（失败原因见 proc，含 list_missing / 未处理）
    """
    if k in csv_ok:
        return "ok"
    if proc.get(k) in ("merged_skip", "fail:merged_issue"):
        return "merged_skip"
    return "pending_fail"


def backfill(from_w: tuple = BACKFILL_MIN, to_w: tuple = None,
             force: bool = False, limit: int = None) -> None:
    """历史回补：枚举 → 逐期下载解析 → upsert；可中断续跑（已有 ok 周跳过不下载）。

    失败期只记 changes.log，不写 CSV 失败行（build_site.py:69-80 会把历史失败行
    渲染成常驻错误横幅）；对账 = 收尾后按 CSV 最终状态三分类（design §4.2/§6.4），
    进程内 {周键: 过程结果} 只作失败原因明细，不数日志行。
    """
    items, merged_cov = enumerate_archive()
    ok_rows = {(int(r["iso_year"]), int(r["iso_week"])): r
               for r in load_rows() if r.get("status") == "ok"}
    # 目标区间依据 = 单周条目 ∪ 合并版覆盖周（复核 B1：全是合并版或合并版收尾时，
    # 只看 items 会把合并周排除在目标外，对账凭空少一周一段）
    known = set(items) | set(merged_cov)
    in_range = [k for k in known if k >= from_w and (to_w is None or k <= to_w)]
    if not in_range:
        print(f"[backfill] 枚举结果中无 {from_w[0]}W{from_w[1]} 之后的条目")
        return
    hi = max(in_range)
    target = _expected_weeks(from_w, to_w if to_w else hi)
    final: dict = {}
    done = 0
    print(f"[backfill] 目标 {len(target)} 周（{from_w[0]}W{from_w[1]}→{hi[0]}W{hi[1]}），"
          f"已有 ok 行 {sum(1 for k in target if k in ok_rows)}，force={force}")
    for k in target:
        if k not in items:
            if k in merged_cov:
                m_title = merged_cov[k][0]
                final[k] = "merged_skip"
                log_change(f"{k[0]}W{k[1]}", "skipped_merged", m_title,
                           "列表标题为范围式周次（合并版）")
                print(f"[skip] {k[0]}W{k[1]} 合并版（标题：{m_title}）")
            else:
                final[k] = "fail:list_missing"
                log_change(f"{k[0]}W{k[1]}", "backfill_fail", "list_missing",
                           "ivdc 列表无此周条目（亦无范围式合并版覆盖）")
            continue
        title, art_url, pub = items[k]
        if WEEK_RANGE.search(title):
            final[k] = "merged_skip"
            log_change(f"{k[0]}W{k[1]}", "skipped_merged", title, "标题含范围式周次")
            print(f"[skip] {k[0]}W{k[1]} 合并版（标题：{title}）")
            continue
        if k in ok_rows and not force:
            final[k] = "ok"  # 已有 ok 行：跳过，不下载（--force 例外）
            continue
        if limit is not None and done >= limit:
            continue  # 冒烟模式：剩余周不处理，留待对账显示为 pending_fail(unprocessed)
        done += 1
        try:
            cache = TXT_DIR / f"{k[0]}_W{k[1]}.txt"
            anchor = ""
            fresh = False
            if force or not cache.exists():
                art = http_get(art_url).decode("utf-8", "replace")
                m = re.search(r'href="([^"]+\.pdf)"[^>]*>([^<]+)<', art, re.I)
                if not m:
                    raise RuntimeError("no_pdf: 文章页未找到 PDF 链接")
                pdf_url, anchor = urljoin(art_url, m.group(1)), m.group(2).strip()
                txt = pdf_to_text(http_get(pdf_url))
                fresh = True
                time.sleep(RATE_LIMIT)
            else:
                txt = cache.read_text(encoding="utf-8")
            # 锚文本范围式周次/期号 = 合并版（复核 B1；散置期号不可靠不在此判）
            if _anchor_is_merged(anchor):
                final[k] = "merged_skip"
                log_change(f"{k[0]}W{k[1]}", "skipped_merged", anchor[:80],
                           "锚文本为范围式周次/期号（合并版）")
                print(f"[skip] {k[0]}W{k[1]} 合并版（锚文本：{anchor}）")
                continue
            row, warns = parse_issue(txt, title=title)
            if fresh:
                # 解析成功才落缓存：--force 重抓到坏 PDF 时不破坏旧缓存（design §3.2，复核 B2）
                TXT_DIR.mkdir(parents=True, exist_ok=True)
                cache.write_text(txt, encoding="utf-8")
            # 锚文本期号只告警不判失败（实测上游会标错：2024W26 锚文本 811 vs PDF 内 810）
            if anchor:
                a_set = set(re.findall(r"第\s*(\d+)\s*期", anchor))
                mp = re.search(r"第\s*(\d+)\s*期", txt)
                if len(a_set) > 1:
                    # 同一锚文本含多个不同期号：无条件告警（复核 B1；可能一版多期，
                    # 也可能上游笔误——是否真合并版由 PDF 期号频次守卫另行兜底）
                    log_change(f"{k[0]}W{k[1]}", "multi_issue_warn",
                               f"锚文本含多个期号：{'、'.join(sorted(a_set, key=int))}",
                               f"PDF内第{mp.group(1) if mp else '?'}期（数据照常入库）")
                elif a_set and mp and next(iter(a_set)) != mp.group(1):
                    log_change(f"{k[0]}W{k[1]}", "issue_no_warn",
                               f"锚文本第{next(iter(a_set))}期",
                               f"PDF内第{mp.group(1)}期（数据照常入库）")
            for w in warns:
                code, _, detail = w.partition(": ")
                log_change(f"{k[0]}W{k[1]}", code or "warn", detail, "")
            old = ok_rows.get(k)
            new = {"fetched_at": datetime.now().isoformat(timespec="seconds"),
                   "status": "ok", "source_url": art_url,
                   "source_pubdate": pub.replace("/", "-"), **row}
            if force and old is not None and not any(w.startswith("parse_error") for w in warns):
                if (old.get("south_ili_pct"), old.get("south_flu_positive_pct")) == \
                        (row["south_ili_pct"], row["south_flu_positive_pct"]):
                    print(f"[force] {k[0]}W{k[1]} 数值无变化，不覆盖")
                    final[k] = "ok"
                    continue
                log_change(f"{k[0]}W{k[1]}", "backfill_revise",
                           f"ILI% {old.get('south_ili_pct')} / 阳性率 {old.get('south_flu_positive_pct')}",
                           f"ILI% {row['south_ili_pct']} / 阳性率 {row['south_flu_positive_pct']}")
            upsert(new)
            final[k] = "ok"
        except Exception as e:
            msg = str(e)
            if msg.startswith("HTTP 获取失败"):
                code = "http_error"
            elif msg.startswith("pdftotext 失败"):
                code = "pdf_error"
            else:
                code = msg.split(":", 1)[0] if ":" in msg else "parse_error"
            final[k] = f"fail:{code}"
            log_change(f"{k[0]}W{k[1]}", "backfill_fail", code, msg[:160])
            print(f"[fail] {k[0]}W{k[1]} {msg}", file=sys.stderr)

    # 收尾：行序归一（复用同一安全写入）+ 按最终状态三分类对账（design §4.2/§6.4，复核 B3）
    rows = load_rows()
    rows.sort(key=lambda r: (int(r["iso_year"]), int(r["iso_week"])))
    save_rows(rows)
    csv_ok = {(int(r["iso_year"]), int(r["iso_week"]))
              for r in rows if r.get("status") == "ok"}
    cls = {k: _final_class(k, csv_ok, final) for k in target}
    counts = {"ok": 0, "merged_skip": 0, "pending_fail": 0}
    for v in cls.values():
        counts[v] += 1
    print(f"\n[对账] 目标 {len(target)} 周：ok={counts['ok']} "
          f"merged_skip={counts['merged_skip']} pending_fail={counts['pending_fail']}")
    pf = {k: final.get(k, "unprocessed").removeprefix("fail:")
          for k in target if cls[k] == "pending_fail"}
    if pf:
        rc = Counter(pf.values())
        print("[pending_fail 按原因] " + " ".join(f"{r}×{n}" for r, n in sorted(rc.items())))
        shown = [f"{k[0]}W{k[1]}({v})" for k, v in sorted(pf.items())][:20]
        print("[pending_fail] " + " ".join(shown) + (" …" if len(pf) > 20 else ""))
    ms = [f"{k[0]}W{k[1]}" for k in target if cls[k] == "merged_skip"]
    if ms:
        print(f"[merged_skip] {ms}")


def _parse_week_arg(s: str) -> tuple:
    m = re.fullmatch(r"(\d{4})[wW](\d+)", s.strip())
    if not m:
        raise SystemExit(f"周次格式应为 YYYYWnn（如 2023W1），收到：{s}")
    y, w = int(m.group(1)), int(m.group(2))
    try:
        date.fromisocalendar(y, w, 1)  # 1–53 不足以排除 2025W53 这类不存在的一周
    except ValueError:
        raise SystemExit(f"周次不存在：{y} 年没有第 {w} 周（ISO 历法校验失败）")
    return (y, w)


if __name__ == "__main__":
    if TMP_CSV.exists():
        TMP_CSV.unlink()  # 启动清理：上次被杀遗留的半成品不得参与任何逻辑（design §4.0）
    argv = sys.argv[1:]
    if argv and argv[0] == "--backfill":
        # 参数分支必须先于「任何参数当 URL」分支，否则 --backfill 会被当成文章 URL
        opts = {"from_w": BACKFILL_MIN, "to_w": None, "force": False, "limit": None}
        it = iter(argv[1:])
        for a in it:
            if a == "--force":
                opts["force"] = True
            elif a == "--from":
                opts["from_w"] = _parse_week_arg(next(it, ""))
            elif a == "--to":
                opts["to_w"] = _parse_week_arg(next(it, ""))
            elif a == "--limit":
                try:
                    opts["limit"] = int(next(it, ""))
                except ValueError:
                    raise SystemExit("--limit 需要一个整数")
                if opts["limit"] <= 0:
                    raise SystemExit("--limit 需为正整数")
            else:
                raise SystemExit(f"未知参数: {a}")
        if opts["from_w"] < BACKFILL_MIN:
            raise SystemExit(
                f"--from 不允许早于 {BACKFILL_MIN[0]}W{BACKFILL_MIN[1]}："
                "2016–2018 为扫描件无文本层，2019–2022 缺南方分母（design §0 版式分代）")
        if opts["to_w"] is not None and opts["from_w"] > opts["to_w"]:
            raise SystemExit(f"--from {opts['from_w']} 晚于 --to {opts['to_w']}，区间为空")
        backfill(**opts)
    elif argv:  # 抽验模式：对指定文章 URL 解析打印，不写 CSV
        art = http_get(argv[0]).decode("utf-8", "replace")
        pdf_url = find_pdf_link(art, argv[0])
        print(f"PDF: {pdf_url}")
        res, warns = parse_issue(pdf_to_text(http_get(pdf_url)))
        print("解析结果:", res)
        for w in warns:
            print("[告警]", w)
    else:
        fetch_latest()

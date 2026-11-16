#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""黑龙江疾控流感/急性呼吸道监测周报采集器（A2）。

数据源：黑龙江省疾控中心 疾病专题列表
  https://www.hljcdc.org/pc/index.php?c=zixun&a=index&id=120
两个独立产品（设计契约见 .trellis/tasks/11-12-regional-monitor/design.md §2.1/§2.2/§3.2）：

  B1 heilongjiang_flu.csv     流感监测周报：省级 ILI%/阳性率/标本计数（可算 Goldstein）
  B2 heilongjiang_sentinel.csv 急性呼吸道哨点监测周报：门急诊/住院正文选列病原率（不算指数）

用法：
  python -X utf8 src/fetch_heilongjiang.py                     # 最新一期 B1+B2
  python -X utf8 src/fetch_heilongjiang.py --backfill          # B1 按 2025W1 起回补（B2 仍只取最新）
  python -X utf8 src/fetch_heilongjiang.py --backfill --force  # 已有同周也重抓比对
  python -X utf8 src/fetch_heilongjiang.py --backfill --limit 20   # 冒烟：只处理前 20 个发现
  python -X utf8 src/fetch_heilongjiang.py --write-url URL     # 人工指定单篇消歧（需用户确认后使用）
  python -X utf8 src/fetch_heilongjiang.py --result-file P --run-id ID   # 管线集成

退出码：0 全部成功；1 任一产品失败。失败不写 CSV 失败行，保留旧成功值并记 changes.log。
"""
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from bs4 import BeautifulSoup

from data_io import atomic_write_csv
from fetch_flu_south import RATE_LIMIT, http_get

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHANGES_LOG = DATA / "changes.log"
B1_CSV = DATA / "heilongjiang_flu.csv"
B2_CSV = DATA / "heilongjiang_sentinel.csv"

B1_FIELDS = ["iso_year", "iso_week", "week_start", "ili_pct", "flu_positive_pct",
             "goldstein_index", "sample_count", "positive_count",
             "source_url", "source_pubdate", "fetched_at", "status"]
B2_FIELDS = ["iso_year", "iso_week", "week_start", "setting", "pathogen", "positive_pct",
             "sample_count", "total_samples",
             "source_url", "source_pubdate", "fetched_at", "status"]

LIST_URL = "https://www.hljcdc.org/pc/index.php?c=zixun&a=index&id=120"
ART_BASE = "https://www.hljcdc.org/pc/"

# 列表条目：<a href="index.php?c=zixundetail&a=index&id=7267&lid=120">标题</a><i>2026-11-10</i>
LIST_ITEM = re.compile(
    r'<a[^>]+href="(?:https?://[^"]*?)?index\.php\?c=zixundetail&amp;a=index&amp;id=(\d+)&amp;lid=\d+"[^>]*>'
    r'([^<]+)</a>\s*<i>(\d{4}-\d{2}-\d{2})</i>', re.S)
# 兼容未转义 & 的页面
LIST_ITEM_RAW = re.compile(
    r'<a[^>]+href="(?:https?://[^"]*?)?index\.php\?c=zixundetail&a=index&id=(\d+)&lid=\d+"[^>]*>'
    r'([^<]+)</a>\s*<i>(\d{4}-\d{2}-\d{2})</i>', re.S)

BACKFILL_FROM = (2025, 1)          # B1 回补下界（设计：列表已发现 2025W1 及以后）
# 下界周的 ISO 周一（2025W1 = 2024-12-30）。列表页整页发布日期都早于该日 → 已翻过目标窗口。
# 注意必须用整页日期判断：2025W1 之后的列表页可能整页都是非周报文章（实测第 23-39 页）。
BACKFILL_CUTOFF = "2024-12-30"
MAX_PAGES = 100                    # 分页硬上界（实测 69 页）
MAX_EMPTY_STREAK = 6               # 连续无候选页上限（实测第 5、6、12-14 页被非周报文章隔断）

B1_TITLE = "流感监测周报"
B2_TITLE = "急性呼吸道传染病哨点监测周报"

# 周次与日期区间：`2026年第45周（2026.11.2-2026.11.8）` / `2026年第45周（2026年11月2日-11月8日）`
# / `2025年第1周（2024.12.30-2025.1.5）`
WEEK_RANGE = re.compile(r"(\d{4})\s*年\s*第\s*(\d{1,2})\s*周\s*[（(]\s*([^）)]+?)\s*[）)]")
DATE_PART = re.compile(r"(\d{4})\s*[年.．/-]\s*(\d{1,2})\s*[月.．/-]\s*(\d{1,2})\s*日?")
TITLE_WEEK = re.compile(r"(\d{4})\s*年\s*第\s*(\d{1,2})\s*周")
RANGE_SPLIT = re.compile(r"[-–—~至]")

ILI_PAT = re.compile(r"ILI%+（[^）]*）\s*为\s*([\d.]+)\s*%")
ILI_PAT_ASCII = re.compile(r"ILI%+\([^)]*\)\s*为\s*([\d.]+)\s*%")
SAMPLE_PAT = re.compile(
    r"共采集\s*ILI\s*标本\s*([\d,]+)\s*份\s*[，,]\s*"
    r"(?:(?:其中\s*)?([\d,]+)\s*份标本流感病毒阳性|(?:核酸检测)?\s*均为阴性)")
RATE_PAT = re.compile(r"阳性率\s*([\d.]+)\s*%")

B2_TOTAL_PAT = re.compile(
    r"共采集\s*([\d,]+)\s*份标本\s*，\s*其中门急诊\s*ILI\s*病例\s*([\d,]+)\s*份\s*，\s*住院\s*SARI\s*病例\s*([\d,]+)\s*份")
B2_GROUP_PAT = re.compile(
    r"(门急诊\s*ILI\s*病例|住院\s*SARI\s*病例)\s*中检测到的病原体主要为\s*(.+?)(?=[；。]|$)")
B2_ITEM_PAT = re.compile(
    r"([\u4e00-\u9fa5A-Za-z]+)\s*[（(]\s*(?:([^，,）)]*并列[^，,）)]*)[，,]\s*)?阳性率\s*([\d.]+)\s*%\s*[）)]")


def _now():
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


def log_change(week, which, old, new):
    """changes.log 追加一行（格式同 fetch_sentinel/fetch_flu_south 五列 tab）。

    本模块独立持有 CHANGES_LOG 常量，便于沙箱测试改写路径而无需污染真实 data/。
    契约（A2 复核 IMP-13）：字段内 tab/换行替换为空格，防破坏列边界；空值占位「无变更」。
    """
    from datetime import datetime

    def clean(v):
        return (str(v).replace("\t", " ").replace("\r", " ")
                .replace("\n", " ").strip()) or "无变更"

    ts = datetime.now().isoformat(timespec="seconds")
    CHANGES_LOG.parent.mkdir(parents=True, exist_ok=True)
    with CHANGES_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\t{clean(week)}\t{clean(which)}\t{clean(old)}\t{clean(new)}\n")


def parse_date_range(text):
    """把 `2024.12.30-2025.1.5` / `2026年11月2日-11月8日` 解析成 (start, end)。

    尾段允许缺年/月（继承首段）。无法解析返回 None。
    """
    parts = [p for p in RANGE_SPLIT.split(text.strip()) if p.strip()]
    if not parts:
        return None
    m = DATE_PART.search(parts[0])
    if not m:
        return None
    y1, mo1, d1 = (int(x) for x in m.groups())
    try:
        start = date(y1, mo1, d1)
    except ValueError:
        return None
    end = start
    if len(parts) > 1:
        tail = parts[1]
        m2 = DATE_PART.search(tail)
        if m2:
            y2, mo2, d2 = (int(x) for x in m2.groups())
        else:
            # 尾段缺年：`7月5日` / `11.8` —— 继承首段年份
            m3 = re.search(r"(\d{1,2})\s*[月.．/-]\s*(\d{1,2})\s*日?", tail)
            if not m3:
                return None
            y2, mo2, d2 = y1, int(m3.group(1)), int(m3.group(2))
        try:
            end = date(y2, mo2, d2)
        except ValueError:
            return None
    if end < start:
        return None
    return start, end


def extract_article(html):
    """从文章页取 (title, pubdate, body_text)。正文容器 article.about1，排除导航。"""
    soup = BeautifulSoup(html, "html.parser")
    art = soup.find("article", class_="about1") or soup.find("article")
    if art is None:
        return None
    h3 = art.find(["h3", "h2", "h1"])
    title = h3.get_text(strip=True) if h3 else ""
    h4 = art.find("h4")
    pubdate = ""
    if h4:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", h4.get_text(" ", strip=True))
        pubdate = m.group(1) if m else ""
    body = art.get_text("\n", strip=True)
    return title, pubdate, body


def classify(title):
    """按完整标题区分 B1/B2；都不是返回 None。"""
    if B2_TITLE in title:
        return "b2"
    if B1_TITLE in title:
        return "b1"
    return None


def check_week(title, body):
    """标题/正文/日期区间联合核周。返回 (iso_year, iso_week, week_start) 或抛 RuntimeError。"""
    m = WEEK_RANGE.search(body)
    if not m:
        raise RuntimeError("parse_error: 正文未找到「第N周（日期区间）」")
    y, w = int(m.group(1)), int(m.group(2))
    rng = parse_date_range(m.group(3))
    if rng is None:
        raise RuntimeError(f"parse_error: 日期区间无法解析「{m.group(3)}」")
    start, end = rng
    if end - start != timedelta(days=6):
        raise RuntimeError(f"parse_error: 日期区间不是 7 天（{start}~{end}）")
    try:
        iso_y, iso_w, _ = start.isocalendar()
    except ValueError:
        raise RuntimeError(f"parse_error: 周起始日非法 {start}")
    if (iso_y, iso_w) != (y, w):
        raise RuntimeError(f"parse_error: 日期区间与周次不符（正文 {y}年第{w}周 vs ISO {iso_y}年第{iso_w}周）")
    tm = TITLE_WEEK.search(title)
    if tm and (int(tm.group(1)), int(tm.group(2))) != (y, w):
        raise RuntimeError(
            f"conflict: 标题周次 {tm.group(1)}年第{tm.group(2)}周 ≠ 正文 {y}年第{w}周，整篇拒绝")
    return y, w, start.isoformat()


def parse_b1(title, body):
    """B1 流感监测周报 → B1 行 dict。抛 RuntimeError 表示整篇失败。"""
    y, w, ws = check_week(title, body)
    m = ILI_PAT.search(body) or ILI_PAT_ASCII.search(body)
    if not m:
        raise RuntimeError("parse_error: 未解析到当期 ILI%")
    ili = m.group(1)
    ms = SAMPLE_PAT.search(body)
    if not ms:
        raise RuntimeError("parse_error: 未解析到标本/阳性计数")
    den = int(ms.group(1).replace(",", ""))
    # 「核酸检测均为阴性」= 阳性 0，官方阳性率 0%
    num = int(ms.group(2).replace(",", "")) if ms.group(2) else 0
    if den <= 0 or num < 0 or num > den:
        raise RuntimeError(f"parse_error: 计数域非法（检测 {den}，阳性 {num}）")
    mr = RATE_PAT.search(body, ms.end())
    if not mr:
        raise RuntimeError("parse_error: 未解析到当期阳性率")
    rate = mr.group(1)
    d = len(rate.split(".")[1]) if "." in rate else 0
    tol = 0.5 * (10 ** -d) + 1e-9
    calc = num / den * 100
    if abs(calc - float(rate)) > tol:
        raise RuntimeError(
            f"parse_error: 官方率 {rate}% 与计数比 {calc:.4f}% 超出小数位舍入容差")
    if not (0.0 <= float(ili) <= 100.0):
        raise RuntimeError(f"parse_error: ILI% 越界 {ili}")
    return {"iso_year": y, "iso_week": w, "week_start": ws,
            "ili_pct": ili, "flu_positive_pct": rate,
            "goldstein_index": "", "sample_count": str(den), "positive_count": str(num),
            "source_url": "", "source_pubdate": "", "fetched_at": _now(), "status": "ok"}


def parse_b2(title, body):
    """B2 急性呼吸道哨点监测周报 → B2 行列表。整批校验，任一不明整期抛 RuntimeError。"""
    y, w, ws = check_week(title, body)
    mt = B2_TOTAL_PAT.search(body)
    if not mt:
        raise RuntimeError("parse_error: 未解析到标本总数/两组构成")
    total, n_opd, n_inp = (int(g.replace(",", "")) for g in mt.groups())
    if n_opd < 0 or n_inp < 0 or n_opd + n_inp != total:
        raise RuntimeError(f"parse_error: 两组标本 {n_opd}+{n_inp} ≠ 总数 {total}")
    rows = []
    seen = set()
    groups = B2_GROUP_PAT.findall(body)
    setting_map = {"门急诊": ("门急诊", n_opd), "住院": ("住院", n_inp)}
    if len(groups) < 2:
        raise RuntimeError("parse_error: 未同时找到门急诊与住院两组病原描述")
    found_settings = set()
    for head, items in groups:
        setting = "门急诊" if head.startswith("门急诊") else "住院"
        found_settings.add(setting)
        sname, scount = setting_map[setting]
        matches = list(B2_ITEM_PAT.finditer(items))
        # 段完整消费守卫（复核 IMP-08）：每个病原条目恰好含一个「阳性率…%」；
        # 出现无法匹配的片段（新版式/排版漂移）必须整期失败，不允许静默跳过
        if items.count("阳性率") != len(matches):
            raise RuntimeError(
                f"parse_error: {setting}组存在无法解析的病原条目"
                f"（阳性率出现 {items.count('阳性率')} 次，仅匹配 {len(matches)} 项）")
        got = len(matches)
        for m in matches:
            name, tie, rate = m.group(1), m.group(2), m.group(3)
            if not (0.0 <= float(rate) <= 100.0):
                raise RuntimeError(f"parse_error: {setting}{name} 阳性率越界 {rate}")
            key = (setting, name)
            if key in seen:
                raise RuntimeError(f"parse_error: {setting}{name} 重复出现（冲突）")
            seen.add(key)
            rows.append({"setting": sname, "pathogen": name, "positive_pct": rate,
                         "sample_count": str(scount), "total_samples": str(total)})
            # 并列展开：并列伙伴同率成行（同率重复合并已在 seen 去重）
            if tie:
                # 并列句式有「（与X并列，阳性率…）」与「（X并列，阳性率…）」两种；
                # 去掉「并列…」后剩「与X」时剥掉连接词，避免产出「与X」病原名
                partner = re.sub(r"并列.*$", "", tie).strip()
                if partner and partner[0] in "与和及":
                    partner = partner[1:].strip()
                if partner:
                    pkey = (setting, partner)
                    if pkey in seen:
                        # 伙伴已有独立条目：必须同率，否则是冲突而非并列（复核 IMP-08）
                        prior = next(r for r in rows
                                     if (r["setting"], r["pathogen"]) == pkey)
                        if prior["positive_pct"] != rate:
                            raise RuntimeError(
                                f"parse_error: {setting}组并列伙伴 {partner} 率 {rate}%"
                                f"与已有 {prior['positive_pct']}% 不一致")
                    else:
                        seen.add(pkey)
                        rows.append({"setting": sname, "pathogen": partner,
                                     "positive_pct": rate,
                                     "sample_count": str(scount), "total_samples": str(total)})
        if got == 0:
            raise RuntimeError(f"parse_error: {setting}组未解析到任何病原阳性率")
    # 设置集合守卫（复核 IMP-08）：两组必须是门急诊+住院各一，不能两段同为门急诊
    if found_settings != {"门急诊", "住院"}:
        raise RuntimeError(
            f"parse_error: 病原描述组设置异常 {sorted(found_settings)}（应为门急诊+住院各一组）")
    for r in rows:
        r.update({"iso_year": y, "iso_week": w, "week_start": ws,
                  "source_url": "", "source_pubdate": "", "fetched_at": _now(), "status": "ok"})
    return rows


def load_csv(path, fields):
    import csv
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if set(fields) <= set(r)]


def save_csv(path, fields, rows):
    atomic_write_csv(path, fields, rows)


def _b1_row_key(r):
    return (int(r["iso_year"]), int(r["iso_week"]))


def upsert_b1(new, url, pubdate):
    """写入/比对单周 B1。同值更新 fetched_at；变值记 changes.log。返回状态 str。"""
    rows = load_csv(B1_CSV, B1_FIELDS)
    k = _b1_row_key(new)
    old = None
    rest = []
    for r in rows:
        if _b1_row_key(r) == k:
            old = r
        else:
            rest.append(r)
    if old is not None:
        same = all(old[f] == new[f] for f in
                   ("week_start", "ili_pct", "flu_positive_pct", "sample_count", "positive_count"))
        if same:
            old["fetched_at"] = new["fetched_at"]
            old["source_url"], old["source_pubdate"] = url, pubdate
            old["status"] = "ok"
            merged = sorted(rest + [old], key=_b1_row_key)
            save_csv(B1_CSV, B1_FIELDS, merged)
            return "ok_same"
        log_change(f"{k[0]}W{k[1]}", "heilongjiang_flu",
                   f"ili={old['ili_pct']}/pos={old['flu_positive_pct']}/n={old['sample_count']}/{old['positive_count']}",
                   f"ili={new['ili_pct']}/pos={new['flu_positive_pct']}/n={new['sample_count']}/{new['positive_count']}")
    new = dict(new, source_url=url, source_pubdate=pubdate,
               fetched_at=new.get("fetched_at") or _now(), status="ok")
    merged = sorted(rest + [new], key=_b1_row_key)
    save_csv(B1_CSV, B1_FIELDS, merged)
    return "ok_new"


def replace_b2(rows, url, pubdate):
    """整周替换 B2 行（本次未提及项移除）。返回替换行数。

    变化留痕（复核 IMP-13）：新旧集合不同必须记 changes.log（上游修订/选项删除可审计）。
    """
    existing = load_csv(B2_CSV, B2_FIELDS)
    k = (int(rows[0]["iso_year"]), int(rows[0]["iso_week"]))
    old_week = sorted((r for r in existing
                       if (int(r["iso_year"]), int(r["iso_week"])) == k),
                      key=lambda r: (r["setting"], r["pathogen"]))
    kept = [r for r in existing if (int(r["iso_year"]), int(r["iso_week"])) != k]
    out = []
    for r in rows:
        r = dict(r, source_url=url, source_pubdate=pubdate)
        out.append(r)
    merged = sorted(kept + out, key=lambda r: (int(r["iso_year"]), int(r["iso_week"]),
                                               r["setting"], r["pathogen"]))
    if old_week:
        # 签名必须涵盖全部结构化观测数值（复核 IMP-13 round-2）：
        # 只比 setting+pathogen+阳性率会漏掉标本数/总数修订（无痕覆盖），
        # 因此 sample_count 与 total_samples 一并纳入
        sig = lambda rs: ";".join(
            f"{r['setting']}{r['pathogen']}={r['positive_pct']}"
            f"({r.get('sample_count')}/{r.get('total_samples')})"
            for r in sorted(rs, key=lambda r: (r["setting"], r["pathogen"])))
        if sig(old_week) != sig(out):
            log_change(f"{k[0]}W{k[1]}", "heilongjiang_sentinel",
                       sig(old_week), sig(out))
    save_csv(B2_CSV, B2_FIELDS, merged)
    return len(out)


def fetch_article(url):
    html = http_get(url)
    if isinstance(html, bytes):
        html = html.decode("utf-8", "replace")
    return extract_article(html)


def _dedupe_week(cands):
    """同周多篇：全同值→(source_pubdate, url) 确定性代表；不同值→None（冲突）。"""
    if not cands:
        return None
    first = cands[0]
    for c in cands[1:]:
        if any(c["row"][f] != first["row"][f] for f in
               ("week_start", "ili_pct", "flu_positive_pct", "sample_count", "positive_count")):
            return None
    return sorted(cands, key=lambda c: (c["pubdate"], c["url"]))[0]


def _b2_sig(rows):
    """B2 一期的规范化签名（复核 IMP-08/13）：涵盖全部结构化观测数值。"""
    return ";".join(
        f"{r['setting']}{r['pathogen']}={r['positive_pct']}"
        f"({r.get('sample_count')}/{r.get('total_samples')})"
        for r in sorted(rows, key=lambda r: (r["setting"], r["pathogen"])))


def _pick_b2(items):
    """B2 同周多篇规范化选择（复核 IMP-08 round-2/3）。

    解析最新标题周次的全部候选：全同值→确定性代表（pubdate,url 最小）；
    异值→conflict（本轮失败，保全旧成功表，不按列表顺序取第一篇覆盖）。
    round-3 修正：候选筛选先确定目标周——不能排除「属于目标周或更新周」的
    候选解析失败时，整期失败保全，不得从成功集合倒退选旧周宣称成功。
    返回 {"status": "none"|"ok"|"conflict"|"failed", "rep", "rows",
    "week", "n", "errors"}。
    """
    b2_items = [it for it in items if it["kind"] == "b2"]
    if not b2_items:
        return {"status": "none", "errors": []}

    def _tw(it):
        m = TITLE_WEEK.search(it["title"])
        return (int(m.group(1)), int(m.group(2))) if m else None

    # 候选筛选：标题周次明确早于最新标题周的跳过（省正文请求）；
    # 标题不可解析者无法排除，必须解析后按正文周次归位。
    # 复核修正：守卫按「正文周次」分组比对，不能按标题周次——
    # 标题不可解析时曾把不同周的文章放进同一集合比签名，必然伪冲突。
    tws = [_tw(it) for it in b2_items]
    known = [t for t in tws if t is not None]
    newest_title = max(known) if known else None
    cand_items = [it for it, t in zip(b2_items, tws)
                  if t is None or t == newest_title]
    parsed = []
    errors = []
    for it in cand_items:
        try:
            p = parse_one(it)
        except Exception as e:
            errors.append((it, f"{type(e).__name__}: {e}"))
            continue
        parsed.append({"item": it, "rows": p["rows"],
                       "pubdate": p["pubdate"] or it["date"]})
    # round-3 复核 IMP-08 NEW-BY-FIX：cand_items 里的每个候选都无法排除
    # 「属于目标周或更新周」（标题==最新周，或标题不可解析），任何解析
    # 失败都使目标周不可知——整期失败保全，绝不从成功集合倒退选周。
    if errors:
        if not parsed:
            reason = f"最新 B2 候选全部解析失败（{errors[0][1]}）"
        else:
            err_desc = "；".join(
                f"{it['id']}({e})" for it, e in errors[:5])
            reason = (f"候选解析失败，无法确认最新周，"
                      f"本轮失败保全旧值：{err_desc}")
        return {"status": "failed", "reason": reason, "errors": errors}
    if not parsed:
        return {"status": "none", "errors": errors}
    for c in parsed:
        c["week"] = (int(c["rows"][0]["iso_year"]),
                     int(c["rows"][0]["iso_week"]))
    week = max(c["week"] for c in parsed)
    same_week = [c for c in parsed if c["week"] == week]
    sigs = {_b2_sig(c["rows"]) for c in same_week}
    if len(sigs) > 1:
        return {"status": "conflict", "week": week, "n": len(same_week),
                "errors": errors}
    rep = sorted(same_week, key=lambda c: (c["pubdate"], c["item"]["url"]))[0]
    return {"status": "ok", "rep": rep, "rows": rep["rows"], "week": week,
            "n": len(same_week), "errors": errors}


def fetch_latest(products=("b1", "b2")):
    """最新一期 B1 + B2（列表第 1 页发现）。返回结果 dict。

    products（复核 IMP-11）：只抓指定产品，未请求的产品保持 unknown（不联网、不写表）。
    产品级故障隔离（复核 IMP-09）：任一产品的网络/解析异常不阻断另一产品。
    """
    results = {"heilongjiang_flu": {"status": "unknown"},
               "heilongjiang_sentinel": {"status": "unknown"}}
    try:
        items = list_items(1)
    except Exception as e:  # 网络层异常：两个产品都无法发现，整组失败但不抛出
        for v in results.values():
            v.update(status="failed", reason=f"列表页获取异常 {type(e).__name__}: {e}")
        return results
    if items is None:
        for v in results.values():
            v.update(status="failed", reason="列表页获取失败")
        return results

    # B1：第 1 页最新的 B1 候选 + 同周其他篇
    if "b1" not in products:
        results["heilongjiang_flu"]["reason"] = "未在本轮请求范围（--products）"
    else:
        try:
            _fetch_latest_b1(items, results)
        except Exception as e:  # B1 任何意外不阻断 B2（复核 IMP-09）
            results["heilongjiang_flu"].update(
                status="failed", reason=f"{type(e).__name__}: {e}")

    # B2：列表顺序第一篇 B2 = 最新
    if "b2" not in products:
        results["heilongjiang_sentinel"]["reason"] = "未在本轮请求范围（--products）"
    else:
        try:
            _fetch_latest_b2(items, results)
        except Exception as e:
            results["heilongjiang_sentinel"].update(
                status="failed", reason=f"{type(e).__name__}: {e}")

    return results


def _fetch_latest_b1(items, results):
    b1_cands_idx = [i for i, it in enumerate(items) if it["kind"] == "b1"]
    if not b1_cands_idx:
        results["heilongjiang_flu"].update(status="failed", reason="列表页未发现流感监测周报")
        return
    i0 = b1_cands_idx[0]
    try:
        parsed = parse_one(items[i0])
    except RuntimeError as e:
        results["heilongjiang_flu"].update(status="failed", reason=str(e))
        log_change("latest", "heilongjiang_flu", "无变更", f"失败：{e}")
        parsed = None
    if parsed:
        week = (parsed["row"]["iso_year"], parsed["row"]["iso_week"])
        cands = [{"row": parsed["row"], "url": items[i0]["url"], "pubdate": items[i0]["date"]}]
        for j in b1_cands_idx[1:]:
            try:
                p2 = parse_one(items[j])
            except RuntimeError:
                continue
            if p2 and (p2["row"]["iso_year"], p2["row"]["iso_week"]) == week:
                cands.append({"row": p2["row"], "url": items[j]["url"], "pubdate": items[j]["date"]})
        rep = _dedupe_week(cands)
        if rep is None:
            results["heilongjiang_flu"].update(status="failed", reason=f"同周 {week} 多篇数值冲突")
            log_change(f"{week[0]}W{week[1]}", "heilongjiang_flu", "无变更", "失败：同周多篇数值冲突")
        else:
            st = upsert_b1(rep["row"], rep["url"], rep["pubdate"])
            if len(cands) > 1:
                log_change(f"{week[0]}W{week[1]}", "heilongjiang_flu", "无变更",
                           f"同周 {len(cands)} 篇同值，确定性代表 {rep['url']}")
            results["heilongjiang_flu"].update(status="ok", week=f"{week[0]}W{week[1]}", write=st)


def _fetch_latest_b2(items, results):
    # 同周多篇规范化比较（复核 IMP-08 round-2/3）：不再只取列表第一篇
    pick = _pick_b2(items)
    if pick["status"] == "none":
        if pick["errors"]:
            reason = f"最新 B2 候选全部解析失败（{pick['errors'][0][1]}）"
            log_change("latest", "heilongjiang_sentinel", "无变更", f"失败：{reason}")
        else:
            reason = "列表页未发现急性呼吸道哨点监测周报"
        results["heilongjiang_sentinel"].update(status="failed", reason=reason)
        return
    if pick["status"] == "failed":
        # round-3 IMP-08 NEW-BY-FIX：候选解析失败→目标周不可知，整期失败保全
        msg = pick["reason"]
        results["heilongjiang_sentinel"].update(status="failed", reason=msg)
        log_change("latest", "heilongjiang_sentinel", "无变更", f"失败：{msg}")
        return
    if pick["status"] == "conflict":
        wk = pick["week"]
        msg = f"同周 {wk[0]}W{wk[1]} 多篇 B2 数值冲突，本轮失败保留旧值"
        results["heilongjiang_sentinel"].update(status="failed", reason=msg)
        log_change(f"{wk[0]}W{wk[1]}", "heilongjiang_sentinel", "无变更", f"失败：{msg}")
        return
    rep, rows = pick["rep"], pick["rows"]
    n = replace_b2(rows, rep["item"]["url"], rep["pubdate"])
    if pick["n"] > 1:
        log_change(f"{rows[0]['iso_year']}W{rows[0]['iso_week']}",
                   "heilongjiang_sentinel", "无变更",
                   f"同周 {pick['n']} 篇同值，确定性代表 {rep['item']['url']}")
    results["heilongjiang_sentinel"].update(
        status="ok", week=f"{rows[0]['iso_year']}W{rows[0]['iso_week']}", rows=n)


def parse_one(item):
    """取单篇文章并按类型解析。返回 {'kind','row'|'rows','title','pubdate'} 或抛 RuntimeError。"""
    # 复核 IMP-09 round-3：fetch_article 失败返回 None，解包先于检查会 TypeError
    got = fetch_article(item["url"])
    if not got:
        raise RuntimeError("parse_error: 未找到正文容器 article.about1")
    title, pubdate, body = got
    kind = classify(title or item["title"])
    if kind != item["kind"]:
        raise RuntimeError(f"parse_error: 标题分类与列表不符（{title!r}）")
    if kind == "b1":
        return {"kind": "b1", "row": parse_b1(title, body), "title": title, "pubdate": pubdate}
    return {"kind": "b2", "rows": parse_b2(title, body), "title": title, "pubdate": pubdate}


def list_items(pageno):
    """列表页 → 条目列表 [{'id','title','date','url','kind'}]；获取失败返回 None。"""
    url = LIST_URL + ("" if pageno <= 1 else f"&pageno={pageno}")
    html = http_get(url)
    if isinstance(html, bytes):
        html = html.decode("utf-8", "replace")
    if not html:
        return None
    items = []
    for pat in (LIST_ITEM, LIST_ITEM_RAW):
        for m in pat.finditer(html):
            aid, title, d = m.group(1), m.group(2).strip(), m.group(3)
            kind = classify(title)
            if kind is None:
                continue
            items.append({"id": aid, "title": title, "date": d, "kind": kind,
                          "url": ART_BASE + f"index.php?c=zixundetail&a=index&id={aid}&lid=120"})
        if items:
            break
    if not items and ("news1" not in html):
        # 容器仍在但一条目都没有 = 列表结构异常（复核 IMP-09）；
        # 容器消失 = 不能确认是正常列表页（验证码/维护/改版同样无容器），
        # 一律按获取失败返回 None，由调用方判 failed，不当作"越过末页"。
        return None
    return items


def _expected_weeks(lo, hi):
    out = []
    y, w = lo
    while (y, w) <= hi:
        out.append((y, w))
        try:
            nxt = date.fromisocalendar(y, w, 1) + timedelta(days=7)
        except ValueError:
            break
        y, w = nxt.isocalendar()[0], nxt.isocalendar()[1]
    return out


def backfill(limit=None, force=False, from_w=None, products=("b1", "b2")):
    """B1 回补：遍历列表到 2025-01-01 之前；同周多篇按同值代表/冲突失败。

    from_w（复核 IMP-11）：`--from 2025W10` 指定起点，不得早于 2025W1。
    products：b2 不在范围时跳过 B2 抓取（保持 unknown）。
    """
    results = {"heilongjiang_flu": {"status": "unknown"}, "heilongjiang_sentinel": {"status": "unknown"}}
    if from_w is None:
        from_w = BACKFILL_FROM
    # 产品门控（复核 IMP-11 round-2）：--products b2 时不做 B1 分页遍历/解析/写入
    if "b1" not in products:
        results["heilongjiang_flu"]["reason"] = "未在本轮请求范围（--products）"
        if "b2" in products:
            results["heilongjiang_sentinel"] = fetch_latest_b2_only(None)
        else:
            results["heilongjiang_sentinel"]["reason"] = "未在本轮请求范围（--products）"
        return results
    all_items = []
    seen_pages = set()
    last_content = None
    stopped = False
    empty_streak = 0
    for pno in range(1, MAX_PAGES + 1):
        url = LIST_URL + ("" if pno <= 1 else f"&pageno={pno}")
        html = http_get(url)
        if isinstance(html, bytes):
            html = html.decode("utf-8", "replace")
        if not html:
            results["heilongjiang_flu"].update(status="failed", reason=f"第 {pno} 页内容异常/为空")
            return results
        if "news1" not in html:
            # 复核 IMP-09 round-3：容器消失不能证明越过末页——验证码/维护/改版页
            # 同样没有容器，且短错误响应（Bad Gateway/Access denied）也满足
            # 「无容器且短」，长度不是终点证据。可验证的停止依据只有已验证的
            # 日期边界（BACKFILL_CUTOFF，见下方整页日期判断）。到达无容器页
            # 一律按发现失败处理，不静默当正常终点。
            results["heilongjiang_flu"].update(
                status="failed",
                reason=f"第 {pno} 页无列表容器（疑似验证码/维护/改版或越过末页），"
                       "不能确认为正常终点")
            return results
        if html == last_content:
            results["heilongjiang_flu"].update(status="failed", reason=f"第 {pno} 页与上一页重复")
            return results
        last_content = html
        seen_pages.add(pno)
        page_items = []
        page_dates = []
        raw_count = 0
        for pat in (LIST_ITEM, LIST_ITEM_RAW):
            hits = list(pat.finditer(html))
            raw_count = max(raw_count, len(hits))
            for m in hits:
                aid, title, d = m.group(1), m.group(2).strip(), m.group(3)
                page_dates.append(d)
                kind = classify(title)
                if kind is None:
                    continue
                page_items.append({"id": aid, "title": title, "date": d, "kind": kind,
                                   "url": ART_BASE + f"index.php?c=zixundetail&a=index&id={aid}&lid=120",
                                   "page": pno})
            if page_items:
                break
        if raw_count == 0:
            # 容器仍在但整页 0 条目 = 列表结构异常（标题/版式变化），不是终点（复核 IMP-09）；
            # 真正越过最后一页的表现是 news1 容器消失，已在上面 stopped 处理。
            results["heilongjiang_flu"].update(
                status="failed",
                reason=f"第 {pno} 页容器仍在但无任何条目（疑似列表结构变化）")
            return results
        # 该页全部条目（含非周报文章）的日期都已早于下界 → 已翻过目标窗口。
        # 必须用整页日期而非候选日期判断：2025W1 之后列表页可能整页都是非周报文章
        # （实测第 23-39 页均为 2024 年底及更早），只看候选会一路翻到古早页。
        if max(page_dates) < BACKFILL_CUTOFF:
            stopped = True
            break
        if not page_items:
            # 该页整页都是非周报文章属正常现象（实测第 5、6、12-14 页），继续翻页；
            # 只有连续多页无候选才判结构异常（标题格式变化会让每页候选都为 0）。
            empty_streak += 1
            if empty_streak >= MAX_EMPTY_STREAK:
                results["heilongjiang_flu"].update(
                    status="failed", reason=f"连续 {empty_streak} 页无候选条目（疑似标题格式变化）")
                return results
            time.sleep(RATE_LIMIT)
            continue
        empty_streak = 0
        all_items.extend(page_items)
        if limit and len([i for i in all_items if i["kind"] == "b1"]) >= limit:
            stopped = True
            break
        time.sleep(RATE_LIMIT)
    if not stopped and len(seen_pages) >= MAX_PAGES:
        results["heilongjiang_flu"].update(status="failed", reason=f"分页超过硬上界 {MAX_PAGES} 页")
        return results

    # 按 id 去重（跨页重复发布）
    by_id = {}
    for it in all_items:
        if it["id"] not in by_id:
            by_id[it["id"]] = it
    b1_items = [i for i in by_id.values() if i["kind"] == "b1"]
    b2_items = [i for i in by_id.values() if i["kind"] == "b2"]

    # 逐周解析（一周多篇成组）
    weeks = {}
    err_by_week = {}
    for it in b1_items:
        try:
            p = parse_one(it)
        except Exception as e:  # RuntimeError 与意外异常都隔离（复核 IMP-09 round-2）
            it["error"] = f"{type(e).__name__}: {e}"
            # 解析失败的条目仍按标题里的周次归位，避免误报成"列表未发现"
            wk = None
            tm = TITLE_WEEK.search(it["title"])
            if tm:
                wk = (int(tm.group(1)), int(tm.group(2)))
            else:
                rm = WEEK_RANGE.search(it["title"])
                if rm:
                    wk = (int(rm.group(1)), int(rm.group(2)))
            if wk:
                err_by_week.setdefault(wk, []).append({"id": it["id"], "error": str(e)})
            continue
        row = p["row"]
        weeks.setdefault((row["iso_year"], row["iso_week"]), []).append(
            {"row": row, "url": it["url"], "pubdate": p["pubdate"] or it["date"]})
        time.sleep(RATE_LIMIT)

    if not weeks and not err_by_week:
        results["heilongjiang_flu"].update(status="failed", reason="列表未解析到任何 B1 周报")
        return results
    # 对账上界包含"已发现但解析失败"的周（复核 IMP-09）：
    # 最新期解析失败时不能把它排除在覆盖报告外，否则会误缩目标区间
    hi = max(set(weeks) | set(err_by_week))
    expected = [k for k in _expected_weeks(from_w, hi) if k <= hi]
    existing = {_b1_row_key(r): r for r in load_csv(B1_CSV, B1_FIELDS)}

    counts = {"ok": 0, "ok_same": 0, "conflict": 0, "parse_fail": 0, "skip_existing": 0}
    pending_fail = []
    for k in expected:
        cands = weeks.get(k)
        if not cands:
            if k in err_by_week:
                counts["parse_fail"] += 1
                pending_fail.append(
                    f"{k[0]}W{k[1]}: 解析失败（{err_by_week[k][0]['error']}）")
            else:
                pending_fail.append(f"{k[0]}W{k[1]}: list_missing（列表未发现该周 B1 文章）")
            continue
        rep = _dedupe_week(cands)
        if rep is None:
            counts["conflict"] += 1
            pending_fail.append(f"{k[0]}W{k[1]}: 同周多篇数值冲突，本轮失败保留旧值")
            log_change(f"{k[0]}W{k[1]}", "heilongjiang_flu", "", "回补失败：同周多篇数值冲突")
            continue
        if k in existing and not force:
            counts["skip_existing"] += 1
            continue
        st = upsert_b1(rep["row"], rep["url"], rep["pubdate"])
        if len(cands) > 1:
            log_change(f"{k[0]}W{k[1]}", "heilongjiang_flu", "",
                       f"同周 {len(cands)} 篇同值，确定性代表 {rep['url']}")
        counts["ok" if st == "ok_new" else "ok_same"] += 1
    # 列表里发现但不落在目标区间的周（如早于 2025W1）如实记录
    extra = [k for k in weeks if k < BACKFILL_FROM]

    ok_all = counts["ok"] + counts["ok_same"] + counts["skip_existing"]
    print(f"[B1 回补对账] 目标 {len(expected)} 周：ok={counts['ok']} ok_same={counts['ok_same']} "
          f"skip_existing={counts['skip_existing']} conflict={counts['conflict']} "
          f"parse_fail={counts['parse_fail']} "
          f"list_missing={sum('list_missing' in p for p in pending_fail)}")
    for p in pending_fail:
        print("  [未入库]", p)
    if extra:
        print(f"  [范围外发现] {sorted(extra)}（不入库，不宣称更早覆盖）")
    b1_status = "ok" if ok_all == len(expected) else "partial"
    results["heilongjiang_flu"].update(status=b1_status, counts=counts,
                                        target=f"{from_w[0]}W{from_w[1]}..{hi[0]}W{hi[1]}")

    # 回补模式下 B2 仍只取最新（复核 IMP-11：--products b1 时跳过，不联网不写表）
    if "b2" in products:
        b2r = fetch_latest_b2_only(b2_items)
        results["heilongjiang_sentinel"] = b2r
    else:
        results["heilongjiang_sentinel"]["reason"] = "未在本轮请求范围（--products）"
    return results


def fetch_latest_b2_only(b2_items=None):
    if b2_items is None:
        items = list_items(1)
        if items is None:
            return {"status": "failed", "reason": "列表页获取失败"}
    else:
        items = b2_items
    # 同周多篇规范化比较（复核 IMP-08 round-2/3）：与最新入口同一套守卫
    pick = _pick_b2(items)
    if pick["status"] == "none":
        if pick["errors"]:
            reason = f"最新 B2 候选全部解析失败（{pick['errors'][0][1]}）"
            log_change("latest", "heilongjiang_sentinel", "无变更", f"失败：{reason}")
            return {"status": "failed", "reason": reason}
        return {"status": "failed", "reason": "未发现 B2 文章"}
    if pick["status"] == "failed":
        # round-3 IMP-08 NEW-BY-FIX：候选解析失败→目标周不可知，整期失败保全
        msg = pick["reason"]
        log_change("latest", "heilongjiang_sentinel", "无变更", f"失败：{msg}")
        return {"status": "failed", "reason": msg}
    if pick["status"] == "conflict":
        wk = pick["week"]
        msg = f"同周 {wk[0]}W{wk[1]} 多篇 B2 数值冲突，本轮失败保留旧值"
        log_change(f"{wk[0]}W{wk[1]}", "heilongjiang_sentinel", "无变更", f"失败：{msg}")
        return {"status": "failed", "reason": msg}
    rep, rows = pick["rep"], pick["rows"]
    n = replace_b2(rows, rep["item"]["url"], rep["pubdate"])
    if pick["n"] > 1:
        log_change(f"{rows[0]['iso_year']}W{rows[0]['iso_week']}",
                   "heilongjiang_sentinel", "无变更",
                   f"同周 {pick['n']} 篇同值，确定性代表 {rep['item']['url']}")
    return {"status": "ok",
            "week": f"{rows[0]['iso_year']}W{rows[0]['iso_week']}", "rows": n}


def write_result_file(path, run_id, results):
    import json
    from data_io import atomic_write_json
    atomic_write_json(Path(path), {"schema": 2, "stage": "fetch", "run_id": run_id,
                                   "sources": results})


def main(argv):
    result_file = run_id = None
    mode = "latest"
    force = False
    limit = None
    write_url = None
    products = ("b1", "b2")
    from_w = None
    probe_url = None

    def _val(argv, i, opt):
        # 复核 IMP-11 round-3：缺值/把下一个选项当值（如 --result-file --force）
        # 必须在联网前拒绝，不能把 "--force" 当文件名静默进入抓取
        v = argv[i] if i < len(argv) else ""
        if not v or v.startswith("--"):
            print(f"用法：{opt} <值>（缺值或值是另一个选项）", file=sys.stderr)
            return None
        return v

    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--backfill":
            mode = "backfill"
        elif a == "--force":
            force = True
        elif a == "--products":
            i += 1
            raw = _val(argv, i, "--products")
            if raw is None:
                return 2
            # 别名兼容（复核 IMP-11 round-2）：冻结计划 :205-206 用 flu/sentinel 命名
            alias = {"flu": "b1", "sentinel": "b2"}
            got = [alias.get(x.strip(), x.strip()) for x in raw.split(",") if x.strip()]
            if not got or any(x not in ("b1", "b2") for x in got):
                print("用法：--products b1|b2|b1,b2（别名 flu|sentinel）", file=sys.stderr)
                return 2
            products = tuple(dict.fromkeys(got))
        elif a == "--from":
            i += 1
            raw = _val(argv, i, "--from")
            if raw is None:
                return 2
            m = re.fullmatch(r"(\d{4})[wW](\d{1,2})", raw)
            if not m:
                print("用法：--from YYYYWnn（如 2025W10）", file=sys.stderr)
                return 2
            wk = (int(m.group(1)), int(m.group(2)))
            try:
                # ISO 历法校验（复核 IMP-11 round-2）：2025W53/2026W99 这类
                # 不存在的周不能只靠大小比较放行
                date.fromisocalendar(wk[0], wk[1], 1)
            except ValueError:
                print(f"周次不存在：{wk[0]} 年没有第 {wk[1]} 周（ISO 历法校验失败）",
                      file=sys.stderr)
                return 2
            if wk < BACKFILL_FROM:
                print(f"--from 不得早于 {BACKFILL_FROM[0]}W{BACKFILL_FROM[1]}"
                      f"（B1 官方栏目回补下界）", file=sys.stderr)
                return 2
            from_w = wk
        elif a == "--limit":
            i += 1
            raw = _val(argv, i, "--limit")
            if raw is None or not raw.isdigit() or int(raw) <= 0:
                print("用法：--limit N（正整数）", file=sys.stderr)
                return 2
            limit = int(raw)
        elif a == "--result-file":
            i += 1
            raw = _val(argv, i, "--result-file")
            if raw is None:
                return 2
            result_file = raw
        elif a == "--run-id":
            i += 1
            raw = _val(argv, i, "--run-id")
            if raw is None:
                return 2
            run_id = raw
        elif a == "--write-url":
            i += 1
            # 缺值必须拒绝（复核 IMP-11 round-2）：不能静默落入默认抓取
            raw = _val(argv, i, "--write-url")
            if raw is None or not raw.startswith("http"):
                print("用法：--write-url <文章URL>（缺值或非 URL）", file=sys.stderr)
                return 2
            write_url = raw
        elif a.startswith("--"):
            print(f"未知参数：{a}\n用法见文件头注释", file=sys.stderr)
            return 2
        else:
            probe_url = a  # 位置参数 = 只读抽验 URL（打印解析结果，不写任何 CSV）
        i += 1

    if probe_url:
        # 只读抽验（复核 IMP-11）：抓单篇 → 分类 → 解析 → 打印，不写 CSV/不写日志
        try:
            title, pubdate, body = fetch_article(probe_url)
            if title is None:
                print("失败：未找到正文容器", file=sys.stderr)
                return 1
            kind = classify(title)
            print(f"[抽验] 标题：{title}")
            print(f"[抽验] 发布时间：{pubdate or '（页面未标注）'}  分类：{kind}")
            if kind == "b1":
                row = parse_b1(title, body)
                print(f"[抽验] B1 {row['iso_year']}W{row['iso_week']} ILI={row['ili_pct']}% "
                      f"阳性率={row['flu_positive_pct']}%（{row['positive_count']}/{row['sample_count']}）"
                      f" week_start={row['week_start']}")
            elif kind == "b2":
                rows = parse_b2(title, body)
                print(f"[抽验] B2 {rows[0]['iso_year']}W{rows[0]['iso_week']} 共 {len(rows)} 行：")
                for r in rows:
                    print(f"  {r['setting']} {r['pathogen']} {r['positive_pct']}%"
                          f"（{r['sample_count']} 份组）")
            else:
                print(f"失败：标题无法分类 {title!r}", file=sys.stderr)
                return 1
            print("[抽验] 只读模式：未写入任何数据")
            return 0
        except RuntimeError as e:
            print(f"失败：{e}", file=sys.stderr)
            return 1

    if write_url:
        # 人工消歧：单篇强制按内容校验入库（B1 单周 upsert / B2 整周替换）
        title, pubdate, body = fetch_article(write_url)
        if title is None:
            print("失败：未找到正文容器", file=sys.stderr)
            return 1
        kind = classify(title)
        if kind == "b1":
            row = parse_b1(title, body)
            st = upsert_b1(row, write_url, pubdate)
            print(f"[write-url B1] {row['iso_year']}W{row['iso_week']} {st}")
            ok = True
        elif kind == "b2":
            rows = parse_b2(title, body)
            n = replace_b2(rows, write_url, pubdate)
            print(f"[write-url B2] {rows[0]['iso_year']}W{rows[0]['iso_week']} 共 {n} 行")
            ok = True
        else:
            print(f"失败：标题无法分类 {title!r}", file=sys.stderr)
            ok = False
        if result_file:
            write_result_file(result_file, run_id or "manual",
                              {"heilongjiang_flu": {"status": "ok" if ok else "failed"},
                               "heilongjiang_sentinel": {"status": "unknown"}})
        return 0 if ok else 1

    if mode == "backfill":
        results = backfill(limit=limit, force=force, from_w=from_w, products=products)
    else:
        results = fetch_latest(products=products)
    if result_file:
        # 复核 IMP-11 round-3：结果文件只表达本次请求的产品——未请求的产品
        # 保持 unknown 属于内部完整性需要，写入结果文件会误导状态聚合方
        prod_keys = [key for p, key in
                     (("b1", "heilongjiang_flu"), ("b2", "heilongjiang_sentinel"))
                     if p in products]
        write_result_file(result_file, run_id or "manual",
                          {k: results[k] for k in prod_keys})
    print(f"[结果] heilongjiang_flu={results['heilongjiang_flu'].get('status')} "
          f"heilongjiang_sentinel={results['heilongjiang_sentinel'].get('status')}")
    # 退出码只按本轮请求的产品判定（复核 IMP-11 round-2）：
    # 未请求的产品保持 unknown（不联网、不写表），不能把整轮拖成 exit=1
    keys = (("b1", "heilongjiang_flu"), ("b2", "heilongjiang_sentinel"))
    all_ok = all(results[key].get("status") == "ok" for p, key in keys if p in products)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

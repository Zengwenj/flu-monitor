# -*- coding: utf-8 -*-
"""抓取中疾控《全国急性呼吸道传染病哨点监测情况》周报（HTML 正文三表），写两个 CSV。

M3a 契约（.trellis/tasks/11-06-data-fetch/design.md r2）：
- sentinel_national_rates.csv（表1长表）：每周 11病原×{门急诊,住院}=22 行
- sentinel_rank.csv（表2/3）：南北片+4年龄组前三名，并列存顿号串原样
- r3 周级覆盖〔B2〕：当周解析出完整 22 行（键唯一、数值有效）才覆盖旧行；
  任一缺失/重复/无效 → parse_failed，不覆盖旧周
- 不修改 M2 的任何文件

用法：
  python src/fetch_sentinel.py              # 抓最新一期（增量模式）
  python src/fetch_sentinel.py --backfill   # 遍历全部列表页回补历史（礼貌限速）
  python src/fetch_sentinel.py <文章URL>    # 抽验模式：解析打印不写 CSV
"""
import csv
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.chinacdc.cn/jksj/jksj04_14275/"
RATES_CSV = ROOT / "data" / "sentinel_national_rates.csv"
RANK_CSV = ROOT / "data" / "sentinel_rank.csv"
CHANGES_LOG = ROOT / "data" / "changes.log"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
DELAY = 2.5  # 礼貌限速（秒/请求）

PATHOGENS = ["新型冠状病毒", "流感病毒", "呼吸道合胞病毒", "腺病毒", "人偏肺病毒",
             "副流感病毒", "普通冠状病毒", "博卡病毒", "鼻病毒", "肠道病毒", "肺炎支原体"]
RATES_FIELDS = ["iso_year", "iso_week", "week_start", "setting", "pathogen",
                "positive_pct", "delta_last_week", "source_url", "source_pubdate",
                "fetched_at", "status"]
RANK_FIELDS = ["iso_year", "iso_week", "dimension", "category", "setting",
               "rank1", "rank2", "rank3", "source_url", "fetched_at", "status"]


def http_get(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise LookupError("404")  # 列表翻页终点，由调用方处理
        raise
    except Exception:
        pass
    import subprocess
    r = subprocess.run(["curl", "-s", "-A", UA["User-Agent"], url],
                       capture_output=True, timeout=120)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f"HTTP 获取失败: {url}")
    return r.stdout.decode("utf-8", "replace")


def list_issues(max_pages: int = 20) -> list:
    """遍历静态分页（首页 + index_N，404=终点），返回 [(art_url, title, pubdate)] 时间倒序。"""
    items, seen, page = [], set(), 0
    while page < max_pages:
        url = BASE if page == 0 else f"{BASE}index_{page}.html"
        try:
            html = http_get(url)
        except LookupError:
            break  # 翻页终点（404）
        found = re.findall(
            r'<a href="(\./20\d{4}/t\d+_\d+\.html?)"[^>]*>([^<]+)<span>\s*([\d-]+)', html)
        if not found:
            break
        new = 0
        for rel, title, pub in found:
            full = BASE + rel[2:]
            if full not in seen:
                seen.add(full)
                items.append((full, title.strip(), pub.strip()))
                new += 1
        if new == 0:
            break
        page += 1
        time.sleep(DELAY)
    return items


def issue_no(title: str) -> tuple:
    m = re.search(r"(\d{4})\s*年\s*第\s*(\d+)\s*周", title)
    if not m:
        raise RuntimeError(f"标题无期号: {title}")
    return int(m.group(1)), int(m.group(2))


def norm_num(s: str) -> str:
    return s.replace("%", "").replace("＋", "+").replace("－", "-").strip()


def parse_article(html: str, art_url: str, pub: str) -> dict:
    """解析三表。返回 {iso_year, iso_week, rates:[22行], ranks:[...] 或 None, rank_note}。
    ranks 解析失败（版式差异）不阻塞 rates——诚实降级：rank_note 记原因，入库占位行。"""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 3:
        raise RuntimeError(f"表格数 {len(tables)} != 3")

    def tds(tr):
        return [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]

    # --- 表1：11病原 × {门急诊, 住院} × [本周值, 较上周] ---
    rows1 = [tds(tr) for tr in tables[0].find_all("tr")]
    rates, seen_keys = [], set()
    for cells in rows1:
        vals = [c for c in cells if c]  # 去空列（2024 版有空 td）
        if len(vals) != 5:
            continue
        name, op, od, sp, sd = vals
        if name not in PATHOGENS:
            continue
        for setting, val, delta in (("门急诊", op, od), ("住院", sp, sd)):
            key = (setting, name)
            if key in seen_keys:
                raise RuntimeError(f"表1 重复键 {key}")
            seen_keys.add(key)
            if not re.fullmatch(r"[+-]?\d+(\.\d+)?", norm_num(val)):
                raise RuntimeError(f"表1 无效数值 {name}/{setting}: {val!r}")
            rates.append({"setting": setting, "pathogen": name,
                          "positive_pct": norm_num(val),
                          "delta_last_week": norm_num(delta) or "0"})
    if len(rates) != 22:
        raise RuntimeError(f"表1 完整性校验失败：{len(rates)}/22 行")

    # --- 表2/表3：版式差异容忍（如 W6/W12 表2+表3 同表且并列粘连）——失败不阻塞 rates ---
    ranks, rank_note = [], ""
    try:
        ranks = _parse_rank_tables(tables, tds)
    except RuntimeError as e:
        ranks, rank_note = None, str(e)

    m = re.search(r"(\d{4})\s*年\s*第\s*(\d+)\s*周", soup.get_text())
    if not m:
        raise RuntimeError("未解析到期号")
    iso_year, iso_week = int(m.group(1)), int(m.group(2))
    return {"iso_year": iso_year, "iso_week": iso_week, "rates": rates,
            "ranks": ranks, "rank_note": rank_note,
            "url": art_url, "pub": pub}


def _parse_rank_tables(tables, tds) -> list:
    ranks = []
    rows2 = [tds(tr) for tr in tables[1].find_all("tr")]
    for c in rows2:
        vals = [x for x in c if x]
        if len(vals) != 7 or vals[0] not in ("南方省份", "北方省份"):
            continue
        for setting, trio in (("门急诊", vals[1:4]), ("住院", vals[4:7])):
            ranks.append({"dimension": "region", "category": vals[0],
                          "setting": setting,
                          "rank1": trio[0], "rank2": trio[1], "rank3": trio[2]})
    if len(ranks) != 4:
        raise RuntimeError(f"表2 行数 {len(ranks)} != 4")

    rows3 = [tds(tr) for tr in tables[2].find_all("tr")]
    ages = ["0～4岁", "5～14岁", "15～59岁", "60岁及以上"]
    cur_age, rank_i = None, 0
    raw_age = []
    for c in rows3:
        vals = [x for x in c if x]
        if not vals:
            continue
        if vals[0] in ages:
            cur_age, rank_i = vals[0], 1
            vals = vals[1:]
        if cur_age is None or len(vals) < 2:
            continue
        trio = {}
        for setting, v in (("门急诊", vals[0]), ("住院", vals[-1])):
            trio[setting] = v
        for setting in ("门急诊", "住院"):
            raw_age.append({"dimension": "age", "category": cur_age,
                            "setting": setting,
                            f"rank{rank_i}": trio[setting]})
        rank_i += 1
        if rank_i > 3:
            cur_age = None
    merged = {}
    for r in raw_age:
        k = (r["category"], r["setting"])
        merged.setdefault(k, {"dimension": "age", "category": r["category"],
                              "setting": r["setting"]})
        for i in (1, 2, 3):
            if f"rank{i}" in r:
                merged[k][f"rank{i}"] = r[f"rank{i}"]
    age_rows = list(merged.values())
    if len(age_rows) != 8:
        raise RuntimeError(f"表3 行数 {len(age_rows)} != 8")
    for r in age_rows:
        if not all(r.get(f"rank{i}") for i in (1, 2, 3)):
            raise RuntimeError(f"表3 {r['category']}/{r['setting']} 名次不全")
    return ranks + age_rows


def parse_merged(html: str, art_url: str, pub: str) -> list:
    """合并版（月度多篇，如'2025年4月，第14周—18周'）：表1为 病原体×多周 宽表。
    返回 [{iso_year, iso_week, rates:[22行]}...]；delta_last_week 置空。
    合并版表2/3 归属周次语义不明，不入库（调用方记 changes.log）。"""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 1:
        raise RuntimeError("合并版无表格")
    trs = tables[0].find_all("tr")
    tds = lambda tr: [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
    head2 = tds(trs[1]) if len(trs) > 1 else []
    weeks = [w for w in head2 if re.fullmatch(r"第\d+周", w)]
    if len(weeks) < 4 or len(weeks) % 2:
        raise RuntimeError(f"非合并版表1（周头 {len(weeks)} 个）")
    wn = [int(w[1:-1]) for w in weeks]
    half = len(wn) // 2  # 表头含两场景各 half 个周头（门诊 half + 住院 half）
    out = {w: [] for w in wn}
    for tr in trs[2:]:
        vals = [c for c in tds(tr) if c]
        if not vals or vals[0] not in PATHOGENS:
            continue
        name = vals[0]
        nums = vals[1:]
        if len(nums) < half * 2:  # 个别病原某周缺值 → 整行跳过，该周行数校验兜底
            log_change("merged", f"行缺值 {name}", str(len(nums)), f"需{half*2}")
            continue
        for i, w in enumerate(wn[:half]):  # 只遍历门诊段周头；住院段同周次取 half+i
            out[w].append({"setting": "门急诊", "pathogen": name,
                           "positive_pct": norm_num(nums[i]),
                           "delta_last_week": ""})
            out[w].append({"setting": "住院", "pathogen": name,
                           "positive_pct": norm_num(nums[half + i]),
                           "delta_last_week": ""})
    m = re.search(r"(\d{4})\s*年\s*\d+\s*月", soup.get_text())
    if not m:
        raise RuntimeError("合并版无年份")
    year = int(m.group(1))
    results = []
    for w in wn:
        if len(out[w]) != 22:
            log_change("merged", f"W{w} 行数不足", str(len(out[w])), "22，该周不入库")
            print(f"[warn] 合并版 W{w} 行数 {len(out[w])}/22，跳过", file=sys.stderr)
            continue
        results.append({"iso_year": year, "iso_week": w, "rates": out[w],
                        "ranks": None,
                        "rank_note": "合并版(月度)，表2/3归属周次语义不明不入库",
                        "url": art_url, "pub": pub})
    if not results:
        raise RuntimeError("合并版无完整周可入库")
    return results


def load(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save(p: Path, rows: list, fields: list) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def log_change(week: str, which: str, old: str, new: str) -> None:
    ts = datetime.now().isoformat(timespec="seconds")
    with CHANGES_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\t{week}\t{which}\t{old}\t{new}\n")


def write_week(res: dict) -> None:
    """r3 周级覆盖：22 行校验已在 parse_article 完成；写前比对旧行留痕。"""
    if len(res["rates"]) != 22:  # 防御纵深：绕过 parse 的调用同样拦截
        raise RuntimeError(f"write_week 拒绝：{len(res['rates'])}/22 行")
    now = datetime.now().isoformat(timespec="seconds")
    y, w = res["iso_year"], res["iso_week"]
    wk = f"{y}W{w}"

    old_rates = load(RATES_CSV)
    keep = [r for r in old_rates if not (int(r["iso_year"]) == y and int(r["iso_week"]) == w)]
    if len(keep) != len(old_rates):  # 覆盖已有周 → 留痕差异
        om = {(r["setting"], r["pathogen"]): r["positive_pct"] for r in old_rates
              if int(r["iso_year"]) == y and int(r["iso_week"]) == w}
        for nr in res["rates"]:
            ov = om.get((nr["setting"], nr["pathogen"]))
            if ov is not None and ov != nr["positive_pct"]:
                log_change(wk, f"rates {nr['setting']}/{nr['pathogen']}", ov, nr["positive_pct"])
    for nr in res["rates"]:
        keep.append({"iso_year": y, "iso_week": w, "week_start": "", **nr,
                     "source_url": res["url"], "source_pubdate": res["pub"],
                     "fetched_at": now, "status": "ok"})
    save(RATES_CSV, keep, RATES_FIELDS)

    old_ranks = load(RANK_CSV)
    keep2 = [r for r in old_ranks if not (int(r["iso_year"]) == y and int(r["iso_week"]) == w)]
    if res.get("ranks"):
        for nr in res["ranks"]:
            keep2.append({"iso_year": y, "iso_week": w, **nr,
                          "source_url": res["url"], "fetched_at": now, "status": "ok"})
    else:  # 诚实降级：排序版式差异不入库，写占位行显式标记"未提供"
        keep2.append({"iso_year": y, "iso_week": w, "dimension": "region",
                      "category": "全部", "setting": "全部",
                      "rank1": "官方该期版式差异，排序未解析", "rank2": "",
                      "rank3": "", "source_url": res["url"], "fetched_at": now,
                      "status": "rank_unavailable"})
        log_change(wk, "ranks", "版式差异", res.get("rank_note", "未解析"))
    save(RANK_CSV, keep2, RANK_FIELDS)
    print(f"[ok] {wk}: rates 22 行 + ranks "
          f"{len(res['ranks']) if res.get('ranks') else '未提供(占位)'}")


def fetch_one(art_url: str, pub: str = "", write: bool = True) -> dict:
    res = parse_article(http_get(art_url), art_url, pub)
    if write:
        write_week(res)
    return res


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--merge":
        for res in parse_merged(http_get(sys.argv[2]), sys.argv[2], ""):
            write_week(res)
    elif len(sys.argv) > 1 and sys.argv[1] == "--write-url":
        # 指定文章 URL 直接入库（用于个别漏抓期，如 W6/W12）
        fetch_one(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
    elif len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        res = fetch_one(sys.argv[1], write=False)
        print("周次:", res["iso_year"], "W", res["iso_week"])
        print("rates 首末:", res["rates"][0], res["rates"][-1])
        if res.get("ranks"):
            print("ranks:", *res["ranks"], sep="\n  ")
        else:
            print("ranks: 未提供（", res.get("rank_note"), "）")
    elif len(sys.argv) > 1 and sys.argv[1] == "--backfill":
        issues = list_issues()
        print(f"共发现 {len(issues)} 期")
        have = {(int(r["iso_year"]), int(r["iso_week"])) for r in load(RATES_CSV)}
        for url, title, pub in issues:
            try:
                y, w = issue_no(title)
            except RuntimeError:
                continue
            if (y, w) in have:
                continue
            try:
                fetch_one(url, pub)
            except Exception as e:
                print(f"[parse_failed] {title}: {e}", file=sys.stderr)
            time.sleep(DELAY)
        print("回补完成")
    else:
        url, title, pub = list_issues()[0]
        print(f"最新一期: {title} ({pub})")
        fetch_one(url, pub)

# -*- coding: utf-8 -*-
"""抓取国家流感中心《中国流感监测周报》，解析南方片 ILI% 与流感阳性率。

M2 r3 契约（.trellis/tasks/11-06-disease-monitor/design.md）：
- 成功才覆盖：同周新 ok 数据覆盖旧行（幂等）
- 失败永不覆盖成功：失败时若该周已有 ok 行则不动，仅记日志；该周无行才写失败行
- goldstein_index 列由 compute_index.py 写回，本脚本留空

用法：
  python src/fetch_flu_south.py            # 正常流程：抓最新一期，写 CSV
  python src/fetch_flu_south.py <文章URL>  # 抽验模式：只解析打印，不写 CSV（用于跨年格式抽验）
"""
import csv
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "flu_south.csv"
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
    from urllib.parse import urljoin
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


def parse_issue(txt: str) -> dict:
    """解析南方片 ILI%、流感阳性率（多精度，优先小数位最多的匹配）、周次与周起始日。"""
    week = re.search(r"(\d{4})\s*年\s*第\s*(\d+)\s*周(?:\s*第\s*(\d+)\s*期)?", txt)
    if not week:
        raise RuntimeError("未解析到期号")
    iso_year, iso_week = int(week.group(1)), int(week.group(2))

    m_ili = re.search(r"南方省份哨点医院报告的\s*ILI%\s*为\s*([\d.]+)\s*%", txt)
    if not m_ili:
        raise RuntimeError("未解析到南方 ILI%")

    # 阳性率两种版式（G2 跨年抽验发现）：
    # 2026 式：南方省份检测到 1796(17.14%)份流感病毒阳性标本  -> 用官方括号百分比
    # 2025 式：南方省份检测到 75 份流感病毒阳性标本（无百分比）-> 分母自算
    m_pos = re.search(r"南方省份检测到\s*[\d,]+\s*\(([\d.]+)%\)", txt)
    if m_pos:
        pos = m_pos.group(1)
        pos_src = "官方括号"
    else:
        m_num = re.search(r"南方省份检测到\s*([\d,]+)\s*份流感病毒阳性", txt)
        m_den = re.search(r"检测(?:流感样病例监测标本)?\s*([\d,\s]+?)\s*份", txt)
        if not (m_num and m_den):
            raise RuntimeError("未解析到南方流感阳性率")
        num = int(m_num.group(1).replace(",", "").replace(" ", ""))
        den = int(m_den.group(1).replace(",", "").replace(" ", ""))
        if den <= 0:
            raise RuntimeError("分母异常")
        pos = f"{num / den * 100:.2f}"
        pos_src = f"自算 {num}/{den}"
    print(f"[解析] 阳性率来源: {pos_src}")

    m_ws = re.search(r"第\s*%d\s*周（(\d{4})\s*年\s*(\d+)\s*月\s*(\d+)\s*日" % iso_week, txt) \
        or re.search(r"(\d{4})\s*年\s*(\d+)\s*月\s*(\d+)\s*日", txt)
    week_start = ""
    if m_ws:
        g = m_ws.groups()
        try:
            week_start = date(int(g[-3]), int(g[-2]), int(g[-1])).isoformat()
        except ValueError:
            pass

    return {"iso_year": iso_year, "iso_week": iso_week, "week_start": week_start,
            "south_ili_pct": m_ili.group(1), "south_flu_positive_pct": pos}


def load_rows() -> list:
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save_rows(rows: list) -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


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
        parsed = parse_issue(txt)
        upsert({**base, **parsed,
                "source_url": art_url, "source_pubdate": pub.isoformat()})
    except Exception as e:
        print(f"[失败] {e}", file=sys.stderr)
        # r3：失败行仅在能定位目标周次时才有意义。列表页都失败时连周次都未知，
        # 只报错退出，不写占位垃圾行（避免 iso_week=0 类无效主键）。
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:  # 抽验模式：对指定文章 URL 解析打印，不写 CSV
        art = http_get(sys.argv[1]).decode("utf-8", "replace")
        pdf_url = find_pdf_link(art, sys.argv[1])
        print(f"PDF: {pdf_url}")
        res = parse_issue(pdf_to_text(http_get(pdf_url)))
        print("解析结果:", res)
    else:
        fetch_latest()

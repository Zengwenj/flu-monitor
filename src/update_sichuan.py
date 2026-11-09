# -*- coding: utf-8 -*-
"""四川流感指数月度半自动录入（M4a / D19：纯本地交互，零 API）。

流程：抓省疾控首页找最新"流感指数"文章 → 下载文中区域图到 .tmp_sichuan/
→ 自动打开图片（你亲看仪表盘等级）→ 命令行输入等级(I/II/III/IV/V)
→ 写 data/sichuan_monthly.csv（主键 year+month+region 幂等，confirmed_by=人工）
→ 询问是否 git push（可选，失败不崩——境内网络可能 reset，重试即可）。

用法：双击 update_sichuan.bat，或 python src/update_sichuan.py
"""
import csv
import re
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "sichuan_monthly.csv"
IMG_DIR = ROOT / ".tmp_sichuan"
HOME = "https://www.sccdc.cn/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
LEVEL_NAME = {"V": "低水平活动", "IV": "活跃期", "III": "较高水平活动",
              "II": "高水平活动", "I": "极高水平活动"}
FIELDS = ["year", "month", "region", "level", "level_name", "source_url",
          "source_pubdate", "fetched_at", "confirmed_by", "note"]


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def find_latest_article() -> tuple:
    """首页找最新流感指数文章。返回 (绝对URL, 标题)。"""
    html = http_get(HOME).decode("utf-8", "replace")
    hits = re.findall(
        r"href='(/Article/View\?id=\d+)'[^>]*>([^<]*流感指数[^<]*)<", html)
    if not hits:
        raise RuntimeError("首页未找到'流感指数'文章链接（版式可能变化，请到 sccdc.cn 手动找）")
    path, title = hits[0]  # 首页列表最新在前
    return HOME + path.lstrip("/"), title.strip()


def parse_article(url: str, title: str) -> dict:
    """取文章页图片链接与年/月。月从标题'您的N月'取、年从发布时间取（容忍标签间隔）。"""
    from urllib.parse import urljoin
    html = http_get(url).decode("utf-8", "replace")
    # 图片：Editor/image 下的 png，可能是 https / ../../ 相对 / 根相对 三种形式 → urljoin 归一
    raw = re.findall(r"""['"]([^'"]*Files/Editor/image/[^'"]+\.png)['"]""", html)
    imgs = [urljoin(url, u) for u in dict.fromkeys(raw)]
    # 年月：标题含"您的N月"；发布时间"发布时间：</p><p>YYYY/M/D"（容忍标签）
    m_mon = re.search(r"您的(\d{1,2})月", title) or re.search(r"您的(\d{1,2})月", html)
    m_pub = re.search(r"发布时间：.*?(\d{4})/(\d{1,2})/(\d{1,2})", html, re.S)
    year = int(m_pub.group(1)) if m_pub else datetime.now().year
    month = int(m_mon.group(1)) if m_mon else (int(m_pub.group(2)) if m_pub else datetime.now().month)
    if not (1 <= month <= 12):
        raise RuntimeError(f"月份解析异常: {month}")
    return {"url": url, "images": imgs,
            "year": year, "month": month,
            "pubdate": f"{m_pub.group(1)}-{int(m_pub.group(2)):02d}-{int(m_pub.group(3)):02d}" if m_pub else ""}


def write_csv(year: int, month: int, level: str, level_name: str,
              url: str, pubdate: str) -> str:
    """幂等写入（主键 year+month+region=平原）。返回 行为描述。"""
    rows = []
    if CSV.exists():
        with CSV.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    key = lambda r: (int(r["year"]), int(r["month"]), r["region"])
    tgt = (year, month, "平原")
    action = "覆盖已有行" if any(key(r) == tgt for r in rows) else "新增行"
    rows = [r for r in rows if key(r) != tgt]
    rows.append({"year": str(year), "month": str(month), "region": "平原",
                 "level": level, "level_name": level_name, "source_url": url,
                 "source_pubdate": pubdate,
                 "fetched_at": datetime.now().isoformat(timespec="seconds"),
                 "confirmed_by": "人工",
                 "note": "update_sichuan 半自动录入（用户亲看图输入）"})
    with CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return action


def maybe_push() -> None:
    ans = input("是否推送到 GitHub？(y/N): ").strip().lower()
    if ans != "y":
        print("已跳过推送（本地 data/ 已更新，之后可手动 git push）")
        return
    for cmd in (["git", "add", "data/sichuan_monthly.csv"],
                ["git", "commit", "-m", f"chore(data): 四川流感指数 {datetime.now():%Y-%m} 半自动录入"],
                ["git", "push"]):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[推送失败] {' '.join(cmd)}\n{r.stderr.strip()[:200]}")
            print("（境内网络可能被重置——稍后手动 `git push` 重试即可）")
            return
    print("已推送 ✓")


def main() -> None:
    url, title = find_latest_article()
    print(f"最新文章: {title}\n  {url}")
    art = parse_article(url, title)
    print(f"期次: {art['year']}年{art['month']}月 | 图片 {len(art['images'])} 张")
    IMG_DIR.mkdir(exist_ok=True)
    saved = []
    for i, u in enumerate(art["images"][:5]):
        p = IMG_DIR / f"sichuan_{i}.png"
        p.write_bytes(http_get(u))
        saved.append(p)
    if not saved:
        raise RuntimeError("文章无图片（版式可能变化）")
    print(f"图片已存 {IMG_DIR}/，正在打开（多图版第1张=成都/平原；单长图含全部区域）…")
    import os
    os.startfile(str(saved[0]))  # 只开第一张：多图版即成都，单长图版含全部区域
    if len(saved) > 1:
        print(f"（共 {len(saved)} 张，其余在 {IMG_DIR}/ 可手动打开核对）")
    print("\n请看图输入成都（代表平原地区）的等级：")
    print("  V=低水平活动  IV=活跃期  III=较高水平活动  II=高水平活动  I=极高水平活动")
    while True:
        lv = input("等级 (I/II/III/IV/V): ").strip().upper()
        if lv in LEVEL_NAME:
            break
        print("无效输入，请输 I / II / III / IV / V")
    action = write_csv(art["year"], art["month"], lv, LEVEL_NAME[lv],
                       art["url"], art["pubdate"])
    print(f"[ok] {art['year']}年{art['month']}月 成都平原区 = {lv} 级·{LEVEL_NAME[lv]}（{action}）")
    maybe_push()


if __name__ == "__main__":
    main()

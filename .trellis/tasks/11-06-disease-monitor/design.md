# Design：M2 最小闭环（流感一条线纵切）——修订版 r2

> 本文档是 **M2 里程碑的技术设计**，范围横跨 data-fetch / compute-index / build-site 三个子任务的"流感最小切片"。基于 M1 可行性报告的已确认事实。M3 再扩展。
> **r2 修订（2026-11-06）**：吸收 metis 缺口分析（GAP-1~9）与 momus 评审（BLOCKER 1/2）。修订点以〔B1〕〔B2〕〔G#〕标注。

## M2 目标（一句话）

用最少代码让"抓流感周报 → 算 Goldstein 指数 → 极简分块页本地可打开"端到端跑通一次，产出第一个有真实数据的成品页。纵切不横切：只做流感一条线。

## 范围边界

**M2 做**：抓最近 1 期流感周报 PDF 解析南方 ILI%+阳性率算指数；四川分级手填 M1 已确认值（2026-10）；生成极简分块页 file:// 可打开。

**M2 不做**（留 M3/M4）：多病原/儿童/FluNet/历史回补（M3）、四川自动识别脚本（M3）、Actions/Pages（M4）、同期对比曲线（M3）。

## 数据契约（修订后，权威）

### `data/flu_south.csv`
列：`iso_year, iso_week, week_start, south_ili_pct, south_flu_positive_pct, goldstein_index, source_url, source_pubdate, fetched_at, status`
- `status` ∈ `ok / fetch_failed / parse_failed` 〔B2〕
- `goldstein_index` 由计算步骤**写回本列**〔B1：接口闭合，不再有"独立输出"选项〕
- 主键 `(iso_year, iso_week)`。**写入规则（r3，消解失败覆盖冲突）**：
  1. **成功才覆盖**：新抓到同周 ok 数据 → 覆盖该周旧行（幂等，支持官方修订）
  2. **失败永不覆盖成功**：运行失败时，若该周已有 ok 行则**不动它**，失败仅记日志；仅当该周无任何行时才写一行 `fetch_failed/parse_failed`（数值列空）
  3. 页面取数：数值/指数永远取**最新 status=ok 行**；若存在比它更晚周次的失败行 → 叠加失败横幅（"最新一期获取失败 · 显示上次成功数据（{W}周）"）

### `data/sichuan_monthly.csv`
列：`year, month, region, level, level_name, source_url, source_pubdate, fetched_at, confirmed_by, note`
- 主键 `(year, month, region)` 唯一〔G3/B2〕；M3 识别脚本遇同主键已存在且 `confirmed_by=人工` 时不覆盖，只允许 `note` 记录差异
- `source_pubdate`（官方发布日）与 `fetched_at`（写入时间）分离〔B2〕

## 技术设计

### 数据获取（流感切片）
- **源**：国家流感中心流感周报，两跳：列表页 `chinacdc.cn/jksj/jksj04_14249/` → 最新一期文章页 → PDF 链接 → 下载。
  - **"最新一期"识别**〔G1〕：S2 前先抓该列表页，确认其为静态 HTML 且首条即最新；实现时按文章链接旁的**发布日期**取最新，不盲取第一个 `<a>`。相对路径 `./YYYYMM/t….html` 拼 `https://www.chinacdc.cn/jksj/jksj04_14249/` 前缀成绝对 URL。
  - **HTTP 客户端**〔G8〕：先 urllib（带浏览器 UA）；403/空页即切 curl 子进程，不调参。
- **解析**：`pdftotext -layout`（`C:/Users/zengw/anaconda3/Library/bin/pdftotext.exe`），**子进程显式 `encoding='utf-8'`**〔G7〕。
  - **正则多精度**〔G2〕：阳性率括号兼容 `(XX%)`/`(XX.X%)`/`(XX.XX%)`；同一数值多处出现时**优先取正文"病原学监测"节的高精度版本**（摘要表可能是一位小数）。实施时另抽一期跨年样本（如 2025 年某期）验证格式稳定后才定稿正则。
- **容错**〔B2/r3〕：下载失败/解析失败时按上述"写入规则 2"处理——**不覆盖任何已有 ok 行**；该周无行才写失败行（数值空）。不写坏值不写 0。下游按"写入规则 3"显示失败横幅。

### 指数计算（Goldstein 切片）〔B1〕
- 读 flu_south.csv 的两列，`goldstein = south_ili_pct × south_flu_positive_pct`（直乘，4.8×17.14≈82.3），**写回同 CSV 的 `goldstein_index` 列**（唯一产物形式，页面只从该列读）。
- 标注为相对强度指数（CONTEXT 术语），不解释为感染率。无历史→同期对比标"无往年数据"。

### 四川分级（手填切片）〔B2/G3〕
- 手填值：2026-10 成都平原区 IV 级活跃期，`confirmed_by=人工`，`source_pubdate=2026-10-19`，note="M1 multimodal 识别+人工确认"。
- **展示语义**：该值是 10 月已确认值；首屏当前月（11 月）无新值时显示**"本月待更新"**，不默认绿、不冒充当月。

### 网页构建（阶段一切片）
- **内联形态=方式 A**〔G4〕：`build_site.py` 用字符串插值把数值直接渲染进 HTML 模板；不生成独立 JSON、不用 `fetch()`。改数字=重跑 build。
- 两块 + 每块标注覆盖期/来源发布日/状态：
  - 流感块：Goldstein 指数、南方 ILI%、阳性率、周次、发布日；首期环比标"首期无上周数据"
  - 四川块：2026-10 已确认等级 + "本月待更新"状态〔B2〕
- **文案来源**〔G5〕：状态文案用本设计附录枚举清单（用户已过目批准）；防护建议**只引官方原文**（四川分级标准表对应等级的防控建议 + 哨点周报健康提示），标出处，不自拟。
- 纯静态 HTML+内联 CSS，移动端可读。

## 状态文案枚举（唯一允许的状态文案）〔G5〕

| 场景 | 页面文案 |
|---|---|
| 正常 | 数据正常 · 第{W}周（{起}-{止}）· 来源发布 {date} |
| 首期无环比 | 首期数据 · 下次运行后显示环比 |
| 无往年同期 | 暂无往年同期数据 |
| 四川上月值 | {month}月已确认等级 · 本月待更新 |
| 四川缺值 | 官方分级未获取 · 状态未知 |
| 流感获取失败 | 最新一期获取失败 · 显示上次成功数据（{W}周） |
| 流感解析失败 | 最新一期解析失败 · 请人工核对官网 |
| 从未成功获取 | 暂无数据 · 请运行更新 |

## 目录（M2 新建）

```
data/flu_south.csv          data/sichuan_monthly.csv
src/fetch_flu_south.py      src/compute_index.py      src/build_site.py
site/index.html             run_local.bat
```

## 端到端验证

1. `python src/fetch_flu_south.py` → CSV 生成；南方 ILI%/阳性率与官网当期 PDF 人工核对一致
2. `python src/compute_index.py` → goldstein_index 列有值且=手算直乘
3. `python src/build_site.py` → index.html 生成
4. file:// 打开 → 两块真实数据、状态/口径标注齐全、离线无白屏、手机排版正常
5. **异常验例×3**〔B2〕：跨月旧四川值→"本月待更新"；四川缺值→"状态未知"；流感 status≠ok→失败横幅。各确认不显 0/最新/绿

## 权衡

- 四川 M2 手填不写识别脚本（M3 的 update_sichuan）；只抓 1 期不回补（M3）；回滚=删新建文件。
- 兼容性：不改已提交文档；M3 在此 CSV 契约上加列/加源，不推翻。

## r2 修订对照

| 来源 | 修订 |
|---|---|
| momus B1 | 指数写回 CSV 列，删除"或独立输出"二义 |
| momus B2 | status 字段 + 四川时间元数据 + "本月待更新"语义 + 异常验例 |
| metis G1 | 列表页先验结构、按发布日取最新 |
| metis G2 | 正则多精度 + 优先正文高精度 + 跨年抽验 |
| metis G3 | 四川主键唯一 + M3 不覆盖人工确认值 |
| metis G4 | 内联=方式 A 字符串插值 |
| metis G5 | 状态文案枚举清单 + 防护建议只引官方 |
| metis G6 | S7 输出可操作核对信息（本期周次+PDF文件名+对照页） |
| metis G7 | pdftotext 子进程 encoding='utf-8' |
| metis G8 | urllib 失败即切 curl |
| metis G9 | bat 加 cd /d "%~dp0" |

# FROZEN PLAN SNAPSHOT — A1a 流感周报历史回补（数据层）

- freeze_id: A1A-PLAN-R2
- frozen_at: 2026-11-11 (Asia/Shanghai)
- task: `.trellis/tasks/11-11-flu-south-backfill`（父任务 `11-06-disease-monitor`）
- 审阅范围: 本文件全文 = prd + design + implement 的冻结拼接。
  外部只读依据（不在冻结体内，评审可读但要记录其 hash）：`D:/FluMonitor/src/fetch_flu_south.py`、`D:/FluMonitor/src/build_site.py`、`D:/FluMonitor/src/compute_index.py`、`D:/FluMonitor/CONTEXT.md`、`D:/FluMonitor/docs/handoff.md`、`D:/FluMonitor/.trellis/tasks/11-11-flu-south-backfill/research/gap-analysis.md`

## 组成文件与各自 SHA-256（拼接前）

| 组成文件 | 行数 | SHA-256 |
|---|---|---|
| `prd.md` | 60 | `42BB56EEE1A3C712AA7715876205B2F9380FBF2DAF9C0A14F531DBE7875FB508` |
| `design.md` | 336 | `275C9E68507E92C218C07621AE7ED8A16AF85344AC43D00AB020F7126987EC83` |
| `implement.md` | 124 | `CB36D7715D79E17A15912432A2C667F753328132FBF1534DF6BA663B4A32D06D` |

> 冻结约定：本文件一经生成即为本次评审对象。评审期间不得再修改；
> 若实施前需改动 prd/design/implement，必须重新生成快照（新 freeze_id）并重新评审。


<!-- ======================= BEGIN PRD (prd.md) ======================= -->

# A1a 流感周报历史回补（数据层）

> 父任务：`11-06-disease-monitor`。来源：`docs/handoff.md` §5 A1。
> 状态：PRD 已按 `research/gap-analysis.md`（含主会话实测）修订，2026-11-11。

## Goal

实现 `src/fetch_flu_south.py --backfill`：从国家流感中心档案回补《中国流感监测周报》**200 期**（2023W1–2026W44），解析南方片 ILI% / 流感阳性率写入 `data/flu_south.csv`，解锁南方片 Goldstein 历史序列与"往年同期"的数据基础。

**展示层改动不在本任务内**（见 R9）。

## 背景修正（相对初稿）

初稿写"约 150 期"，实测为 **200 期**（2023W1→2026W44 = 52×3+44）。"150"是近三年口径。

初稿假设走 `LIST_URL`（中疾控 chinacdc）分页。实测该列表只回溯到 **2024W1（第786期）**，仅 148 期；能回到 2016 的是国家流感中心档案 `ivdc.chinacdc.cn/cnic/zyzx/lgzb/`（30 页 `.htm`，600 条，2016–2026 每年 52 周无缺口）。两源同源（2024W1 解析结果一致）。

**实测发现已上线的解析 bug**：`src/fetch_flu_south.py:118` 自算分支把全国合计当分母，阳性率系统性偏低 21%–50%。修它成为回补的前置条件。

## Requirements

- **R0（新增，前置）** 修复 `parse_issue()` 自算分支的南方片分母：改用 PDF 表 1「检测数 南方省份/北方省份/合计」第一列；括号版式保留并与表分母互校；表 1 缺失判失败，不回退全国合计。数值域、期号一致、合并版识别、week_start ISO 校验一并加入。详见 `design.md §2、§3.3`。
- R1 新增 `--backfill` 模式：枚举 ivdc 档案（`index_N.htm`，页数读 `var countPage = N`）→ 逐期"文章页 → PDF → pdftotext → parse_issue → upsert"，限速 2.5s。
- R2 复用现有 `parse_issue()` / `upsert()` / `http_get()` / `find_pdf_link()` / `pdf_to_text()`；`--from/--to/--force/--limit` 解析须在 URL 分支之前（`fetch_flu_south.py:202`）。
- R3 写入守卫沿用 r3：成功才覆盖、失败永不覆盖成功周。
- R4 失败期**只记 `data/changes.log`，不写 CSV 失败行**——否则 `build_site.py:69-80` 会常驻错误横幅。原因码见 `design.md §4.3`。
- R5 可中断续跑：已有 ok 周跳过不下载；txt 缓存 `.tmp_flu_backfill/`（不进仓库）；`--force` 重抓比对，有差异留痕后覆盖（依据 CONTEXT.md:71）。**整表写入必须中断安全**：写临时文件 + `os.replace` 原子替换，失败/中断不得损坏权威 CSV（详见 `design.md §4.0`）。
- R6 诚实性：缺期不补 0、不插值；合并版/PDF 版式异常的期间明确留痕。
- R7 南方片历史基线只用流感周报南方片同口径数据，不混入全国 FluNet（D17）。
- R8 本地一次性执行；不改云端 `weekly.yml`。
- **R9（新增）** 展示层（环比相邻周守卫、"往年同期"块）拆到 A1b 新子任务，本任务不碰 `build_site.py`。

## Acceptance Criteria

- [ ] `flu_south.csv` 覆盖 2023W1–2026W44 全部可得周，主键 `(iso_year, iso_week)` 无重复、按周升序、只含 `status=ok` 行
- [ ] 覆盖对账按**最终状态互斥归并**成立：200 个目标周分别且仅归入 `ok` / `pending_fail` / `merged_skip`，三集合并集 = 全集、两两无交集（`merged_skip` 不重复计入 `pending_fail`；不得用 `changes.log` 行数代入）
- [ ] 七期基准阳性率与 PDF 表 1 南方分母一致（2023W1/2024W1/2025W14/2025W40/2026W1/2026W10/2026W30，基准见 `research/gap-analysis.md`）
- [ ] 抽验 2026W44 URL 回归输出 `4.8 / 17.14`；括号版式期数值不变
- [ ] `compute_index.py` 为全部 ok 周算出 Goldstein，且 `= ILI% × 阳性率`（2 位）
- [ ] 回归口径：无参单期模式与 `<URL>` 抽验模式的 CLI 行为与写入行为不变；括号版式期（2026W44）数值仍为 `4.8 / 17.14`；自算版式期按修复后的基准值验收（不要求保持原错误值）；`--backfill` 不被当 URL
- [ ] 续跑：完整状态下再跑下载数为 0，CSV 逐字节一致
- [ ] 中断安全：写入中途受控中断后权威 CSV 逐字节不变且可完整读取；遗留临时文件被清理（`design.md §4.0`）
- [ ] r3 守卫：注入缺 ILI% 的文本，该周已有 ok 行不动
- [ ] 人工抽验：2023/2024/2025/2026 每年至少 2 期（含年初/年末周），PDF 原文与 CSV 一致
- [ ] `build_site.py --local` 正常构建，页面无外部加载资源

## 已闭环的 Open Questions

| 问题 | 结论 |
|---|---|
| 分页能否回溯 2023？ | chinacdc 只到 2024W1；ivdc 档案到 2016，2023 全年齐全。改用 ivdc 作回补源 |
| 2023/2024 版式兼容？ | 兼容，抽样 14 期全部解析成功，week_start 均为周一 |
| 回补起点？ | 默认 2023W1；`--from` 下界硬校验为 2023W1（2016–2018 无文本层、2019–2022 南方分母不可得，见 design §0 分代表） |
| 展示层是否属本任务？ | 否，拆 A1b（R9） |
| PDF 是否缓存？ | 不缓存 PDF，只缓存 pdftotext 出的 txt 到 `.tmp_flu_backfill/` |

## Notes

- 复杂任务：`design.md` + `implement.md` 已成稿，走 plan-critic → 用户批准 → 实施 → 独立只读复核 → 汇报 → 两笔提交（docs / feat）+ push。
- 回补一次性写入约 200 行，须先让用户在 Excel 过一遍再提交。

<!-- ======================== END PRD (prd.md) ======================== -->

<!-- ======================= BEGIN DESIGN (design.md) ======================= -->

# Design：A1a 流感周报历史回补（数据层）

> 父任务 `11-06-disease-monitor`；本任务 `11-11-flu-south-backfill`。
> 依据：`research/gap-analysis.md`（gap-analyst + 主会话实测补充，2026-11-11）。
> 继承 M2 的 r3 写入契约、pdftotext utf-8、urllib→curl 回退。
> **本文件不含展示层改动**（环比相邻周检查、"往年同期"块 → A1b，见 §7）。

## 0. 决策前提（已实测，非假设）

| 事实 | 证据 |
|---|---|
| 唯一可用历史源是 ivdc 国家流感中心档案 `https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/` | 30 页 `index_N.htm`，600 条周报条目，2015W19–2026W44（2015 仅部分，列表 30 页截断） |
| chinacdc `jksj/jksj04_14249/` 只回溯到 2024W1 | 13 页 × 12 = 148 条，最早 2024年第1周第786期 |
| 两源同源 | 2024W1 在 chinacdc 与 ivdc 解析结果一致（ILI% 9.7 / 阳性率 52.52%）；PDF 文件不同名但内容同版 |
| **2016–2018 的 PDF 是扫描图像，无文本层** | 2016W1/2016W10/2017W20/2018W20 经 pdftotext 只得到 87–196 个字符的页码数字（汉字数=0），ILI% 与表 1 均不可解析 → 该年份**技术不可回补**（除非引入 OCR，本任务不做） |
| 2019–2021 有文本层，但**版式不同**（第三代） | 2019W20："南方省份检测到流感阳性标本 `788` 份（22.1%）"——阳性数与百分比之间是**全角括号且"标本"在前**；表 1「检测数 南方省份 北方省份 合计」**不存在** |
| 2022 起为现行"分省叙述"版式，但 2022 也**没有**表 1 | 2022W20："南方省份检测到 499 份流感病毒阳性标本，其中…"——有分子无分母、无可百分比 |
| **2023 起版式可完整解析** | 2023W1/2/14/30/40/52 全部成功，表 1 存在且 `南方+北方=合计` |
| 现解析器分母取错（BLOCKER） | `src/fetch_flu_south.py:118` 取正文"全国…共检测 N 份"，分子却是南方片（`:117`）。见 §2 |

**版式分代结论**（决定 `--from` 的下界）：

| 代 | 年份 | 有文本层 | 南方分母来源 | 本任务 |
|---|---|---|---|---|
| 扫描件 | 2016–2018 | ✗ | 无 | 不支持（需 OCR） |
| 第三代 | 2019–2021 | ✓ | 内含百分比 `（22.1%）`，无表 1 | **不支持**（逻辑与现行分支不同，擅自扩展风险高） |
| 二代 | 2022 | ✓ | **无**（有分子无分母） | **不支持**（无法自算） |
| 现行 | 2023–2026 | ✓ | 表 1 南方列 | **支持**（本任务范围） |

故 `--from` 的**实际可用下界是 2023W1**。文档中"`--from` 可到 2016W1"的表述作废：
更早年份属技术不可行或版式不兼容，若将来要支持须另立任务（OCR 或新解析分支）。

## 1. 范围

### 做什么（A1a）

1. **修复 `parse_issue()` 的南方片分母**（§2）——回补的前置条件，否则批量写入静默错值。
2. 新增 `--backfill` 模式：ivdc 档案枚举 → 逐期下载 → `parse_issue` → `upsert`。
3. 断点续跑、`--force` 重抓比对、失败留痕（`data/changes.log`）、行序归一。
4. 回补期号一致性、合并版识别、周起始日校验等防错守卫。
5. 回补后重跑 `compute_index.py` 生成 Goldstein 历史序列。

### 不做什么

- 不改 `build_site.py`（环比箭头相邻周守卫、往年同期块 → A1b）。
- 不改 `weekly.yml`、不改无参单期模式的上游来源（仍走 chinacdc `LIST_URL`）。
- 不缓存 PDF 原件，不把 PDF/txt 提交进仓库。
- 不伪造：解析失败不写 CSV 行（见 §4.3 理由）。
- 不追求 2015 及更早：列表已被 30 页截断（最早 2015W19），且 2016 起才凑得齐 3 个完整年度的同期对比。

### 回补区间

默认 `2023W1 → 最新已发布周`，即 **200 期**（2023/2024/2025 各 52 + 2026 至 W44 = 44）。
理由：D17 的"往年同期"只需 3 个完整历史年度；且 **2023 是现行版式的起点**（§0 分代表）。

`--from` 的合法下界由代码硬校验为 `2023W1`：更早的区间一律拒绝并说明原因——
2016–2018 无文本层（需 OCR）、2019–2021 与 2022 的南方分母不可得（§0）。
若将来要支持更早年份，须另立任务，不在本任务里放宽。

## 2. 解析修复（前置）

### 问题

```python
# src/fetch_flu_south.py:117-118（现状）
m_num = re.search(r"南方省份检测到\s*([\d,]+)\s*份流感病毒阳性", txt)
m_den = re.search(r"检测(?:流感样病例监测标本)?\s*([\d,\s]+?)\s*份", txt)
```
分子是**南方片**阳性数，分母却是正文"全国…共检测 N 份"的**全国合计**。阳性率被系统性稀释（实测 −21% ~ −50%）。

### 修法

分母改为 PDF 表 1「检测数 南方省份 / 北方省份 / 合计」的第一列，锚定表头避免误取暴发疫情表：

```python
# 表 1 分母：锚定「南方省份 北方省份 合计」表头，限制 40 字符内出现「检测数」，再取三列
m_tab = re.search(
    r"南方省份\s+北方省份\s+合计[\s\S]{0,40}?检测数\s+(\d[\d,]*)\s+(\d[\d,]*)\s+(\d[\d,]*)", txt)
# m_tab.group(1)=南方  group(2)=北方  group(3)=合计
```

规则：
- **括号版式优先**（`南方省份检测到 1796(17.14%)份…`，`:112` 现有分支保持不变），
  并用 `N / south_den` 与括号值互校，相对误差 > 1.5% 判 `parse_failed`。
  实测 2026W44：1796/10481 = 17.1358% → 官方 17.14%（偏差 0.025%）✓。
- **自算版式**（无括号）：`pos = N / south_den`。
- **表 1 取不到 → 判失败**，绝不回退全国合计（这正是原 bug 的形态）。
- 现有唯一数据行 2026W44 走括号分支，修复后数值不变（回归基准 `4.8 / 17.14 / 82.27`）。

#### 已在 27 个跨年真实样本上验证

缓存样本（2023W1/2/14/30/40/52、2024W1/2/26/52、2025W1/14/20/30/40/52、
2026W1/10/20/30/35/40/41/42/43/44、ivdc 2024W1）**全部命中表 1 正则**，
且每一期都满足 `南方 + 北方 = 合计`（列列自洽，无一例外）。

候选修复版 `parse_issue` 对这 27 个样本**端到端全跑通过（27 ok / 0 fail）**，
week_start 全部等于 `date.fromisocalendar(y, w, 1)`，无数值域告警。抽样结果：

| 期 | ILI% | 阳性率 | 南方分母 | 来源 |
|---|---|---|---|---|
| 2023W1 | 3.6 | 0.04 | 4522 | 自算 2/4522 |
| 2023W14 | 8.9 | 57.29 | 6128 | 自算 3511/6128 |
| 2023W52 | 9.6 | 54.22 | 5339 | 自算 2895/5339 |
| 2024W1 | 9.7 | 52.52 | 5863 | 自算 3079/5863 |
| 2024W52 | 5.7 | 24.51 | 8628 | 自算 2115/8628 |
| 2025W14 | 3.9 | 2.85 | 9697 | 自算 276/9697 |
| 2025W52 | 6.1 | 41.90 | 10876 | 自算 4557/10876 |
| 2026W1 | 5.4 | 35.82 | 10269 | 自算 3678/10269 |
| 2026W44 | 4.8 | 17.14 | 10481 | 官方括号（互校偏差 0.025%） |

**该验证同时闭合了原 bug 的机理**：2023W1 的表 1 是 `南方 4522 / 北方 3982 / 合计 8504`，
而旧代码 `:118` 抓到的正是 **8504**（合计）——分子 2 份 ÷ 8504 = 0.02%，真值 2 ÷ 4522 = 0.04%。
与 GAP-5 首条的推断完全一致。

候选实现留档：`C:\Users\zengw\AppData\Local\Temp\opencode\candidate.py`（含守卫与校验，可直接移植进 `src/fetch_flu_south.py`）。

#### 括号版式的分子也要单独取

括号版式下 `:117` 的 `南方省份检测到\s*([\d,]+)\s*份流感病毒阳性` **匹配不到**
（`1796(17.14%)份` 中间隔着括号）。互校需要的分子用：

```python
m_br = re.search(r"南方省份检测到\s*([\d,]+)\s*\(([\d.]+)%\)", txt)
# m_br.group(1)=分子  group(2)=官方百分比
```

### 连带影响

修复同时作用于无参单期模式（同一 `parse_issue`）——这是修复而非回归：单期模式原本也可能写出稀释值
（2026W43 起均为无括号版式，现值会写 9.0x% 而非 18.03%）。

验收口径统一为：
- **CLI 与写入行为不变**（无参 = 抓最新一期写 CSV；`<URL>` = 只打印不写）；
- **括号版式期数值不变**（2026W44 仍为 4.8 / 17.14 / 82.27）；
- **自算版式期按修复后的基准值验收**（七期基准见 §2 表），不要求保持原来的错误值。

## 3. 枚举与抓取

### 3.1 列表枚举（ivdc）

- 入口 `https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/`，分页 `index.htm`、`index_N.htm`（**`.htm` 不是 `.html`**）。
- **页数取自页内 JS 变量** `var countPage = 30;//共多少页`（实测存在），正则 `var\s+countPage\s*=\s*(\d+)`。
  不要硬编码 30，也不要依赖"翻到空页为止"——越界页 `index_30.htm` 返回 HTTP 200 + 146 字节的"找不到"提示页，
  `http_get` 的 curl 兜底无 `-f`（`src/fetch_flu_south.py:50-54`），会被当成成功响应。
- 条目正则（实测可直接用，含同 `<li>` 内的发布日期）：

```python
ITEM = re.compile(
    r'<span class="span_01">\s*<a href="([^"]*t\d+_\d+\.htm[l]?)"[^>]*>([^<]*)</a>\s*</span>'
    r'\s*<span class="span_02">\s*\(([\d-]+)\)', re.S)
WEEK = re.compile(r"^(\d{4})\s*第\s*(\d+)\s*周")
```

  标题形如 `2026 第44周`。实测 30 页共 **600 条，全部是周报**（无杂条目），
  最早 **2015W19**、最新 2026W44；2015 年只有 W19 起（列表 30 页的截断），2016 起每年 52 周齐全。
  列表日期与文章页"发布时间"抽验 6 期（2023W1/2024W26/2025W1/2026W10/2016W10/2026W44）**逐条一致**，
  故 `source_pubdate` 可直接取列表日期，省一次文章页请求。
- **列表页标题只有年+周，没有期号**（实测"2026 第44周"）。期号从**文章页 PDF 链接的锚文本**取：
  实测 `全文下载：<a href="./P020261105832023192346.pdf">2026年第44周第933期中国流感监测周报.pdf</a>`。
  故 §3.3 的期号一致性校验在"文章页已取到"后执行，比较对象是：**PDF 链接锚文本的年/周/期** ↔ **PDF 文本内的年/周/期**。
- 结果按 `(iso_year, iso_week)` 去重索引；同周重复时保留**列表靠前**（较新发布）的一条，并把被丢弃项记入报告。

### 3.2 单期抓取

复用现有 `http_get` / `find_pdf_link` / `pdf_to_text`。每期间隔 2.5s（沿用 `fetch_sentinel.py:32` 的礼貌限速）。

**txt 缓存**：`.tmp_flu_backfill/txt/<year>_W<week>.txt`，已存在则跳过下载与转换。用途是正则调试不必重复拉 1GB；`.gitignore:2` 的 `.tmp_*/` 已覆盖。不缓存 PDF 原件（体积 + 版权）。

**`--force` 必须绕过缓存**：`--force` 下无论缓存是否存在都重新下载 PDF 并重新转换 txt，
成功后用新 txt 覆盖旧缓存。理由：`--force` 的用途就是发现上游修订（`CONTEXT.md:71`），
若命中缓存就解析旧文本，"重抓比对"形同虚设。
`--force` 重抓失败时**保留已有 ok 行与旧缓存不动**，不得让旧缓存冒充本次重抓结果。

预估耗时：200 期 × (下载 3–10s + 限速 2.5s) ≈ **25–45 分钟**；体积约 0.9–1.1GB。

### 3.3 防错守卫（任一不满足 → 该期 `parse_failed`，不写 CSV）

1. **年/周一致（硬校验）**：列表条目标题（`2026 第44周` 或 `2026年第44周第933期`）解析出的 `(年, 周)`
   必须等于 PDF 文本内解析出的 `(年, 周)`；不等 → `issue_mismatch`，判失败。
   - **锚文本期号只作告警**：实测 2024W26 的 PDF 锚文本是 `2024年第26周第811期…`，
     但 PDF 内部自洽为 `第810期`（`2024 年第 26 周` + 通篇 `第 810 期`）——**上游把锚文本期号标错了**。
     若把期号当硬校验，会误杀这期正常数据。故锚文本期号与 PDF 期号不等时 →
     正常入库，同时写 `changes.log: issue_no_warn` 留痕。
   - 锚文本解析不出年/周/期（实测 2016W10 锚文本只有 `0.pdf`）→ 跳过锚文本校验，只做 PDF 内部一致校验。
2. **合并版（只看标题/锚文本，不看正文）**：仅当**列表标题或锚文本**出现范围式周次
   （`第\s*\d+\s*[-–~至]\s*\d+\s*周`）或 ≥2 个不同期号时判合并版。
   **禁止对 PDF 正文做这个判断**——实测 13/27 期正常周报正文含累计区间表述
   （如 2026W44 的"2026 年第 14-44 周…共报告 658 起"、"第 5-6 周实验室检出阳性数"），
   对正文做范围匹配会把大量正常期误判为合并版。
   PDF 内部 ≥2 个不同**期号**仍是有效信号（实测所有正常期全篇只用同一个期号），可保留。
3. **周起始日**：解析出的 `week_start` 与 `date.fromisocalendar(iso_year, iso_week, 1)` 比对，不一致则照存解析值但写 changes.log 告警（不静默改）。
4. **数值域**：`0 ≤ south_ili_pct ≤ 100`、`0 ≤ south_flu_positive_pct ≤ 100`，越界判失败。

## 4. 写入契约

### 4.0 中断安全的整表写入（新增，BLOCKER A1A-INTERRUPT-SAVE）

**问题**：`save_rows()`（`src/fetch_flu_south.py:150-155`）用 `CSV_PATH.open("w")` 直接覆盖权威 CSV——
先截断、再逐行序列化。`upsert()` 每成功一期就调它一次（`:166`、`:176`），
而回补要连续写 **200 次**。任何一次 Ctrl-C / 断电落在"已截断、未写完"的窗口，
**此前所有成功行都会从唯一权威副本里消失**，与 R5「可中断续跑"的承诺直接冲突。

**修法**（只改写入的物理方式，不改 r3 业务规则）：

```python
TMP_CSV = Path(".tmp_flu_backfill") / "flu_south.csv.tmp"   # 与 data/ 同卷；.gitignore:2 的 .tmp_*/ 已覆盖

def save_rows(rows: list) -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    TMP_CSV.parent.mkdir(parents=True, exist_ok=True)
    with TMP_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
        f.flush()
        os.fsync(f.fileno())
    os.replace(TMP_CSV, CSV_PATH)   # 同卷重命名 → 原子；目标被替换，不会出现半张表
```

- 临时文件放 `.tmp_flu_backfill/`（已被 `.gitignore:2` 的 `.tmp_*/` 覆盖），**不新增 `.gitignore` 条目、不在 `data/` 留残余**。
- 要求：临时文件与 `data/flu_south.csv` 必须**同卷**（都在 `D:` 仓库内，成立）。若将来把 `.tmp_flu_backfill/` 指到别的盘，需改回同目录。
- 每次启动先清理遗留的 `TMP_CSV`（上次被杀留下的半成品不得参与任何逻辑）。
- §4.2 的收尾排序也走同一 `save_rows`，不另写一份。
- 单期模式行为不变（写出的 CSV 字节相同），只是变得更抗中断。

### 4.1 续跑与重抓

- 默认：该周已有 `status=ok` 行则**跳过，不下载**（`--force` 例外，见 §3.2）。
- `--force`：**绕过 txt 缓存**重抓，与现有 ok 行比对；数值不同才覆盖，并在 `changes.log` 记录 `backfill_revise / 旧值 / 新值`。
  依据：`CONTEXT.md:71` 明确不采纳"缓存周次永不重抓"，上游会修订，需低频受控复核。

### 4.2 行序归一

`upsert` 是"删旧追加"（`src/fetch_flu_south.py:163-166`），回补必然打乱行序（影响 Excel 核对与 `build_site.py:85` 的 `prev[-1:]`）。
`--backfill` 结束时统一按 `(iso_year, iso_week)` 升序重排一次并落盘。此排序是 `--backfill` 的收尾步骤，
**不改 `upsert` 的增删规则**，单期模式的数值与行内容不受影响（写入的物理方式见 §4.0）。

### 4.3 失败不留 CSV 行

`build_site.py:69-80`：只要存在任意非 ok 行，且不晚于最新 ok 周，页面就常驻"最新一期解析失败 · 请人工核对官网"横幅。历史失败行会污染线上页面。
因此回补失败**只写 `data/changes.log`**，不写 CSV，与哨点回补先例一致（`fetch_sentinel.py:353-354` 只打印不写行）。

**注意日志与状态的区别**：`changes.log` 是**追加式事件流水**，同一周可能有多行（先失败后成功、两次失败）。
覆盖对账（§6 第 4 条）必须用进程内的"最终状态"字典按周键归并，**不能数日志行**。

`changes.log` 沿用现有 tab 格式（`fetch_sentinel.py:271-274`）：

| which | old | new |
|---|---|---|
| `backfill_fail` | 原因码（`no_pdf` / `pdf_error` / `parse_error` / `bracket_mismatch` / `issue_mismatch` / `merged_issue` / `out_of_range`） | 具体说明 |
| `backfill_revise` | `ILI% x / 阳性率 y` | `ILI% x' / 阳性率 y'` |
| `week_start_check` | 解析值 | ISO 周一 |
| `issue_no_warn` | 锚文本期号 | PDF 内期号（上游标注不一致，数据仍入库） |
| `skipped_merged` | 标题/锚文本 | 判定依据 |

**写入量控制**：首次成功入库**不写日志**（200 行成功日志只会淹没真正有用的记录）；
只记失败、修订（`--force` 发现差异）、告警与合并版跳过。一次干净的全量回补若全部成功，
`changes.log` 应当**零新增行**——这本身也是一条验收信号。

### 4.4 主要列不变

CSV schema 不变（`FIELDS`，`src/fetch_flu_south.py:35-37`）。`source_url` 记 ivdc 文章页，
`source_pubdate` 取列表条目日期（已实测与文章页"发布时间："一致）；`goldstein_index` 仍由 `compute_index.py` 回填。
`fetched_at` 记本次抓取时间，不沿用历史。

## 5. CLI

```bat
python -X utf8 src/fetch_flu_south.py --backfill
python -X utf8 src/fetch_flu_south.py --backfill --from 2023W1 --to 2026W44
python -X utf8 src/fetch_flu_south.py --backfill --force
python -X utf8 src/fetch_flu_south.py --backfill --limit 5     :: 冒烟：只处理 5 期
```

参数解析必须插在 `if __name__ == "__main__":` 的 `len(sys.argv) > 1` 分支**之前**（`src/fetch_flu_south.py:202`），否则 `--backfill` 会被当成文章 URL。

## 6. 验证方式

1. **回归**：`python -X utf8 src/fetch_flu_south.py https://www.chinacdc.cn/jksj/jksj04_14249/202611/t20261105_1842732.html` 仍输出 `south_ili_pct 4.8 / south_flu_positive_pct 17.14`。
2. **分母正确性**：对 2023W1 / 2024W1 / 2025W14 / 2025W40 / 2026W1 / 2026W10 / 2026W30 七期，阳性率等于 PDF 内"南方省份检测到 N 份 ÷ 表 1 南方检测数"，且与人工核对一致（基准值见 `research/gap-analysis.md` 表格）。
3. **续跑**：完整状态下再跑 `--backfill`，下载数 = 0，CSV 逐字节不变。
4. **覆盖对账（按最终状态归并，不数日志行）**：把 `2023W1–2026W44` 的 200 个目标周逐个归入**互斥且唯一**的一类：
   - `ok`：CSV 中有该周 ok 行
   - `pending_fail`：该周无 ok 行，且最后一次尝试失败（原因码取最后一次，不累计历史失败次数）
   - `merged_skip`：该周被判合并版跳过（**从 `pending_fail` 中排除，不双计**）

   判据：`ok 集合 ∪ pending_fail 集合 ∪ merged_skip 集合 = 200 周全集`，且三集合两两无交集。
   **不得用 `changes.log` 行数代入等式**——同一周失败两次或"先失败后成功"都会让行数不等于周数。
   实现方式：回补进程维护内存中的 `{周键: 最终状态}` 字典，收尾时打印三类计数与差集；重跑不虚增。
5. **r3 守卫**：注入缺 ILI% 的 PDF 文本，该期已有 ok 行保持不动。
6. **`--backfill` 不被当 URL**：执行 `--backfill --limit 1` 不产生"HTTP 获取失败: --backfill"。
7. **goldstein**：`compute_index.py` 后所有 ok 行非空，且 `= ILI% × 阳性率`（2 位），抽 3 行手算核对。
8. **人工抽验**：2023/2024/2025/2026 每年至少 2 期（含年初、年末周），PDF 原文与 CSV 一致。
9. **写入中断安全**（§4.0）：在 CSV **副本**上做受控中断实验——
   于 `save_rows()` 写完临时文件之前抛出 `KeyboardInterrupt`，验证副本**逐字节不变**且 `load_rows()` 仍能完整读出；
   中断后重跑能正常写入且遗留 `.tmp_flu_backfill/flu_south.csv.tmp` 被清理。
   **绝不在真实 `data/flu_south.csv` 上做此实验。**

## 7. 与 A1b 的边界

A1b（另建子任务）承接：`build_site.py:81-85` 的环比相邻周守卫、`:88` 与 `:246-251` 的"往年同期"块。
A1a 交付后 A1b 才有数据可用。

**写域**：
- A1a：`src/fetch_flu_south.py`、`data/flu_south.csv`、`data/changes.log`、
  `.trellis/tasks/11-11-flu-south-backfill/research/backfill-report.md`、
  `.tmp_flu_backfill/`（`.gitignore:2` 已覆盖，不入库）
- A1b：`src/build_site.py`

**发布门（必须遵守）**：A1a 虽然不碰 `build_site.py`，但它在**允许失败周不入 CSV** 的前提下
引入了一个新的错误展示路径——`src/build_site.py:81-85` 取"最新周之前的最近一个 ok 周"
直接标"较上周"，**不校验是否相邻**。于是"2026W44 成功、W43 失败、W42 成功"
会让页面把 W44 与 W42 相比却写成"较上周"，违反 D17。

因此：**只要最新周与紧邻上一周不是都有 ok 行与可用指数，A1a 的产物不得标记为"可发布"**，
也不得据此 push 到线上页面。两条出路：
1. 先完成 A1b 的相邻周守卫再发布；或
2. 回补结果必须覆盖最新周及其紧邻上一周（本任务目标区间覆盖到 2026W44，
   而 2026W43 可解析——正常回补后两者都有 ok 行，发布门自然满足）。

回补后须显式核验这两周都在 CSV 中；缺任一周则在汇报中列为阻塞项，不得声称页面可发布。

## 8. 回滚

`data/flu_south.csv` 与 `data/changes.log` 均为 git 跟踪，`git checkout -- data/flu_south.csv` 即回到单行状态；
`src/fetch_flu_south.py` 的解析修复可单独保留（它是独立 bug 修复，与回补解耦）。缓存目录 `.tmp_flu_backfill/` 直接删除。

## 9. 风险

| 风险 | 处置 |
|---|---|
| 回补期间上游某期 PDF 已下架 | 记 `backfill_fail/no_pdf`，覆盖对账里计入，不伪造 |
| 2023 年初 PDF 10MB，下载超时 | `http_get` 已有 urllib→curl 回退；单期失败不中断整批 |
| 本地整表重写与 bot 每周五回写 `data/` 冲突 | 推送避开周五，且先 `git pull`（handoff §6） |
| 200 行一次性入库不便人工核对 | 回补后按周升序输出核对清单（年/周/ILI%/阳性率/来源），交用户 Excel 过一遍再提交 |
| 回补中途中断损坏权威 CSV | §4.0 的临时文件 + `os.replace` 原子替换；§6 第 9 条的副本中断实验 |

<!-- ======================== END DESIGN (design.md) ======================== -->

<!-- ======================= BEGIN IMPLEMENT (implement.md) ======================= -->

# Implement：A1a 流感周报历史回补执行清单

> 技术契约见本目录 `design.md`。依据 `research/gap-analysis.md`。
> **前置条件：plan-critic APPROVE + 用户批准（两者独立，不可互相替代）后才能写代码。**

## 执行前

- [ ] plan-critic 评审本组文档 → APPROVE（REJECT 则修订后复审）
- [ ] 用户批准（明确许可写代码）
- [ ] 记录当前 CSV 基线：`data/flu_south.csv` 仅 1 行（2026W44，4.8 / 17.14 / 82.27）
- [ ] 记录回归基准：抽验 2026W44 URL 输出 `4.8 / 17.14`

## 有序步骤

### S1 分母修复 + 解析守卫 + 中断安全写入（独立可验证，先做）

`src/fetch_flu_south.py`

1. `parse_issue()` 分母改为表 1 南方列（`design.md §2` 的正则）；括号分支保留并加互校（相对误差 > 1.5% → `RuntimeError`）；表 1 缺失 → `RuntimeError`，不回退全国合计。
2. 加守卫（`design.md §3.3`）：
   - 年/周硬校验（列表标题 ↔ PDF 文本）；
   - 锚文本期号 **只告警不判失败**（2024W26 上游把锚文本期号标错，写成 811，PDF 内是 810）；
   - 合并版判定 **只看标题/锚文本**（PDF 正文含累计区间表述，实测 13/27 期会误判）；
   - 数值域校验。
3. `week_start` 用 `date.fromisocalendar` 校验（第 3 条），不一致照存但返回告警标记。
4. `save_rows()` 改为"临时文件 + `os.replace` 原子替换"（`design.md §4.0`）：
   临时文件 `.tmp_flu_backfill/flu_south.csv.tmp`，`flush` + `fsync` 后替换；
   启动时清理遗留临时文件。**r3 增删规则不动**，只改物理写入方式。

**验证**（不联网项先做，全部用已缓存的 27 个跨年 txt 回归）：
- 表 1 正则对 27 个样本 **全部命中**，且每期 `南方 + 北方 = 合计`（已实测通过）。
- 阳性率等于基准表数值，误差 0（2023W1 0.04、2024W1 52.52、2025W14 2.85、2025W40 4.80、
  2025W52 41.90、2026W1 35.82、2026W10 9.02、2026W30 18.03）。
- 抽验 2026W44 URL → `4.8 / 17.14`（回归）；括号互校偏差 0.025% < 1.5%，通过。
- 造一份缺表 1 的文本 → 抛错，不产生数值。
- **误杀回归**：2024W26 必须正常入库（锚文本期号 811 vs PDF 810 只告警）；
  2025W20/30/40/52、2026W20/30/35/40/41/42/43/44（正文含累计区间）**不得**被误判为合并版。
- **中断安全（用 CSV 副本，不碰真实数据）**：把 `data/flu_south.csv` 复制成 20 行以上的测试副本，
  指向该副本，在一次 `save_rows` 写入过程中受控中断（如 monkeypatch 在 `writerows` 中途 `raise KeyboardInterrupt`）→
  副本**逐字节未变**且仍能完整读取；去掉中断后重跑 → 内容正确、遗留临时文件被清理。

### S2 列表枚举

5. 新增 `enumerate_archive()`：拉 ivdc 列表 → 解析条目 → `{(y,w): (title, url, pubdate)}`；
   页数取 `var countPage = N`（不硬编码、不靠空页判断，越界页返回 200 的伪页）；非周报条目跳过；
   同周重复保留列表靠前项并记录。

**验证**：枚举结果 2016–2026 各年周数与该期实测一致（2023=52、2024=52、2025=52、2026=44 已发布）；总条目 600±（新增周会增长）；与 `research/gap-analysis.md` 的覆盖表一致。

### S3 回补主流程

6. 新增 `backfill(from_w, to_w, force, limit)`：
   - 按 `(y,w)` 倒序或正序遍历枚举结果，默认跳过已有 ok 行；
   - txt 缓存 `.tmp_flu_backfill/txt/`，命中则不下载（`--force` 例外，见 design §3.2）；
   - 逐期 `http_get → find_pdf_link → pdf_to_text → parse_issue → upsert`；
   - 限速 2.5s；单期异常捕获后记 `changes.log: backfill_fail`，继续下一期。
7. `log_change()` 移植到本脚本（格式同 `fetch_sentinel.py:271-274`）。
8. `--from / --to / --force / --limit` 参数解析，插在 `src/fetch_flu_south.py:202` 的 URL 分支之前。
   `--from` 下界硬校验 `2023W1`（§0 分代表）：早于该周直接报错退出并说明原因，不静默裁剪。

**验证**：
- `--backfill --limit 2`：处理 2 期即退出，日志与 CSV 变化符合预期，不报"HTTP 获取失败: --backfill"。
- `--backfill --from 2022W20` → 退出码非 0，提示"早于 2023W1 的期次不可解析（见 design §0）"，且 CSV 未被改动。
- 中途 Ctrl-C 再跑：已 ok 周下载数 0；**且中断后 `data/flu_south.csv` 仍是完整可读的 CSV（不出现半张表/空文件）**，
  这是 §4.0 的验收点，实测方法见 S1 验证的"中断安全"。

### S4 全量回补

9. `python -X utf8 src/fetch_flu_south.py --backfill --from 2023W1`（约 25–45 分钟，0.9–1.1GB）。

**验证**：
- 覆盖对账（按最终状态归并，不数日志行）：200 个目标周互斥归入 `ok` / `pending_fail` / `merged_skip` 三类，
  三集合并集 = 全集且两两无交集；不成立则逐条查缺口。
- CSV：`(iso_year, iso_week)` 无重复、按周升序、只含 ok 行。
- 数值域：所有 `south_ili_pct`、`south_flu_positive_pct` ∈ [0,100]。
- 抽 8 期（每年 2 期，含年初/年末）与 PDF 原文核对。

### S5 无参回归 → 指数 → 端到端

**顺序不能颠倒**：无参模式写行时会用空字段打底（`src/fetch_flu_south.py:163-166`），
会把该周 `goldstein_index` 清空。因此回归必须放在最后一次 `compute_index` **之前**。

10. 无参回归：`python -X utf8 src/fetch_flu_south.py` → 2026W44 的 ILI%/阳性率不变（`fetched_at` 除外）。
11. `python -X utf8 src/compute_index.py` → 全部 ok 行有 `goldstein_index`。
12. `python -X utf8 src/build_site.py --local` → 页面能打开、南方片块显示最新周。
    **发布门核对**：最新周（2026W44）与紧邻上一周（2026W43）都必须有 ok 行与指数，
    否则页面会把 W44 与更早的周相比却标"较上周"（违反 D17）——此时不得声称页面可发布，列入阻塞项。

**验证**：
- `goldstein_index = ILI% × 阳性率`（2 位），抽 3 行手算；2026W44 仍为 82.27。
- 最终 CSV 与页面一致（页面构建于最后一次 compute 之后）。
- `site/index.html` 无外部加载资源（`--local` 打开正常）。

### S6 汇报 + 停靠

13. 输出核对清单（年/周/ILI%/阳性率/指数/来源 URL）写入 `.trellis/tasks/11-11-flu-south-backfill/research/backfill-report.md`。
14. 汇报：行数、覆盖对账结果、失败清单、抽验值。**停下等用户 Excel 核对**，不自行提交。

## 停靠点

S6 完成即停。用户核对 200 行后，再走"独立只读复核 → 两笔提交（docs / feat）+ push"。

## 回滚

- 数据：`git checkout -- data/flu_south.csv data/changes.log`
- 缓存：删 `.tmp_flu_backfill/`（含遗留的 `flu_south.csv.tmp`）
- 代码：分母修复与原子写入可保留（都是独立缺陷修复，与回补解耦）；`--backfill` 相关函数可 `git checkout -- src/fetch_flu_south.py` 整体回退

## 验收（对应 design.md §6）

- [ ] 抽验 2026W44 URL 仍输出 4.8 / 17.14
- [ ] 七期基准阳性率与表 1 南方分母一致（2023W1/2024W1/2025W14/2025W40/2026W1/2026W10/2026W30）
- [ ] 覆盖对账按最终状态互斥归并成立（200 周，三类并集=全集、两两无交集）
- [ ] `--from 2022W20` 被拒绝（退出码非 0），CSV 未改动
- [ ] CSV 无重复、按周升序、只含 ok 行、数值域合法
- [ ] 所有 ok 行 goldstein 非空且等于 ILI%×阳性率
- [ ] 续跑下载数为 0，CSV 逐字节一致
- [ ] **中断安全**：写入中途受控中断后 CSV 逐字节不变、仍可完整读取；遗留临时文件被清理
- [ ] r3 守卫：注入缺 ILI% 文本，已有 ok 行不动
- [ ] `--backfill` 不被当 URL
- [ ] 无参模式不改动既有数值
- [ ] **发布门**：2026W44 与 2026W43 均有 ok 行与指数（否则列为阻塞项，不声称可发布）
- [ ] `build_site.py --local` 正常构建，无外部加载资源
- [ ] 每年 2 期人工抽验与 PDF 一致

<!-- ======================== END IMPLEMENT (implement.md) ======================== -->

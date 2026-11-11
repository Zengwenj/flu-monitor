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

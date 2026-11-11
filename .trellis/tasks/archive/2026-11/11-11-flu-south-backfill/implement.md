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
   临时路径以 `ROOT` 为锚（`ROOT / ".tmp_flu_backfill" / "flu_south.csv.tmp"`，**不用相对路径**，避免跨卷失效）；
   `flush` + `fsync` 后替换；启动时清理遗留临时文件。**r3 增删规则不动**，只改物理写入方式。

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

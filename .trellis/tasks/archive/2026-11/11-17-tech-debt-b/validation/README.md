# B 组技术债 — 验证记录

日期：2026-11-17　执行：主会话（无子代理改写，全部现场实测）
基线 HEAD：`a4f70b4 chore(data): weekly update 2026-11-17`

## 结论速览

| 项 | 状态 | 关键证据 |
|---|---|---|
| B1 week_start 回填 + 写入源头 | ✅ | 非 week_start 单元格 diff = 0；2288 行全填；产物 SHA-256 不变 |
| B2 排名缺口原因细分 | ✅ | 夹具 6 类全过；正常周零影响；今日产物字节不变 |
| B3 changes.log 4 列旧契约 | ✅ 记录性关闭 | 147 行 = 5 列 143 + 4 列 4，不改写 |
| B4 Actions 大版本升级 | ✅ 代码 + dispatch 实测 | 4 个 action 运行时 node24；run success 且 annotation 清零 |
| B5 workspace 敏感排查 | ✅ 零命中 | 3 个 tracked 文件扫描，另 196 个 .trellis 文件仅 1 例误报 |

## 文件清单（本任务改动）

```
.github/workflows/weekly.yml         4 处 uses 升大版本
data/sentinel_national_rates.csv     week_start 列回填（2288 行）
data/changes.log                     +1 行留痕
src/fetch_sentinel.py                新增 iso_week_start()；write_week 调用
src/build_site.py                    新增 CHANGES_LOG + rank_gap_cause()；region_rank_block 占位分支附原因
```

## B1 细节

- `src/fetch_sentinel.py:21` `from datetime import date, datetime`。
- `src/fetch_sentinel.py:277` 起 `iso_week_start(y, w)`：`date.fromisocalendar(int(y), int(w), 1).isoformat()`，`ValueError/TypeError` → `""`（不猜值）。
- `src/fetch_sentinel.py:307` `write_week` 写入行改为 `"week_start": iso_week_start(y, w)`。
- 回填脚本 `.tmp_small/backfill_week_start.py`（`--apply` 才落盘；走 `data_io.atomic_write_csv` + 追加 changes.log 留痕行）。
- 证据 `b1b2-safety-evidence.txt`：
  - `HEAD rows=2288  工作副本 rows=2288`
  - `非 week_start 列的差异单元格数 = 0 {}`
  - `week_start 已填行数 = 2288 / 2288`
  - `distinct 周数 = 104；最早周=2024-11-11 最晚周=2026-11-02`
  - `未填周数 = 0`；`与 fromisocalendar 不符的周数 = 0`；`周次序列单调递增 = True`
- 夹具 `b1-write-week-fixture.txt`（CHECK1–5 全 True）：22 行完整性、`iso_week_start` 边界（2026W45→2026-11-02、2024W1→2024-01-01、2020W53→2020-12-28、2026W0→""、99999W1→""）、同周重写幂等、表头顺序、ranks 表写入。
- **页面惰性证明**：`site/index.html` sha256 回填前后均为 `5da6b12afb33ab2b0e651f8b5cb8af188004c29ad540c017d50141c955806910`（138227 bytes）。原因：`build_site.py:213-276` 的 `build_flu_view` 只读流感族 CSV 的 week_start，哨点 rates 该列不参与渲染。

## B2 细节

- `src/build_site.py:28` `CHANGES_LOG = ROOT / "data" / "changes.log"`。
- `src/build_site.py:769-793` `rank_gap_cause(y, w)`：逐行 split("\t")，匹配 `cols[1]==f"{y}W{w}"` 且 `cols[2]=="ranks"`，取最后一条；5 列取 `cols[4]`、4 列取 `cols[3]`；归一化为「该期为月度合并版，表2/3归属周次不明」/「该期表2版式差异，解析未取得」，其余原样返回。
- `src/build_site.py:857-863` `region_rank_block` 占位分支：`detail = f"（{_esc(cause)}）" if cause else ""`，拼到「本工具未取得{y}年第{w}周前三名排名」后。
- 夹具 `b2-rank-cause-fixture.txt` 8/8 PASS（月度合并版 / 版式差异 / 无记录文案不变 / 4 列旧契约 / 不含「官方未提供」/ 正常周不受影响 / `<script>` 已转义 / 真实数据今日无后缀）。
- 数据事实：11 个 `rank_unavailable` 占位周 = 2025W14–W22（9 周，月度合并版）+ 2026W6 + 2026W12（表2 行数 0 != 4）。今日锚周 2026W45 排名正常 → 产物零变化（当前 2 处「本工具未取得」是 `tpl-local_nodata`/`tpl-prov_nodata` 模板文案，与排名无关）。

## B3 细节

- `b3-log-columns.txt`：147 行，5 列 143 / 4 列 4。
- 4 列行为 `2025W33 table_sum_check`、`2026W11 cover_leftover_issue`，各出现两次（2026-11-11T15:34:17 与 2026-11-12T17:53:15）。
- 处置：**不改写**（审计完整性优先）。A2 套件已按历史变体接纳；B2 的 `rank_gap_cause` 亦兼容 4 列。

## B4 细节

- 变更：`checkout@v4→v7`、`setup-python@v5→v7`、`upload-pages-artifact@v4→v5`、`deploy-pages@v4→v5`；`runs-on: ubuntu-latest` 保留。
- 证据 `b4-actions-upgrade.txt`（全部来自 `gh api`，非记忆）：
  - latest：checkout v7.0.1、setup-python v7.1.0、upload-pages-artifact v5.0.0、deploy-pages v5.0.1。
  - `runs.using`：checkout `node24`、setup-python `node24`、deploy-pages `node24`、upload-pages-artifact `composite`（内部 `actions/upload-artifact@bbbca2d… # v7.0.0`，即 Node20 警告的传递依赖，升 v5 即解）。
  - 兼容性：artifact 名默认 `github-pages`、`page_url` 输出名、`path` 输入均未变。
  - `persist-credentials` 改存 `$RUNNER_TEMP` 但官方声明 "No workflow changes required"；Docker container action 才需 runner ≥ v2.329.0，本仓库 `git push` 是 shell step → 不受影响。

## B5 细节

- 扫描对象：`git ls-files .trellis/workspace` = 3 个文件（`index.md` 2307 chars、`zengw/index.md` 756、`zengw/journal-1.md` 89——后者仅标题+空行）。
- 模式：手机号 `(?<!\d)1[3-9]\d{9}(?!\d)`、邮箱、token/私钥（`ghp_`/`github_pat_`/`sk-`/`AKIA`/`BEGIN PRIVATE KEY`）、口令键值、bearer。
- 结果 `b5-secret-scan.txt`：workspace hits = 0。顺带扫其余 196 个 tracked .trellis 文件仅 1 例「命中」`.trellis/.template-hashes.json` → **误报**（sha256 十六进制串内的数字片段，上下文为 `"workflow_phase.py": "146b69c1ec0e62..."`）。

## 回归（全部现场执行）

| 套件 | 结果 | 说明 |
|---|---|---|
| `check_history_compat.py --check Reg` | 4/4 OK, exit=0 | 冻结 6 函数零改动 |
| `check_lit.py`（A4 套件） | 0 项失败, exit=0 | 45 项 |
| `check_search_query.py` | 56 tests, failures=3, exit=1 | 全部 Q6 pin：`changes.log`（本次 B1 留痕，授权）、`flu_north.csv`（既有漂移）、`locations.csv`（小项①别名补录，授权） |
| `py_compile`（build_site / fetch_sentinel） | OK | — |
| `build_site.py --local` | exit=0，产物哈希不变 | 见上 |

pin 失败口径：失败集合 = 既有 flu_north 漂移 + 本次两处 authorized 数据变更，无未解释项。

## 已知限制 / 遗留

1. `data/*.csv` 经 `data_io.atomic_write_csv` 写出为 CRLF（`newline=""`），而 `.gitattributes` 规定 `data/*.csv text eol=lf` → 工作副本 CRLF、提交归一为 LF。属既有契约差异，本任务不修 `data_io`。
2. `changes.log` 追加行为 CRLF，其余 146 行为 LF（同上，历史混合，不重写）。
3. `sentinel_rank.csv` 未改动，仍为 LF。

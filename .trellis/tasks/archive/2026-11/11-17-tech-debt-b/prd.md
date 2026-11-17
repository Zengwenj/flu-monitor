# B 组技术债：week_start 回填 + 排序缺口原因细分 + Actions 大版本升级 + 日志排查

## Goal

清理 `docs/handoff.md` §5「B 小技术债」五项，均为不紧急但会持续产生噪音/误导的遗留项。原则：**能只留痕就不改数据，能改写入源头就不改历史行**；页面渲染结果必须零变化（当前锚周无缺口、rates 的 week_start 页面不消费）。

## Requirements

### B1 `sentinel_national_rates.csv` 的 `week_start` 全空
- R1.1 写入源头 `src/fetch_sentinel.py` 的 `write_week` 必须真算 ISO 周一：新增纯函数 `iso_week_start(y, w) -> str`，用 `date.fromisocalendar(y, w, 1).isoformat()`；非法周次（W0、越界年）返回空串，**不猜值、不抛异常**。
- R1.2 历史 2288 行就地回填（104 个 distinct 周，2024W46→2026W45）。
- R1.3 回填只动 `week_start` 列，其余任何单元格不得变化；必须留痕 `data/changes.log`（tab 5 列现行契约）。
- R1.4 页面产出必须与回填前字节相同（`build_site.py:213-276` 只消费流感族 week_start，哨点 rates 的该列不参与渲染——这是允许回填的前提，需实测证明）。

### B2 排序缺口 11 周的两类原因未在页面细分
- R2.1 新增模块级 `rank_gap_cause(y, w)`，从 `data/changes.log` 的 `ranks` 行读取该周记录（取**最后一条**），兼容 4 列历史契约与 5 列现行契约。
- R2.2 归一化只做本工具侧的**记录复述**（月度合并版 / 表2 版式差异），**不得断言官方原因**，也不得输出「官方未提供」之类越权措辞。
- R2.3 只在 `region_rank_block` 的 `rank_unavailable` 占位分支附加原因（该函数不在冻结 6 项内）；`child_block` 等冻结函数零改动。
- R2.4 正常周（status=ok 有名称）输出不得受任何影响；原因文本必须经 `_esc` 转义。

### B3 `changes.log` 部分历史行是 4 列旧契约
- R3.1 不改写历史行（审计完整性优先），仅核对并记录分布（5 列/4 列各多少行、4 列行内容）。

### B4 Actions 弃用提醒（Node20→24、ubuntu-latest→26）
- R4.1 升级到仍在维护的大版本：`actions/checkout@v7`、`actions/setup-python@v7`、`actions/upload-pages-artifact@v5`、`actions/deploy-pages@v5`。
- R4.2 升级前必须核实：各 action 的运行时已是 node24；输入名/默认 artifact 名（`github-pages`）/输出名（`page_url`）未变；`persist-credentials` 变更不影响本 workflow 的 shell `git push`。
- R4.3 `runs-on: ubuntu-latest` 保留（GitHub 已自动迁移到 26，pin 具体版本反而会过期）。
- R4.4 升级后必须真跑一次 dispatch，确认 run success 且 **无 Node20/ubuntu 弃用 annotation**。

### B5 `.trellis/workspace/` 日志敏感排查
- R5.1 扫描仓库内 tracked 的 `.trellis/workspace/` 文件（该目录在 public 仓库内），模式覆盖手机号/邮箱/token/私钥/口令/bearer。
- R5.2 命中必须逐条判定真伪并给出处置；误报需说明误报原因。

## Acceptance Criteria

- [ ] B1：夹具证明 `write_week` 写入正确周一（含边界 W1/W53/W0/越界年）；真实 CSV 回填后非 `week_start` 单元格 diff = 0；`build_site --local` 产物 SHA-256 回填前后一致。
- [ ] B2：夹具覆盖「月度合并版/版式差异/无记录/4 列旧契约/正常周/HTML 转义」六类；真实数据当日产物字节不变。
- [ ] B3：列数分布与 4 列行清单已留档，明确不改写。
- [ ] B4：dispatch run conclusion=success，annotations 中不再出现 Node20 强制升级与 ubuntu-latest 迁移提示；线上首页 HTTP 200 且关键结构串仍在。
- [ ] B5：扫描结果留档，命中项（若有）已判定并处置。
- [ ] 回归：`check_history_compat --check Reg` 4/4；`check_lit` 0 项失败；`check_search_query` 失败集合 = 仅 Q6 pin 类（flu_north 既有漂移 + 本次 authorized 的 changes.log/locations.csv 漂移）。
- [ ] 文档：`docs/handoff.md` §5 B 列表更新为已完成，并记录 B4 的新版本号与新坑（如有）。

## Notes

- 冻结函数 6 项（`_adjacent_week`/`svg_sparkline`/`trend_block`/`ranking_block`/`child_block`/`sichuan_block`）本次零改动，`region_rank_block` 不在其中。
- `data_io.atomic_write_csv` 用 `newline=""`（Windows 写 CRLF），而仓库 `.gitattributes` 规定 `data/*.csv text eol=lf` → 回填后工作副本为 CRLF、提交时归一为 LF，属既有契约差异，**不在本次修 data_io**。
- 页面零变化是 B1/B2 的核心安全网：任何字节差异都必须先解释清楚再提交。

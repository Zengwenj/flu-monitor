# Design：M3a 数据层（data-fetch 完整实施）

> M3a = data-fetch 子任务的完整实施。在 M2 流感切片（flu_south.csv + fetch_flu_south.py）基础上扩展多病原/排序/FluNet/历史回补。继承 M2 的 r3 写入契约、状态枚举、pdftotext utf-8、urllib→curl 回退。
> 基于 M1 可行性报告 + metis 缺口分析（2026-11-09）。〔G#〕标注 metis 缺口消解点。

## 范围（M3a 做什么）

1. 中疾控哨点周报**表1**：全国 11 病原阳性率（门急诊 ILI + 住院 SARI，各含本周值+较上周）
2. 哨点周报**表2/表3**：南北片、4 年龄组的前三名病原（名称排序，支持并列）
3. **WHO FluNet** 中国全量（按列映射表入库）
4. **哨点周报历史回补**（约 100 期，先验分页机制）

**M3a 不做**（归 M3b/缓做/M4）：任何页面渲染（M3b）、流感周报多年回补（缓做）、四川识别脚本（M4）、同期对比计算（M3b 用文字差值）。

## 数据契约（新增文件，与 M2 的 flu_south.csv 并存不改）

### `data/sentinel_national_rates.csv`（表1，长表〔G2〕）
列：`iso_year, iso_week, week_start, setting, pathogen, positive_pct, delta_last_week, source_url, source_pubdate, fetched_at, status`
- `setting` ∈ `门急诊 / 住院`；`pathogen` = 11 病原之一
- **长表**（每周 11×2=22 行）理由〔G2〕：病原将来可能增减，长表加病原不改 schema；M2 的 flu_south.csv 保持宽表不动（它只 2 个数值，宽表更直观）
- 主键 `(iso_year, iso_week, setting, pathogen)`
- r3 写入扩展〔G5/B2〕：以"周"为覆盖单位。**"成功"的严格判定**：当周必须解析出完整 22 行（11 病原 × {门急诊,住院}，键唯一无重复、positive_pct 均为有效数字）才算 ok，才允许覆盖该周旧行。**任一缺失/重复/无效 → 判为 parse_failed，不覆盖任何旧周**（保留旧的完整周）。上游修订=新周同样通过 22 行完整校验后整周重写，变更摘要写入 `data/changes.log`（追加：时间/周次/字段/旧值→新值）留痕

### `data/sentinel_rank.csv`（表2/表3，排序）〔G7〕
列：`iso_year, iso_week, dimension, category, setting, rank1, rank2, rank3, source_url, fetched_at, status`
- `dimension` ∈ `region / age`；`category` = 南方省份/北方省份 或 0-4岁/5-14岁/15-59岁/60岁及以上
- `rank1/2/3` 存原始字符串，**并列直接存顿号串**（如 `"流感病毒、腺病毒"`）〔G7〕，界面原样展示不机器解析
- 主键 `(iso_year, iso_week, dimension, category, setting)`

### `data/flunet_china.csv`（WHO FluNet）〔G6〕
列映射（从 32MB 全量 CSV 筛 `COUNTRY_CODE=CHN`，按官方表头字典取）：
`iso_year(ISO_YEAR), iso_week(ISO_WEEK), week_start(ISO_WEEKSTARTDATE), spec_processed(SPEC_PROCESSED_NB), inf_all(INF_ALL), inf_a(INF_A), inf_b(INF_B), inf_positive_pct(=INF_ALL/SPEC_PROCESSED_NB), source=WHO_FluNet, fetched_at`
- M3a 实现前先用表头行确认列名精确拼写（M1 见 NOTDEFINED 列须避开）；分型列缺失/空值按空存不报错
- 定位：全国背景+交叉校验，**不作南方片指数输入**（D15/D17）

## 技术要点（metis 消解）

- **哨点表1 解析**：复用 M2 已验证的 pdftotext？否——哨点周报表1 在 HTML 网页正文（非 PDF，M1 实测），用 webReader/urllib 取 HTML 表格解析。11 病原×2 列数值+较上周（带 +/- 符号）。
- **历史回补分页**〔G8/B3〕：哨点列表页 `chinacdc.cn/jksj/jksj04_14275/` 翻页机制 M1 未验。**S1 先验**：试 `index_1.html`…等静态分页 URL（流感周报已证实 `index_N.html` 式）。
  - 若静态分页 → 遍历各页取全部历史期 URL，批量回补至 2024-W46。
  - 若 JS 动态加载首屏之外取不到 → **不降级放行**，依次尝试替代发现路径：① 直接构造文章页 URL 规律（M1 已知形如 `/YYYYMM/tYYYYMMDD_NNNN.html`，按周递推探测）② 站内检索 ③ 若仍无法枚举，则历史回补记为**未完成阻塞项**，附已获期次清单与缺口，交用户决定（不得在历史回补目标未达成时标 M3a 验收通过）。
- **FluNet 下载**〔G6〕：curl 下 32MB（M1 实测 25s），流式筛 CHN 行，不全量入内存。
- **历史深度标注**〔G9〕：哨点周报 2024-W46 开办，至今约 2 年——多病原同期对比最多"去年同周"，无"前几年"。CSV 不处理，交 M3b 展示层显式标注"数据自 2024 年第 46 周起"。

## 验证方式

1. 跑表1抓取→`sentinel_national_rates.csv` 某周 22 行，与官网当期网页表1人工核对（抽 3 病原）
2. 表2/表3→`sentinel_rank.csv`，并列情形（找一期有顿号的）正确存串
3. FluNet→`flunet_china.csv`，**行数与覆盖范围校验**〔B4〕：中国行数≈1021（M1 实测基准，允许随新周增长）、最早周=2005 年、最新周 inf_positive_pct 与 M1 值吻合、无 NOTDEFINED 混入数值列
4. 历史回补：分页先验结论明确；回补后周次连续无重复，changes.log 机制在模拟上游修订时留痕
5. r3 周级覆盖：模拟某周失败→旧周 22 行不动

## 回滚

全部新建文件（sentinel_national_rates.csv / sentinel_rank.csv / flunet_china.csv / changes.log + 对应抓取脚本），不改 M2 的 flu_south.csv 与三脚本。失败删新增文件。

## 与 M2/M3b 的边界

- 不改 M2 的 flu_south.csv/fetch_flu_south.py/compute_index.py/build_site.py
- M3b 读本阶段产出的 3 个 CSV 做展示；compute_index 的多病原/同期对比逻辑属 M3b
- 新增抓取脚本建议：`src/fetch_sentinel.py`（表1+表2/3）、`src/fetch_flunet.py`

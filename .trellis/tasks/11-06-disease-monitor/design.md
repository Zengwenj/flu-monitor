# Design：M3b 展示层（仪表盘）

> M3b = 在 M2 极简分块页基础上升级为阶段二仪表盘，横跨 compute-index（计算扩展）+ build-site（渲染）两个子任务。消费 M3a 产出的 3 个新 CSV。继承 M2 方式A内联 / file://离线 / 无外部依赖 / 分块不合成总分 / 状态文案枚举 契约。
> 基于 metis 缺口分析（2026-11-09，GAP-1~10）+ 用户 3 项决策。前一里程碑 M3b 的 design 覆盖 M2 版（M2 版见 git 1aad7ea）。

## 用户已定（本次 AskUserQuestion）

- **趋势图**：本年度全国哨点阳性率逐周折线，**不叠往年线**（数据仅约2年+D17禁口径混用），内联 SVG 渲染（零外部依赖，file://可开）〔GAP-1/3〕
- **往年差值块**：显占位"待历史回补后启用"，**不碰 M2 的 fetch_flu_south.py**〔GAP-2〕
- **多病原排行**：全 11 病原按门急诊阳性率降序〔GAP-4〕

## 默认假设（metis 建议，带入实施，可随时叫停）

- 儿童卡：显门急诊 0-4岁 + 5-14岁 前三名，标注"全国哨点门急诊、排序非数值"〔GAP-8〕
- 排序占位：2026W6/W12 与 2025W14-22 统一显示"该期排序未获取"，不 join changes.log 细分〔GAP-6〕
- 趋势图 X 轴：用"第N周"标注，不推算 week_start 日期（避免跨年 ISO 周验证）〔GAP-7〕
- 合并版空 source_pubdate：显示"（月度合并版，日期未单独标注）"〔GAP-9〕
- compute/build 两步顺序执行各自验收，M3b 不再细拆〔GAP-10〕

## 职责边界（GAP-5 消解）

- **compute_index.py 扩展**：新增函数读 sentinel_national_rates.csv / sentinel_rank.csv，产出**内存中的汇总结构**传给 build（不写新中间 CSV）。Goldstein 部分不动。
  - `pathogen_ranking()`：取最新 ok 周 11 病原门急诊行降序（数值主数据，sentinel_national_rates.csv 的 rates 几乎每周齐全）
  - `child_rank()`〔B3 修正〕：取最新**有排序数据的**周（可能与 rates 最新周不同）；**返回结构含该周 status**——若目标周 sentinel_rank.csv 为 rank_unavailable，返回 `{available:False, week, reason}` 供渲染层显占位，而非跳过该周静默取更早周。调用层据 available 决定显数据还是显"该期排序未获取"。
- **build_site.py 扩展**：调 compute 的汇总函数 + 新增 3 块渲染 + SVG 趋势图生成。方式A内联不变。
- **不改**：fetch_flu_south.py、fetch_sentinel.py、fetch_flunet.py、三个 data CSV、compute_index.py 的 Goldstein 逻辑。

## 页面结构（M2 两块 → M3b 升级为分块仪表盘）

```
成都·呼吸道防护参考（标题不变）
├ [横幅] 数据失败/过期提示（沿用 M2 逻辑）
├ 块1 四川官方分级（M2 既有，不动）
├ 块2 南方片流感（M2 既有：Goldstein+ILI%+阳性率+环比）
├ 块3 本周vs往年同期  → 占位"待历史回补后启用"〔新，GAP-2〕
├ 块4 全国多病原活跃度排行〔新〕：11 病原门急诊阳性率降序，每行 病原名+阳性率+环比箭头(↑/→/↓较上周)
├ 块5 流感/新冠/RSV 本年度趋势〔新〕：3 条内联 SVG 折线（全国门急诊阳性率，X=第N周，Y=%）
├ 块6 儿童分龄前三〔新〕：0-4岁/5-14岁 门急诊前三名病原（排序非数值）
└ [脚注] 口径说明（扩充：新增块均为全国哨点口径，非成都；排序为名称非数值）
```

## 关键技术点

### SVG 趋势图（GAP-3 选项1）
- compute 从 sentinel_national_rates.csv 取某病原逐周门急诊 positive_pct 序列（按 iso_year,iso_week 排序）
- build 用纯 Python 生成 `<svg>`：折线 polyline + Y 轴刻度(0~峰值) + X 轴稀疏周标 + 当前值点
- 3 个病原（流感/新冠/RSV）各一张小图（sparkline 风格），内联进 HTML
- 无 JS、无 Canvas、无外部库——SVG 字符串直接插值（file:// 绝对安全）
- 缺数据周：polyline 断点（不连线），不画 0

### 多病原排行（GAP-4）
- 取最新 ok 周的 11 病原门急诊行，按 positive_pct 降序
- 环比箭头：delta_last_week >0 ↑ / =0 → / <0 ↓（空串=未提供，显"—"）〔GAP-9 合并版 delta 空〕
- D17："增加 N 个百分点"不写"N%"

### 环比箭头 vs 往年（D17 一致性）
- 箭头只表较上周（delta_last_week 原生）；不涉及往年（往年块占位）

## 数据状态文案（沿用 M2 枚举 + 新增）

| 场景 | 文案 |
|---|---|
| 往年差值块（本期） | 待历史回补后启用 |
| 排序占位周 | 该期排序未获取（官方版式差异/月度合并版） |
| 合并版无发布日 | （月度合并版，日期未单独标注） |
| 多病原 delta 空 | —（未提供） |
| 趋势图缺数据周 | 断点（不连线） |

## 验证方式

1. compute 扩展：单元跑通读 3 CSV，打印 11 病原排行 + 儿童前三 + 趋势序列长度，与 CSV 抽样核对
2. build：生成 index.html，file:// 打开——6 块齐全、SVG 折线正常显示、无**加载型**外部请求（grep 0 处 fetch/script src/link href/img src=http/url(http；官方来源 `<a href>` 允许保留）、手机排版
3. 口径标注：新增块均标"全国哨点口径非成都"；排行用"百分点"
4. 异常：某病原全周缺→趋势图该线断点不画0；排序占位周→显"未获取"不空白
5. M2 隔离：fetch 三脚本 + 三 data CSV + compute 的 Goldstein 逻辑 git diff 空

## 回滚

M3b 改 compute_index.py + build_site.py + site/index.html（均 M2 已 tracked）。回滚=git checkout 这三个文件回 M3a 后状态。数据 CSV 不动。

## 兼容性

不推翻 M2 方式A契约；不改 M3a 数据产物；M4 自动化时 build 调用链不变（compute→build）。

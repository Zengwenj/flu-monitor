# Implement：M3b 展示层执行清单

> 仪表盘升级。技术契约见本目录 design.md。继承 M2 方式A/file://离线。已获 metis 分析+用户 3 决策；momus APPROVE + 用户批准后执行。覆盖 M2 版（git 1aad7ea）。

## 执行前
- [ ] momus 复审 M3b design/implement → APPROVE
- [ ] 用户批准 M3b（写代码）
- [ ] 不改 fetch 三脚本、三 data CSV、compute 的 Goldstein 逻辑

## 有序步骤

### S1 compute 扩展（计算层，先验数据结构）
- compute_index.py 新增函数（不动 Goldstein）：
  - `pathogen_ranking()`：读 sentinel_national_rates.csv，取最新 ok 周 11 病原门急诊行，按 positive_pct 降序，附 delta 箭头
  - `child_rank()`：读 sentinel_rank.csv，取最新**有排序数据**周的 age 维度 0-4岁/5-14岁 门急诊前三；〔B3〕返回含 `available` 标志——目标周为 rank_unavailable 时返回 `{available:False, week, reason}`，不静默回退更早周，供渲染显占位
  - `pathogen_trend(pathogen)`：读 sentinel_national_rates.csv，某病原逐周门急诊序列（流感/新冠/RSV 各一）
- **验证**：命令行跑这几个函数，打印结果与 CSV 抽样核对〔样例以实测最新 ok 周 2026W44 为准，B1 修正〕：排行首位=流感病毒 15.6（门急诊）、第二鼻病毒 11.4、第三人偏肺病毒 4.3；0-4岁门急诊前三=①鼻病毒②流感病毒③副流感病毒；流感趋势序列长度=ok周数（当前 103）。注：验证时以运行时实际最新周为准重新核对，不硬编码周次。

### S2 SVG 趋势图生成器
- build_site.py 新增 `svg_sparkline(series)`：Python 生成内联 `<svg>`（polyline+轴+点），缺周断点
- **验证**：单元测一条真实序列→输出合法 SVG 字符串；手工塞一个缺周→断点不画0

### S3 build 渲染 6 块
- build_site.py：保留 M2 块1(四川)/块2(南方流感)，新增块3占位/块4排行/块5趋势3图/块6儿童卡；脚注扩充口径
- 状态文案只用 design 枚举表
- **验证**：生成 index.html，file:// 打开——6 块齐全、SVG 显示、排行降序正确、儿童卡标注齐、往年块显占位

### S4 离线与隔离校验
- 检查 index.html **无加载型外部资源**〔B2 修正：只查会触发网络加载的标签/属性，不误伤正当来源超链接〕：
  grep 命中 `fetch(`、`<script src=`、`<link ...href=`、`<img src="http`、`url(http`（CSS）——均应为 0；
  **允许** `<a href="https://...">`（官方来源跳转链接，不加载资源、不破坏 file:// 离线）
- 手机宽度排版正常（窄屏不溢出）
- git diff 确认 fetch 三脚本/三 CSV/compute Goldstein 段未改
- **验证**：上述全过（加载型外部资源 0 处；a 超链接允许保留）

### S5 异常 + 端到端 + trellis-check + 汇报
- 异常验例：①某病原造全周缺→趋势线断点不画0 ②〔B3〕造"最新排序周为 rank_unavailable"情形→child_rank 返回 available:False、页面儿童卡显"该期排序未获取"（不静默回退更早周、不空白）③多病原 delta 空→显"—"
- 清空重跑 compute→build 一次确认可复现
- 可操作核对输出：本次排行首位病原+阳性率、趋势图覆盖周数、儿童前三
- 派 trellis-check 复核 → 汇报停下等用户验收

## 停靠点
S5 完成即停。用户验收仪表盘后，M3 整体（M3a+M3b）完成，进 M4 自动化。

## 回滚
git checkout compute_index.py build_site.py site/index.html 回 M3a 后状态。数据 CSV 不动。

## 验收（对应 roadmap M3b + metis 消解）
- [ ] 6 块仪表盘 file:// 离线可开，无外部请求
- [ ] 趋势图本年度折线（不叠往年）、缺周断点、SVG 内联
- [ ] 多病原 11 降序 + 环比箭头 + "百分点"措辞
- [ ] 儿童卡 0-4/5-14 门急诊前三 + 口径标注
- [ ] 往年差值块显占位；排序占位周显"未获取"
- [ ] M2/M3a 产物零改动（git diff 空）

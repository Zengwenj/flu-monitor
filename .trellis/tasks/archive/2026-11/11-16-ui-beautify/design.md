# A4 界面美化 · design.md（r3）

> 任务：`.trellis/tasks/11-16-ui-beautify` ｜ 日期：2026-11-16 ｜ 状态：r2 复审 6/7 关闭 + 新增 08/09，已全部修订（A4-PLAN-06/08/09），待用户裁决后续（round 3 复审或直接批准实施）；修订对照见 §10
> 依据：`docs/handoff.md` A4、`CONTEXT.md` D1–D19、gap 分析 GAP-A4-01~07（本任务 research/）、designer 视觉规格 v1（已按已核事实修正三处，见 §8）。

## 1. 目标与非目标

### 1.1 用户目标（m00039 原话）
「界面清晰可读性强，界面设计重点突出，突出现代、科技元素，元素设计和配色适配 flumonitor（流行病监测）主题。」

### 1.2 用户已确认的四项设计决策（m00186，问题卡全选推荐）
1. **浅色医疗风**（不做深色模式）
2. **双主角并列**：四川官方分级 + 南方片指数
3. 四川分级卡 = 左侧色条 + 等级徽章/标尺，不整卡染色
4. **≥900px 双列仪表盘**，wrap 上限约 1080px

### 1.3 量化的问题基线（改前实测，probe_style.py，见 research/audit-*.txt）
- 360px：152 文本节点，**25 处低于 WCAG AA**，33 处 <12px；first_big=411、second_big=828（首屏只见第 1 个 .big）
- 1280px：24 处低于 AA，32 处 <12px；first_card=265、second_big=599
- 最差对比度：.q-ver 2.35、.hist-sub2 2.66、.hist-scroll-hint 2.85、.sub 3.28、.unit/.hist-sub/hist-tbl 表头 3.54
- 布局：640px 单列，桌面两侧大量空白；卡标题 15px #555 与正文争夺注意力；所有状态共用一种浅蓝 .tag
- 无横向溢出（320/360/414）——**本轮不修溢出类问题，因为不存在**

### 1.4 非目标（明确不做）
- 深色模式（冻结函数硬编码浅底灰字，改不干净；用户已选浅色）
- 霓虹/外发光、玻璃拟态 backdrop-filter、入场动画/数字滚动、径向进度环（环暗示百分比，与 D17"相对强度非百分位"冲突）、粒子/视差
- 任何行为契约变更：搜索交互、397 目录、JS 逻辑、模板结构、文案语义
- 任何数据/管线变更；不碰 data/*.csv
- 不修复 B 小技术债（week_start 空值等）
- 桌面端 3 列及以上布局（信息密度与可读性折中取 2 列）

## 2. 设计系统：「检验单」（Clinical Readout）

视觉隐喻 = **一份可核查的检验报告单**：白纸、发丝线、等宽编号；数据靠位置和对齐建立秩序。科技感来自精度（等宽数字、mono 眉标、五级标尺、网格纹理），不来自发光和深底——发光/深底会制造语义污染（把"存量数据"读成"警报"，踩诚实性红线）。

### 2.1 色彩双轴（本方案地基）

| 轴 | 用途 | 允许位置 | 禁止 |
|---|---|---|---|
| 病种识别色（#c0392b 流感/#7f8c8d 新冠/#8e44ad RSV/#1f4e79 等历史系列色） | 只标识"这条线是谁" | **折线、端点**（SVG 数值文字一律重着色为可读墨色，见 §3-2 边界） | 任何实心填充块、卡片底、状态文字、**图内数值文字** |
| 数据状态色 | 表达新鲜/待更新/失败/未知 | 状态点、1px 左边条、状态文字 | 给地区判"风险高低" |

红色总面积 < 全页 1%，仅以 1.6px 线宽 + 2.6px 端点出现（护栏写入 CSS 注释）。

### 2.2 色板（全部实算过 WCAG 对比度）

- 背景：`--bg:#E9EEF1`（页面底）、`--surface:#FFF`（卡）、`--surface-2:#F4F7F8`（引文/斜纹底）、`--notice:#FFF6E5`（横幅）、`--hair:#DDE5E8`/`--hair-strong:#C3D2D7`（描边）、`--field-border:#7B8C93`（输入/按钮边框 3.49 ✓）
- 文字：`--ink-1:#0E1B20`（标题/关键数字/表正文 17.55 ✓）、`--ink-2:#3D4E56`（卡标题/标签 8.67 ✓）、`--ink-3:#56686F`（.src/.meta/.foot/图表标注 5.82 ✓）、`--ink-4:#8C9BA2`（**仅** placeholder/disabled/装饰角标）、`--link:#0A6273`（6.98 ✓）
- 品牌：`--brand:#0B5D6B`（7.52 ✓）、`--brand-soft:#E5F0F2`、`--focus:#0A6B7A`（6.18 ✓）
- 状态：正常 `#0F6B4F` 点+文字（6.49 ✓）；待更新 `#7A4E00`/`#FFF6E5` 左边条（6.71 ✓）；失败 `#A02D1E`/`#FFF6E5` 左边条（6.77，**唯一允许的红色文字**）；**未知 = `--ink-2` 文字 + `--surface-2` 底 + 1px 虚线 `#7B8C93`**（第三态，色阶之外，绝不落成Ⅴ空心版）
- 五级官方分级（单色相单调明度，Ⅴ 浅→Ⅰ 深；**方向已核**：CONTEXT.md:15「V 低→更高」+ LEVEL_ADVICE 与之互证）：
  Ⅴ `#D8E8EB`/字`#2F5760`（6.28）｜Ⅳ `#AECFD6`/`#0C3F4A`（6.95）｜Ⅲ `#7FAEB9`/`#062A32`（6.25）｜Ⅱ `#3D7C8B`/白（4.71）｜Ⅰ `#14505F`/白（8.96）。不用红黄绿：Ⅴ 是最低级，红黄绿会反向；五级是序数，正确编码是明度单调。

### 2.3 排版

- 字体栈：`--sans` = -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei UI"/"Microsoft YaHei", "Noto Sans CJK SC", sans-serif；`--mono` = ui-monospace, "Cascadia Mono", Consolas, Menlo（**只用于纯 ASCII/数字标识**：周次、序号、眉标；中文不配 mono）
- 阶梯：`.big` 46px/700（≥720）/34px（<720，保证 320px 不换行爆宽）；h1 21px/600；`.card h2` **13px/600/0.02em `--ink-2`（降级标题、升级数字——重点突出的第一手段）**；正文（.adv/.chain/.rank/.kv）**15px**/1.62；`.kv b` 20px/600；`.src`/`.meta`/`.foot` **12px** `--ink-3`；`.tag` 12px/500；mono 眉标 **12px**/600/0.08em（与 V6 的 ≥12px 口径统一，r2 修订 A4-PLAN-03）
- 数字：`.big`/`.kv b`/`.rank`/`.hist-tbl` 全部 `font-variant-numeric:tabular-nums`（.big 现状缺失，是数字跳动根因）；`.big` 字距 -0.02em；`.unit` 13px/500/`--ink-3`
- `.big.nodata`：24px 不加粗 `--ink-3`（缺测数字物理上明显小于真实数值，防扫视误读）

### 2.4 布局

- 断点（r2 统一口径，A4-PLAN-A03）：<720 单列 padding 16px；720–899 单列 padding 24px；**≥900 双列栅格**（媒体查询 `min-width:900px`，用户决策④）；≥1024 wrap 上限 `min(1080px,100%)`（900–1023 双列流体宽，不设上限）。验收补测断点邻域 880/900/920（V5）
- **栅格：`#default-view` 直接 `display:grid; grid-template-columns:repeat(12,1fr); gap:20px; align-items:start`（≥900px，用户决策④）**。不加 wrapper（banner 首子问题，见 §4 GAP-A4-05）、不加卡类（Q10 字面切块，见 GAP-A4-04），**用 `:has()` 内容签名定位**（已验证默认视图 6 卡签名互斥，见 research/scan_sigs 输出）：
  - `.card:has(.adv)`（sc）span 12 ｜ `.card:has(.kv)`（flu_south）span 5 ｜ `.card:has(.hist-tbl)`（hist_south）span 7 ｜ `.card:has(.rank)`（rank）span 5 ｜ `.card:has(.trendrow)`（trend）span 7 ｜ `.card:has(.childg)`（child）span 12
  - 行分配 12 / 5+7 / 5+7 / 12，每行满 12 无空洞；DOM 序=视觉序（禁 order/grid-row 重排，保 Tab 序）
  - `.banner` 与未匹配卡一律 `grid-column:1/-1` 兜底；**不支持 :has() 的浏览器自动退化为单列（等同现状）**，无需 @supports
  - **隐藏守卫（r2 修订 A4-PLAN-01）**：搜索 JS 靠 `defaultView.hidden=true` 切视图（src/build_site.py:1363-1364,1338-1342），而作者级 `#default-view{display:grid}` 会覆盖 UA 的 `[hidden]{display:none}` → CSS_THEME 内显式写 `#default-view[hidden]{display:none}`（特异性 id+属性 > id，先于网格规则生效），不修改 JS。配套 V5b headless 驱动验证（check_view_toggle.py）
  - `#query-view > .card{grid-column:1/-1}` 保持查询视图单列阅读流
- 卡：padding 14px 20px 18px；`border:1px solid var(--hair)`；圆角 12→**10px**；阴影近零 `0 1px 2px rgba(14,27,32,.04)`（描边承担分层）
- 长文（.adv/.foot/.hist-sub）`max-width:68ch`
- 首屏优先级：sc（唯一满宽+品牌竖条+标尺）> 南方片 89.1（46px+眉标）> rank > hist_south > trend > child

## 3. 六个「现代科技元素」做法（按性价比）

1. **五级标尺 level rail**（最值）：hero 内 5 段 6px 色条 + 段下 mono 罗马数字 Ⅴ–Ⅰ，当前级实心、其余 opacity .22，`aria-hidden`（等级已在 .big 文字中）。一眼看出"Ⅳ 在五档中的位置"，天然无合成分数（D14 合规）。实现于 `_sc_body`（**未冻结**，src/build_site.py:1075-1112）：rail 插在 .big 与 .meta 之间；empty 态不加 rail，`<div class="big">？</div>` 改 `<div class="big nodata">？</div>`（文案不动）。
2. **SVG chrome 重着色**（零 Python 改动，属性选择器）：`svg text[fill="#999"]{fill:#3D4E56}`、`text[fill="#6b7280"]` 同理；`line[stroke="#e5e7eb"/"#eef0f2"]→#EFF3F4`；`line[stroke="#9ca3af"/"#d1d5db"]→#9FB0B6`；`rect[fill="#f3f4f6"]→#F4F7F8`。**只重着色 chrome 与文字，绝不碰折线/端点的数据系列色**（#c0392b/#7f8c8d/#8e44ad/#1f4e79 的 stroke 属性原样保留）。**文字/线条边界（r2 修订 A4-PLAN-04）**：SVG 内数值文字（如新冠末端百分比 #7f8c8d≈3.48:1）一律经 `svg text[fill="#c0392b"],svg text[fill="#7f8c8d"],svg text[fill="#8e44ad"]{fill:#3D4E56}` 重着色为可读墨色（8.67 ✓）——识别语义由折线+端点承载，文字只负责可读；数值内容与系列线色不变，HTML 属性 hex 原样保留（CSS 只覆盖呈现）。**hex 次数验收范围（r3 修订 A4-PLAN-08）= 产物中 `<svg>…</svg>` 片段内的属性 hex，显式排除 `<style>` 与注释**（新增 CSS 选择器自身含系列色 hex，全页 grep 必然不等）；改前参照快照 `.tmp_a4/before-product.html`（实施前对当前产物整页拷贝）。风险：hex 耦合 → CSS 注释声明（注释本身不含被拦子串）+ 新增回归断言（产物 SVG 片段仍含这些 hex）。
3. **卡左上角 mono 序号**：`.card{counter-increment:card}` + `.card::before{content:counter(card,decimal-leading-zero); 12px mono}`，h2 让位 padding-left。纯 CSS 零 DOM。pointer-events:none。若读屏报号不可接受 → 退化为 12px 品牌色小方块（评审可裁）。
4. **hero 微网格底纹**：两层 `repeating-linear-gradient`（0deg/90deg，1px 线 @24px）叠在浅渐变上，整体 opacity .035，仅 hero 卡，print 隐藏。不超 .06。
5. **账本式表格**：`.rank`/`.hist-tbl` 行分隔 1px `#EFF3F4`，表头 **12px** mono/0.08em/`--ink-3`，数值列右对齐 tabular-nums；当前年行 `#F4F7F8` 底 + 左 2px `--brand` 条（位置标记非颜色标记）；hover（仅 hover:hover 媒体）`#F7FAFB`。
6. **统一焦点环**：全部可交互元素 `outline:2px solid var(--focus); outline-offset:2px`，替换现状 1px/2px 混用。

另外两项可读性修复（非"科技"但必做）：
- **sparkline 周标放大**：`svg text[font-size="9"]{font-size:10px}`（CSS 覆盖呈现属性，冻结函数字节不动）+ <520px 时 .tlabel 从 72px 侧列改为堆叠在 SVG 上方（SVG 可用宽 296px，缩放比从 0.72 提到 0.98）
- **状态四态化（r3 修订 A4-PLAN-06：按四川数据模型真实语义映射）**：.tag 现状"数据正常"与"未获取"同貌 → 按 §2.2 状态色重排。状态输出落点映射：

| 状态 | 类名 | 默认页落点（生产者，冻结状态） | 判定依据（**不重算日期**） |
|---|---|---|---|
| 当月已确认 | `st-ok` | sc 卡 `.meta > .tag`（`_sc_body` :1075，**未冻结**） | 冻结 `sichuan_block()`（:653-664）返回 `state=="ok"` 且 `line` 以「数据正常」开头（:660） |
| 存量待更新 | `st-wait` | 同上 | `state=="ok"` 且 `line` 含「本月待更新」（:662）——**当前真实数据（2026,10 vs 审核日 2026-11-16）即此态** |
| 无记录 | `st-unknown` | sc 空态 tag（`_sc_body` empty 分支）+ `.big.nodata` 泛化样式 | `state=="empty"`（:656） |

  - **四川数据模型只有上述三态，不存在失败态**——不为不存在的语义强造 `st-fail`（`st-fail` 仅用于查询页 chip 函数 `_src_chip`/`_compute_chip`（:1573/:1594，未冻结）按其既有数据语义分支输出，文本节点逐字不动）。
  - CSS 无法从相同 DOM 结构辨别状态 → 一律由未冻结渲染函数输出稳定状态类；冻结函数不解冻、不按 DOM 序号猜状态。文案字面不动（Q2 计数约束已核）。
  - 验证用**内存夹具**核对三态输出（当月/过月/empty），断言具体标签的 class，而非全页字符串包含（见 implement Step 5）。

## 4. 冻结合规矩阵（GAP-A4-01~07 逐条应对）

| GAP | 应对 |
|---|---|
| 01 PAGE_TPL 是 str.format | 新 CSS 全部进独立原始字符串常量 `CSS_THEME`（单花括号原生写法），PAGE_TPL 内 `<style>` 尾部加一个 `{css}` 占位，render 处 `PAGE_TPL.format(..., css=CSS_THEME)`。存量 CSS 中的既有占位不动。 |
| 02 冻结函数 6 项 | 本方案**零改动** `_adjacent_week/svg_sparkline/trend_block/ranking_block/child_block/sichuan_block`。改动落点：PAGE_TPL 尾部占位、CSS_THEME（新）、`_sc_body`(:1075)、`flu_body_html`(:1010 眉标)、`_src_chip`/`_compute_chip`(:1573/:1594 状态类)、`_card` **签名与输出字面均不动**（设计师原提议加 cls 参数——已否决，改 :has()）。实施后 `check_history_compat.py --check Reg` 4/4 必须仍 OK。 |
| 03 白名单 4 子串 + Q4 危险 API | CSS_THEME 不含 `<script src`/`fetch(`/`@import`/`url(http`；不引入任何 JS；`repeating-linear-gradient` 允许（已核 _validate_pages:1797 只拦 4 子串）；不用 data: URI。script 段数保持 3。 |
| 04 Q10 字面切块 | card div 保持 `  <div class="card">` 逐字；`.big` 保持 `<div class="big">{值}<span class="unit">` 结构（rail 作兄弟节点插入，不包裹）。 |
| 05 Q11 banner 字面 | PAGE_TPL 的 `<div id="default-view">\n  {run_banner}\n  {banner}\n{cards}` 结构与缩进不动；banner 按 class 而非 :first-child 定位（run_banner 空态首子可能是卡）。 |
| 06 验收通道 | probe_style.py audit 改后复测 360/1280（**r2：SVG 文本改采 computed fill 并带 --selftest**，A4-PLAN-05）+ probe_narrow 320–1280 溢出（含 880/900/920 断点邻域）+ **check_view_toggle.py（r2 新增：headless 驱动真实 SEARCH_JS 验证切换/恢复/清空，A4-PLAN-01）** + observer 前后截图目检。 |
| 07 归档套件可跑 | 用 .tmp_a4/reg/ 下已修复副本；验收判据 = 失败集合与基线一致（仍仅 Q6 flu_north.csv 哈希既有漂移，成因已留痕：A2 冻结后 bot 周更，deaefd9）。 |

**Q5/Q2/Q1 字面保全清单**（改后必须逐字存在）：`min-height:44px`、`font-size:16px`、`focus-visible`、`'  <div class="card">'`、`<div class="big">{goldstein}<span class="unit">`、`<div id="default-view">\n  <div class="banner">`、`四川官方流感分级` 全页恰 1 次、脚手架 ids（q/q-list/q-status/query-view/default-view）、`已恢复成都默认`/`请从列表中选择`/`未找到匹配的省市`/`个单位`、script 恰 3 段。
**数据依赖断言的验收对象区分（r3 修订 A4-PLAN-09）**：`官方分级未获取 · 状态未知` 仅由 `_sc_body` empty 分支输出（src/build_site.py:1083），当前四川数据非空 → **产物不含此串，断言对象=源码 + 内存夹具**（`_sc_body({"state":"empty"})` 须含该文案、`nodata`、`st-unknown`、无 rail）；当前产物只断言 rail 恰 1、等级文案、标题唯一计数。同理 `st-ok`/`st-wait` 的产物断言以 `sichuan_block()` 实时返回的态为准（当前数据 → `st-wait`），不得硬编码。

## 5. 视觉变化承诺（评审与验收对照）

1. **一叠便签 → 一张报告单**：1080px/12 列栅格，hero 独占行带竖条与标尺；1280×900 首屏同时见 四川分级+89.1+排行+历年 四块（现状 1.5 块）；纵向滚动预计减 ~40%
2. **数字终于比标题大**：标题 15px#555→13px 眉标化，数字 34→46px 等宽+眉标+品牌短线；视线路径从"读标题找重点"变为"数字自己跳出来"
3. **状态第一次可读**：正常=青点、待更新=琥珀左边条、失败=砖红左边条、未知=中性虚线框，四态余光可分；"未获取"无任何一点像"安全"

## 6. 验收标准（量化，全部可复核）

| # | 判据 | 工具 |
|---|---|---|
| V1 | 本地构建成功，`python -X utf8 src/build_site.py --local` 退出 0 | shell |
| V2 | check_history_compat `--check Reg` 4/4 OK（冻结函数零字节改动） | 归档套件 |
| V3 | check_search_query 失败集合 == 基线：**仅 Q6 且仅其中 flu_north.csv 哈希子项**（成因留痕 research/：A2 冻结 pin 3851e1dc 与 bot 周更后 blob 漂移，deaefd9）；输出逐用例留档 validation/v3-search-after.txt，与改前基线 diff 为空 | .tmp_a4/reg 副本 |
| V4 | §4 字面保全清单逐项 grep 命中（数据依赖断言按 §4 对象区分：`官方分级未获取 · 状态未知`→源码+夹具；`st-ok`/`st-wait`→产物类与 `sichuan_block()` 实时态一致，当前=st-wait）；script 段数 3；_validate_pages 通过（构建即验）；**SVG 片段内**（排除 `<style>`）#999/#6b7280/#e5e7eb 及系列色 hex 次数与改前快照一致；源码含 st-ok/st-wait/st-unknown/st-fail 类名定义；夹具三态（当月 st-ok+rail / 过月 st-wait+rail / empty st-unknown+nodata+无 rail）class 断言通过 | 脚本（check_lit.py 扩展） |
| V5 | 横向溢出：320/360/414/768/**880/900/920**/1280 over 全空 | probe_narrow |
| V5b | **搜索视图切换（r2，A4-PLAN-01）**：headless 驱动真实 SEARCH_JS——输入非成都候选并显式选中后 `#default-view` computed display 为 none、`#query-view` 单独可见；点「回成都」恢复默认视图；清空输入框不切换/不清除已呈现结果 | check_view_toggle.py（新建） |
| V6 | 非 SVG 文本 **0 处 <12px**（眉标、表头、序号均已统一 12px，无例外类）且 AA 违规 0 处（360 与 1280 双档） | probe_style |
| V7 | SVG 文本 computed ≥10px（sparkline 几何冻结的既定例外，周标由 9px 覆写为 10px）且**按 computed fill 计**对白底对比度 ≥4.5（数值文字统一墨色重着色后可达；系列线/端点识别色不属文字、不计入）；探针自检通过：同 color 不同 fill 的两段 SVG 文本测得不同对比度，否则 V7 无效 | probe_style（fill 版 + --selftest） |
| V8 | 1280px 视口（按 900 高折算）：≥3 张卡的首元素 top ≤850；first_big ≤320 | probe_style 锚点 |
| V9 | observer 目检前后截图（.tmp_a4/shots/）：层级/状态四态/双列无重叠错位；结论记录归档 | observer 子代理 |
| V10 | **oracle 独立只读实现复核（r2 修订 A4-PLAN-07，handoff §7 强制门）**：输入 = src/build_site.py diff、V1–V9 证据、基线例外清单；BLOCKER 关闭确认后才进入 V11 | oracle 子代理 |
| V11 | 用户人工验收（浏览器双击 site/index.html）后批准提交 | 用户 |

## 7. 风险与规避（实施期生效）

| 风险 | 规避 |
|---|---|
| :has() 兼容（旧浏览器） | 退化=单列=现状，可接受；不写 @supports |
| **作者级 grid 覆盖 [hidden] UA 规则 → 搜索切换泄漏（r2）** | `#default-view[hidden]{display:none}` 显式守卫 + V5b check_view_toggle.py 驱动真实 SEARCH_JS 验证 |
| **探针测 color 而非 SVG fill → V7 假通过（r2）** | 采集器对 SVG 文本改读 computed fill + `--selftest`（同 color 不同 fill 必须测出差异），自检不过则 V7 判无效 |
| **10px 规格与 V6 冲突（r2）** | 眉标/表头/序号全部统一 12px，无例外类 |
| 属性选择器 hex 耦合冻结函数未来改色 | CSS 注释（不含被拦子串）+ V4 加"产物含 #999/#6b7280/#e5e7eb"断言 |
| 46px .big 在 320px 换行 | <720 锁 34px；.unit 允许换行 display:block |
| 行高 1.62 增高 ~15% | 双列抵消；V8 卡首屏数兜底 |
| 序号 ::before 进读屏可访问名 | 评审可裁：删序号换品牌色小方块 |
| CSS_THEME 内 `{}` 与 format 冲突 | CSS_THEME 是**独立常量不经 format**（GAP-A4-01 的意义）；仅 PAGE_TPL 自身占位需双花括号，现状已如此 |
| span 5/7 卡内 hist-tbl(min-width 340) 溢出 | 7 列卡 ≥900px 时实宽 ≥502px；<900px 单列不受影响；V5 兜底 |
| 状态类名改动触碰文案断言 | 只加/改 class 属性，文本节点逐字不动；V3/V4 兜底 |
| **CSS 注释写入被拦子串 → 构建必败（r2，A4-PLAN-02）** | 禁串清单只保留在本计划与 check_lit.py；CSS_THEME 注释用中文描述且不得含任何被拦子串字样（连提及都不行，_validate_pages 逐字扫描不分注释） |

## 8. 对 designer 规格的三处修正（已核事实优先）

1. ~~`.card.c5/.c7`/`.card.hero` 由 `_card(title, body, cls="")` 产出~~ → **Q10 按字面 `'  <div class="card">'` 切块（:631,634），加类即碎**。改为 §2.4 的 `:has()` 内容签名方案；`_card` 签名与输出字面均不动。
2. 五级方向由"假设"升级为**已核事实**：Ⅴ 低 → Ⅰ 高（CONTEXT.md:15 + LEVEL_ADVICE 互证），色阶不翻转，标尺自左 Ⅴ（浅）至右 Ⅰ（深）。
3. 深色模式从"需上游确认"改为**明确非目标**（用户决策①）。

## 9. 实施顺序与验证映射

见 implement.md（同目录）。冻结快照：plan-freeze-r3.md 记录本文件与 implement.md 的 SHA-256 及依赖 hash（src/build_site.py 当前 HEAD blob）。

## 10. r1→r2 修订记录（对照 plan-critic round 1 BLOCKER）

| BLOCKER | 修订位置 |
|---|---|
| A4-PLAN-01 grid 覆盖 [hidden] | §2.4 隐藏守卫（`#default-view[hidden]{display:none}`，不改 JS）+ §6 V5b（check_view_toggle.py）+ §7 风险行 |
| A4-PLAN-02 CSS 注释含禁串必败 | §7 末行 + implement.md Step 1（禁串清单只在计划与 check_lit.py；注释用中文描述且不含被拦子串字样） |
| A4-PLAN-03 10px 与 V6 冲突 | §2.3 眉标 12px、§3-3 序号 12px、§3-5 表头 12px、implement Step 2 同步；V6 口径无例外 |
| A4-PLAN-04 V7 全文本 4.5 与保留数据标注色冲突 | §2.1 禁止列加"图内数值文字"、§3-2 文字/线条边界（SVG 数值文字统一墨色 #3D4E56，识别色只留折线/端点）、§6 V7 重写 |
| A4-PLAN-05 探针测 color 非 fill | §6 V7（fill 版 + --selftest）、§7 风险行、implement Step 6.5 探针升级 |
| A4-PLAN-06 四态落点缺默认页 .tag | §3 状态落点映射表（_sc_body 加 st-ok/st-unknown；chip 函数加四态类；冻结函数不解冻）、§6 V4 增状态类断言 |
| A4-PLAN-07 缺 oracle 独立复核 | §6 V10（oracle 只读复核，关闭确认后才 V11 用户验收）、implement Step 8 重排 |
| A4-PLAN-A01/A02/A03（建议） | implement Step 8 命令全展开；V3 细化到 Q6 内 flu_north.csv 子项并留档 diff；§2.4 断点统一 ≥900 双列 + V5 增 880/900/920 |

### r2→r3（round 2：6/7 关闭，A4-PLAN-06 未关闭 + 新增 08/09）

| BLOCKER | 修订位置 |
|---|---|
| A4-PLAN-06 `state=="ok"`≠当月正常，2026,10 存量会被误标 st-ok | §3 状态落点映射表重写：按冻结 `sichuan_block` 的 `line` 字段语义分三态（「数据正常」前缀→st-ok；「本月待更新」→st-wait，即当前真实态；`state=="empty"`→st-unknown）；明确四川模型无失败态、不强造 st-fail；夹具三态 class 断言（implement Step 5） |
| A4-PLAN-08 新增 CSS 自身含系列色 hex，全页 grep 次数必不等 | §3-2 与 §6 V4：hex 次数比较范围=产物 `<svg>…</svg>` 片段，排除 `<style>`/注释；改前快照 `.tmp_a4/before-product.html` |
| A4-PLAN-09 要求当前产物含 empty 态文案 | §4 字面保全清单拆分数据依赖断言：`官方分级未获取 · 状态未知`→源码+`_sc_body({"state":"empty"})` 夹具；当前产物只断言 rail/等级/标题计数；st-* 产物断言以 `sichuan_block()` 实时态为准（当前=st-wait）；§6 V4 同步 |
| A02 执行注意 / A05 特异性提醒 | implement Step 8 v3 留档注意事项（Q6 assert 提前终止→独立枚举 pin 结果）；Step 2 加 `.hist-tbl thead th`/caption 特异性核对提醒 |

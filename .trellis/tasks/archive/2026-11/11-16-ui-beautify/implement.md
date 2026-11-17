# A4 界面美化 · implement.md（r3）

> 前置：design.md r3 冻结后按本文件实施。所有改动仅涉及 `src/build_site.py` 一个源文件（新增常量 + 少量未冻结函数内插入），无数据变更。
> r2 变更：关闭 round 1 全部 7 项 BLOCKER（A4-PLAN-01~07）。
> r3 变更：关闭 round 2 的 A4-PLAN-06（四川三态按 line 语义映射 + 夹具）、A4-PLAN-08（hex 次数限 SVG 片段）、A4-PLAN-09（empty 文案断言对象改源码+夹具）。
> 环境：pwsh 内联 python 中文必炸 → 一律写脚本文件再跑；本地构建必带 `--local`。

## Step 0 — 冻结基线（已在本任务 research/ 留档，实施前复核一次）

```bat
git rev-parse HEAD
git status --porcelain          :: 期望仅 .trellis/tasks/11-16-ui-beautify/ 与 .tmp_a4/ 新文件
python -X utf8 .tmp_a4\reg\11-12-regional-monitor\validation\check_history_compat.py --check Reg   :: 4/4 OK
python -X utf8 .tmp_a4\reg\11-12-regional-monitor\validation\check_search_query.py                 :: 55/56（仅 Q6）
copy site\index.html .tmp_a4\before-product.html   :: r3 新增：改前产物快照（SVG hex 次数对照基线）
```

## Step 1 — CSS_THEME 常量 + {css} 占位（GAP-A4-01）

1. 在 `PAGE_TPL` 定义之前新增模块级原始字符串常量 `CSS_THEME = r""" ... """`（单花括号原生 CSS，不经过 format）。
2. `PAGE_TPL` 内 `<style>` 块末尾（现有最后一条规则之后）加一个占位行 `{css}`。
3. `render()`（:1666）中 `PAGE_TPL.format(...)` 调用追加 `css=CSS_THEME`。
4. **验证**：`python -X utf8 src\build_site.py --local` 构建成功；产物 `<style>` 内出现 CSS_THEME 全文。

CSS_THEME 内容按 design.md §2/§3 顺序组织（变量声明 → 背景层 → 排版覆盖 → 网格与 :has() 定位（含隐藏守卫）→ rail/序号/纹理/表格/焦点环 → 状态四态 → SVG 重着色 → <520 tlabel 堆叠 → <720 .big 34px → print）。
**红线自查（r2 修订 A4-PLAN-02）**：`<script src`/`fetch(`/`@import`/`url(http` 四个子串的**检查清单只保留在本文件与 check_lit.py**，**绝不写入 CSS_THEME**——`_validate_pages`（src/build_site.py:1797）对整页 HTML 逐字扫描、不区分注释，注释里"提及"被拦子串也会让构建必败。CSS_THEME 顶部注释只写不含任何被拦子串的中文说明，示例：`/* 主题层：纯呈现覆盖，不引用任何外部资源，不含脚本标签或远程地址；病种识别色仅用于线条与端点，不进入背景；红色总面积小于百分之一 */`。自查方式 = 构建成功本身 + check_lit.py 断言四子串不在产物。

## Step 2 — 存量 CSS 字面保全的最小覆写

- 不删除 PAGE_TPL 内任何既有规则；字号/颜色类覆写全部在 CSS_THEME 里**后置覆盖**（同特异性后来者胜；**r3 提醒 A4-PLAN-A05：存量 `.hist-tbl thead th` 特异性高于 `.hist-tbl th`，caption 另有 11px 规则——覆盖选择器须按实际 computed 值核对，V6 会兜底抓漏**）。
- 必须保留逐字出现：`min-height:44px`、`font-size:16px`、`focus-visible`（Q5）。
- 覆盖清单：`.sub`→12px `--ink-3`；`.card h2`→13px/600/`--ink-2`/0.02em；`.big`→tabular-nums/-0.02em；`.unit`→13px/500/`--ink-3`；`.src`/`.meta`/`.foot`/`.q-ver`/`.hist-sub`/`.hist-sub2`/`.hist-scroll-hint`→12px `--ink-3`；`.hist-tbl th`→12px/mono 眉标风；`.tag`→12px/500；正文（.adv/.chain/.rank/.kv）→15px/1.62；`.wrap`→`min(1080px,100%)`+padding 分档；`.card`→padding/border/圆角 10px/近零阴影；`.banner`→`--notice` 底 + `#7A4E00` 字 + 1px 左边条。
- **验证**：构建成功 + grep 产物含三字面（见 Step 8 的 check_lit.py）。

## Step 3 — 网格与 :has() 定位（GAP-A4-04 规避）

CSS_THEME 内（≥900px 媒体查询）：

```css
#default-view{display:grid;grid-template-columns:repeat(12,1fr);gap:20px;align-items:start}
#default-view[hidden]{display:none}   /* 隐藏守卫：搜索 JS 靠 hidden 切视图，必须压过上面的网格声明 */
#default-view > .banner,#default-view > .card{grid-column:1/-1}
#default-view > .card:has(.kv){grid-column:span 5}
#default-view > .card:has(.hist-tbl){grid-column:span 7}
#default-view > .card:has(.rank){grid-column:span 5}
#default-view > .card:has(.trendrow){grid-column:span 7}
#default-view > .card:has(.adv){border-left:3px solid var(--brand)}   /* hero 品牌竖条 */
#query-view > .card{grid-column:1/-1}
```

- sc 与 child 未列 = 默认整行。`.card:has(.adv)` 同时承担 hero 竖条 + 微网格底纹（§design 3.4）。
- **隐藏守卫（r2，A4-PLAN-01）**：搜索成功路径用 `queryView.hidden=false; defaultView.hidden=true` 切视图（src/build_site.py:1363-1364），恢复路径 :1338-1342；作者级 `display:grid` 会覆盖 UA `[hidden]` 规则 → `#default-view[hidden]{display:none}`（特异性 id+属性 > id）必须紧随网格声明。**不改任何 JS。**
- **验证**：
  1. 构建后 1280 档 probe_style：cards=6、无 over；first_card/first_big/second_big 锚点显著前移（V8）。
  2. 新建 `.tmp_a4\check_view_toggle.py`（headless 同源 iframe，同 probe 系做法，驱动**真实 SEARCH_JS**）：`#q` 输入非成都关键词 → 候选列表出现 → 显式点选第一项 → 断言 `getComputedStyle(#default-view).display==='none'` 且 `#query-view` 可见、其内卡片单独呈现；点「回成都」→ 断言默认视图恢复可见；清空输入框 → 断言已呈现结果不被清除/切换（V5b 三断言）。

## Step 4 — `_sc_body` 五级标尺（未冻结 :1075-1112）

1. ok 态：`.big` 与 `.meta` 之间插入：
   `<div class="rail" aria-hidden="true"><i class="on"></i>…</div><div class="rail-labels" aria-hidden="true">Ⅴ Ⅳ Ⅲ Ⅱ Ⅰ 段下 mono 数字</div>`
   具体结构：五段 `<i>`，当前级（`{"V":0,"IV":1,"III":2,"II":3,"I":4}[sc["level"]]`）加 class="on"；段下五个 `<span>` 罗马数字 Ⅴ Ⅳ Ⅲ Ⅱ Ⅰ（自左向右浅→深）。
2. empty 态：`<div class="big">？</div>` → `<div class="big nodata">？</div>`；`.meta` 的 tag 文案逐字不动；CSS 给 empty 态容器虚线未知框（`.card:has(.big.nodata) .meta .tag` → 中性虚线样式）。
3. **验证**：构建后 grep 产物：`class="rail"` 恰 1 处、`四川官方流感分级` 全页仍恰 1 次（Q2）；`官方分级未获取 · 状态未知` **不在当前产物**（四川数据非空，r3 修订 A4-PLAN-09——该串断言移至源码与夹具，见 Step 5.4）；check_search_query 仍 55/56。

## Step 5 — 眉标与状态类（未冻结 :1010/:1075/:1573/:1594）

1. `flu_body_html`（:1010）：`.big` 前插入 mono 眉标行 `<div class="eyebrow">GOLDSTEIN 指数 · 第 {week} 周</div>`（**12px**，周次从既有上下文变量取，不新增计算）。`.big` 与其内部结构字面不动。
2. `_src_chip`/`_compute_chip`（:1573/:1594）：仅在输出元素上加状态类（st-ok/st-wait/st-fail/st-unknown 四类，按函数内既有数据语义分支映射），文本节点逐字不动；四态视觉全在 CSS_THEME。
3. **`_sc_body`（:1075，r3 修订 A4-PLAN-06：按冻结 `sichuan_block` 的 line 语义映射，不重算日期）**：
   - `state=="ok"` 且 `line` 以「数据正常」开头 → `.meta` 内 `.tag` 加 `st-ok`；
   - `state=="ok"` 且 `line` 含「本月待更新」 → `.tag` 加 `st-wait`（**当前真实数据 2026,10 vs 2026-11-16 即此态**）；
   - `state=="empty"` → `.tag` 加 `st-unknown`（`.big.nodata` 泛化未知样式保留）。
   文本节点逐字不动；`sichuan_block` 等冻结函数不解冻、不按 DOM 序号猜状态；四川模型无失败态，不强造 st-fail。落点映射见 design.md §3 状态四态化表。
4. **夹具验证（r3 新增，check_lit 内实现）**：内存构造三个 dict 直接调 `_sc_body`：
   - 当月：`{"state":"ok","level":"IV","level_name":"活跃期","year":"2026","month":"11","line":"数据正常 · 11月 · 来源发布 2026-11-05","advice":["通风"],"source_url":"https://example.invalid/"}` → 断言输出含 `st-ok`、`class="rail"`，不含 `st-wait`/`st-unknown`；
   - 过月：同上但 `month="10"`、`line="10月已确认等级 · 本月待更新"` → 断言含 `st-wait`、`class="rail"`；
   - empty：`{"state":"empty"}` → 断言含 `st-unknown`、`nodata`、`官方分级未获取 · 状态未知`，且不含 `class="rail"`。
   断言对象=具体标签的 class，非全页字符串包含。
5. **验证**：check_search_query 仍 55/56（Q10/Q11/Q2/Q5 均不触碰）；check_lit 产物断言以 `sichuan_block()` 实时态为准（当前数据 → sc 卡 `.tag` 含 `st-wait`；11 月数据录入后构建则应为 `st-ok`），源码含 st-ok/st-wait/st-unknown/st-fail 四类名定义（chip 的 st-fail 数据态依赖，页面断言以源码+夹具为准）。

## Step 6 — SVG 重着色与 sparkline 周标（CSS_THEME 内，零 Python）

```css
svg text[fill="#999"],svg text[fill="#6b7280"]{fill:#3D4E56}
svg text[fill="#c0392b"],svg text[fill="#7f8c8d"],svg text[fill="#8e44ad"]{fill:#3D4E56}
svg line[stroke="#e5e7eb"],svg line[stroke="#eef0f2"]{stroke:#EFF3F4}
svg line[stroke="#9ca3af"],svg line[stroke="#d1d5db"]{stroke:#9FB0B6}
svg rect[fill="#f3f4f6"]{fill:#F4F7F8}
svg text[font-size="9"]{font-size:10px}
```

- 第二行是 r2 修订 A4-PLAN-04 的**文字/线条边界**：数值文字（含新冠末端百分比 #7f8c8d≈3.48:1）统一重着色为可读墨色 #3D4E56（8.67 ✓）；识别色只留在折线（path/polyline 的 stroke）与端点（circle 的 fill/stroke）——这些元素选择器完全不命中。HTML 属性 hex 原样保留（CSS 只覆盖呈现）。
- <520px：`.tlabel` 由侧列改堆叠（flex-direction:column），SVG 拉满 296px。
- **验证（r3 修订 A4-PLAN-08）**：probe_style（fill 版）360 档：SVG 文本 computed ≥10px 且按 fill 计对比度 ≥4.5；**hex 次数对比范围=产物中 `<svg>…</svg>` 片段（正则提取，排除 `<style>` 与注释），对照 `.tmp_a4\before-product.html` 同口径计数**——系列色 #c0392b/#7f8c8d/#8e44ad/#1f4e79 与 chrome 色 #999/#6b7280/#e5e7eb 各自相等；check_history_compat Reg 4/4（本步零 Python，理应天然通过）。

## Step 6.5 — probe_style.py 探针升级（r2 修订 A4-PLAN-05，先于 Step 8 执行）

1. 采集器修改：文本节点若为 SVG 命名空间（`node.namespaceURI` 含 svg 或 `closest('svg')` 命中），前景色改读 `getComputedStyle(node).fill`（必要时叠加 fill-opacity）；HTML 文本仍读 `color`。输出记录 `fgsrc: color|fill` 以便核对。
2. 新增 `--selftest` 子命令：内嵌最小测试页（两段 `<svg><text>`，同 `color` 继承、不同 `fill="#000000"/"#767676"`），断言两者测得不同对比度；失败则探针判坏，V7 结果无效。
3. **验证**：`python -X utf8 .tmp_a4\probe_style.py --selftest` 退出 0；对改后页面 audit 360/1280，SVG 节点 fgsrc==fill。

## Step 7 — 焦点环、序号、打印样式（CSS_THEME 内）

- 统一 `:focus-visible{outline:2px solid var(--focus);outline-offset:2px}`（保留 "focus-visible" 字面）。
- `.card{position:relative;counter-increment:card}` + `.card::before` mono 序号（**12px**）；`pointer-events:none`；`<720` 序号隐藏（密度考虑，可选，评审裁）。
- `@media print`：纹理/阴影/横幅隐藏。
- **验证**：构建成功；人工 Tab 一遍（observer 截图内看焦点环）。

## Step 8 — 验收执行（design.md §6 V1–V11 逐项；命令全展开，r2 修订 A01）

```bat
python -X utf8 src\build_site.py --local                                                                    :: V1
python -X utf8 .tmp_a4\reg\11-12-regional-monitor\validation\check_history_compat.py --check Reg            :: V2
python -X utf8 .tmp_a4\reg\11-12-regional-monitor\validation\check_search_query.py                          :: V3，输出留档 validation\v3-search-after.txt
python -X utf8 .tmp_a4\check_lit.py                                                                        :: V4（字面+script数+hex+状态类）
python -X utf8 .tmp_a4\check_view_toggle.py                                                                :: V5b（切换/恢复/清空三断言）
python -X utf8 .tmp_a4\probe_narrow.py measure 320                                                          :: V5
python -X utf8 .tmp_a4\probe_narrow.py measure 360
python -X utf8 .tmp_a4\probe_narrow.py measure 414
python -X utf8 .tmp_a4\probe_narrow.py measure 768
python -X utf8 .tmp_a4\probe_narrow.py measure 880
python -X utf8 .tmp_a4\probe_narrow.py measure 900
python -X utf8 .tmp_a4\probe_narrow.py measure 920
python -X utf8 .tmp_a4\probe_narrow.py measure 1280
python -X utf8 .tmp_a4\probe_style.py --selftest                                                           :: V7 前置（不过则 V7 无效）
python -X utf8 .tmp_a4\probe_style.py audit 360                                                            :: V6/V7/V8
python -X utf8 .tmp_a4\probe_style.py audit 1280                                                           :: V6/V7/V8
```

- **V3 判据（r2 修订 A02；r3 执行注意）**：失败集合 == **Q6 内且仅 flu_north.csv 哈希子项**（成因留痕：A2 冻结 pin 3851e1dc 与 bot 周更 blob 漂移，deaefd9，见 research/）。注意 `check_search_query.py:371-377` 在同一循环内 `assertEqual`，flu_north 失败即中止、后续文件不检查——留档时须**独立枚举全部 pin 的匹配结果**（小脚本逐 pin 比对，写 validation\v3-pins.txt），不要拿被截断的套件日志当语义判据；`v3-search-after.txt` 记录原始输出供追溯。
- check_lit.py（Step 5/6 已扩展）：断言产物含 §4 保全清单全部字面（**数据依赖断言按 §4 对象区分：`官方分级未获取 · 状态未知`→源码+夹具，不在当前产物**）+ **SVG 片段内（排除 `<style>`）hex 计数对照 before-product.html 同口径相等** + script 段数==3 + `<div class="rail"` 恰 1 + sc 卡 `.tag` 类与 `sichuan_block()` 实时态一致（当前=st-wait）+ 源码含 st-ok/st-wait/st-unknown/st-fail 类名定义 + 夹具三态 class 断言（当月/过月/empty）+ 四禁串不在产物。
- 截图：`python -X utf8 .tmp_a4\probe_narrow.py shot 1280 .tmp_a4\shots\after-1280.png`、`python -X utf8 .tmp_a4\probe_narrow.py shot 360 .tmp_a4\shots\after-360.png`；派 observer 对比 base-desktop/base-360 出具 V9 结论（本模型不能读图）。
- **V10（r2 修订 A4-PLAN-07，handoff §7 强制门，先于用户验收）**：V1–V9 全过后派 oracle 独立只读复核，输入 = `git diff src/build_site.py`、V1–V9 证据与 validation/ 留档、基线例外清单（Q6 漂移成因）；oracle BLOCKER 全部关闭确认后才进入 V11。
- **V11**：汇报用户人工验收（双击级指引：资源管理器双击 `site\index.html`）→ 用户批准提交。

## Step 9 — 收尾

- `.trellis/tasks/11-16-ui-beautify/` 归档 design/implement/validation 产物与验证输出。
- 提交分两笔（docs: 任务文档 / feat: build_site 样式），**不提交** site/、site_publish/、.tmp_*。
- 用户批准后 pull → push → workflow_dispatch → 线上验证。

## 回退方案

单一源文件改动 + site/ 不入库：`git checkout -- src/build_site.py && python -X utf8 src\build_site.py --local` 即完全回退。任何 V2/V3 破损即停，修到与基线一致才继续。

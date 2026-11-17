# A4 实施期缺陷修复与复核记录（V9 之后）

> 更新：2026-11-17。承接 `validation/v2`–`v8` 各组结果（见同目录）。
> 本文件记录：V9 目检发现的 3 项真实缺陷 → 我方实测核实 → 修复 → 复跑证据。

## 1. V9 目检提出的问题与核实结论

V9 observer（视觉子代理）报告 2 项阻断 + 3 项可选。我方未直接采信，逐项用渲染级探针实测：

| 编号 | observer 判断 | 我方实测结论 | 证据脚本 |
|---|---|---|---|
| P1 | 桌面「01 四川」独占首行，「02 南方片」被挤到第二行左，双主角未并列；02 卡下半 60% 纯白空洞 | **真**（但成因不同：不是卡内拉伸，而是行内两卡高度差造成的行留白） | `probe_layout.py`、`probe_gaps.py` |
| P2 | 05 卡小图右侧 `2026W45` 被裁成 `2026W`、`18.8%` 的 % 被裁、`0.8%`/`1.2%` 与 `2026W45` 重叠 | **真**（既有缺陷，非 A4 引入） | `probe_svg.py`、`probe_overlap.py` |
| P3 | 01 卡防控建议双重编号 `1. (1) …` | **真** | `show_adv.py`、`probe_adv.py` |
| P4 | 窄屏 `(2026年10月)` 断成 `(2026年10` / `月)` | **误读**（当前 360/414 下 `.unit` 未折行，单行高 17px） | `probe_style.py` json、`probe_title.py` |
| P5 | 桌面第三行右侧 05 卡底部留白约 1/3 | **真，但属行对齐自然结果**（`align-items:start`，每卡底部空白恒为 19px=padding18+border1） | `probe_gaps.py` |

补充实测否定项：observer 观察到的「after-360 右侧 38% 纯白」不是页面缺陷，是截图 iframe 高度/宽度比造成的观感。

## 2. probe_gaps.py 关键结论（否定「卡内拉伸」假设）

所有断点下每张卡的「底部空白」恒为 19px（= padding-bottom 18px + border 1px），说明 `align-items:start` 生效、卡片未被同行拉伸填满。因此 P1 中「02 卡 60% 空白」实为：同行 hist 卡高 721px，flu 卡仅 234px，两卡顶部对齐后在行内留出垂直空隙——修法是改栅格配对，不是改卡内布局。

## 3. probe_layout.py 四方案对比（1280px，修复前 r3 栅格）

| 方案 | 首屏（≤900px）可见块数 | 同行高度差 | 结论 |
|---|---|---|---|
| r3 现状（sc 全宽 + flu/hist + rank/trend + child） | 3 块（sc, flu, hist；rank top=1381 屏外） | hist vs flu 差 487px | 否决：违背 design §5.1「1280×900 首屏见四块」与用户决策② |
| 变体 B（sc7 + flu5 / hist7 + rank5 / trend7 + child5） | 4 块 | 45–282px | **采用**：900/1024/1280 三档均 4 块首屏、无横向溢出 |

## 4. 本轮代码修改（src/build_site.py，CSS_THEME 内）

1. **栅格改变体 B**（@media min-width:900px 块）：`.card:has(.adv){grid-column:span 7}`、`.card:has(.kv){span 5}`、`.card:has(.hist-tbl){span 7}`、`.card:has(.rank){span 5}`、`.card:has(.trendrow){span 7}`、`.card:has(.childg){span 5}`。DOM 序未变（未使用 order / grid-row，遵守 design「DOM 序=视觉序」）。
2. **防控建议去双重编号**：`.adv{…list-style:none;padding-left:0;margin:8px 0 0}` + `.adv li{padding-left:1.6em;text-indent:-1.6em}`。保留官方原文「（1）…（5）」，悬挂缩进保证换行对齐。
3. **`.unit` 不折行**：`.unit{…;white-space:nowrap}`。
4. **小图标签重叠修复**（不动冻结函数 `svg_sparkline`，纯 CSS 层）：
   `.trendrow svg{overflow:visible;margin-bottom:12px}` + `svg text[y="68"]{transform:translateY(10px)}`。
   依据：两个周次标签共用 `y=68` 基线，一起下移 10px 后与末端百分比脱开，且两周次标签基线保持一致（只移右端会导致 2024W46 与 2026W45 基线错位 10px）。

## 5. 修复后复跑证据（全部实测）

| 检查 | 结果 | 留档 |
|---|---|---|
| V1 构建 + 四禁串扫描 | 通过 | 构建输出 |
| V2 check_history_compat --check Reg | 4/4 OK，exit=0 | `v2-history-compat.txt` |
| V3 check_search_query | 56 tests，failures=1，唯一失败= flu_north pin `f72ec16d… != 3851e1dc…`（既有漂移，与改前基线一致） | `v3-search-after.txt`、`v3-pins.txt` |
| V4 check_lit（45 项） | 45/45，0 失败，exit=0 | `v4b-check_lit-after-v9fix.txt` |
| V5 probe_narrow | 320/360/414/768/900/1280 全 `over=[]` | 见 §6 |
| V5b check_view_toggle | 9/9 PASS，exit=0（含 `#default-view[hidden]` 守卫） | `v5c-view_toggle-after-v9fix.txt` |
| V6/V7 probe_style audit | 360px：文本 158、低于 AA=0、<12px=9；1280px：文本 157、低于 AA=0、<12px=9（9 处全为 SVG 内文本，属 design V7 既定例外） | `final2-v6-360.txt`、`final2-v6-1280.txt` |
| V8 栅格断点 | 899 单列 640；900 双列（sc 493+flu 347 / hist 493+rank 347 / trend 493+child 347）；1024 552+388；1280 622+438；每卡 `grid-column` 正确 | `v8b-grid-after-v9fix.txt` |
| V9b SVG 标签 | 1280/1024/900/768/414/360/320 全部「无重叠/无越界」 | `v9b-svg-labels.txt` |
| V9b 卡内空白 | 所有断点每卡底部空白恒 19px（=padding18+border1），无拉伸 | `v9b-card-gaps.txt` |
| V9b 编号 | `list-style:none`、`li padding-left:24px / text-indent:-24px`、5 条文案以「（1）…（5）」开头 | `v9b-adv-numbering.txt` |
| V9b 标题折行 | 1280/414/360 全部单行；320 有两处括号内折行（`四川官方流感分级（月度 · 成都=平原区）`、`流感 / 新冠 / RSV 趋势（周度 · 本年度）`），非阻断（320 为最窄极端档） | `probe_title.py` 输出 |

## 6. V5 窄屏无溢出实测（修复后）

```
320 / 360 / 414 / 768 / 900 / 1280 → over=[]，sw==cw
```

## 7. 与冻结计划（r3）的偏离，及理由

冻结的 design.md / implement.md r3 规定的桌面栅格行分配为：**12 / 5+7 / 5+7 / 12**（sc 四川卡独占首行全宽）。本轮实测后改为：**7+5 / 7+5 / 7+5**（sc 与 flu 首行并列）。

| 项 | 冻结计划 | 实际实施 | 偏离理由 |
|---|---|---|---|
| 首行 | sc 全宽（span 12） | sc span 7 + flu span 5 | 冻结方案在 1280×900 首屏只能见 3 块（rank top=1381 屏外），既违反 design §5.1「1280×900 首屏见四块」的自设验收，也违反用户决策②「双主角并列」；变体 B 在三档断点均 4 块首屏 |
| 第 4 行 | child 全宽 | trend span 7 + child span 5 | 同上：child 全宽会形成第 4 行，首屏块数进一步减少 |

不受影响的设计约束（已逐项复核）：`≥900px 双列`、`wrap 上限 1080px`、`DOM 序=视觉序（未用 order / grid-row）`、`.card:has()` 内容定位（卡 div 不加类）、无 `:has()` 支持时退化为单列。

该偏离属「向用户决策与 design 自设验收靠拢」，不是范围扩张；已在实施报告中单列，交用户确认。

**2026-11-17 用户裁定**：经问题卡裁定「**保留现在的并列布局**」——偏离获用户正式批准，授权缺口关闭。冻结文档本身未改动（design.md SHA-256 `9d4cce48…` / implement.md `e840a43d…` 复核 MATCH），偏离与批准记录以本节为准。

## 8. 附加工具核验（本轮新增）

- `probe_svg_collide.py`：SVG 文本（`overflow:visible` 后越出 viewBox 的部分）与卡内非 SVG 文本元素是否碰撞 → 1280/1024/900/768/414/360/320 **全部无碰撞**。
- `probe_selector_scope.py`：产物 8 个 SVG 片段中，`y="68"` 只命中 3 个趋势小图（viewBox 0 0 300 70）的周次标签；历史 SVG（viewBox 0 0 280 192）的 11 个 text 无 y=68 → `svg text[y="68"]` 规则不误伤历史图。
- `probe_template_trend.py`：12 个 `<template>` 内 `.trendrow` 数=0，默认视图内=3 → 查询结果视图不含趋势小图，CSS 修复无模板侧副作用。
- 产物四禁串计数：`<script src`/`fetch(`/`@import`/`url(http` **各 0 次**（源码各 2 次，均属 `_validate_pages` 既有检查列表字面）。

## 9. 第二轮目检（V9b）复核结论

第二轮 observer 实际打开了 `base-desktop` / `after2-1280` / `base-360` / `after2-360` 四图，逐条判断：

| 项 | 判断 | 我方核对 |
|---|---|---|
| P1 双主角并列 | **已解决**（01 与 02 首行左右并列，各约 50%） | 与 `probe_grid.py` 一致：sc 622 + flu 438（1280 档） |
| P2 小图裁剪/重叠 | **已解决**（`2026W45`、`18.8%`/`0.8%`/`1.2%` 完整、无叠字） | 与 `probe_svgcheck_final.py` 全断点 OK 一致 |
| P3 双重编号 | **已解决**（仅剩 `（1）…（5）`） | 与 `probe_adv.py` 一致（`list-style:none`） |
| P4 窄屏单位折行 | **已解决**（`(2026年10月)` 完整一行） | `probe_title.py`：360px 全部单行 |
| P5 矮卡留白 | **部分解决**（今在 #02/#06 右侧约 40% 感知留白） | **实为卡外页面空白**：`probe_gaps.py` 显示每卡内部底部空白恒 19px，卡片高度即内容高度，非卡内留白 |

新增可选意见与处置：

1. **窄屏 #03 对照表行底色贴到卡片右内边距** — 表格位于横向滚动容器内，行底色随表格延伸；`overflow` 已裁剪，不越出卡片（`probe_narrow.py` 全档 `over=[]`）。属观感细节，不改（改动滚动容器 padding 会影响表格可读宽度）。
2. **#01–#06 序号窄屏不可见** — **设计意图**：CSS_THEME 中 `::before` 序号在 `<720px` 隐藏，避免与长标题抢位（design §2.2）。非缺陷。
3. **after-360 右侧约 22% 白色画布** — **截图工具缺陷，非页面缺陷**。Chrome 窗口宽度下限 560px，`shot()` 原先直接用 `--window-size=max(width,560)` 落盘；已改为「先按 560 落盘，再用 PIL 按 iframe 实际宽度裁切」。实测像素：内容最右非白像素 x=359（图宽 560），证实页面本身无溢出。修工具后重拍 `after3-1280.png`(1280×3400) / `after3-360.png`(360×3600)。

另需记录的观测修正：observer 对「#02 卡内 40% 空白」的描述与像素级度量不符（卡内恒 19px）。真实现象是**同一栅格行内两卡高度不等**（1280 档 sc 342px vs flu 234px，hist 721px vs rank 477px，trend 341px vs child 198px），页面背景在矮卡下方露出。这是两列等高栅格的自然结果，消除需瀑布流（会破坏「DOM 序=视觉序」约束）或增删内容（超 A4 范围），**接受为已知限制**。

## 10. 尚未解决 / 已知限制

- V3 唯一失败项属 A2 冻结后 bot 周更造成的既有数据漂移，非 A4 引起；`data/` 工作树干净。处置：不改 pin、不动 data/，验收以「失败集合与改前基线一致」为准。
- 320px 下两张卡片标题在括号内折行（`（…` 与 `…）` 分两行）。可通过 `word-break:keep-all` 缓解但不能完全消除（实测仍折行），且 320px 非目标档位（用户决策聚焦 ≥900 桌面与 360 手机）。记录为可选优化。
- P5「05 卡底部留白」：改为变体 B 后同行高度差降至 45–282px，仍存在但显著减轻；彻底消除需重排卡片内容或引入瀑布流，超出 A4 视觉层范围。

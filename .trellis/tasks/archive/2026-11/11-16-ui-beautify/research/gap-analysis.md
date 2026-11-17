# A4 缺口分析结论（GAP-A4-01~07）

> 分析时间：2026-11-16；分析者：gap-analyst（ses_e1cc12acdffeg35szhKcDWEXnO）+ 主会话逐项核实。
> 所有行号对应依赖快照 src/build_site.py SHA-256 1cf49bd7…（HEAD 8cf9bce 干净工作副本）。

- **GAP-A4-01** PAGE_TPL 是 str.format 模板：新增 CSS 必须走独立原始字符串常量 CSS_THEME + `{css}` 占位（`format(css=...)` 注入），避免逐条双花括号；CSS_THEME 本体不经 format。
- **GAP-A4-02** 冻结函数 6 项（check_history_compat.py:105-106，对比基线 a9459175）：`_adjacent_week / svg_sparkline / trend_block / ranking_block / child_block / sichuan_block`。视觉改造不得改其字节。渲染函数 `_sc_body`(:1075)、`flu_body_html`(:1010)、`_src_chip`(:1573)、`_compute_chip`(:1594)、`_card`(:764，输出字面另受 Q10 约束)、`_slot_templates`(:1621) 未冻结。
- **GAP-A4-03** `_validate_pages` 只拦 4 个逐字子串（src/build_site.py:1797）：`"<script src"`、`"fetch("`、`"@import"`、`"url(http"`；linear-gradient / box-shadow / @keyframes / var() / clamp 均允许。Q4 另拦 innerHTML/eval(/new Function/document.write/insertAdjacentHTML/XMLHttpRequest（check_search_query.py:308-311），script 段数==3（:314）。
- **GAP-A4-04** Q10 `_card_block` 用字面 `'  <div class="card">'` 切块（check_search_query.py:631,634）→ card div 不得加类/属性；`.big` 结构字面 `<div class="big">{值}<span class="unit">` 不得再包层。→ 网格分栏用 `:has()` 内容签名（见 scan_sigs-output.txt：默认视图 6 卡签名互斥）。
- **GAP-A4-05** Q11 断言 `'<div id="default-view">\n  <div class="banner">'`（:774，or 分支恒不生效）→ PAGE_TPL 的 default-view/banner 结构与缩进保持；run_banner 正常态返回 ""（:141-142,153-154）、local 构建返回 ℹ 横幅 → banner 按 class 定位，不得用 :first-child。
- **GAP-A4-06** 验收扩通道：probe_style.py（计算样式+WCAG 对比度+元素锚点位置）+ probe_narrow.py（真实窄屏 iframe 溢出测量；headless --window-size 有 ~500px 下限，直接量 360 得到的是被裁切的 512 布局）。
- **GAP-A4-07** 归档套件 check_search_query.py 原地跑 ModuleNotFoundError（ROOT=parents[4] 错指）→ 已复制修复副本至 .tmp_a4/reg/11-12-regional-monitor/validation/（FREEZE/BASELINE_S0 路径改指归档 research/）。基线 55/56，唯一失败 Q6 flu_north.csv 冻结哈希漂移（A2 冻结后 bot 周更所致，与 A4 无关，验收判据=失败集合与基线一致）。

## 附：关键已核事实
- 五级方向 Ⅴ 低 → Ⅰ 高（CONTEXT.md:15 + LEVEL_ADVICE :165 互证）。
- Q5 字面（:333-335）：`min-height:44px`、`font-size:16px`、`focus-visible`。
- Q2（:117）：PAGE.count("四川官方流感分级")==1。
- 卡内容签名（scan_sigs-output.txt）：sc=`class="adv"`、flu_south=`class="kv"`、hist_south=`class="hist-tbl"`、rank=`class="rank"`、trend=`class="trendrow"`、child=`class="childg"`；默认视图互斥；模板区共享签名但位于 `<template>` 内不受 `#default-view >` 作用域影响。
- sichuan_block(653-668) 只算数据 dict；HTML 渲染在 `_sc_body`(1075-1112) 未冻结 → 五级标尺可插入。
- `官方分级未获取 · 状态未知` 是 _sc_body empty 态文案（:1083），仅 SC 数据缺失才渲染（child_block :748 亦有同串作缺省 reason，冻结不改）。

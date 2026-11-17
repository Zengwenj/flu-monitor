# plan-freeze-r1 · 2026-11-16

对象：A4 界面美化成稿计划（design.md r1 + implement.md r1）

| 文件 | SHA-256 |
|---|---|
| D:\FluMonitor\.trellis\tasks\11-16-ui-beautify\design.md | b0f161dcc44c2e7878b66f39dfb0e11ceecc3a826f8ebddbb08afc39152e3ac1 |
| D:\FluMonitor\.trellis\tasks\11-16-ui-beautify\implement.md | 6959da4ded9eb12f881d6776858d59e697a8ddbae296847c8867716164b2653f |

依赖快照：
- src/build_site.py（工作副本，HEAD 干净）SHA-256 = 1cf49bd77ffa9ccec8b774c96401b9e3f00b02be50307d2557261755eaecde68
- 回归门：.tmp_a4/reg/11-12-regional-monitor/validation/（check_search_query.py 56 项，基线 55/56 仅 Q6；check_history_compat.py Reg 4/4）
- 视觉基线：.tmp_a4/audit-360-before.txt、audit-1280-before.txt、shots/base-desktop.png、shots/base-360.png

评审范围（review_scope）：本冻结对象两文件；引用的 src/build_site.py 行号以本快照 hash 为准。
轮次：round 1。
冻结后任何字节变化即重算 digest 并视为新一轮。

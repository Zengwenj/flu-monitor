# 规划证据

- CONTEXT.md:17,62 支持同地区同期曲线，禁止百分位风险等级；docs/handoff.md:113 的废止叠线适用范围待查。此前称必须由用户裁决的产品矛盾，证据不充分。
- src/build_site.py:81-85 缺相邻校验，且 prev[-1:] 的有效性判断和 max(prev) 不是同一条取数规则。
- src/build_site.py:88,246-251 仍为固定历史占位。
- src/build_site.py:107-115 共享 helper 使用 y*53+wk 与宽松年末规则，不能未经验证复用或改变全国趋势图。
- 起始工作树干净，已通过 Trellis CLI 建立任务，未实施。

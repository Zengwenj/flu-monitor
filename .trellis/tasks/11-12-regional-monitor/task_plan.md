# A2 规划工作计划

## Goal
建立多地区查询的可执行方案，先证明官方数据可用性，再设计，不在本轮实施。

## Current Phase
Phase 4：评审已 PASS，等待用户批准新版实施。

### Phase 1：证据与缺口
**Status:** complete
- 来源证据已闭环：research/location-sources.md 为主会话亲核版（CC0 名录固定 SHA/民政部核对/双产品片区名单/港澳台与兵团边界，2026-11-14）。用户已确认首版目录范围、双产品映射分开核实、草湖市单条补正（2026-11-15）三项决策。
### Phase 2：设计与执行计划
**Status:** complete
- design r3→r4/implement r3→r4 已对齐来源结论（基础集 396+补录 1=可查询 397、flu_region 独立依据、草湖市例外写实、停靠条件）。
### Phase 3：冻结与成稿评审
**Status:** complete
- plan-freeze-r3.md round 1 INCONCLUSIVE（轮次字段混用/基线证据缺口/草湖市矛盾，存档 plan-review-search-r1.md）。
- plan-freeze-r4.md round 2 **PASS 无 BLOCKER**（33 依赖+data 基线 10+工作树清单；digest b5f916fb…e8f6；存档 plan-review-search-r2.md）。轮次预算已用尽，冻结再变更须用户授权。
- 两条 ADVISORY（Q6 三分类核验、目录计数断言）已作为实施约束写入 implement.md（PASS 后编辑性落实，留痕于评审存档）。
### Phase 4：交付与批准门
**Status:** in_progress
- 向用户交付评审结论与计划摘要，等待新版实施授权（独立于评审 PASS）。提交/推送/部署仍另行授权。

## Next Step
用户批准后按 implement.md S0→S6 实施：S0 记录基线并生成 locations.csv/location_product_map.csv（397 条含草湖市 source=dmfw）→ S1 数据契约与模板 → S2 内联交互（designer，串行）→ S3 口径验收 → S4 旧实现隔离 → S5 Q1–Q7 验证矩阵（check_search_query.py）→ S6 独立实施复核（oracle）→ 汇报 → 用户人工验收 → 另行批准分笔提交+push+部署。旧五页实现继续暂停验收与发布；旧版 87/51 测试及真实冒烟只证明其覆盖范围；旧实现的独立复核剩余项（锁恢复并发等）不能因需求改动视作关闭。

## Constraints
- 基线 4fc1071；origin/main 领先 1（bot 数据提交 dc6db79），同步需核冲突，不盲选 fetched_at。
- 当前授权为修订规划；保护已有未提交代码和数据，不回退；实施获用户批准前不动生产代码；不提交、不推送、不部署。
- 不擅自更新旧 handoff/roadmap；冲突以 CONTEXT 与最新交付证据为准。

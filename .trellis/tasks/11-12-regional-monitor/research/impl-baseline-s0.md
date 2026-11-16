# S0 实施基线记录（2026-11-15，用户批准实施后立即捕获）

## git 基线
- HEAD: `4fc10710ac830f5b3f4aca4ad55f001190711468`（main），`main...origin/main` = ahead 0 / behind 1（origin 有 bot 提交 `dc6db79 chore(data): weekly update 2026-11-13`，尚未合并）。
- 工作树改动（未提交）：M=weekly.yml、11-06 task.json、README.md、data/changes.log、data/flu_south.csv、data/flunet_china.csv、data/sentinel_national_rates.csv、data/sentinel_rank.csv、run_local.bat、src/{build_site,compute_index,fetch_flu_south,fetch_flunet,fetch_sentinel,write_run_status}.py；??=本任务目录、data/{flu_north,heilongjiang_flu,heilongjiang_sentinel,locations,location_product_map}.csv、src/{data_io,fetch_heilongjiang,run_pipeline}.py。
- 说明：flunet/sentinel_*/flu_south 的 M 来自 2026-11-14 真实本地管线冒烟（run_id 20261114T222654-efc3d8d3，六源 ok），属合法数据推进，不是本次规划污染。

## 冻结与评审
- 受审快照：research/plan-freeze-r4.md（digest b5f916fb…e8f6，33 依赖 + data 基线 10 文件 + 工作树清单）。
- 评审：round 1（r3）INCONCLUSIVE → round 2（r4）**PASS 无 BLOCKER**（research/plan-review-search-r{1,2}.md）；轮次预算已用尽。
- 用户批准：2026-11-15 question「批准实施（推荐）」。提交/推送/部署另行授权。

## S0.3 目录配置（本轮生成）
- `data/locations.csv`：400 行 = 可查询 397（省级 31 + 地级 333 + 省直辖县级 33）+ 港澳台 3 行占位（monitor_coverage=false）。草湖市 659013 source=dmfw（用户批准的单条补正）。SHA-256 前 16 位 `188727992c19cbd6`。
- `data/location_product_map.csv`：400 行；flu_region/sentinel_region 双产品各带来源；分布 south=206 / north=191 / unknown=3（港澳台）。SHA-256 前 16 位 `36ff41f8332d08ce`。
- 生成脚本 `.tmp_a2/gen_catalog.py`（CC0 `data/2025.txt` 本地快照 `.tmp_a2/areacodes_2025.txt`，3212 行校验通过）。
- 生成中修正一处 bug：直辖市规范名含「市」字导致 region 误判 unknown（重庆/北京/天津/上海）→ 重生成后正确（重庆 south 等），已在 changes.log 留痕（三条：新建×2 + 修正×1）。

## 基线映射要点（S5 验收将引用）
- 同名消歧：220000 吉林省 / 220200 吉林市；460000 海南省 / 632500 海南藏族自治州（青海，north）。
- 省直辖县级：419001 济源市(豫)、429004 仙桃市(鄂)、659001 石河子市(新)、659013 草湖市(新, dmfw)——parent 均为省级 + direct_under_province=true。
- 港澳台：710000/810000/820000，monitor_coverage=false，不可查询。

## 流程备注
- implement.md S6「由 implementor 统筹」与项目 AGENTS.md「主会话直接实施」冲突：按项目约定执行（主会话统筹 + designer 串行界面），已在此留痕。

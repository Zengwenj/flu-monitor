# A2 实施报告（regional-monitor）

日期：2026-11-13 ｜ 任务：`.trellis/tasks/11-12-regional-monitor/`（本目录）｜ 基线 commit：a945917（plan-freeze-r2 对应工作树）

## 一、交付内容总览

**五页静态站**（`src/build_site.py` render 一次生成，暂存校验后原子替换）：

| 页 | 内容 | 数据 |
|---|---|---|
| index.html（成都） | 原 6 卡不动 + A1b 历年同周对比 + 两组导航（成都 active）+ 南方片卡"查看南方片页›" | flu_south + sentinel + flunet + sichuan |
| south.html | 与成都共用同一南方片视图/历史卡（同函数同视图实例）+ 片区门急诊/住院前三名（仅名称）+ 全国参考 | flu_south + sentinel + flunet |
| north.html | 北方片流感指数卡 + 北方独立历史同周卡 + 北方片区前三名 + 全国参考 | flu_north（新建）+ sentinel + flunet |
| heilongjiang.html | B1 省级流感摘要（ILI/阳性率/样本/阳性数）+ B2 当期哨点病原观测（门急诊/住院分组，官方率）+ 北方片背景 + 全国背景（均标注非黑龙江实测） | heilongjiang_flu / heilongjiang_sentinel（新建）+ flu_north + sentinel + flunet |
| chongqing.html | 重庆官方入口链接卡（cqcdc 监测预警栏目）+ 版权说明 + 南方片/全国背景 | 无重庆数值（版权未授权转载） |

**数据层**：
- `data/flu_north.csv`：201 行（2023W1–2026W45，全 ok，goldstein 已算）。北方分母取自同一 PDF 表 1 北方列（`parse_issue(region="north")`），括号互校 1.5%、表 1 列和 0.2% 容差、期号频次守卫与南方共用。
- `data/heilongjiang_flu.csv`（B1）：42 行全 ok（2025W1–2026W45，官方栏目有周报的周）。SAMPLE_PAT 三变体：`其中N份…阳性` / 无"其中"前缀 / `核酸检测均为阴性`（阳性 0）。
- `data/heilongjiang_sentinel.csv`（B2）：2026W45 门急诊/住院两组病原行（按周整批替换，并列展开、伙伴同率校验）。
- 回补对账口径（黑龙江 B1）：目标 97 周 = 42 已入库 ok + 1 解析失败（2025W2 上游正文日期笔误「2024.1.6」）+ 54 本次遍历列表未发现（**不写"官方未发布"**，仅"本次遍历未发现"——按复核要求）。覆盖证明脚本 `.tmp_a2/hlj_title_coverage.py`（按标题周次，非列表发布日期）。

**管线与状态**：
- `src/data_io.py`：共享原子写（.tmp_writes 唯一临时文件 + fsync + os.replace）；三个旧采集器（sentinel save / flunet 保存出口 / flu_south save_rows）全部接入，22 行守卫不动。
- `src/run_pipeline.py`：单写者锁（O_CREAT|O_EXCL 排他；死锁可 --force-unlock，活锁强制解锁被拒）、run_id 隔离运行目录、skip 聚合、本地/云端 build 参数（--local / --run-status+--run-id）、pipeline_exit 与 build_exit 分键、site_ready 门（最终状态写成功才置真）。
- `src/write_run_status.py`：v2 schema 聚合；结果文件与子进程终态联合校验（stage/origin/run_id/exit/timed_out）；flunet 判据=真实列；空表不成功；exit=1 部分失败逐产品采信。
- `src/compute_index.py`：TARGETS 注册表 + `--targets south,north,heilongjiang`；ok 行缺值=整文件失败原文件不动；逐目标异常隔离。
- `src/fetch_flu_south.py`：`--regions south,north` 一次下载两区独立解析写入；txt 缓存 + .json meta 来源绑定（article_url/pdf_url/title/week/anchor）；upstream_revise 覆盖留痕；log_change 净化固定 5 列。
- `src/fetch_heilongjiang.py`（新建）：B1/B2 双产品、--backfill（BACKFILL_CUTOFF=2024-12-30 整页日期判界、MAX_EMPTY_STREAK=6、news1 容器消失=正常终点/容器在 0 候选=结构异常失败）、--products b1|b2、--from、位置参数=只读 URL 抽验、同周多篇同值代表/冲突失败。
- `.github/workflows/weekly.yml`：run_pipeline 接入（读 last_run.json exit=pipeline_exit）；run_local.bat 更新。

## 二、来源与授权链（已亲核）

- 南方/北方：国家流感中心《中国流感监测周报》ivdc 列表（每期 PDF 内表 1 含南北两列分母——北方数值官方存在，非推算）。
- 黑龙江 B1：hljcdc 热点关注栏目 id=120（周报唯一发布栏目，其它栏目实测 0 条）；B1 给 ILI%+阳性率+样本数。
- 黑龙江 B2：同栏目《黑龙江省急性呼吸道传染病哨点监测周报》，门急诊/住院两组病原（部分病原官方率，非完整 11 病原表）。
- 重庆：cqcdc 版权声明（catid=36）明确禁止未经许可复制发布 → 经用户确认（question 卡片）只放官方入口链接 catid=209，不转载数值。
- 全国哨点/FluNet/四川：沿 A1 前既有源不变。

## 三、与冻结计划的实施偏差（均已留痕）

| # | 偏差 | 原因 |
|---|---|---|
| 1 | 黑龙江 B1 上界=2025W1（计划按栏目实际最早周报） | 官方栏目 2025-01 前无流感周报（24 页实测） |
| 2 | SAMPLE_PAT 三变体（含"均为阴性"=阳性 0、无"其中"前缀） | 上游正文实测三种句式，缺一即 44 篇中 8 篇误失败 |
| 3 | 分页 0 候选页继续翻页 + 整页日期判界（BACKFILL_CUTOFF） | 列表被非周报文章隔断（p5/p6 候选 0 属正常）；候选日期判界会翻到 2017 年 |
| 4 | 2025W2 判失败（上游正文日期笔误「2024.1.6-2025.1.12」） | 7 天校验拒绝上游笔误，数据诚实性优先 |
| 5 | B2 卡显示官方百分比（计划文本允许：省级哨点实测非片区排行） | display-proposal §4：省级官方公告可显官方率 |
| 6 | 锁移入 .tmp_pipeline/（复核非阻塞认可） | .gitignore 目录模式覆盖 |
| 7 | _pick_b2 分组键从标题周次改为**正文周次**（round-2 修复验证期发现） | 真实数据伪冲突：16 篇 B2 中 1 篇标题不可解析 → 旧"保守全解析"把不同周文章放同一签名集合 → 2026W45 被误判冲突；改后标题不可解析者解析后按正文周归位（回归测试 H3_05/H3_06） |
| 8 | 缓存写入显式 `newline="\n"` + 摘要按 read_bytes 校验（round-2 修复期发现） | Windows 文本模式把 \n 翻译为 \r\n，meta sha256 永远不符（缓存绑定在 Windows 必然失效） |

### oracle round-2（12 项 NOT-CLOSED）修复摘要

修复均已落盘并有测试映射（round-2 完成时 check_regional.py 77 项；round-3 后扩至 87 项）：
- IMP-01 锁：不可读/pid≤0 锁一律拒绝不删；force+死锁复读一致才删；force+活锁拒绝（R4×3）。
- IMP-03：read_result 顶层类型校验；manifest schema/origin/run_id 四重校验（D3_01）。
- IMP-04：PAGE_SOURCES 按卡片实际依赖重写（U6_01）；删"本轮采集计算未全部完成"恒误报后缀；render 拒绝错 run_id（U6_02）。
- IMP-05：预聚合失败=管线失败不构建（R3_01）；最终判断含 status_ok；say(file=) 修复。
- IMP-06：暂存目录带 pid+uuid 唯一化；_validate_pages 单双引号全量+绝对路径拒绝（E1_02-04、E2）。
- IMP-07：占位行（category=全部）参与锚周不静默回退；"官方未提供"改"本工具未取得"；每组各自当期链接（U5×3）。
- IMP-08：B2 同周多篇规范化比较（等值确定性代表/异值冲突保全旧表），分组键=正文周次（H3×6，含偏差 #7 修正）。
- IMP-09：无 news1 的非空响应=疑似验证码/改版失败；解析异常捕获扩到 Exception；hi 含解析失败周。
- IMP-11：--products 别名 flu/sentinel；--from ISO 周校验；--write-url/--result-file/--run-id 缺值拒绝；产品门控不越界（D6）。
- IMP-12：缓存 meta 五键全验（article_url/pdf_url/title/week/sha256 按字节）；不符重下留痕；旧裸 txt 一次性复用+补建 meta（D3_05 A-E 场景）。
- IMP-13：B2 签名含 sample_count/total_samples；B1/B2 覆盖前比对留痕；log_change 五列净化（tab/换行）。
- IMP-14：C1 flunet 走 _convert 真实保存出口强杀；R3 受控故障注入矩阵（预聚合失败/构建失败/单源失败/超时）；E2 校验失败不替换旧页；U5 真实占位行夹具；R1/R2/R4 隔离根不碰真实锁。


## 四、验证证据（全部主会话见证执行）

| 门 | 命令 | 结果 |
|---|---|---|
| S5 正式套件 | `python -X utf8 .trellis/tasks/11-12-regional-monitor/validation/check_regional.py` | **Ran 87 tests, OK**（exit 0；含强杀沙箱 C1×5、锁 R1/R2/R4 隔离根+受控故障注入 R3×5、D3×7 缓存全绑定+read_result/step_of 分支、H3×8 B2 多周守卫、U5×4 占位锚周+来源标注、E2 校验/替换失败保旧页） |
| A1b 回归 | `python -X utf8 .trellis/tasks/11-12-regional-monitor/validation/check_history_compat.py --check` | **Ran 51 tests, OK** |
| 本地构建 | `python -X utf8 src/build_site.py --local` | exit 0，五页生成（暂存→校验→替换） |
| 页面契约 | `python -X utf8 .tmp_a2/s3_page_contract.py` | PASS 0 项问题 |
| S1 离线回归 | `.tmp_a2/s1_region_regress.py` / `s1_hlj_regress.py` | 0 FAIL / 0 FAIL |
| git 卫生 | `git diff --check` | exit 0（仅 CRLF 提示） |

oracle round-1（ses_e2d5cda0bffehWejGKwPfsXI0I）14 项 BLOCKER、round-2 剩余 12 项、round-3 剩余 7 项均已修复；round-3 修复明细见下节，评审记录 research/plan-review-imp-r3.md。

### oracle round-3（7 项 NOT-CLOSED）修复摘要

修复均已落盘并有测试映射（check_regional.py 77→87 项）：
- IMP-01 锁恢复竞态（关闭条件：同一互斥协议/同步屏障测试）：force+死锁删除改为 **rename 原子夺取 + 内容复核**——rename 成功者复读 token，pid 与判定值一致才获得删除权；不一致（夺走的是他人重建的新锁）放回原位回循环重判，绝不基于过期判定绕过（R4_05 双恢复者同步屏障测试：恰一个持锁、无 .dead.* 残片；顺带修掉 uuid4 未导入的 NameError）。
- IMP-04 显式状态完整校验（关闭条件：v2+run_id+origin+结构）：render 对 --run-status 输入五重校验（dict/非"bad"/schema=2/run_id 匹配/origin∈local,cloud/sources 为 dict），任一不符 SystemExit(2)；无显式状态的本地ℹ注明/云端坏文件降级路径不变（U6_02 夹具升级）。
- IMP-08 round-3 变体（候选保全）：_pick_b2 对"标题=最新周或不可解析"的候选**任何**解析失败即整期失败（reason 区分全部/部分失败），绝不从成功集合倒退选周（H3_07/H3_08）。
- IMP-09 终点判定：删除"非空短响应=正常越页"分支——news1 容器消失一律 failed（验证码/维护页同罪），停止依据只剩 BACKFILL_CUTOFF 整页日期边界与 MAX_EMPTY_STREAK；parse_one 解包前 None 检查。
- IMP-11：`_val(argv,i,opt)` 助手（缺值/值以 -- 开头 → 联网前 return 2，D3_04 扩 4 例）；write_result_file 只写请求产品（D6_02）。
- IMP-12 完整绑定分级（关闭条件：pdf_url 有效性）：meta 须五键且 pdf_url 为有效 http 才算完整绑定（零请求信任）；pdf_url 无效（如 legacy 补建空串）=一次性候选，复用文本但每轮重取文章页补全绑定（1 请求、0 PDF），补全写回完整 meta + cache_legacy_bind 留痕；坏 JSON meta 也留痕 cache_invalid（D3_05 A–F 六场景，含 F："pdf_url 空不升级信任"）。
- IMP-14 测试补齐：D3_01b（read_result 顶层类型/step_of 条目非 dict→None，生产侧 step_of 同步改严格契约）；R3_05（最终状态写失败 → site_ready 关门）；R4_04（空锁/坏 JSON/pid0 + force 仍拒绝）；R4_05（双恢复者 Barrier(2)）；E2_02（os.replace 失败外显不吞、后续页保旧）；H2_09（B2 仅标本数修订留痕）；U5_04（来源标注"表2"非"表2/表3"）。

## 五、未验证项（如实）

- 云端新省站（hljcdc/cqcdc）在 GitHub runner 的连通性未实测——境内可达已亲核；境外受限时 B 组源标 failed、南方/全国源不受影响（失败隔离已沙箱验证）。
- 线上五页部署与 workflow 真实运行：待用户批准提交推送后首次触发验证。
- file:// 双击打开 + 320/360 视觉：subagent 只读复核通过（320/360/414 无横滚、导航 ≥44px、对比度达标）；键盘 Tab 焦点无自动证据，建议用户双击 `site/index.html` 亲验一次。
- 黑龙江 B1 历史"重复/冲突 id"（7090/7104 等）已在 source-feasibility.md §4 留线索，当前实现对同值重复取确定性代表、冲突判失败，未逐篇人工复核全部 44 篇。

## 六、文件清单

- 生产代码：`src/build_site.py`（+渲染五页/暂存校验/按页横幅）、`src/run_pipeline.py`（新）、`src/data_io.py`（新）、`src/fetch_heilongjiang.py`（新）、`src/fetch_flu_south.py`（regions/缓存 meta/留痕）、`src/compute_index.py`（targets/整文件失败/隔离）、`src/write_run_status.py`（v2 联合校验）、`src/fetch_sentinel.py`+`src/fetch_flunet.py`（仅保存出口原子化）、`.github/workflows/weekly.yml`、`run_local.bat`、`README.md`
- 数据：`data/flu_north.csv`（新）、`data/heilongjiang_flu.csv`（新）、`data/heilongjiang_sentinel.csv`（新）、`data/flu_south.csv`（W45 追加）、`data/changes.log`
- 任务资料：本目录 prd/design/implement/validation/check_regional.py/check_history_compat.py/research/*

## 实施复核链终态（oracle round-1 到 round-5）

round-1 BLOCKED（七项）→ round-2 CLOSED 02/07/IMP-01，NOT 01/03/04/05/06 → round-3 修复后 01/03/04/05 CLOSED，06 NOT（映射/断言深度/克隆异常）→ round-4 A01 CLOSED（匹配三级：精确→前缀→包含，剥后缀移除），06 NOT（映射纠偏/管线两断言/克隆异常）→ round-5 PASS：七项全部 CLOSED；IMP-01 按人工恢复策略关闭（边界：删锁前停所有写者；独立 CLI 不与管线并发；不称绝对单写者）。

最终门：Q-SUITE OK 56/56（Q1-Q13）、build --local 过、git diff --check 干净、data/ 12 文件 sha256 不变；真实无头 Chromium+file:// a-f 六序列 ALL-PASSED（含语法错误/缺模板/克隆异常三类故障恢复）；映射表 138 条（保留 111/等效 13/恢复 3/废弃 11，占位 0）。未验证边界如实保留：读屏播报、触屏/IME、窄屏、Firefox/Safari、用户人工验收。结论不构成提交/推送/发布授权。

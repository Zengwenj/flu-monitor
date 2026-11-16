# A2 可执行计划 r2

当前仅规划；执行从用户批准后开始。主会话负责抓取/计算/管线现场实现；designer负责视觉与模板改造，同一build_site.py必须串行交接；oracle负责独立只读复核。本文中的新CLI/测试命令为待实现接口，不是假称当前已存在或已运行。

## S0 基线与来源夹具（主会话）

1. git status、HEAD与最新远端差异核对；保护用户修改，不自动stash/pull冲突。记录基线版本与data全文件hash。备份到`.tmp_a2/baseline/`，不提交。
2. 重新读取CONTEXT、handoff红线、A1a/A1b归档设计以及本任务冻结计划。task.py start在实施批准后调用。
3. 把可复现验证写入本任务`validation/check_regional.py`（unittest）；沙箱固定时钟和临时ROOT，不改权威数据。官方全文/PDF缓存只在.tmp_a2，入库夹具采用最小结构化自造片段，真实样例保存URL+SHA与期次/预期字段说明。
   同时把A1b归档用例迁移到本任务`validation/check_history_compat.py`，不修改历史归档。通过向上寻找同时含`CONTEXT.md`与`src/build_site.py`的目录定位ROOT，找不到即失败，不用固定parents层数；入口`--check`实际执行unittest并以0/1报告通过/失败，usage非0。适配清单见S5，先建立49项逐ID映射后才改展示代码。
4. 北方先核2023W32空白变体、2025W18两列、W44/W45两入口与括号/零值样例；按source-feasibility.md基准，不照抄研究者错误算术。复核黑龙江B1至少当前/历史/重复/冲突各一类，B2当前+旧版拒绝。黑龙江使用条件若发现限制，暂停相关产品交用户决定。

验收：所有未来回归输入可由仓库测试脚本复现，真实样本可溯源。当前199/199只是前期探针，不代替该步骤。未通过来源与期次契约，不开始写权威数据。

## S1 数据接口与隔离（主会话）

范围：`src/data_io.py`新增；`src/fetch_flu_south.py`区域显式解析/写入参数与结果文件；`src/fetch_heilongjiang.py`新增；`src/compute_index.py`参数化和原子写；`src/fetch_sentinel.py`的save及`src/fetch_flunet.py`最终保存仅接入原子助手。最后两者不改解析、字段、覆盖规则或22行守卫。旧南方CLI默认不变。新CLI必须用明确参数解析，不把未知选项误当URL。

目标CLI：

```text
python -X utf8 src/fetch_flu_south.py --regions south,north --result-file <path> --run-id <id>
python -X utf8 src/fetch_flu_south.py --backfill --regions north --from 2023W1
python -X utf8 src/fetch_heilongjiang.py --products flu,sentinel --result-file <path> --run-id <id>
python -X utf8 src/fetch_heilongjiang.py --backfill --products flu --from 2025W1
python -X utf8 src/compute_index.py --targets south,north,heilongjiang --result-file <path> --run-id <id>
```

黑龙江URL抽验只打印不写；`--write-url`是经确认后人工消歧入口，不作为自动失败回退。新结果文件只表达本次请求产品；错误输入/ISO周/反向范围/limit非正数在联网写入前拒绝。

聚焦验证：区域互不阻断、共同身份错误、old CLI兼容、force坏结果保留缓存、同周冲突保留CSV、B2整周替换及并列多行、三个指数目标独立失败、temp写中断/replace失败原表不变。禁止在真实CSV注入故障。
旧采集器保存故障须用真实子进程沙箱：父进程等待测试屏障确认临时文件已打开且部分行写入后强制终止（不能仅raise异常模拟硬终止），验证sentinel两表及flunet旧表hash不变、完整可读；另在sentinel第一表replace后、第二表写入中终止，断言第一表完整新值、第二表完整旧值，各卡不混周，独立成功产品不回退。后续步骤忽略残留暂存文件。临时git仓库复用项目.gitignore，硬终止遗留`data/.tmp_writes/`后执行`git add data/`，断言`git diff --cached --name-only`不含临时文件（仅沙箱执行）。该组通过才接S2超时路径。

## S2 本地与云端运行闭环（主会话）

范围：`src/run_pipeline.py`新增，`src/write_run_status.py`升级，`run_local.bat`与`.github/workflows/weekly.yml`接线。依据design §4/6实现run_id隔离、阶段状态、timeout、锁、退出码与site_ready。可先用fake子进程测试，再接真实入口；不为测试运行远端部署。

验证：六源分别失败/跳过/未知、批量一个成功一个失败、compute失败、子进程被终止、旧run_id、空环境outcome、坏JSON、local/cloud相互污染、第二个管线启动拒绝。省站不受CDC门影响。确认只有云端完成后写data/run_status，直接build --local不读取历史运行记录。

## S3 展示（主会话数据适配→designer串行视觉→主会话文案）

范围仅`src/build_site.py`，不得与S2对同文件并发写。主会话先提供区域视图/状态输入契约和固定夹具；designer按display-proposal与design五页内容落实两组导航、复用A1b、B1摘要/B2分组表、重庆链接卡。主会话核对所有地区/样本框/来源/时间/失败文案。

`python -X utf8 src/build_site.py --local`生成五页（不联网/不改CSV）；新增`--run-status/--run-id`接受本轮状态。五页先临时生成校验，失败不打开、不部署；无跨文件原子承诺。

## S4 首次数据补齐（主会话，依赖S1/S2离线通过）

1. 更新锁外的回补只允许单写者，确认无运行中的workflow与本地管线，不启动两次。
2. north-only回补2023W1至实际发现最新周；复用缓存并下载缺周，礼貌限速>=2.5s，网络失败可中断续跑，不反复强刷。逐周对账及源链；南方CSV此步骤hash不变。
3. 黑龙江B1按已发现2025W1以来周报回补，报告覆盖与冲突，不把未发现写为不存在。B2首次仅当前2026版式；若未知新版失败，保留旧数据与原因。
4. 再跑全部最新抓取→全部指数计算→本地构建，顺序不可颠倒，避免抓取将最终指数清空。
5. 检查新CSV唯一/升序/有限值/来源元数据/指数公式；南方全部旧数值与A1基线比对，允许真实新周与有证据的上游修订但必须逐项留痕，不无意改旧数据。

停靠：最新北方与前周无法核验、黑龙江当期无有效样本、覆盖存在未解释差额时，不宣称完整成功。先报告原因；仅有已解释历史缺口可进入诚实断线验收。

## S5 最终验证与独立复核

写作与实现合并后由主会话一次执行全量，精确记录命令、退出码、日志、CSV统计和页面检查。修复后只重验失效证据，最终产物重新生成。

```text
python -X utf8 .trellis/tasks/11-12-regional-monitor/validation/check_regional.py
python -X utf8 .trellis/tasks/11-12-regional-monitor/validation/check_history_compat.py --check
python -X utf8 src/build_site.py --local
git diff --check
```

| ID | 必须断言 |
|---|---|
| D1 | 南北分母列与前期实测基准、字间空白、零、越界/非有限值、未知版式拒绝 |
| D2 | 南北部分成功及共同失败；north-only不改south；force失败旧缓存及CSV逐字节保全 |
| H1 | B1当期与前周不会错抓；计数四舍五入校验；标题正文日期/ISO冲突拒绝；重复等值确定性、冲突不覆盖 |
| H2 | B2两场景齐全、并列>3、缺组拒绝、样本和一致；同周重抓清旧选择；不补零/不算指数 |
| C1 | 每文件原子计算、附加列保留、故障中断/replace失败、其他产品继续；旧sentinel/flunet保存子进程强杀与两表中途终止保护；暂存残留不入库 |
| R1 | 六源状态/run_id/origin/缺键/旧JSON/坏JSON/中断；fetch成功compute失败不假成功 |
| R2 | 0/1/2退出码语义；超时继续其他源、锁拒绝；构建失败site_ready=false且bat不打开/CI不上传 |
| U1 | 五页相对导航闭合、活动项唯一、零外部加载；重庆无数值转载和虚构fetch状态 |
| U2 | 非成都无四川等级；全国/片区不冒充本地；成都/南方同锚同值；北方无南方硬编码（导航与口径说明除外） |
| U3 | A1b原49项逐ID迁移/替代映射，无无理由skip；历史按各自同口径，不混FluNet |
| U4 | B2表为正文部分观测，失组/旧期/失败显示准确；非当前查询不展示无关源失败 |
| E1 | 生成五页及失败重建均不修改CSV；完整生成才允许发布；真实数据基线与日志可核对 |

### A1b回归迁移清单（49项全部对应，不以原脚本直接运行替代）

原始文件：`.trellis/tasks/archive/2026-11/11-12-flu-south-history-view/validation/check_history.py`；实施时在`validation/history-case-map.md`记录每个原`Class.test_*`对应的新测试及有意差异。运行日志列出真实测试ID、数量、失败/skip，不以usage或“49项”文字作通过证据。

| 原组 | 数量 | 迁移/替代约束 |
|---|---:|---|
| Reg | 3 | test_01仍比对未改的全国/儿童/四川helper（原FUNCS仅去除run_banner）；test_02仍做非目标卡片输出对比；test_03不再对比旧banner输出，替代为v1历史信息、v2本轮、local无状态与run_id不符等R1断言 |
| D1 / D2 | 9 / 5 | 全部保留周键、重复冲突、确定性平局、有限值/零值、异常锚周不回退及元数据/URL验证；仅适配显式south字段接口 |
| M / H | 11 / 9 | 全部保留ISO相邻周、跨年W53、缺周/异常/失败区分及历史窗口/非法行上屏；源运行提示的新增内容另由R1验证，不弱化数据周断言 |
| B / G | 5 / 3 | 全部保留来源链接安全、转义与注入防护、轴尺度/域和孤立点可见；适配地区参数而不删断言 |
| T | 2 | test_01改名固定W44表格夹具：四年行的日期、ILI、阳性率、指数与来源URL一同固定（2026=82.27、2025=75.72、2024=16.49、2023=128.36）；逐行6列及来源归属仍验，不读实时CSV后硬断言W44。test_02转义保留。另新增实时数据检查，以实际最大合法周推导期望表值，不硬编码最新周 |
| E | 2 | 把旧OUT单文件替身迁移为隔离五页输出目录；全站无外部加载/无旧占位、构建不改data字节均保留并扩展五页；失败构建另由E1验证 |

浏览器：逐页file://实开；320/360/桌面宽，页面无横滚、导航全可点、Tab焦点可见、触控项>=44px，历史表仅容器滚动；记录实际浏览器/方式/截图。无自动化时用户双击site/index.html，F12切尺寸截图，明确人工证据；不能用HTTP截图代称file://已验。设计负责人处理视觉问题，主会话不越权改视觉。

oracle只读复核代码、来源/覆盖报告、全部验证记录；有阻断先修，不用测试个数替代数据与状态正确性。用户Excel抽验新增CSV并确认页面后，才进入交付批准。

## S6 文档与授权门

本任务`research/implementation-report.md`记录覆盖、真实URL、所有偏差、测试及未验证项；README说明五页与run_local、旧CLI、数据口径。handoff更新仅在用户授权收尾文档时进行，不能把旧状态继续当事实。当前不提交、不推送、不触发部署。

用户另行批准提交上线后：先核对workflow空闲与远端，安全pull并处理bot数据差异；分docs/feat两笔，归档安排在触发workflow之前，禁止部署运行期间push。部署验收必须日志site_ready/正确CSV计数+五个线上URL可见且跳转无误；失败按原因停，不谎称上线。

## 写域与回滚

生产代码允许：上述9个src文件（data_io/run_pipeline/fetch_heilongjiang新增，fetch_flu_south/compute_index/write_run_status/build_site修改，fetch_sentinel/fetch_flunet仅保存动作原子化）、run_local.bat、weekly.yml。数据允许：flu_north/heilongjiang_flu/heilongjiang_sentinel新增，flu_south/changes.log必要更新，run_status仅云端；既有sentinel/flunet文件仅正常已授权全管线采集更新，不改其解析和业务守卫。README和任务资料为相关文档。site与.tmp均不提交。

不改全国22行守卫、四川录入、共享全国_adjacent_week、A3/A4。新增产品有独立CSV，因此回退不需迁移旧表；备份恢复只针对已核受损文件，先检查后来修改。回退构建为原单页后清理仅本任务生成的额外页须先核目标清单，不宽泛删除site或data。

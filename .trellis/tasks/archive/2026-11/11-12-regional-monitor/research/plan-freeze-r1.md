# A2 frozen plan r1

protocol_version: review-1
round: 1
baseline_commit: 4fc10710ac830f5b3f4aca4ad55f001190711468

## SHA-256 source and dependency manifest

- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\prd.md` SHA256 `f18d76ecc8f75a4f3b52c4805aea8f0bdace32249de986374457c346178d2aec`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\design.md` SHA256 `d5364a918822a8402ed8c8424cb1770a760e6034cd089f6071b27fef78c9a0cc`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\implement.md` SHA256 `70849e00e6e9971fdfc9d978378a0fed6946e48bb384672cbea819afe7ecc822`
- `D:\FluMonitor\CONTEXT.md` SHA256 `cf08c836fe8de9c21646d32032fd515e2bfbfece87048a69f6d6585eebb89c36`
- `D:\FluMonitor\docs\handoff.md` SHA256 `dd254a9e64d0380675097958f3df1f593e794d3d47217ffb99815296050bb91e`
- `D:\FluMonitor\src\fetch_flu_south.py` SHA256 `1f09cff6739a3f3e42caedfbb24dc4bd7f35fc3acafd4bafe574982bcb12bd20`
- `D:\FluMonitor\src\compute_index.py` SHA256 `ca28b25e5dfea866e0f81be1ff1c50fc8aa1eb5aa82750658f1fd9d9f904f63a`
- `D:\FluMonitor\src\build_site.py` SHA256 `510534388b6b56c21e363488ae3f0093b64af37696a404432995db3117a75b09`
- `D:\FluMonitor\src\write_run_status.py` SHA256 `20b06b1907b02af14de14fb3c31eb9f2fcebdcc9d9cb073f42f63401a9197eb7`
- `D:\FluMonitor\.github\workflows\weekly.yml` SHA256 `b8f46a0bd4841df51384d05b519a0a841d65831f30fb34fb17e62d0882069b3b`
- `D:\FluMonitor\run_local.bat` SHA256 `cf41d019d86ab2e77bb899a05423a87c87863dc085a2b3e0c6676a9610262f8a`
- `D:\FluMonitor\.trellis\tasks\archive\2026-11\11-12-flu-south-history-view\design.md` SHA256 `f97f80dab8c2ec4e3b3a373ba5d1bb3d21cdcc6b2d36fcbf4047fd1b86876283`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\research\source-feasibility.md` SHA256 `255b69b82ef364825953aad1a7a0cc32ba3061688df46cd0648e69477036596f`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\research\gap-analysis.md` SHA256 `99c608edd29ca6208980ffbfda8c73335ce5f26e07688dbde0aa0177eabb914a`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\research\display-proposal.md` SHA256 `4f18210b0939f3c54ff3c3ef4c6c4f88780b20d2b1d0ee665ffd0bbdc855b585`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\research\architecture-advisory.md` SHA256 `ebeb0c0c0fc0f0a01014e93ccccdf441f08c827b5bb919dd1b859c7816cc01d0`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\research\findings.md` SHA256 `2bc75610afe29eb88b9a7f0ca58335375bb80a65b4f8809b0908effede615231`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\implement.jsonl` SHA256 `6a9651d9ebcd95b86b75bf576d8131f1e7fd193fdac1ef0076a21fead1c2c399`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\check.jsonl` SHA256 `dbf2b0d9d46c17e999197b9cce5d3cede43aba3e7f36fbca5575aa56284e5168`
- `C:\Users\zengw\.config\opencode\REVIEW-PROTOCOL.md` SHA256 `0bf74c7d2d923ace38cb328d588b27bb915d6c9ba9abfc9a6a223323787ea67e`

---

# SOURCE: D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\prd.md

# A2 多地区呼吸道监测查询

## Goal

规划南北片切换及黑龙江、重庆地区查询，核实官方来源、口径与更新频率，形成设计与可执行计划，经成稿评审及用户批准后实施。

## Requirements

- 默认保留成都页，规划南北片查询及黑龙江、重庆补充查询，区分片区、省市与全国证据。
- 先核实官方源的字段、频率、历史覆盖和可获取性，再确定自动采集或明确降级；不得预设省市阳性率存在。
- 全国多病原数值、片区前三名称、省级公告分块标注，不能混算指数或冒充当地风险。
- 保持 CSV 权威存储、静态内联页面、本地 file:// 可用与云端/本地双触发；不引入服务器和云端多模态调用。
- 规划阶段只修改本任务资料与父任务关联，不改运行时代码、data/、部署配置，不提交或发布。
- 已确认：重庆首版采用官网链接方案，保留重庆页与明确标注口径的南方片/全国参考，当地卡不转载正文、数值或图片。该选择仅确认规划范围，不是实施批准。
- 北方片采用独立同口径历史序列；黑龙江流感B1与多病原B2分源，不互换分母、不混算指数。

## Acceptance Criteria

- [ ] 官方源可行性矩阵有可复核链接、样本时间、字段和未验证部分。
- [ ] 完成计划前缺口分析，需求歧义与数据限制有明确处理。
- [ ] design.md 界定数据契约、地区映射、页面状态、兼容性与写入守卫。
- [ ] implement.md 给出分阶段文件范围、依赖、验证命令、停靠点与回滚。
- [ ] implement.jsonl/check.jsonl 为真实文档条目且验证通过。
- [ ] 冻结成稿并完成独立计划审核；实施须另获用户批准。

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.

---

# SOURCE: D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\design.md

# A2 多地区监测设计 r1

## 0. 状态与依据

仅规划，未获实施批准。基线 `4fc1071`；A1a/A1b已完成。前置缺口分析、展示咨询、来源复核与架构咨询见 research/ 四份对应文件，均不替代正式成稿评审。审核路由Standard（不迁移旧CSV、可按文件回退），按项目要求调用plan-critic。

用户已选择重庆“官网链接方案”：保留页面，当地卡只指向官方栏目，不转载其正文/数值/图片。其他范围在本设计经审核后整体交用户批准。

## 1. 范围与页面

输出同目录五页：`index.html` 成都默认，`south.html` 南方片，`north.html` 北方片，`heilongjiang.html` 黑龙江，`chongqing.html` 重庆。地区与片区两组相对链接导航，当前项aria-current，允许换行；遵循 research/display-proposal.md §3 的设计负责人规格。零JS/外部运行依赖，file://可直接用；外链允许但仅http/https、HTML转义、target=_blank时rel=noopener。

| 页 | 内容 |
|---|---|
| 成都 | 原有全部卡片与A1b历史卡保留，加导航；全国块仍标全国 |
| 南方片 | 与成都共用同一南方视图/历史卡；片区门急诊、住院前三名称；全国参考 |
| 北方片 | 北方指数/相邻周环比/北方独立历史同周卡；北方两场景前三名称；全国参考 |
| 黑龙江 | B1省级流感指数及相邻周环比；B2当期正文部分观测；北方背景名称与全国参考，禁止改标省级 |
| 重庆 | 自撰官方入口卡，链接 https://www.cqcdc.org/index.php?a=lists&catid=209 ；南方背景名称与全国参考，均非重庆实测 |

黑龙江首版不加省级多年叠线卡，避免把抽查历史当完整基线；保留入库历史供核对。B2不生成多病原趋势或完整排行榜。黑龙江、重庆、纯片区页不含四川分级；成都继续保留。不得新增综合总分、感染概率或跨地区指数排名。

## 2. 权威存储与兼容

旧 `flu_south.csv` 列、默认CLI与所有既有CSV保持兼容。新增文件均UTF-8 CSV，日期ISO、数值为百分数（3.01不是0.0301），空值不写0，按ISO年周排序。新增源不写入全国哨点两张表，不更改22行守卫。

### 2.1 三个流感产品

- south：原表头不变。
- `flu_north.csv`：`iso_year,iso_week,week_start,north_ili_pct,north_flu_positive_pct,goldstein_index,source_url,source_pubdate,fetched_at,status`。
- `heilongjiang_flu.csv`：`iso_year,iso_week,week_start,ili_pct,flu_positive_pct,goldstein_index,sample_count,positive_count,source_url,source_pubdate,fetched_at,status`。
- 主键均(iso_year,iso_week)；只持久化成功记录，失败保留旧值并记运行状态及changes.log，不生成会污染历史横幅的失败周。
- 抓取成功的更新行指数置空，再由计算阶段回填。失败与未执行不改fetched_at。数值改变记旧/新值；同值重抓可不重写，状态记录本次成功核验。
- 计算规则与现有南方一致：有限数值、ILI/阳性率在[0,100]，`round(float(ili)*float(pos),2)`；不改为Decimal或全国混算。新文件缺失时计算目标返回unknown/缺数据，不偷偷视成功。
- 计算逐文件完整验证后原子替换。文件中非法成功行导致该文件本次计算失败，原文件不动；其他文件继续。构建仍按A1b规则屏蔽非法行，且相关卡提示计算失败。

### 2.2 黑龙江B2正文观测

`heilongjiang_sentinel.csv`：`iso_year,iso_week,week_start,setting,pathogen,positive_pct,sample_count,total_samples,source_url,source_pubdate,fetched_at,status`。
主键(年,周,setting,pathogen)；setting固定门急诊/住院；sample_count为该设置标本数，total_samples为该期两组总数。仅保留官方正文明确给出的病原及百分比；并列展开多行，不把“前三位”强制为三行。

完整一批须具备两个设置、各自非负整数标本数、两组相加等于总数、各组至少一条有限[0,100]率、无病原冲突重复；单组或任何已提取项解析不明，整期不覆盖。同周成功重抓替换该周全部B2行，去除上次选中、本次未提及项；旧周保留。未提及不是零，不补齐11病原，不将文字顺序加工为额外排名。页面逐组标“正文选列，非完整病原谱”。B2不进入Goldstein计算。

## 3. 解析与发现

### 3.1 南北同PDF

保留 `parse_issue(txt, title="")` 南方兼容包装；内部带region显式参数，返回区域字段和告警，不切换全局CSV路径。`fetch_flu_south.py --regions south,north` 为新增显式批量模式；旧无参/URL抽验/--backfill仍默认south。双区域下载和pdftotext一次，区域分别校验写入；缺北方ILI/北方分母非法不阻断南方成功。共同文档身份错误使双方失败。独立CSV路径与字段参数传给写入助手。

沿用A1a文档身份/合并标题与锚文本/封面残留/列合计/失败保全/force绕缓存/最终三分类等契约。表1分母按“南方省份 北方省份 合计”取对应列；共同列合计检验先防总数<=0，再用既有0.2%容差。各区分母>0、0<=阳性数<=分母。正文官方括号优先，沿用1.5%相对互校（含零值）；否则分子/对应分母保留两位，不取表1一位百分比。北方新增分子匹配允许字间/换行空白；南方数值回归必须不变。ILI抽取仍要求区域明确，不从全国或暴发疫情段取分子。

当前周从chinacdc流感列表发现文章及PDF；历史从ivdc归档发现，不拼猜文章URL。两列表进度不同按实际文章身份核验，不用其中一个推断另一个未发布。缓存必须绑定文章URL、PDF URL、文件摘要及周次；旧裸txt仅供首次本地回补候选，须通过身份守卫并由对应历史来源条目关联，不伪造其下载时刻。force重新获取并成功解析后才替换缓存，失败留旧。

北方首次目标2023W1至启动时实际发现的最新合法周（规划观察至少2026W45）；先复用199份缓存，再补缺PDF。按实际目标周集合对账ok/merged_skip/pending_fail，互斥且穷尽。失败不得冒充补齐；缺口仍可诚实展示。首版验收要求最新北方及紧邻上周成功，历史覆盖完整或每个缺口有来源/原因记录与页面断线；不可声称无缺口。既有南方CSV在north-only回补中逐字节不变。

### 3.2 黑龙江

单脚本 `fetch_heilongjiang.py`，B1/B2独立入口和结果。列表 https://www.hljcdc.org/pc/index.php?c=zixun&a=index&id=120 ，GET分页pageno；遍历有界，重复页、异常空内容、分页发现失败要报错，不当作成功终点。列表只用于发现，文章标题/正文/日期区间联合核周，不能把发布时间当数据周。用已装BeautifulSoup从正文容器取文本，排除导航/相关文章。

B1按完整标题“流感监测周报”区分B2“急性呼吸道…哨点监测周报”。提取当期ILI%、当期阳性率、检测/阳性计数，不抓“前一周/往年同期”数值。先校验计数域；官方率与count比率在官方小数位四舍五入误差内一致（容差=0.5×10^-d个百分点+浮点epsilon，d为官方百分比小数位）；不得用粗略固定相对误差误杀小比例。日期区间须7天且与合法ISO周一致，标题周次若存在必须一致。冲突不自动按发布时间择值。

同周多文章：完整规范化数值相同则以(source_pubdate,source_url)确定性选代表并留痕；不同则本轮该周失败、保留旧成功，不自动认定某篇为官方修订。可用`--write-url URL`人工指定单篇消歧（仍需所有内容校验、旧新值日志；未经用户确认不主动使用）。禁止抓一份来源元数据配另一篇数值。

B1首次按列表已发现2025W1及以后流感周报回补（不是宣称2025开办），到较早日期页后仍检查页内所有候选；仅做已发现周集合，不虚构更早覆盖。目标缺期写覆盖报告，最新与前一期抽验。B2首版只收2026现行分组版式最新一期，随后逐周积累；不回补2025合并框架，不承诺历史可比。发现新一期版式不满足§2.2时整期失败保全，不回退更旧期冒充最新。

黑龙江资料使用条件在S0复核；只存结构化观测与必要出处，不复制建议段或图片。若发现禁止相应使用的条款，暂停该产品实施并请用户决定，不静默降级为已完成。

## 4. 写入、执行与运行状态

采用少量共享原子写助手 `src/data_io.py`：同目录唯一临时文件→flush/fsync→os.replace，finally清临时。不跨CSV事务。抓取与计算的每个目标文件独立成功；失败不会回退其他成功产品。旧附加列和列序在计算阶段保留。日志按既有五列tab格式记录原因，文本换行/tab转义，不记录凭证。

新增轻量 `src/run_pipeline.py` 统一本地/云端顺序调用现有脚本，不引入新调度服务。持仓库级更新锁，第二个管线实例拒绝；直接CLI/人工编辑/回补不得与管线并发，明确提示此锁不覆盖绕过管线的独立进程。异常退出finally释放，崩溃遗留锁需检查原进程不再存活后人工清理，不凭时间自动删锁。

运行目录 `.tmp_pipeline/<uuid>/`，初始化状态含schema_version=2、run_id、origin、带时区started_at、finished_at与complete=false。来源键：flu_south,flu_north,heilongjiang_flu,heilongjiang_sentinel,sentinel,flunet。各键fetch枚举ok/failed/skipped/unknown；前三个指数产品另有compute同枚举、reason与已知target_week。无结果/缺键/坏JSON=unknown。抓取批量子进程写自己的结果文件（带同一run_id），父进程校验后合并；未终结的结果、run_id不匹配或子进程异常退出不得保留“ok”推定。

父管线步骤：初始化→WHO→全国哨点→双片流感→黑龙江双产品→三个指数计算→汇总运行状态→构建五页→完成状态。捕获进程退出码与超时，单源失败继续；0表示全部请求采集计算成功，1表示可构建的部分失败，2表示管线/构建失败。构建的状态快照标采集计算已结束，整轮complete仍待构建完成；失败/中断不显示为整轮完成。`write_run_status.py` 承担v2聚合与校验，legacy环境变量入口继续可用但空outcome不再默认为ok。

构建显式 `--run-status <path> --run-id <id>`，验证匹配及来源标识；`--local`无显式状态只读CSV、注明未提供本次运行记录，绝不读云端或旧本地状态。云端默认可读已保存v1状态作历史运行信息，标其run_at而不称本次；新管线必须传v2路径。云端完成后将本轮状态原子写到data/run_status.json；本地不写该云端文件。

源提示与数值状态正交：失败/跳过/unknown分别提示，旧值标数据周；计算失败不把fetch成功当指数成功。正常只代表本轮验证成功，不代表预期最新期已发布。重庆无抓取键；地方来源链接卡不假装自动监测成功。按页只显示相关源状态，缺数据不显0、不推测官方未发布。首版不用未经研究支持的统一陈旧天数阈值，显示准确数据期与获取/尝试时间即可。

## 5. 计算与构建复用

`compute_index.py` 保留无参south；新增显式目标选择south,north,heilongjiang。`compute_file(path, ili_field, positive_field)`验证、原子写；返回逐产品结果，不一失败就跳过后续目标。

`build_flu_view` 以默认south字段映射接受北方/B1，保留A1b冲突重复、有限值、最新ok周先锚定、非法周计数、ISO相邻7天环比规则。图、表、aria描述、来源标题全部参数化地区，不把北方或B1挂“南方”标签。黑龙江B1仅用摘要/环比，不开启历史曲线。

片区前三名称从sentinel_rank过滤dimension=region/category=对应省份组，门急诊与住院分别选锚周，缺组明确缺失，不借全国或另一组填充。重复冲突降级，不擅自重排。各组保持来源与周次，不假称所有卡同一期。

生成五页先写唯一临时目录，完整校验全部文件/链接后才替换site受管五文件。本地替换若中途失败返回构建失败，不自动打开；没有目录级原子承诺。云端只有构建成功才上传整个site，不能残留旧页混版。旧非受管文件不删除。

## 6. 运行接线与发布

`run_local.bat` 保留Python路径/UTF8，改调用run_pipeline --local；退出0/1可打开本轮已校验五页并区别警告，2不自动打开旧页。不自动push。

weekly.yml保留schedule/permissions/concurrency及安装步骤，统一调用run_pipeline --cloud；不再用CDC首页可达性跳过独立省站，具体源直接尝试并超时。管线退出1仍允许完整降级站点部署，2阻止上传。实现时分别记录pipeline exit与site_ready布尔输出，不能仅continue-on-error掩盖构建失败。bot仍仅git add data/，提交成功再上传/部署；不得将.tmp缓存或官方原文入库。运行期间不人工push，避免A1b已实见的bot非快进失败。

## 7. 验证、停靠、回滚

验收矩阵与命令见implement.md。必须保留A1b49项回归，并将可复现A2夹具/验证脚本随任务入库；真实数据采集与模拟故障分开，模拟仅沙箱。

实施前备份受影响CSV及hash；北方/黑龙江新文件独立，南方旧表不迁移。回退代码到实施前版本并重新单页构建；取消上传新五页产物。数据只恢复明确受损文件，不能覆盖bot或用户后来有效改动。正式上线须用户人工验收与独立复核后另行确认提交/推送/部署。规划批准不授予发布权限。

---

# SOURCE: D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\implement.md

# A2 可执行计划 r1

当前仅规划；执行从用户批准后开始。主会话负责抓取/计算/管线现场实现；designer负责视觉与模板改造，同一build_site.py必须串行交接；oracle负责独立只读复核。本文中的新CLI/测试命令为待实现接口，不是假称当前已存在或已运行。

## S0 基线与来源夹具（主会话）

1. git status、HEAD与最新远端差异核对；保护用户修改，不自动stash/pull冲突。记录基线版本与data全文件hash。备份到`.tmp_a2/baseline/`，不提交。
2. 重新读取CONTEXT、handoff红线、A1a/A1b归档设计以及本任务冻结计划。task.py start在实施批准后调用。
3. 把可复现验证写入本任务`validation/check_regional.py`（unittest）；沙箱固定时钟和临时ROOT，不改权威数据。官方全文/PDF缓存只在.tmp_a2，入库夹具采用最小结构化自造片段，真实样例保存URL+SHA与期次/预期字段说明。
4. 北方先核2023W32空白变体、2025W18两列、W44/W45两入口与括号/零值样例；按source-feasibility.md基准，不照抄研究者错误算术。复核黑龙江B1至少当前/历史/重复/冲突各一类，B2当前+旧版拒绝。黑龙江使用条件若发现限制，暂停相关产品交用户决定。

验收：所有未来回归输入可由仓库测试脚本复现，真实样本可溯源。当前199/199只是前期探针，不代替该步骤。未通过来源与期次契约，不开始写权威数据。

## S1 数据接口与隔离（主会话）

范围：`src/data_io.py`新增；`src/fetch_flu_south.py`区域显式解析/写入参数与结果文件；`src/fetch_heilongjiang.py`新增；`src/compute_index.py`参数化和原子写。旧南方CLI默认不变。新CLI必须用明确参数解析，不把未知选项误当URL。

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
python -X utf8 .trellis/tasks/archive/2026-11/11-12-flu-south-history-view/validation/check_history.py
python -X utf8 src/build_site.py --local
git diff --check
```

| ID | 必须断言 |
|---|---|
| D1 | 南北分母列与前期实测基准、字间空白、零、越界/非有限值、未知版式拒绝 |
| D2 | 南北部分成功及共同失败；north-only不改south；force失败旧缓存及CSV逐字节保全 |
| H1 | B1当期与前周不会错抓；计数四舍五入校验；标题正文日期/ISO冲突拒绝；重复等值确定性、冲突不覆盖 |
| H2 | B2两场景齐全、并列>3、缺组拒绝、样本和一致；同周重抓清旧选择；不补零/不算指数 |
| C1 | 每文件原子计算、附加列保留、故障中断/replace失败、其他产品继续 |
| R1 | 六源状态/run_id/origin/缺键/旧JSON/坏JSON/中断；fetch成功compute失败不假成功 |
| R2 | 0/1/2退出码语义；超时继续其他源、锁拒绝；构建失败site_ready=false且bat不打开/CI不上传 |
| U1 | 五页相对导航闭合、活动项唯一、零外部加载；重庆无数值转载和虚构fetch状态 |
| U2 | 非成都无四川等级；全国/片区不冒充本地；成都/南方同锚同值；北方无南方硬编码（导航与口径说明除外） |
| U3 | 沿用A1b所有异常/缺周/ISO跨年/冲突/转义49项；历史按各自同口径，不混FluNet |
| U4 | B2表为正文部分观测，失组/旧期/失败显示准确；非当前查询不展示无关源失败 |
| E1 | 生成五页及失败重建均不修改CSV；完整生成才允许发布；真实数据基线与日志可核对 |

浏览器：逐页file://实开；320/360/桌面宽，页面无横滚、导航全可点、Tab焦点可见、触控项>=44px，历史表仅容器滚动；记录实际浏览器/方式/截图。无自动化时用户双击site/index.html，F12切尺寸截图，明确人工证据；不能用HTTP截图代称file://已验。设计负责人处理视觉问题，主会话不越权改视觉。

oracle只读复核代码、来源/覆盖报告、全部验证记录；有阻断先修，不用测试个数替代数据与状态正确性。用户Excel抽验新增CSV并确认页面后，才进入交付批准。

## S6 文档与授权门

本任务`research/implementation-report.md`记录覆盖、真实URL、所有偏差、测试及未验证项；README说明五页与run_local、旧CLI、数据口径。handoff更新仅在用户授权收尾文档时进行，不能把旧状态继续当事实。当前不提交、不推送、不触发部署。

用户另行批准提交上线后：先核对workflow空闲与远端，安全pull并处理bot数据差异；分docs/feat两笔，归档安排在触发workflow之前，禁止部署运行期间push。部署验收必须日志site_ready/正确CSV计数+五个线上URL可见且跳转无误；失败按原因停，不谎称上线。

## 写域与回滚

生产代码允许：上述7个src文件（data_io/run_pipeline/fetch_heilongjiang新增，fetch_flu_south/compute_index/write_run_status/build_site修改）、run_local.bat、weekly.yml。数据允许：flu_north/heilongjiang_flu/heilongjiang_sentinel新增，flu_south/changes.log必要更新，run_status仅云端；既有sentinel/flunet文件仅正常已授权全管线采集更新，不改其抓取逻辑。README和任务资料为相关文档。site与.tmp均不提交。

不改全国22行守卫、四川录入、共享全国_adjacent_week、A3/A4。新增产品有独立CSV，因此回退不需迁移旧表；备份恢复只针对已核受损文件，先检查后来修改。回退构建为原单页后清理仅本任务生成的额外页须先核目标清单，不宽泛删除site或data。

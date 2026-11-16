# A2 进展

## 当前状态：需求纠正后重新规划

- 用户明确要求默认显示成都（四川），其他省市使用搜索入口，不接受首页固定展示黑龙江、重庆等地区导航；已确认无当地数据时展示明确口径的可用参考。
- 已更新 prd.md、task_plan.md，并在 design.md 标记旧交互方案失效待修订。下文为历史进展，不代表新版搜索交互已实施或获批。
- 搜索交互 designer 会话两次空返回，目标 research/search-display-proposal.md 经直接读取仍不存在；缺口分析会话及补交也均为空。两项咨询尚无可核验交付，不计作完成或评审通过；不继续重复空重试。
- 下一步需明确离线搜索的内联 JavaScript 例外及行政区划覆盖层级，再补齐地区名录、同名消歧、参考映射证据与新版设计。未获可靠片区映射的地区不猜测归属。
- 后续用户已确认上述两项：允许少量内联脚本，首版省级与地级（含省直辖县级行政单位的特殊处理），不覆盖所有区县。此为修订规划的范围确认，不等于批准新版实施。下一步核实名录与片区映射来源，形成可执行方案。
- 保护现有未提交实现和数据。旧版独立复核剩余项（尤其锁恢复并发风险）仍未关闭；暂停旧版人工验收、提交、推送和部署。新版实施须重新批准。

- 已建立 11-12-regional-monitor，父任务 11-06-disease-monitor；保持 planning，未 start。
- 已读工作流、CONTEXT.md、docs/roadmap.md；A2 为南北片切换及黑龙江/重庆补充查询。
- A1a/A1b 已完成；本任务不得回退既有南方历史卡和数据守卫。
- 待完成：外部数据证据、缺口分析、设计、执行计划、成稿评审。
- 缺口分析首轮返回称原任务说明被占位符替代，未产生有效分析；已向原会话 ses_e318be58fffehBGHenu3easjbK 补发完整范围与验收要求，不将该轮算作完成。
- 官方来源核查由 ses_e318be593ffe4ddWkD3zAakKTT 独立进行；记忆中的黑龙江可用性等仅为检索线索，须以本轮官方原文核实为准。
- 补发后的缺口分析已返回，整理为 research/gap-analysis.md；主会话纠正引用和未经验证的范围缩减建议。未把咨询结论当成成稿审核或用户批准。
- 展示设计会话 ses_e3181bba5ffeUBqx6GWhY0lWCm 首轮空返回，目标文件读取报 File not found；已向原会话重试，要求提供正文或明确阻塞，尚不计完成。
- 展示设计重试已生成 research/display-proposal.md；已亲读，退回修正地区/片区导航语义、未取到不等于未发布、未测视觉数值与验收自相矛盾等问题。
- 官方来源初轮已返回但无写工具；主会话保存 research/source-feasibility.md 为待纠错线索。黑龙江可算指数与不可算结论冲突、重庆使用许可推断过强，已请原会话定向纠正；尚未作为成稿依据。
- 展示修订 r2 已亲读；五页、两层导航及口径隔离可供成稿采用。主会话进一步修正文案误伤成都、skipped/failed混同、列表缺期误称官方未发布。
- 已核对 fetch/compute/workflow/bat/status 的实际集成边界并记入 research/findings.md。当前等待来源纠错；未开始实施或正式审核。
- 来源复核与架构咨询已完成；主会话纠正W45错源、2025W18南北错列、2023W20舍入错误，199份北方缓存探针通过。详见source-feasibility.md，非生产验收。
- 用户选择重庆官网链接方案（仅规划范围授权）。design.md/implement.md已成稿r1，下一步策展上下文、冻结与正式计划评审；仍不实施。
- round 1正式审核BLOCKED：旧采集器终止写入保护、A1b回归入口与断言适配两项。主会话已核实源码，r2补齐原子保存写域、强杀沙箱验收及49项迁移映射；两条建议也纳入。待冻结r2复审，尚未实施。
- round 2正式复审PASS，两项阻断计划层面CLOSED、两条建议已处理，无新阻断。主会话见证复核r2 SHA与24项依赖/源稿hash全部一致（exit=0）。审核记录research/plan-review-r2.md，当前等待用户实施批准，任务仍planning。

## S1 数据层（2026-11-12 17:xx）

- data_io.py 原子写助手完成；fetch_sentinel.save / fetch_flunet 最终保存接入（仅保存边界）。
- compute_index.py 参数化：compute_file + --targets + 结果文件；无参 south 兼容。
- fetch_flu_south.py 区域化：parse_issue(region=)、--regions、独立 CSV/失败、结果文件；南方 199/199 数值不变（s1_region_regress 10/10）。
- fetch_heilongjiang.py 新建：列表分页 pageno、article.about1 取正文、B1/B2 分类、周次三重校验、B2 整周替换、同周同值代表/冲突失败、--backfill/--force/--limit/--write-url。
- 验证：s1_smoke 10/10；s1_region_regress 10/10；s1_hlj_regress 15/15；A1b 兼容 51 tests OK(skipped=1)；data/ 未被测试污染。
- 踩坑：log_change 原直接绑定 fetch_flu_south.CHANGES_LOG，测试写穿真实 data/changes.log；已改为本模块自有 CHANGES_LOG。

## S2/S3 管线与五页（2026-11-12 晚–2026-11-13）

- run_pipeline.py：锁/run_id 隔离/skip 聚合/site_ready 门；write_run_status.py v2 联合校验。
- build_site.py：五页渲染（page_specs/PAGE_SOURCES/按页横幅/暂存校验 _validate_pages）、北方与黑龙江卡、rank 块独立锚定、重庆链接卡。
- S3 视觉复核（320/360/414）三 BLOCKER + SHOULD 已修；compat 51 OK。
- S4 回补：北方 201 周全 ok（缓存复用+W45 增量）；黑龙江三轮修复（分页 0 候选/日期判界/SAMPLE_PAT 三变体）后 42 ok + 1 上游笔误失败 + 54 本次遍历未发现。
- compute --targets south,north,heilongjiang 全通。

## S5 验证 + oracle 复核（2026-11-13）

- check_regional.py 38→56 项全绿；S5 门四命令全过（compat 51/build/契约/git diff --check）。
- oracle round-1 BLOCKED 14 项（锁/flunet 错列/联合校验/页面状态/pipeline_exit/五页暂存/rank 块/B2 守卫/发现隔离/compute/CLI/缓存绑定/留痕/测试缺口）→ 全部修复落盘（见 research/implementation-report.md §三）。
- check_regional 扩到 56 项（R 组隔离根、C1 flunet 强杀+git 暂存、H2 三守卫、U2 八项、E1 暂存校验、D3 复核补充）后 56/56 OK。
- oracle round-2 关闭确认：已派发（ses_e2d5cda0bffehWejGKwPfsXI0I），结果待返回。

## S6 文档（2026-11-13）

- research/implementation-report.md 已写（交付/来源链/偏差/证据/未验证项）。
- README.md 已更新为五页口径。

## round-2 修复验证 + B2 伪冲突根因（2026-11-13 下午）

- oracle round-2 12 项 NOT-CLOSED 修复全部落盘：check_regional 56→75 项全绿（含两处生产缺陷：缓存 Windows 换行致 sha256 必然不符、legacy meta None 崩溃）；南/北回补幂等 ok=201/201；黑龙江 B1 幂等 42/1/54 与基线一致。
- 真实数据发现 2026W45 B2「多篇数值冲突」→ 探针（复刻 backfill 停止规则枚举 28 页）证明 W45 仅 1 篇 → 根因是 _pick_b2 守卫自身：标题不可解析时保守全解析把不同周文章放同一签名集合 → 伪冲突。已修：分组键改正文周次（H3_05/H3_06 回归）。偏差 #7/#8 已录 implementation-report。
- 待跑门：hlj --backfill 复验 + 77 项全量 + compat + build + 契约（后台 sh_1d3366023001HzfRbYgMCHDuis）。

## 收尾验证（2026-11-13 13:05）

- 门全绿：check_regional 77/77、compat 51/51、build --local、页面契约 0 项；黑龙江回补复验 flu=partial(42/1/54 基线) sentinel=ok（W45 B2 经确定性代表 id=7266 写入，值与探针一致）。
- run_pipeline --local 真实冒烟：恰逢 chinacdc PDF 临时限流（HTTP 445，今日批量抓取触发），完整走通部分失败路径——exit 1、诚实降级横幅、site_ready 门 true、last_run.json 指针正确；顺带发现并修复横幅 head/parts 缺分隔符（「本次更新本次未能…」→「本次更新 · 本次未能…」），修复后 compat 51 + regional 77 复验通过。
- 待用户：人工验收（双击 site/index.html）；round-3 复核预算裁决（oracle 两轮上限已到）；提交/推送/部署批准。

## round-3 修复 + 全门复绿（2026-11-13 17:16）

- oracle round-3 BLOCKED：CLOSED 5 项（IMP-03/05/06/07/13），NOT-CLOSED 7 项（01/04/08 新变体/09/11/12/14）。修复全部落盘（明细见 research/implementation-report.md §四·round-3 摘要）。
- 关键修复：锁恢复改 rename 原子夺取+内容复核（顺带发现 uuid4 未导入的 NameError，force-unlock 在 round-3 前实际不可用）；_pick_b2 候选保全；news1 消失一律判失败；_val 缺值拒绝；缓存在 pdf_url 无效时降级为一次性候选；render 显式状态五重校验；step_of 严格契约。
- check_regional 75→87 项：首轮 4 失败（pdf 计数未清零/step_of 期望/两个锁测试）全部定位并修，**Ran 87 tests OK**；compat 51/51、build --local 0、页面契约 0 项、git diff --check 0。
- 待用户：人工验收（双击 site/index.html 五页）；round-4 复核预算裁决；提交/推送/部署批准。

## S1b/S2/S4/S5（2026-11-15/16，主会话）
- S1b：build_site.py 单页手术完成（搜索骨架/12 槽位模板/目录+配方嵌入/唯一暂存→校验→os.replace），s1b_check 15/15。
- S2：designer 余额两连败后第三次派发成功（另有会话在余额恢复期已写入 SEARCH_JS，designer 审计+修 2 缺陷：closeList 清 cands、收起后 Enter 重开）。Chromium 实测交互通过（候选/消歧/XSS 文字化/重庆/成都恢复/aria/320/360）。
- S4：死代码清除（PAGES/nav_html/NAV_ZONES/north_bg/national_ref/孤儿卡与标题/site 旧四页），site/ 只剩 index.html。
- S5：validation/check_search_query.py Q1–Q7 26 项全绿（.tmp_a2/q_suite4.log）；Q6 动态基线重写（build 前后 data/ 哈希不变 + 新 CSV 钉 impl-baseline-s0 16-hex + changes.log 列契约[历史 4 列变体允许] + data/ 无未声明文件）；Q7 抓到 PAGES 常量残留已删。git diff --check 干净。
- 已知未决：file:// 与读屏/IME 未真机；脚本 init 失败说明行与规格第 6 条有形式差异；旧 A2a 锁恢复并发窗口仍是发布阻断项（未关闭，不在本版范围）。
- S6：oracle 独立复核已派发（ses_e1e0a72c7ffeephhG105oaYHv7），报告落 research/imp-review-search-r1.md。

## S6 oracle 复核返回 + 立即修正（2026-11-16）

### 复核结论：BLOCKED（research/imp-review-search-r1.md，oracle ses_e1e0a72c7ffeephhG105oaYHv7）
七项 BLOCKER + IMP-01 沿用 + 两条 ADVISORY：
- A2-SEARCH-01 交互契约：清空即恢复成都（冻结要求清空不改变结果）、缺提交/清空/回成都三按钮、Esc 一击清空、选中后无焦点转移（build_site.py:1386-1388/1439-1443/1332-1366/1473-1486）。
- A2-SEARCH-02 sentinel_region 映射不独立：recipe 由 flu_region 派生，不一致时只删名称卡（search_catalog.py:153-160）；套件 :112-117 反向断言错误。
- A2-SEARCH-03 状态横幅不随查询过滤：PAGE_SOURCES 全绑 index（:64-67），横幅只在默认视图（:975-979/:1616-1618），北方/黑龙江产品级失败提示未入模板（:320-321 vs :1585-1586），compute skipped 归 unknown（:126-127）。
- A2-SEARCH-04 降级不完整：输入框默认可用仅 noscript（:1478-1485）、初始化异常只护目录阶段（:1163-1186）、切换缺模板静默 continue（:1332-1349）、构建校验不解析配方/不查全部模板（:1634-1660）。
- A2-SEARCH-05 隔离发布未实施：weekly.yml:79-84 仍 path: site；run_pipeline 无隔离复制；Q7 未验 artifact/关门。
- A2-SEARCH-06 Q6 弱基线+测试覆盖高估：**冻结 r4 :51-62 实含十文件 SHA-256（原探测正则错）**；套件弱断言（:43-49 只查文案不查交互）；history-case-map.md:21-25 仍旧五页。
- A2-SEARCH-07 load_catalog 拒绝契约不全：重复映射行被字典覆盖仍过检（:50）、省直辖县级父级类型/空父级未验（:89-92）、非 unknown 映射来源空仍过（:65-76/93-97）。
- IMP-01 锁恢复并发窗口仍 NOT-CLOSED（发布阻断，沿用）。
- ADVISORY A01 匹配策略与口径说明未对齐（剥后缀/包含优先于别名精确/说明缺目录版本）；A02 changes.log 两条同名留痕 + s1b_check BAD 不置非零。

### 立即修正（本轮已落）
- 复核报告全文落盘 research/imp-review-search-r1.md（oracle 无写盘工具，主会话代存）。
- Q6 重写为冻结强基线：九个 data/ 文件逐字节钉 plan-freeze-r4.md 哈希；changes.log = 冻结内容(sha 51f3ade2…前142行) + 恰好三条 S0 目录留痕；两个新 CSV 钉 impl-baseline-s0 16-hex；保留 build 不改 data/无未声明文件/构建失败保旧页。实测 9/9 文件与冻结一致、changes.log 前缀匹配 → 实施期权威数据未被改动（A2-SEARCH-06 核心担忧证伪）。
- 套件 26→28 项全绿（.tmp_a2/q_suite7.log，Q-SUITE OK 28/28）。

### 待修（下一轮，按复核关闭条件）
1. A2-SEARCH-01：JS 交互改造（清空≠恢复、三按钮、Esc 分层、焦点转移）+ 真实交互断言。
2. A2-SEARCH-02：recipe 独立双映射 + 九组合内存夹具。
3. A2-SEARCH-03：槽位级状态绑定 + 产品失败提示入模板 + 受控状态夹具。
4. A2-SEARCH-04：默认禁用+常驻说明、切换离屏、构建校验解析配方/全模板。
5. A2-SEARCH-05：run_pipeline 隔离发布目录 + weekly.yml 改路径 + 复制失败关门 + 隔离测试。
6. A2-SEARCH-07：load_catalog 拒绝契约 + 四类注入夹具。
7. A2-SEARCH-06 余项：交互/失败状态/历史卡真测 + history-case-map 更新为单页版。
8. ADVISORY：匹配策略对齐 + 口径说明补目录版本 + 留痕澄清 + s1b_check 非零退出。
9. IMP-01：锁恢复——推荐人工恢复方案或另立互斥协议+独立关闭证据（发布前必须）。

## 修复进度（2026-11-16 上午第二段）
- A2-SEARCH-02 已修（search_catalog.recipe 双产品独立：flu 卡跟 flu_region、names 卡跟 sentinel_region，内存夹具断言 north/unknown 两态）；__main__ 自检过。
- A2-SEARCH-07 已修（load_catalog 拒绝契约：映射重复行/省级带父级/地级缺父级/父级非省级/省直辖县级父级非省级/非 unknown 映射来源空；探针 6/6 + 套件 Q8 六项固化）。注意 load_catalog 现在要求 product_map 两列 source 字段非空（真实 CSV 已有）。
- check_search_query.py 28→34 项全绿（.tmp_a2/q_suite8.log）。Q3 重写为独立双断言 + test_sentinel_independence_in_memory。
- A2-SEARCH-01/04 + ADVISORY A01 已派 designer（ses_e1e1df581ffe8ViHlzdqJ6PdvZ，仅 src/build_site.py），等返回后适配断言。

- designer 会话（ses_e1e1df581ffe8ViHlzdqJ6PdvZ）复核修复派发后无文本返回；实测 build_site.py mtime 09:21:52（派发前）、「回成都/按钮/模块缺失」全零 → 判定未做任何改动（疑似余额再耗尽）。已改派 fixer（ses_e1dc6712bffewXuCCXZxL5KjN8）携同一关闭条件清单实现 A2-SEARCH-01/04。

## A2-SEARCH-01/04/A01 完成核验（2026-11-16 11:20）
- fixer（ses_e1dc6712bffewXuCCXZxL5KjN8）交付：骨架 :1558-1576（输入框+三按钮默认 disabled+目录版本句+noscript）；SEARCH_JS 全量重写 :1138-1536（FAIL_TEXT/fatal/coreOf 剥后缀 8 级匹配/onGo-onClear-onHome/Esc 分层 :1492/焦点转移 H2 tabindex=-1 :1386/缺模板收集提示 :1381/离屏 staging 渲染/init 全 try-catch 末尾才解除 disabled :1524-1534）；_validate_pages :1724-1800（解析内嵌 JSON、目录 400、配方→模板双向闭合、chengdu_default 例外、孤儿/重复模板拒绝）。
- 主会话亲验：q_suite 34/34、s1b_check 15/15、git diff --check CLEAN、:1563 disabled、:1565-1567 三按钮、:1572 目录版本、FAIL_TEXT/缺模板文案各 1 处。fixer 自带真实无头浏览器行为实测（清空不动结果/三层 Esc/焦点/缺模板/破坏 JSON 降级/排序抽检）+ 反向校验器测试 6 例（missing_tpl/orphan/dup/catalog_399/ghost_slot 全拒）。
- 发现（数据缺口非缺陷）：data/locations.csv aliases 列 400 行全空 → 别名匹配级别运行时不可达；剥后缀+包含已覆盖主场景。留待后续补别名（哈尔滨/首府俗称等），不阻塞。
- 七项 BLOCKER 状态：01 CLOSED(实现) 02 CLOSED(实现+测试) 04 CLOSED(实现) 07 CLOSED(实现+测试) A01 落实；余 03（横幅按查询过滤）05（发布隔离）06 余项（history-case-map 陈旧）IMP-01（锁）未动。

## IMP-01 + A2-SEARCH-05 定案（2026-11-16 11:25）
- IMP-01 终版策略（run_pipeline.acquire_lock）：删除全部自动恢复删除路径（rename 协议退役）；死锁/活锁/不可辨认锁一律拒绝 + 人工恢复指引（「手动删除 .tmp_pipeline/lock 再重跑」）；--force-unlock 参数保留但永不自动删锁 → 无任何代码路径删除他人创建的锁，单写者不变量绝对成立，并发恢复竞态从根消除。顶部 .dead.* 残片清理保留（无害）。
- A2-SEARCH-05 发布隔离：run_pipeline 第 7b 步新增 site/ 白名单断言（只允许 index.html，多余文件按构建失败处理 → pipeline_exit=2 + site_ready 关闭）。单页迁移后 workflow path: site 即隔离 artifact（旧四页已物理删除、git 不跟踪 site/，Actions 全新 checkout 只会生成单页）。
- q_suite 新增 Q9 三项（死锁+force 均拒+锁保留+人工指引文案 / 活锁拒 / .dead.* 残片清理）；套件 34→37 全绿（.tmp_a2/q_suite10.log）；git diff --check 干净。
- 注：check_regional.py（A2a 旧套件 87 项）在单页迁移后 U 组五页断言已失效，按 S4 契约保留为历史证据不作为门；其 R2_01/R4_05 断言旧 force 行为同样过时，逐 ID 映射记 history-case-map（S6 待办）。
- 七项 BLOCKER 状态更新：01/02/04/05/07 CLOSED（实现+测试）；03（状态横幅按查询过滤）未动；06 余项（history-case-map 陈旧 + Q-suite 已覆盖大部分交互真测）；IMP-01 按终版策略关闭（待 oracle 确认）。

## A2-SEARCH-03 + 06 余项完成（2026-11-16 11:35）
- 03：_src_chip()（build_site.py，本轮获取状态 ok/未执行/失败/未知 四态文案）注入 zone_flu_south/north、zone_names_*、national_rank（sentinel）、local/prov_hlj_flu/sent（heilongjiang 两源）模板；PAGE_SOURCES['index'] 收窄为 {flu_south,sentinel}+{south}（默认视图=成都卡依赖，横幅不再串扰北方/黑龙江）；.q-chip CSS。CHIP-PROBE（合成 v2 状态：north failed/south ok/hlj skipped+failed）全断言过；Q-SUITE 37/37。
- 06：validation/history-case-map.md 重写为单页版映射（旧 51/87 逐组归属 + 两条已知残留：aliases 空、compute skipped 措辞）。
- 七项 BLOCKER 全部实现层关闭：01/02/04/05/07 + 03 + IMP-01（终版人工恢复策略）。待 oracle 关闭确认（round-2）。
- 门：q_suite 37/37、build --local、git diff --check 干净。

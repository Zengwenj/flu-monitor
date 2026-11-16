# A2 frozen plan r3

protocol_version: review-1
round: 3
baseline_commit: 4fc10710ac830f5b3f4aca4ad55f001190711468

## SHA-256 source and dependency manifest

- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\prd.md` SHA256 `7c514609533f1cf80b5f03d8bad8f1b65dd0aeb7168e722d72868a14dbe3dbed`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\design.md` SHA256 `9c936275e95c074b23906929294cfdaba0293bd27416af52a46678033cdcf55e`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\implement.md` SHA256 `630601f3066503af8a1b5e889c05ad736ef168fc19c5621b218a3adbfeea1ccd`
- `D:\FluMonitor\CONTEXT.md` SHA256 `cf08c836fe8de9c21646d32032fd515e2bfbfece87048a69f6d6585eebb89c36`
- `D:\FluMonitor\docs\handoff.md` SHA256 `dd254a9e64d0380675097958f3df1f593e794d3d47217ffb99815296050bb91e`
- `D:\FluMonitor\src\fetch_flu_south.py` SHA256 `360d744d3f744267b467a4ff3cdb4b0ccca0442f8af2f86524360bc864414581`
- `D:\FluMonitor\src\compute_index.py` SHA256 `6958b55d784837633400f976ffc41c16063cdffb0e8e5c6a6751aa7ca370a716`
- `D:\FluMonitor\src\build_site.py` SHA256 `cb32ece39606afcf4aa99e2c40133a38c33d889442a94f5ad1942dd9140aa76a`
- `D:\FluMonitor\src\write_run_status.py` SHA256 `29fdaf6dff7e6d43ff63de30d1cf32ba0543b09d6f3d63033fefd722d27300d6`
- `D:\FluMonitor\.github\workflows\weekly.yml` SHA256 `80a6ce0818c40f0b89490bd92f40ff4746efc9a947e45a30311910e13063de4e`
- `D:\FluMonitor\run_local.bat` SHA256 `d96c755e600bf9bba6b2a4637d00fba468f85b38bfa13267bb6a6db21a236e86`
- `D:\FluMonitor\.gitignore` SHA256 `2b40a135f2160b34adb168be54647fc9642fafa5fc27dc423b3ba70b3656ce8d`
- `D:\FluMonitor\src\fetch_sentinel.py` SHA256 `2f96634fe84ffce889b0c17fe619a30f07daa69d203158af7f28b2442ab20854`
- `D:\FluMonitor\src\fetch_flunet.py` SHA256 `22232ad6753e503fba9b83b5ebc857fb02c1a1e71480d88ed0a5362daa7295cd`
- `D:\FluMonitor\.trellis\tasks\archive\2026-11\11-12-flu-south-history-view\validation\check_history.py` SHA256 `5b0788d736400e96913f1203feee948d84968c4ff91d6671e39f7c678e9d4284`
- `D:\FluMonitor\.trellis\tasks\archive\2026-11\11-12-flu-south-history-view\design.md` SHA256 `f97f80dab8c2ec4e3b3a373ba5d1bb3d21cdcc6b2d36fcbf4047fd1b86876283`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\research\source-feasibility.md` SHA256 `255b69b82ef364825953aad1a7a0cc32ba3061688df46cd0648e69477036596f`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\research\gap-analysis.md` SHA256 `99c608edd29ca6208980ffbfda8c73335ce5f26e07688dbde0aa0177eabb914a`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\research\display-proposal.md` SHA256 `4f18210b0939f3c54ff3c3ef4c6c4f88780b20d2b1d0ee665ffd0bbdc855b585`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\research\architecture-advisory.md` SHA256 `ebeb0c0c0fc0f0a01014e93ccccdf441f08c827b5bb919dd1b859c7816cc01d0`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\research\findings.md` SHA256 `22e9ff9e02d4f1e19206966e2eca327d0d2d6cde96efdef71eccd79151a298fd`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\research\location-sources.md` SHA256 `c2e75bd7982702a92fc11d98d45e3ed6424c195ba9c1f9d30d1fcd5f12fc70ff`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\research\search-display-proposal.md` SHA256 `033e11a1fe8ea5e703fd1ef2ba8b02b42d91167325cc4e1974343235e8325c79`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\implement.jsonl` SHA256 `e7d103666e52ac27ac7d208aafe2f24c45ea22c84897f028d1f8b69649870f32`
- `D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\check.jsonl` SHA256 `4db1401b6841306185e85a0bc90c16d7ce0700b7bb333e8e135deca0785fb625`
- `C:\Users\zengw\.config\opencode\REVIEW-PROTOCOL.md` SHA256 `0bf74c7d2d923ace38cb328d588b27bb915d6c9ba9abfc9a6a223323787ea67e`

---

# SOURCE: D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\prd.md

# A2 多地区呼吸道监测查询

## Goal

默认展示成都（四川）的监测证据，通过一个搜索查询入口查询其他省市；没有当地数据时展示明确标注口径的可用参考。已有南北片和黑龙江数据能力保留复用，不以已接入数据源决定首页固定地区入口。

## 当前变更状态

用户已纠正旧版五页固定导航的产品方向，并确认“无当地数据时展示可用参考”。本轮重新规划交互、地区识别与证据映射，不继续验收或发布五页导航版。此前实施批准不视为修订方案已批准；旧冻结快照与评审留作历史，不改写为新方案的通过证据。

## Requirements

- 首次打开默认成都（四川）；其他省市通过搜索查询，不默认列出黑龙江、重庆等固定地区页签。
- 查询范围目标为全国省市，不仅限已接入的数据地区。行政区划收录层级、别名、同名消歧及映射来源须在修订设计明确；未匹配不能解释为该地区没有监测数据。
- 用户已确认首版覆盖省级与地级（省、自治区、直辖市、地级市、自治州、盟），并单独处理省直辖县级行政单位；不扩展为所有区县。名录来源、版本及特殊地区覆盖限制须明示，不编造缺失层级。
- 用户已允许少量内联 JavaScript，用于本地地名候选、消歧和结果切换，替代旧方案“零 JavaScript”限制；名录与已有数据随页面打包，不使用外部脚本、运行时 fetch 或在线搜索服务。查询范围不等于实测数据覆盖范围。
- 用户已确认：无当地数据时说明“本工具未取得当地数据”，再展示已核实可匹配的省级、片区、全国参考。没有可靠归属映射时不猜测南北片，也不把省级观测改标为城市实测。
- 先核实官方源的字段、频率、历史覆盖和可获取性，再确定自动采集或明确降级；不得预设省市阳性率存在。
- 全国多病原数值、片区前三名称、省级公告分块标注，不能混算指数或冒充当地风险。
- 保持 CSV 权威存储、静态内联页面、本地 file:// 可用与云端/本地双触发；不引入服务器和云端多模态调用。
- 规划阶段只修改本任务资料与父任务关联，不改运行时代码、data/、部署配置，不提交或发布。
- 已确认：重庆当地资料仍采用官网链接方案，不转载正文、数值或图片；查询重庆时呈现，不再要求首页固定重庆导航或独立页面。
- 北方片采用独立同口径历史序列；黑龙江流感B1与多病原B2分源，不互换分母、不混算指数。

## Acceptance Criteria

- [ ] 官方源可行性矩阵有可复核链接、样本时间、字段和未验证部分。
- [ ] 完成计划前缺口分析，需求歧义与数据限制有明确处理。
- [ ] design.md 界定数据契约、地区映射、页面状态、兼容性与写入守卫。
- [ ] implement.md 给出分阶段文件范围、依赖、验证命令、停靠点与回滚。
- [ ] implement.jsonl/check.jsonl 为真实文档条目且验证通过。
- [ ] 冻结成稿并完成独立计划审核；实施须另获用户批准。
- [ ] 首页默认成都，输入其他省市、候选消歧、查询、返回成都的完整流程可验收；默认不展示固定黑龙江/重庆页签。
- [ ] 查询结果分别标注当地数据缺失、省级参考、片区背景与全国口径；地名识别失败与数据缺失是两种独立状态。
- [ ] 离线搜索实现与既有“零 JS”计划差异必须明示；不得暗中引入外部脚本、网络查询、服务器或运行时 fetch。

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.

---

# SOURCE: D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\design.md

# A2 成都默认与省市离线查询设计 r3（草案）

## 0. 状态、授权与历史边界

用户已纠正固定五页导航：首次打开首要显示成都（四川），其他省市经一个搜索入口查询；没有当地观测时展示明确口径的可用参考。已确认允许少量内联 JavaScript，首版覆盖省级、地级及省直辖县级行政单位的特殊情况，不覆盖所有区县。

本轮仅修订规划；尚未取得新版实施、提交、推送、部署批准。本稿未冻结、未正式评审。名录与两个监测产品的片区映射证据已由主会话亲核闭环（research/location-sources.md，2026-11-14），可据此成稿送审，但不足以替代评审与用户批准。旧 r2 文本存于 research/design-fixed-pages-r2.md 与 research/implement-fixed-pages-r2.md，旧 plan-freeze-r2.md 不变。

工作树已包含旧版未提交实现与新增CSV，不是空白项目。保留数据和管线能力，不重做历史回补、不回退用户或bot有效数据。旧版87项区域测试、51项历史兼容测试和真实冒烟属于历史证据，不证明新交互完成；旧实施复核未关闭项仍是发布阻断，尤其锁恢复并发问题。

## 1. 单入口与结果结构

唯一主入口为 site/index.html。首次加载和刷新默认成都，不定位用户、不读取上次地区偏好；不提供固定黑龙江、重庆或南北片导航。已有成都六卡及A1b历史行为保留，来源和数据期不改标为城市实测。

搜索交互采用 research/search-display-proposal.md 的候选、键盘、输入法与窄屏规格；其中数据适用范围以本设计为准。选中地区后隐藏而不删除成都内容，显示单个查询结果；返回成都恢复原内容。清空仅清输入和候选，不改变已显示结果。不添加地图、实时抓取、分享链接或所有城市独立页面。

查询省级单位时，它自身的省级观测是当地产品，不重复插入“市级缺失”。查询地级单位时，无城市记录就明确“本工具未取得当地数据”，再展示可用省级参考、片区背景、全国参考。卡片不混算指数、不排名地区，每卡自带地理口径、样本框、来源、数据期和状态。

| 查询对象 | 专有内容与限制 |
|---|---|
| 成都市 | 恢复默认内容，四川分级仍按原成都适用口径 |
| 四川省及其他四川城市 | 不自动跳回成都，不把平原区等级当全省/该市等级；首版仅来源指路和已核实背景，不扩大人工分级覆盖 |
| 黑龙江省 | 省级B1摘要与相邻周环比、B2正文部分观测；不新增省级多年曲线 |
| 黑龙江地级单位 | 当地未取得＋上述省级参考，明确非该市实测 |
| 重庆市 | 当地只官方入口与自撰说明，不转载正文、数值或图片；参考另列 |
| 其他已收录单位 | 当地/省级覆盖按明确产品注册关系判断；有可靠映射才展示相应片区，已有全国哨点卡可作全国参考 |
| 无匹配 | “未找到匹配地名，请检查名称或查看支持范围”，不判断该地是否存在或有监测 |

不新增FluNet卡；FluNet采集可保留但不成为未渲染卡片的状态依赖。官方链接仅http/https并转义，另开窗口带rel=noopener。

## 2. 名录与映射契约（来源证据已锁定，见 research/location-sources.md）

拟增加 data/locations.csv 与 data/location_product_map.csv 作为人工审核、版本化的静态配置，不参与自动周更新。分发源为 CC0 名录 `yescallop/areacodes` 固定 commit `e2c2b2e1`（2025 年数据），民政部官方接口仅一次性核对不入库；首版选择集 396 条（31 省级 + 333 地级 + 32 省直辖县级），实施时按民政部补入 `659013 草湖市`（标 source=dmfw）。直辖市下辖区县（含两江新区）与港澳台不在首版范围；港澳台名录行保留 `monitor_coverage=false` 占位；兵团无查询入口，仅映射注释。更新节奏每年 1 月人工核对留痕。

locations最小字段：稳定id（6位区划码）、规范名、行政层级、父省id、direct_under_province、经审核别名。省直辖县级单位不伪造地级父级。每个id唯一，父级存在，简称冲突允许但必须消歧。

地理映射按产品分别记录：流感数值产品 flu_region、哨点名称产品 sentinel_region，各取south/north/unknown，均附来源与适用版本。两个产品已分别取得独立官方名单（flu_region 引《全国流感监测技术指南（2017年版）》附件原文，sentinel_region 引哨点监测周报固定脚注，两者名单一致互证；2017 版“现行”属推断，须在口径说明标注）。未知不默认；该产品片区卡缺席并说明映射未核实。不得按经纬度或秦岭淮河线推断。

匹配仅对规范名与审核别名：规范化空白/全半角，精确匹配优先，再前缀、包含匹配；不任意剥除后缀，不猜拼音。匹配输出稳定id，不能用输入字符串决定卡片。多个候选由用户选；修改输入即清除旧候选选择，不自动查询旧id。最多显示8项并报告真实总数，未显示项通过继续输入定位。

## 3. 构建与内联脚本边界

Python继续完成CSV校验、指数/历史视图、SVG与数值文本。生成有限组可信template片段与查询元数据，复用南北片/省级/全国产品，不为每个城市复制全文。JS只做目录过滤、候选选择、模板克隆、文字标签及状态切换，不计算指数或从线上补数据。

所有名录与状态JSON嵌入页面，转义 `<` 等脚本结束风险字符，不能让 `</script>` 提前结束数据块。用户输入/地名仅通过textContent等文本接口插入，禁止innerHTML拼接输入、eval及动态代码。模板及其ID只从构建器固定集合选择；复制后的可见SVG/控件id不得重复，aria引用必须仍有效。

允许固定内联执行脚本和application/json数据块，仍禁止script src、fetch、XHR、WebSocket、动态import、外部CSS/图片/font加载。脚本初始化成功后才启用查询；默认静态成都内容和查询不可用说明先存在。初始化或切换失败须恢复成都且说明查询失败，不留下上一地区标题配新卡片的混合状态。

本稿不承诺JS框架、运行时依赖或地址栏持久化。file://与Pages均需实际验收。

## 4. 状态依赖与数据诚实性

每个产品片段绑定实际fetch/compute依赖。查询结果只展示本次选中片段的相关失败/跳过/unknown状态；全国哨点依赖sentinel，流感片区依赖各自flu_south/flu_north及compute，B1/B2独立。重庆入口无抓取状态，不伪装成功。状态与数据期分开，成功不等于官方已发布预期最新期。

无显式状态的build --local注明仅按存量数据展示，不读取云端记录；显式状态须校验schema、run_id、origin及结构，坏输入拒绝构建。各产品零值有效，缺失不显0；未知地名不是缺数据；无新行不能推官方未发布。首版不新增未经证据支持的统一陈旧天数阈值。

## 5. 继承的数据与管线契约

沿用 research/design-fixed-pages-r2.md §2–§4、§5中的计算/视图条款与§6中的采集接线条款；其五页、按页状态及固定导航要求由本稿替代。继承包括：旧south CLI/CSV兼容；南北同PDF分区独立失败；B1/B2样本框隔离；B2整期替换/同周冲突保全；force失败保留成功值及缓存；每文件原子保存；全国22行守卫不改；run_id隔离；0/1/2退出码与site_ready发布门。

缓存完整来源绑定、候选解析失败保全、结果文件仅请求产品、显式状态完整校验等旧复核项，不因界面改变豁免。锁恢复推荐回到原设计的人工恢复边界：拒绝自动搬动或删除无法可靠判定归属的锁，先停止所有写者再人工清理；具体修复与验证须在新版实施批准后执行。现有rename恢复方案仍未独立关闭，不能称安全。

## 6. 产物迁移与发布门

新版构建仅管理index.html：写唯一暂存文件，验证页面、目录、template、状态与脚本契约后原子替换；失败保留旧index并返回构建失败，不打开旧页冒充成功。旧四页south.html/north.html/heilongjiang.html/chongqing.html按明确清单识别，不宽泛删除site其他文件。

实施时新建隔离发布目录，仅复制验证通过的index.html，workflow只上传此目录，禁止旧五页混入部署产物。本地旧四页在验收迁移时显式列清单处理；清理失败不得误称完成，保留用户非受管文件。此策略替代“上传整个site”旧约定，需同步CI测试。

README与任务报告说明目录覆盖、数据覆盖、离线查询限制及未关闭事项。旧冻结评审不改写；新版冻结评审通过及用户批准后才实施。上线仍需独立实施复核、用户人工验收、另行提交/推送/部署授权。

---

# SOURCE: D:\FluMonitor\.trellis\tasks\11-12-regional-monitor\implement.md

# A2 成都默认与省市搜索：可执行计划 r3（草案）

状态：仅规划。旧版固定五页实现已暂停；本计划不是旧 r2 实施批准的延续。新版必须重新冻结、plan-critic 审核并取得用户实施批准。提交、推送、部署仍另行授权。

## S0 需求、来源与基线冻结（主会话）

1. 保护当前工作树：记录 HEAD、远端差异、所有未提交文件与 data/ 哈希；不自动 pull、stash、reset 或覆盖旧实现。将旧 `design.md`/`implement.md` 快照和旧冻结快照保留在 research/，不改写其评审证据。
2. 读取 CONTEXT.md、docs/handoff.md、A1a/A1b 归档设计及旧版复核记录。把旧五页实现的未关闭问题列入新版风险，不以需求纠正绕过，尤其锁恢复并发风险。
3. `research/location-sources.md` 已完成主会话亲核（2026-11-14）：分发源 CC0 名录固定 SHA、民政部接口核对、396 条首版选择集、省直辖县级 32+1、港澳台/兵团边界。实施时按该文件生成 data/locations.csv 与 data/location_product_map.csv，草湖市补入留痕；不声称超出该来源的覆盖。
4. flu_region 与 sentinel_region 映射已分别取得独立官方依据（技术指南 2017 版原文 / 哨点周报脚注）；实施时两字段各带来源引用，“2017 版现行属推断”写入口径说明。任一产品证据失效时回退 unknown。
5. 形成最小夹具：成都、四川省、四川地级市、黑龙江省/市、重庆、同名候选、未知映射、未收录区县、恶意文本。夹具不写权威 CSV。

**停靠条件：**CC0 名录固定版本不可再获取、民政部核对接口不可达且差异无法裁定，或产品片区证据链失效时，停止成稿中的对应能力，改为明确“目录/映射未核实”的降级，而不是猜测。

## S1 查询数据契约与模板（主会话，依赖 S0）

范围：`src/build_site.py`、必要的任务验证脚本；不改抓取器、计算器、workflow 或 data/。先定义输入输出契约再修改生产代码。

- 生成唯一 `index.html`：成都静态默认内容、查询元数据、固定结果 template 片段。
- 目录字段至少为 `id,name,type,parent_id,aliases`；`zone` 必须拆为 `flu_region` 与 `sentinel_region`，值为 `south/north/unknown`，每个非unknown值带来源引用。
- 结果配方只引用构建器生成的固定片段ID，不将用户输入当HTML；数值、数据期、来源和状态由Python生成，JS不计算。
- 当地、省级、片区、全国卡各自有层级标签；数据缺失不显0，未匹配和无当地数据分开。重庆只保留官方入口，不转载受限正文/图片/数值。
- 成都默认仍保留四川分级和A1b卡；四川省或其他四川地市查询不自动复用“平原区”分级。

**S1 离线回归：**目录解析、规范名/审核别名、同名消歧、稳定选择ID、输入改变清除旧选择、未知片区不显示片区卡、模板ID白名单、JSON安全转义、真实零值与缺失状态。

## S2 内联查询交互（designer 实施，协调负责人验收；串行）

仅允许固定内联脚本与 `application/json` 数据块：禁止 `script src`、外部资源、`fetch`/XHR/WebSocket、动态import、eval、new Function。脚本只过滤候选、克隆固定template、切换可见区和更新无危险文本。

交互验收契约：

- 可见 label、search input、提交/清空/回成都按钮；候选使用 combobox/listbox/option，状态使用 `role=status`。
- compositionstart/end 期间不乱跳；前缀优先、精确优先；最多8项但报告总数；多候选必须选中，不能默认第一项。
- 下/上箭头、Enter、Esc、Tab 可用；选中后焦点转到结果标题；清空不改变当前结果，回成都才恢复默认。
- 脚本禁用、目录损坏或初始化异常时，成都内容完整可读并显示查询不可用说明，不显示空输入框或空页面。
- 输入 `<b>`、引号、`&` 只按文本显示；不得使用输入值拼接 `innerHTML`。

## S3 页面结果与口径验收（主会话）

结果顺序固定为当地→省级→片区→全国，但缺失层级可隐藏并在概览说明原因：

1. 当地记录仅在稳定ID明确绑定且 `status=ok` 时显示。
2. 省级参考必须标“省级参考，非所选地实测”；省级数据不得降格为市级。
3. 片区背景只在对应产品映射有证据时显示；未知映射仅给全国及已核省级参考。
4. 全国哨点/FluNet只标全国参考，不改标题、不与南方片指数混算。
5. 重庆仅官方入口；黑龙江省级B1/B2已有能力可复用，但不新增省级多年曲线。

禁止：综合总分、跨地区排名、感染概率、把片区名称排名写成省市排名、把四川分级扩展到查询地区。

## S4 旧实现迁移与发布隔离（主会话）

- 将旧 A1b 49项与旧 A2 87项测试逐ID映射到新版测试；明确删除/替代理由，不以数量替代覆盖。旧五页输出不再作为新版发布产物。
- 只允许生成并发布受管 `index.html`；旧 `south.html`/`north.html`/`heilongjiang.html`/`chongqing.html` 不得混入新版发布目录。构建使用唯一暂存目录，校验失败不替换旧首页。
- 本地 `--local` 不读云端状态；显式状态校验 schema/run_id/origin/结构。现有数据、抓取和管线改动除非新版契约明确需要，否则不继续扩展。
- 旧实现的锁恢复问题仍是阻断项；新版不宣称已独立关闭，需在实施验证中采用停止写者后人工恢复或经复核批准的可靠协议。

## S5 验证矩阵与停靠点

建议新建 `validation/check_search_query.py`，并保留旧 `check_regional.py` 作为历史实现证据，不直接当新版通过证据。

| 组 | 必须验证 |
|---|---|
| Q1 | 成都默认、回成都、清空、唯一候选、多候选/同名、无匹配、输入改变清除选择 |
| Q2 | 四川省/四川地市不误套成都分级；黑龙江省/市分层；重庆仅链接；普通省市缺当地数据仍展示可用参考 |
| Q3 | flu/sentinel片区映射独立；unknown不猜片区；全国参考不冒充当地；失败/跳过/unknown互不混淆 |
| Q4 | 恶意文本、JSON/HTML脚本结束、模板ID、外部加载和运行时联网静态检查 |
| Q5 | file:// 直接打开、脚本禁用降级；320/360/桌面无页面横滚；键盘、焦点、读屏角色和触控目标 |
| Q6 | data/哈希不变、旧A1b成都卡回归、真零/缺失/数据期/来源链接、构建失败不替换旧首页 |

验证命令（新版实现后才执行，不提前声称通过）：

```text
python -X utf8 .trellis/tasks/11-12-regional-monitor/validation/check_search_query.py
python -X utf8 src/build_site.py --local
git diff --check
```

file://、键盘与窄屏必须由实际浏览器验收；HTTP截图不能代替 file:// 证据。若自动化环境不可用，记录用户双击/F12手测证据及限制。

## S6 独立复核、文档与授权门

本计划在实施前须读取正式审核协议、冻结单一修订计划快照并派 plan-critic；通过后仍须用户批准新版实施，未批准则停在规划阶段。获批后由 implementor 统筹整份计划，designer 负责界面实现，写域相交步骤串行。

实施完成后更新 `research/implementation-report.md`、`progress.md`、README（仅在用户授权范围内），记录名录来源版本、映射证据、测试命令/退出码、未验证项和旧版隔离情况；按协议进行独立实施复核，不以计划评审代替代码复核。

用户另行批准提交后，才可先核 workflow 空闲、处理远端 bot 数据差异，再分 docs/feat 两笔提交。部署需再次确认；不得在运行中 push，不得把旧五页和新版首页混合发布。

## 写域与回滚

规划阶段只写本任务资料。实施阶段预计主要写 `src/build_site.py`、验证脚本、README/任务资料，只有契约证明需要时才调整已有管线；不回退、不覆盖 `data/`。实施前备份受影响文件与哈希；回滚只恢复明确受损文件，先核对其后 bot/用户修改。

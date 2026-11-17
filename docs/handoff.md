# 交接文档（Handoff）

> 写于 2026-11-09（M4b 收官）；更新于 2026-11-16（A1a/A1b/A2 完成上线）；**更新于 2026-11-17（A4 界面美化完成上线）**。用于**另开会话继续遗留可选项目**。
> 读者：接手的新会话（AI）+ 你本人。读完这份 + `CONTEXT.md` 就能接上，不需要读全部历史。

---

## 1. 项目是什么 / 到哪一步了

个人用的传染病趋势监测工具，重点成都，产出是一个**每周五自动更新的在线分块证据页**：**成都默认首页 + 全国省市离线搜索查询**（单页 index.html，无外部 JS/运行时联网）。

| 项 | 值 |
|---|---|
| 线上 | https://zengwenj.github.io/flu-monitor/ |
| 仓库 | https://github.com/Zengwenj/flu-monitor （public，main） |
| 本地 | `D:\FluMonitor` |
| 最新提交 | A4 提交后以 `git log` 为准（2026-11-17，本地 = 远程，工作树干净） |
| 状态 | M0–M4 全部完成；**A1a / A1b / A2 / A4 界面美化 均已完成上线**（各走完整评审链，见 §7）；A3 支原体专题已取消（2026-11-17），余项见 §5（均为可选小项与技术债，无必做项） |
| 自动化 | GitHub Actions 每周五北京 10:00：单写者锁管线（六源抓取→指数→构建→状态落盘）→ 隔离发布目录 `site_publish/` 只部署验证过的首页 → bot 回写 data/ |
| 手动部署 | `gh workflow run weekly.yml --repo Zengwenj/flu-monitor --ref main`（约 90 秒；含 workflow_dispatch） |

## 2. 快速上手（新会话必读顺序）

1. `CONTEXT.md` — 术语表 + D1–D19 决策（**最重要，约束红线都在这**）
2. 本文档 §4–§6
3. `docs/design.md` — 数据源与拼合逻辑
4. `README.md` — 使用说明（已更新为搜索单页口径）
5. 细节：`.trellis/tasks/archive/2026-11/*/`（各站 PRD/design/implement/冻结快照/评审记录/验证套件）

**关键命令**

```bat
python .trellis\scripts\task.py list
python -X utf8 src\build_site.py --local                :: 本地生成页面（--local 必带）
python -X utf8 src\run_pipeline.py --local              :: 本地全管线（锁 .tmp_pipeline\lock，单写者）
python -X utf8 .trellis\tasks\archive\2026-11\11-12-regional-monitor\validation\check_search_query.py   :: A2 回归门（56 项）
```

## 3. 代码与数据地图

```
src/fetch_flu_south.py   流感周报 PDF（南北两区域：--regions south,north；--backfill 回补；txt 缓存+meta 绑定）
src/fetch_heilongjiang.py 黑龙江（B1 流感周报 2025W1 起部分周 + B2 哨点多病原；--backfill；同周多篇冲突守卫）
src/fetch_sentinel.py    哨点周报三表（含表2/3 前三名名称；--merge/--write-url）
src/fetch_flunet.py      WHO FluNet CHN 全量
src/compute_index.py     Goldstein 指数 --targets south,north,heilongjiang（逐目标隔离，整文件失败不动原文件）
src/search_catalog.py    省市目录+片区映射+查询配方（397 可查 + 3 港澳台占位）
src/data_io.py           原子写（.tmp_writes 临时→fsync→os.replace）
src/run_pipeline.py      管线编排：锁/超时/状态聚合/site_ready 门/隔离发布 site_publish
src/build_site.py        单页渲染：成都默认六卡 + 搜索框（内联 JS 仅本地候选/消歧/切换）+ 12 槽位模板 + CSS_THEME 主题层（{css} 注入，A4）
src/write_run_status.py  v2 状态（schema 2，按源/目标分状态；缺键=未知不默认成功）
src/update_sichuan.py    四川月度手动录入（D19 不变）
run_local.bat            本地一键（走 run_pipeline --local）

data/  flu_south.csv(201行 2023W1起) flu_north.csv(201行) heilongjiang_flu.csv(42行)
       heilongjiang_sentinel.csv(7行) locations.csv(400) location_product_map.csv(400)
       sentinel_national_rates.csv(2288行) sentinel_rank.csv(1128行) flunet_china.csv(1022行)
       sichuan_monthly.csv changes.log（tab 5 列契约） run_status.json
site/  生成物（不进 git）；site_publish/ 同（.gitignore）
```

## 4. 不可违背的约束红线（违反即为错误实施）

| 编号 | 约束 |
|---|---|
| **D14** | 不合成"综合风险总分"；页面是分块证据页，每块自标口径与状态 |
| **D15** | 哨点表1 只有**全国**数值；表2/3 只有前三名**名称**——"南方片分病原数值"不存在，不得伪造 |
| **D17** | 箭头仅较上周；指数标"相对强度"；南方片基线不得混全国 FluNet |
| **D12** | CSV 权威；改值必须留痕 changes.log（tab 5 列）；失败行永不写 CSV |
| **D19** | 四川分级本地手动；云端 workflow 禁多模态/API |
| 诚实性 | 缺数据不显 0、旧数据不标最新、"本工具未取得"≠"官方未发布"（后者需可复核证据） |
| **搜索版边界** | 成都默认；查询无当地数据→"本工具未取得"+省级/片区/全国分层参考；省级参考必须标"非该市实测"；重庆**只放官方入口链接**（版权方禁止转载）；不猜片区映射（unknown 显式）；不得恢复固定五页导航（用户 2026-11-14 已否决） |
| **单写者锁** | `.tmp_pipeline/lock`：死锁/活锁一律拒绝并提示**人工删除**（删前停所有写者）；--force-unlock 不自动删锁；独立抓取 CLI 不与管线并发 |
| 内联 JS | 仅本地候选/消歧/结果切换；禁外部脚本/运行时 fetch/在线搜索；file:// 可用 |

**代码层契约**：哨点 r3 22 行完整才覆盖；flu_south/heilongjiang 成功才覆盖；`build_site` 匹配策略=规范名/审核别名 **精确→前缀→包含** 三级（勿再加运行时剥后缀推断）；发布只出 `site_publish/index.html`。

## 5. 遗留可选项目（A1/A2/A4 已完成，A3 已取消）

### ✅ 已完成（2026-11-11 → 11-17）
- **A1a** 流感历史回补：南/北方各 201 周（2023W1 起）、分母 bug 修复（旧值稀释 21–50%）、原子写、缓存来源绑定。任务 `archive/2026-11/11-11-flu-south-backfill`
- **A1b** 历年同周对比卡（A1b 历史 SVG+对照表）。任务 `archive/2026-11/11-12-flu-south-history-view`
- **A2** 成都默认 + 全国省市离线搜索单页（397 单位、双产品片区映射、六态降级、发布隔离）。任务 `archive/2026-11/11-12-regional-monitor`（同一任务先做五页版后被用户纠正为搜索版，过程文档都在）
- **A4** 界面美化（2026-11-17）：浅色医疗仪表盘主题（CSS_THEME 常量 + `{css}` 注入，冻结函数零改动）；≥900px 双列 12 栅格 `:has()` 内容定位（三行 7+5，**用户 2026-11-17 批准，正式偏离 design §5.1 的 12/5+7/5+7/12**，批准记录在任务 validation/v9-fix-record.md §7）；四川卡五级色条标尺 + 四态状态徽章（st-ok/st-wait/st-fail/st-unknown）；GOLDSTEIN 眉标；SVG 文字墨色重着色（文字/线条边界）；WCAG AA 全达标（360/1280 两档低于 AA=0，SVG 文本按 computed fill 计）；≥720 关键数字 46px。验证工具链全部留在 `.tmp_a4/`（probe_style/probe_narrow/probe_grid/check_view_toggle/check_lit/v10_recheck 等）。任务 `archive/2026-11/11-16-ui-beautify`

### ❌ 已取消
- **A3 支原体专题 / 细菌维度**：用户 2026-11-17 决定不做（支原体趋势图、CHINET 半年报耐药率均不实施）

### 待做（均为可选）
- **小项**：①~~`locations.csv` aliases 列全空~~ **已完成（2026-11-17）**：审核别名 14 单位 16 条入库（蓉城/锦城=成都、哈市/冰城=哈尔滨、羊城/鹏城/星城/泉城/榕城/春城/北国春城/乌市/呼市/申城/山城/金陵；江城弃用——武汉/吉林市两用），用户批准，留痕 changes.log。**注意**：A2 套件 Q6 的 changes.log 与 locations.csv 两个 S0 pin 从此预期失败（授权漂移），失败集合基线=Q6 三项（含 flu_north 既有漂移）；新基线 pin：locations.csv `ddbf3888…`。②读屏/触屏/IME/窄屏**真机**验收：清单已备 `docs/real-device-checklist.md`，待用户真机执行后关闭 ③~~文档历史叙述核对~~ **已完成（2026-11-17）**：roadmap M5 范围与「当前位置」已同步实际状态（A2/A1b/A4 落地、A3 取消），冲突时仍以归档任务文档为准

### B 小技术债
1. `sentinel_national_rates.csv` week_start 全空（X 轴用"第N周"）
2. 排序缺口 11 周两种原因未在页面细分（需 join changes.log）
3. changes.log 部分历史行是 4 列旧契约（A1a 前），套件已按历史变体接纳
4. Actions 弃用提醒：Node20 强制 24、ubuntu-latest→26 → 未来升级 `actions/*`
5. `.trellis/workspace/` 日志敏感排查

### C 外部限制（不可改，页面已诚实标注）
成都无市级周度数据 / 黑龙江非每周发布（42+1+54 对账口径）/ 重庆版权只链接 / 多病原历史仅 2 年 / 境外连通性可能变化

## 6. 已知坑（新会话最容易踩）

1. **pdftotext 跨平台**：Windows 用 anaconda 绝对路径，Linux 用 `shutil.which`——已实现勿回退
2. **跨年伪断点**：`_adjacent_week()`（W52→W1 连续）勿改回 `y*53+wk`
3. **URL**：中疾控文章 URL 含下划线；流感 PDF 是相对路径需 urljoin
4. **`build_site` 本地必带 `--local`**：否则读云端 run_status 误报
5. **push 前先 `git pull`**：bot 每周回写 data/；merge 冲突按"逐字段比对仅时间戳差异→保留较新一次"处理（2026-11-16 实证）；**勿在 Actions 运行中 push**（bot push 非快进会致部署失败，2026-11-12 实证）
6. **境内 push 偶发 Connection reset**：重试即通
7. **黑龙江正文变体**：「其中N份阳性」/「均为阴性」/无「其中」三种都存在（SAMPLE_PAT 已兼容）；同周多篇 B2 数值冲突=守卫拒绝+留痕（不是 bug）；2025W2 上游日期笔误判失败属正确
8. **缓存绑定**：`.tmp_flu_backfill/txt` + 同名 .json meta（article_url/pdf_url/title/week/sha256）；Windows `write_text` 必须 `newline="\n"` 否则 sha256 永不匹配
9. **pwsh 环境**：heredoc 不支持、内联 python 中文引号必炸 → **一律先写脚本文件再跑**；日志重定向用 `python -u`；多关键字检索用 python 脚本（`|` 会被当参数）
10. **离线检查**：只查加载型外部资源；`<a href>` 官方链接允许
11. **旧套件**：`check_history_compat.py`/`check_regional.py` 在单页时代有 19 条五页入口断言预期失败——逐 ID 去向见 `11-12-regional-monitor/validation/history-case-map.md`（保留 111/等效 13/恢复 3/废弃 11），勿当门禁整体跑
12. **视觉回归工具链（A4 遗产，在 `.tmp_a4/`，未进 git）**：headless Chrome `--window-size` 有约 500px 下限，测窄屏必须走同源 iframe（probe_narrow.py/probe_style.py 的做法）+ `--allow-file-access-from-files`；截图同样先落 560 宽再用 PIL 裁切（**Windows 上 PIL 必须 `with Image.open(...)` 关句柄再 replace，否则 WinError 32**）；SVG 文本对比度要读 computed `fill` 不是 `color`（probe_style.py 已实现 + `--selftest` 自检）；GLM 模型不能读图，视觉判断派 observer。若 `.tmp_a4/` 已清理，工具按 validation/v9-fix-record.md §8 的描述可重建
13. **A4 后 build_site.py 结构**：CSS 主题在模块级常量 `CSS_THEME`（原始字符串），经 PAGE_TPL 的 `{css}` 占位注入——**新增样式改 CSS_THEME，勿在 PAGE_TPL 里写双花括号**；桌面栅格 `.card:has()` 按**内容签名**定位（adv=四川/kv=南方片/hist-tbl=历年/rank=排行/trendrow=趋势/childg=儿童），卡 div 本身不能加类（Q10 按字面切块）

## 7. 工作流程约定（用户明确要求的门，勿跳）

```
缺口分析（gap-analyst）
  → design.md + implement.md 成稿（冻结快照 plan-freeze-rN.md + SHA-256 + 依赖 hash）
  → plan-critic 正式评审（REJECT/BLOCKED 必须修订后复审；轮次协议见 REVIEW-PROTOCOL.md）
  → 用户批准（独立于评审，不可替代）
  → 主会话直接实施（抓取调试现场迭代；designer 串行做视觉/交互）
  → oracle 独立只读复核（BLOCKED→修复→关闭确认，A2 实例走了 5 轮）
  → 用户人工验收（双击级指引）
  → 用户批准提交 → 分两笔提交（docs / feat）+ pull 合并 bot + push + workflow_dispatch 部署 + 线上验证
```

**证据**：A1a 评审抓到 4 项 BLOCKER、A2 抓到 7+7 项、A4 抓到 7+2 项（含「探针假通过」「断言对象错位」这类度量层缺陷）；A4 oracle 复核走了 3 轮（INCONCLUSIVE→BLOCKED→PASS，工具缺陷逐轮修复）——这套门不是形式。评审全程用冻结快照（round/revision 分离），实施复核同样分轮闭环。

其它协作偏好：决策/汇报用中文、区分事实/推测/建议；操作写双击级；关键选择给推荐项；实质进展派 fixer 写 mnemon 记忆。

## 8. 新会话开场话术（可直接复制）

> 接 FluMonitor 项目（`D:\FluMonitor`，线上 https://zengwenj.github.io/flu-monitor/）。先读 `docs/handoff.md` 和 `CONTEXT.md`。
> 我要做遗留项 **（填 §5 待做/技术债中的某一项）**。请按项目约定走 缺口分析 → design/implement 冻结 → plan-critic → 我批准 → 实施 → oracle 复核 → 我验收提交。

## 9. 不要做的事

- 不要推翻 D14/D15/D17/D12/D19（要改先改 `CONTEXT.md` 并说明理由）
- 不要改已验证的解析与写入守卫（除非任务就是改它，且带回归验证：A1a 77 项 / A2 56 项套件在归档 validation/ 下）
- 不要恢复五页导航或改搜索交互契约（多候选必须显式选中；清空不动结果；缺模板/脚本故障必须恢复成都默认）
- 不要提交 `site/`、`site_publish/`、`.tmp_*`（版权/体积）
- 不要手工改 `data/*.csv` 不留痕
- 不要在云端 workflow 加多模态/API（D19）
- 不要绕过单写者锁并发跑管线；删锁前先确认没有写者在跑

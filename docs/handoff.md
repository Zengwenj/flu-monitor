# 交接文档（Handoff）

> 写于 2026-11-09，M4b 完成、全项目 M0–M4 收官之后。用于**另开会话继续遗留可选项目**。
> 读者：接手的新会话（AI）+ 你本人。读完这份 + `CONTEXT.md` 就能接上，不需要读全部历史。

---

## 1. 项目是什么 / 到哪一步了

个人用的传染病趋势监测工具，重点成都，产出是一个**每周五自动更新的在线分块证据页**。

| 项 | 值 |
|---|---|
| 线上 | https://zengwenj.github.io/flu-monitor/ |
| 仓库 | https://github.com/Zengwenj/flu-monitor （public） |
| 本地 | `D:\FluMonitor` |
| 最新提交 | `1d3d7fd`（本地 = 远程） |
| 状态 | M0 设计 / M1 可行性 / M2 最小闭环 / M3a 数据层 / M3b 仪表盘 / M4a 本地改造 / M4b 云端自动化 **全部完成** |
| 自动化 | GitHub Actions 每周五北京 10:00 自动抓三源→算指数→构建→bot 回写 data→部署 Pages（首跑 2026-11-09 全绿，境外 runner 抓 chinacdc.cn **实测可通**） |

## 2. 快速上手（新会话必读顺序）

1. `CONTEXT.md` — 术语表 + D1–D19 决策（**最重要，约束红线都在这**）
2. `docs/roadmap.md` — M0–M5 里程碑与当前位置
3. `docs/design.md` — 数据源与拼合逻辑（南方片/全国/四川三层）
4. `README.md` — 面向非开发者的使用说明
5. 需要细节时再读：`docs/adr/0001-*.md`（为何选 GitHub Actions）、`docs/publish-checklist.md`（发布合规）、`.trellis/tasks/archive/2026-11/*/`（各站 PRD/design/implement/可行性报告/评审记录）

**关键命令**

```bash
cd /d/FluMonitor
python ./.trellis/scripts/task.py list                    # 任务树（当前应只剩 00-bootstrap + 父任务）
git log --oneline -5                                      # 最近提交
python -X utf8 src/build_site.py --local                  # 本地生成页面（--local 必带！见 §6 坑4）
```

## 3. 代码与数据地图

```
src/fetch_flu_south.py   流感周报（PDF，pdftotext，南方片 ILI%+阳性率 → flu_south.csv）
src/fetch_sentinel.py    中疾控哨点周报（HTML 三表 → sentinel_national_rates.csv 长表 + sentinel_rank.csv 排序）
src/fetch_flunet.py      WHO FluNet 全量 CHN 筛选（→ flunet_china.csv，列映射固定）
src/compute_index.py     Goldstein 指数（写回 flu_south）+ 多病原排行/儿童前三/趋势序列函数
src/build_site.py        渲染 6 块仪表盘（方式A：字符串插值内联，无 JS/fetch/外部库；SVG 纯 Python 生成）
src/update_sichuan.py    四川月度半自动录入（首页找文章→下图→人工输入 I-V→写CSV→可选push）
src/write_run_status.py  云端运行状态（→ data/run_status.json，供页面诚实横幅）
run_local.bat            本地一键：三源→compute→build(--local)→打开
update_sichuan.bat       四川月度入口
.github/workflows/weekly.yml  云端每周任务

data/  flu_south.csv(1行) sentinel_national_rates.csv(2266行/103周) sentinel_rank.csv(1115行)
       flunet_china.csv(1021行) sichuan_monthly.csv(1行) changes.log run_status.json
site/  生成物（.gitignore，不进 git，由 Pages artifact 部署）
```

## 4. 不可违背的约束红线（违反即为错误实施）

| 编号 | 约束 |
|---|---|
| **D14** | **不合成“成都综合风险总分”**。页面是分块证据页，每块自标口径与状态 |
| **D15** | 数据边界：哨点周报表1 只有**全国**阳性率数值；表2/表3 只有**前三名名称**（南北片/年龄组）。官方**没有**“南方片分病原阳性率数值”——不得伪造 |
| **D17** | 箭头=**仅较上周**（不是 vs 往年）；指数写“相对强度”、变化写“**N 个百分点**”；南方片历史基线**不得**用全国 FluNet 混算 |
| **D12** | CSV 是权威存储（用户可 Excel 核对）；彩虹 bot 会回写 data/ |
| **D19** | 四川分级=**本地手动**月度录入（无可靠自动识别通道，勿重造多模态 API 方案） |
| 诚实性 | 缺数据**不显 0**、旧数据**不标最新**、官方分级缺**不默认绿**、状态文案只能用 `design.md` 附录枚举 |

**代码层契约**（`design.md` / 各站 implement.md 有详述）：
- fetch_sentinel 的 r3 写入：**22 行完整才覆盖**，失败永不覆盖成功周（`write_week` 有守卫）
- flu_south 同理（成功才覆盖） 
- build_site 方式 A 内联，**禁止** fetch/外部 JS/图表库；`--local` 时忽略 run_status.json

## 5. 遗留可选项目（按收益排序）

### A1 ★ 流感周报历史回补（收益最大，一次性）
- **做什么**：回补流感周报 PDF 约 150 期（2023 至今），解析南方片 ILI%/阳性率入 `flu_south.csv`
- **为什么最值**：一件事解锁三样——①南方片 Goldstein 历史序列 ②环比箭头（当前只有 1 行数据，无环比）③“本周 vs 往年同期”块（当前是占位）
- **入口**：`src/fetch_flu_south.py` 的 `--backfill` **尚未实现**（目前只有单期 + URL 抽验两模式）；`fetch_sentinel.py --backfill` 可作范式（遍历列表页 `index_N.html`，404=终点，限速 2.5s）
- **注意**：PDF 每期约 6.5MB（≈1GB 下载）；南方 ILI%/阳性率在同一 PDF 文本中；2025 版式**无括号百分比**需分母自算（现有代码已兼容）
- **验收**：flu_south.csv 覆盖至 2023 起、每周一行、Goldstein 可算、页面“往年同期”块出真实对比

### A2 其他省市查询（用户 2026-11-09 定留 M5）
- 南北片切换 + 黑龙江（hljcdc.org 每周 11 病原）/重庆（cqcdc.org 周更哨点）外省页
- 诚实展示原则见 `CONTEXT.md` D14 段：有周报显周报 / 仅省级标“省级参考” / 仅片区标“区域背景” / 无数据写“未取得”
- 注意：多数省只有**月度发病数**，市级几乎为零——分级展示，不伪装

### A3 支原体专题 / 细菌维度
- 支原体已在 11 病原排行中出现；专题=单独趋势图（数据已有，纯展示层）
- 细菌：CHINET 半年报（www.chinets.com，免费 PPTX，儿童株/成人株分列）——注意是耐药率不是阳性率

### A4 界面美化（最后做）

### B 小技术债（不影响使用）
1. `sentinel_national_rates.csv` 的 `week_start` 全空（X 轴现用“第N周”；若要日期需 ISO 周推算）
2. 排序缺口 11 周未区分两种原因：2026W6/W12（官方版式异常，表2+表3 合并粘连）/ 2025W14-22（月度合并版，表2/3 归属周次语义不明）→ 若要细分需 join `changes.log`
3. `changes.log` 的 `--merge` 重复执行会重复留痕（日志噪声）
4. Actions 弃用提醒：Node20→24、ubuntu-latest 将迁 Ubuntu 26 → 未来需升级 `actions/*` 版本
5. `.trellis/workspace/` 日志已跟踪，未来若写入敏感内容需处理（见 publish-checklist）

### C 外部限制（不可改，页面已诚实标注）
成都无市级周度公开数据 / 四川分级需每月手录 / 多病原历史仅 2 年（2024-W46 起）/ 境外连通性可能变化（通→不通时页面显横幅 + 本地 run_local+push 兜底）

## 6. 已知坑（新会话最容易踩）

1. **pdftotext 跨平台**：Windows 用 anaconda 绝对路径，Linux 用 `shutil.which("pdftotext")`（runner 由 poppler-utils 提供）——已实现，勿回退
2. **跨年伪断点**：SVG 折线断点判定用 `_adjacent_week()`（W52→次年W1 连续），**不要**改回 `y*53+wk` 差 1 判断
3. **URL 正则**：中疾控文章 URL 形如 `t20261105_1842732.html`（含下划线），流感 PDF 是**相对文章页目录**的 `./P0....pdf`（需 urljoin）
4. **`build_site` 必须带 `--local` 才在本地跑**：否则会读 bot 回写的 `run_status.json`（云端上一轮状态），导致横幅误报/漏报
5. **本地 push 前先 `git pull`**：bot 每周回写 data/，直接 push 会非快进被拒
6. **境内 push GitHub 偶发 `Connection reset`**：重试即通（已有两次实证）
7. **四川文章图片是 `../../` 相对路径**；“发布时间：”与日期之间有 `</p><p>` 标签；月份从标题“您的N月”取
8. **合并版/异常版式**：2025W14-22 是月度合并版（表1=病原体×多周宽表），2026W6/W12 表2+表3同表且并列粘连——解析已容错降级为排序占位，别再试图“修复”
9. **PRD 里有旧表述**：`11-06-build-site/prd.md` 的“趋势图叠往年对比线”已被 D17 用户决策废止（改本年度折线）——以 `CONTEXT.md` 为准
10. **离线检查**：只查“加载型外部资源”（fetch/script src/link href/img src=http/url(http），**`<a href>` 官方来源链接是允许的**

## 7. 工作流程约定（用户明确要求的）

每站/每个遗留项都走同一套门，不要跳：

```
metis（计划前缺口分析）
  → 成稿 design.md + implement.md
  → momus（成稿评审；REJECT 必须修订后复审）
  → 用户批准（独立于 momus，不可替代）
  → 实施（主会话直接做，抓取调试需现场迭代）
  → trellis-check（独立只读复核）
  → 汇报 + 分两笔提交（docs / feat）+ push
```

**证据**：本项目每站 momus 都抓到真实阻塞项（共约 13 个），trellis-check 每站也都有发现——**这套门不是形式**。用户曾明确质问“为什么不走 metis 和 momus”，后续必须默认执行。

其它协作偏好：
- 决策/计划/汇报**用中文**；区分事实/推测/建议
- 用户无开发经验：操作要写成双击/点击级指引
- 关键选择用 AskUserQuestion 给推荐项（用户惯于“确认推荐方案”）
- 每次实质进展后用后台代理写 mnemon 记忆（见 `C:\Users\zengw\.zcode\cli\memories\...`）

## 8. 新会话开场话术（可直接复制）

> 接 FluMonitor 项目（`D:\FluMonitor`，线上 https://zengwenj.github.io/flu-monitor/）。先读 `docs/handoff.md` 和 `CONTEXT.md`。
> 我要做遗留项 **A1 流感周报历史回补**。请按项目约定走 metis → design/implement → momus → 我批准 → 实施 → trellis-check。

（把 A1 换成 A2/A3/B 等即可）

## 9. 不要做的事

- 不要推翻 D14/D15/D17/D12/D19 的既有契约（要改先改 `CONTEXT.md` 并说明理由）
- 不要改 `fetch_sentinel.py` / `fetch_flu_south.py` 已验证的解析与 r3 写入逻辑（除非任务本身就是改它，且必须有回归验证）
- 不要提交 `site/`（已 gitignore，走 artifact 部署）
- 不要手工改 `data/*.csv` 而不留痕（改值要写 `changes.log`）
- 不要把 `.tmp_m1/`、`.tmp_sichuan/` 或四川原始图片提交进仓库（版权+体积）
- 不要在云端 workflow 里加多模态/API 调用（D19 四川是本地手动）

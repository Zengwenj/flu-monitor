<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

# FluMonitor 项目须知

个人用呼吸道传染病监测工具（重点成都）：`src/fetch_*.py` 抓三源 → `src/compute_index.py` 算 Goldstein 指数 → `src/build_site.py` 生成零依赖静态页。同一条管线两处触发：GitHub Actions 每周五自动（部署 Pages + bot 回写 data/），本地 bat 双击兜底。仓库 public：`github.com/Zengwenj/flu-monitor`，分支 `main`。

## 接手先读（权威度从高到低）

1. `CONTEXT.md` — 术语表 + D1–D19 全部已确认决策
2. `docs/handoff.md` — 项目状态、代码地图、**约束红线（§4）**、已知坑（§6）、遗留项 A1–A4
3. `docs/design.md` — 数据源与"南方片/全国/四川"三层拼合逻辑

注意：`.trellis/spec/` 的 backend/frontend 指南是**未填写的 Trellis 模板**（bootstrap 任务未做），不代表本项目约定——本项目是纯 Python 脚本，无框架。

## 常用命令

```bat
run_local.bat                              :: 一键：三源抓取→算指数→build --local→打开页面（写 data/，不 push）
update_sichuan.bat                         :: 四川月度半自动录入（交互式，人工确认等级后可选 push）
python -X utf8 src/build_site.py --local   :: 本地构建必带 --local
```

- 本地跑任何 `src/*.py` 都要 `python -X utf8`（中文编码）；bat 已固定 anaconda 的 python 绝对路径，缺则回退 PATH。
- 忘带 `--local` 会误读云端 bot 回写的 `data/run_status.json`，导致横幅误报/漏报。
- 抓取脚本 CLI 模式：
  - `fetch_sentinel.py`：无参=最新一期 ｜ `--backfill`=全历史限速回补 ｜ `<文章URL>`=解析打印不写 CSV（抽验用） ｜ `--write-url <url> [周次]` ｜ `--merge <url>`
  - `fetch_flu_south.py`：无参=最新一期 ｜ `<文章URL>`=抽验打印不写 CSV。`--backfill` **未实现**（遗留项 A1，约 150 期 PDF）
- **无测试套件、无 lint 配置**。验证方式 = 实际跑脚本 + 核对生成的 CSV 行数/页面内容。
- 本地推云前**先 `git pull`**：Actions bot 每周五回写 data/，直接 push 会非快进被拒；境内 push 偶发 `Connection reset`，重试即通。
- Pages 部署失败先查仓库 Settings → Pages → Source 是否为 "GitHub Actions"（artifact 部署依赖它，这不是代码 bug）。

## 管线契约（违反即为错误实施）

- **D14** 不合成"成都综合风险总分"；页面是分块证据页，每块自标口径与状态。
- **D15** 哨点周报表1 只有**全国**阳性率数值，表2/3 只有前三名**名称**——"南方片分病原阳性率数值"官方不存在，不得伪造。
- **D17** 环比箭头仅表"较上周"（非 vs 往年）；指数标"相对强度"；南方片历史基线不得用全国 FluNet 混算。
- **D12** `data/*.csv` 是权威存储（用户用 Excel 核对）；手工改值必须留痕 `data/changes.log`；`site/` 是生成物（已 gitignore，勿提交）。
- **D19** 四川分级 = 本地月度手动录入；**云端 workflow 禁止加多模态/API 调用**。
- 诚实性：缺数据不显 0、旧数据不标最新、官方分级缺失不默认绿。
- 写入守卫（除非任务就是改它，且带回归验证）：`fetch_sentinel` r3 当周 22 行完整才覆盖旧行；`fetch_flu_south` 成功才覆盖、失败永不覆盖成功周。
- `build_site` 纯内联（方式 A）：禁止 fetch/外部 JS/图表库（本地 file:// 必须能打开）；`<a href>` 指向官方来源的链接是允许的。

## 解析坑（已容错，勿"修复"或回退）

- pdftotext 跨平台：Windows 用 anaconda 绝对路径，Linux 用 PATH（runner 装 poppler-utils）——已实现，勿回退。
- SVG 跨年断点判定用 `_adjacent_week()`（W52→次年W1 视为连续），勿改回 `y*53+wk` 差 1 判断。
- 中疾控文章 URL 含下划线（`t20261105_1842732.html`）；流感 PDF 是相对文章页目录的 `./P0…pdf`（需 urljoin）。
- 2025W14–22 月度合并版、2026W6/W12 表2+表3 粘连——解析已降级为占位并记 `changes.log`，别再试图修复。
- 四川文章图片是 `../../` 相对路径；"发布时间："与日期之间有 `</p><p>` 标签；月份从标题"您的N月"取。

## 工作流程（用户明确要求的门，勿跳）

缺口分析（计划前）→ design.md + implement.md 成稿 → 成稿评审（REJECT 必须修订后复审）→ **用户批准（独立于评审，不可替代）** → 主会话直接实施（抓取调试需现场迭代，勿全盘委派）→ 独立只读复核 → 汇报 + 分两笔提交（docs / feat）+ push。
（ZCode 中对应 metis / momus / trellis-check；OpenCode 会话用可用的审查角色/子代理执行同等的门。历史证据：每站评审都抓到过真实阻塞项，这套门不是形式。）

## 协作约定

- 决策/计划/汇报用中文；区分事实/推测/建议。
- 用户无开发背景：给用户的操作指引写到双击/点击级。
- 关键选择提供带推荐项的选项（用户惯于确认推荐方案）。
- `.tmp_m1/`、`.tmp_sichuan/`、四川原始图片不进仓库（版权+体积）。

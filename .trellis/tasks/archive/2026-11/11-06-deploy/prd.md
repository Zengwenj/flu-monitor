# PRD：自动化部署与双触发（子任务 4/4）

依赖：build-site。父任务最终集成验证在此之后。

## 要做什么

- **云端（方案 a）**：`.github/workflows/weekly.yml`——每周五定时（cron，UTC 换算确保周报已发布）+ `workflow_dispatch` 手动触发。流程：抓数→算指数→构建网页→**用自定义 Actions 发布 Pages**（`actions/upload-pages-artifact` 上传构建产物 + `actions/deploy-pages` 部署，job 授予 `pages: write` + `id-token: write`）。**不依赖"机器人提交自动触发 Pages 构建"**（实测 GITHUB_TOKEN 提交不触发构建；分支发布目录仅限根或 /docs，故走 artifact 部署）。
- **本地（方案 b）**：两个本地入口——
  - `run_local.bat`：双击执行同一套 Python，生成**数据内联的本地 HTML** 并自动打开；本地默认写独立缓存/输出目录（如 `local_out/`），**不自动 push、不改发布用主数据**，避免 git 同步冲突。
  - `update_sichuan.bat`（D19 四川月度半自动）：每月一次，抓当月四川流感指数图片 + 多模态模型识别等级（OCR 辅助），展示识别结果给用户确认，写入 `data/sichuan_monthly.csv` 并推送。云端不调多模态 API。
  - 可选"一键把本地抓取结果同步到仓库"作为境外 runner 不通时的兜底通道。
- 公开仓库；README 面向非开发者：如何看、本地双击、手动触发、装 Python。
- **发布前核查**：资料使用条件、仓库内个人信息脱敏（不暴露居住地等隐私轨迹）、发布范围确认——公开可访问不等于可任意再分发，已登录不等于已授权发布。

## 约束

- 用户 GitHub 已就绪（gh 登录 Zengwenj，含 workflow 权限）。
- 定时 UTC，换算确保周报已发布。
- 公共仓库 60 天无提交暂停定时——每周有提交自动续。
- GitHub 境外 runner 对 chinacdc.cn 的连通性由 data-feasibility 先验；不通则本地补抓兜底 + 页面显著"数据停更/抓取失败"横幅。
- "近零运维"= 正常自动运行 + 异常有提示和恢复办法，非"永不用管"。

## 验收标准（可独立验证）

- [ ] 手动触发 workflow 成功，Actions 日志绿，Pages 链接可访问并显示最新数据（经 artifact 部署，非依赖 bot 提交触发）。
- [ ] 本地 `run_local.bat` 双击产出数据内联的本地 HTML（file:// 可离线打开），不污染发布用主数据。
- [ ] `update_sichuan.bat` 能抓当月四川图片、识别等级、展示供确认、写入 CSV 并推送；云端构建只读此 CSV、不调多模态 API。
- [ ] cron 配置经校验会在目标周五触发（workflow_dispatch 验证逻辑）。
- [ ] 抓取失败/数据过期时页面有显著横幅，不静默显示旧数据。
- [ ] 仓库无个人隐私信息；README 让非开发者能独立完成四件事。

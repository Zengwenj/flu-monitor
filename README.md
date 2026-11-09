# FluMonitor · 成都呼吸道防护参考

个人用的传染病趋势监测工具：抓公开监测数据 → 算指数 → 生成一个**分块证据页**，重点服务成都（现居地），也展示全国哨点与儿童分龄信息。**不合成总分**，每块数据标注口径与时效。

## 在哪看

- **在线网页（每周五自动更新）**：`https://zengwenj.github.io/flu-monitor/`
- 本地：双击 `run_local.bat`，会自动抓最新数据并打开 `site/index.html`

## 你会看到的 6 块

| 块 | 口径 | 更新 |
|---|---|---|
| 四川官方流感分级 | 省疾控平原区（成都）月度五级 | 每月（你手动录，见下） |
| 南方片流感趋势 | 国家流感中心南方片哨点周度 | 每周自动 |
| 本周 vs 往年同期 | 待历史回补后启用 | — |
| 全国多病原活跃度排行 | 全国哨点 11 病原门急诊阳性率降序 | 每周自动 |
| 流感/新冠/RSV 趋势 | 全国哨点本年度逐周折线（内联 SVG） | 每周自动 |
| 儿童分龄高发前三 | 全国哨点 0-4 / 5-14 岁门急诊排序（非数值） | 每周自动 |

页脚有完整口径说明。数据来源：中国疾病预防控制中心（稿件来源：中国疾病预防控制中心）、四川省疾控、WHO FluNet。

## 日常操作（四件事）

1. **看**：打开上面的网址，或双击 `run_local.bat` 看本地版。
2. **每月一次 · 更新四川分级**：双击 `update_sichuan.bat` → 自动抓当月四川"流感指数"文章并打开成都（平原区）仪表盘图 → 你按图输入等级（I/II/III/IV/V）→ 自动写入并询问是否推送到 GitHub（y 推送 / n 稍后手动 `git push`）。
3. **想立刻云端更新**：GitHub 仓库 → Actions → "Weekly data update" → Run workflow（手动触发一次）。
4. **本地补抓**：双击 `run_local.bat`（抓三源→算指数→生成页面；不自动 push）。
   要上云时：**先 `git pull`（云端每周会自动提交数据，不同步会推送失败）**，再 `git push`。

## 首次配置（换电脑或重建仓库时才需要）

1. 装 Python（含 beautifulsoup4：`pip install -r requirements.txt`）；`pdftotext` 来自 poppler（Windows 走 anaconda 自带，Linux 装 `poppler-utils`）。
2. GitHub 仓库 → **Settings → Pages → Source 选 "GitHub Actions"**。
   - ⚠️ 顺序：先有这个仓库和 workflow 文件，Pages 设置里才会出现 "GitHub Actions" 选项。
   - ⚠️ 若未启用 Pages 就手动跑 workflow，部署步骤会失败——**这不是代码 bug**，启用后重跑即可。

## 云端每周自动更新怎么工作

每周五北京时间 10:00，GitHub 的服务器会：抓三源（流感周报/哨点周报/WHO FluNet）→ 写本次运行状态 → 算指数 → 生成页面 → 把新数据提交回仓库 → 部署到 Pages。

**两种结果都正常**：
- **抓到（连通）**：页面显示最新一周数据，无横幅。
- **抓不到 chinacdc.cn（境外网络受限）**：页面顶部显示"本次更新未能获取最新数据…当前展示为上次成功的存量数据"，Pages 仍会正常部署。此时你每周双击 `run_local.bat` 抓数 + `git push`，云端会继续用新数据构建发布。

## 目录

```
data/         权威数据（CSV，Excel 可开）：flu_south / sentinel_national_rates /
              sentinel_rank / flunet_china / sichuan_monthly / changes.log
src/          抓取（fetch_*）、计算（compute_index）、渲染（build_site）、
              四川录入（update_sichuan）、运行状态（write_run_status）
site/         生成的网页（不进 git，由 Pages artifact 部署）
docs/         设计决策（design.md/roadmap.md/adr/）与发布核查（publish-checklist.md）
.github/      每周自动更新的 workflow
run_local.bat / update_sichuan.bat   本地双击入口
```

## 说明

- 这是个人自用+家庭分享的工具，不是面向公众的产品；数据均来自公开渠道并标注出处。
- 成都无公开的市级周度数据：页面上的"成都"相关块 = 省官方月度分级 + 南方片周度 + 全国哨点，各自标注，不冒充成都市实测。
- 详细设计与决策见 `CONTEXT.md`、`docs/design.md`、`docs/roadmap.md`。

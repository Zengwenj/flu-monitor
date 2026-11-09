# Implement：M4a 跨平台改造执行清单

> deploy 任务的 M4a 阶段（本地改造）。技术契约见本目录 design.md。全本地可验，不碰 .github/、不做 GitHub 网页操作。momus APPROVE + 用户批准后执行。

## 执行前
- [ ] momus 复审 M4a → APPROVE
- [ ] 用户批准 M4a（写代码）
- [ ] 不改 fetch_sentinel/fetch_flunet/compute_index/build_site 的核心逻辑（仅 fetch_flu_south 改 pdftotext 路径解析段）

## 有序步骤

### S1 requirements.txt〔GAP-1〕
- 根目录建 `requirements.txt`：`beautifulsoup4>=4.12`
- **验证**：`pip install -r requirements.txt` 成功（本机已装 bs4，确认 import 无误）

### S2 pdftotext 跨平台〔GAP-1〕
- 改 `fetch_flu_south.py` 的 PDFTOTEXT：`sys.platform=="win32"` 且绝对路径存在→用绝对路径，否则 `shutil.which("pdftotext")`；None 则 raise 明确错误
- **验证**：本机回归用**固定文章 URL 抽验入口**（避免上游出新期后误判）——`python src/fetch_flu_south.py https://www.chinacdc.cn/jksj/jksj04_14249/202611/t20261105_1842732.html` 应输出 W44 ILI%4.8/阳性率17.14（不写盘）；code review 确认非 win32 走 shutil.which 分支（本机 Windows 无法真实跑 Linux 分支，此限制如实标注，Linux 实跑留 M4b runner 首跑）

### S3 update_sichuan（纯本地）〔GAP-3/D19〕
- 建 `src/update_sichuan.py` + `update_sichuan.bat`（bat 首行 `cd /d "%~dp0"`，调 python）
- 逻辑：找 sccdc.cn 当月流感指数文章→下载五区域图到 `.tmp_sichuan/`→`start` 打开成都图→`input()` 收等级(I-V，校验)→写 sichuan_monthly.csv（列头与现有完全一致、主键幂等）→询问是否 push
- `.gitignore` 加 `.tmp_sichuan/`
- **验证**：跑一次——打开图、输入 IV、CSV 新增/覆盖该月行且格式与现有一致、push 询问选 n 可取消；重复跑同月幂等不重复行

### S4 run_local 行为 + .gitattributes〔GAP-6/7〕
- `run_local.bat`：确认写 data/ 不自动 push（现状已是，补注释说明）；pdftotext 跨平台后本机仍可跑
- `.gitattributes` 追加 `data/*.csv text eol=lf`
- **验证**：`git check-attr text eol -- data/flu_south.csv` 显示 `text: set / eol: lf`

### S5 发布前核查 checklist〔GAP-9 + B1〕
- 建 `docs/publish-checklist.md`，两部分：
  - **个人信息**：列将公开文件类别（代码/数据CSV/文档/CONTEXT），逐条标"是否含个人信息+处置"；检查 CONTEXT"现居成都"、CSV fetched_at 时间戳、git user.email 等
  - **资料使用条件**〔B1，prd:13 + CONTEXT:72 要求〕：逐源核查抓取数据能否公开再分发——中疾控哨点/流感周报、WHO FluNet、四川省疾控图片各自的版权/使用条款，记录依据链接+结论（可公开/需署名/待确认），不留空
- **验证**：checklist 两部分均覆盖，无遗漏文件类别未评估个人信息、无数据源未评估使用条件

### S6 端到端回归 + trellis-check + 汇报
- 全链路本地重跑：fetch_flu_south + fetch_sentinel + fetch_flunet + compute_index + build_site → index.html 正常（M2/M3 不回归）
- 派 trellis-check 复核 → 汇报停下等用户验收 M4a，再进 M4b

## 停靠点
S6 完成即停。用户验收 M4a（跨平台就绪+update_sichuan可用）后进 M4b（云端首跑，需网页操作）。

## 回滚
（路径相对项目根 D:/FluMonitor）`git checkout src/fetch_flu_south.py run_local.bat .gitattributes .gitignore` + 删 `requirements.txt`、`src/update_sichuan.py`、`update_sichuan.bat`、`docs/publish-checklist.md`。数据与其他脚本不动。

## 验收（对应 deploy prd M4a 部分 + metis 消解）
- [ ] requirements.txt 可 pip install
- [ ] pdftotext 跨平台（win 绝对路径+which 兜底，非win 走 which），本机回归通过
- [ ] update_sichuan 纯本地可用、CSV 格式对齐、幂等、push 可选
- [ ] .gitattributes CSV eol=lf 生效
- [ ] publish-checklist 覆盖完整
- [ ] M2/M3 全链路不回归

---

# Implement：M4b 云端 Actions 首跑（追加章节）

> M4b 执行清单。契约见 design.md 的 M4b 章节。写 workflow + 用户网页操作 + 首跑验证。momus APPROVE + 用户批准后执行。

## 执行前
- [ ] momus 复审 M4b → APPROVE
- [ ] 用户批准 M4b（写 workflow + 同意网页操作）
- [ ] publish-checklist 两❓（中疾控版权/WHO 许可）已核查记录〔GAP-9〕

## 有序步骤

### S0 核 publish-checklist 两❓〔GAP-9，push 前 gate〕
- 实际访问核：中疾控周报页有无版权/再分发声明、WHO FluNet 许可版本
- 结论写回 publish-checklist.md（即使"暂无明确条款、按出处链接降级保障继续"也记录）

### S1 run_local 扩三源 + site gitignore〔用户决策〕
- `run_local.bat`：抓取步骤扩为 fetch_flu_south + fetch_sentinel + fetch_flunet → compute → build
- `.gitignore` 加 `site/`；从 git 移除已跟踪的 site/index.html（`git rm --cached`）
- **验证**：本地跑 run_local 三源都抓、页面生成；`git check-ignore site/index.html` 命中

### S2 写 weekly.yml + build_site 读 run_status〔核心交付 + momus B1〕
- **先改 build_site.py**：读 `data/run_status.json`（不存在=本地模式不显横幅）；若其中任一 chinacdc 源 skipped/failed → 页面顶部横幅"本次更新未能获取最新数据（{原因}），当前展示为上次成功的存量数据"。原"CSV 有更晚失败行"横幅逻辑保留。
- 按 design 结构写 `.github/workflows/weekly.yml`（cron 0 2 * * 5 + dispatch + 三权限 + 连通性标志 + 三源条件抓取 + 写 run_status.json + 恒构建 + bot commit data/ + artifact 部署）
- **验证**：YAML 语法校验；本地造 run_status.json 两场景（chinacdc skipped→横幅出现、旧数据不标"数据正常"；全 ok→无横幅）；人工核对 permissions/cron/job 结构与 design 一致

### S3 README〔GAP-11，非开发者四件事+配置+首跑路径〕
- `README.md`：①Pages 链接在哪看 ②本地双击 run_local ③手动触发 Actions ④每月 update_sichuan ⑤首次 Settings→Pages→GitHub Actions（顺序+"首跑可能因未启用而失败非bug"）⑥首跑通/不通各做什么 ⑦两❓核查结论摘要
- **验证**：无开发经验者可照做四件事+配置

### S4 push M4a + M4b〔GAP-6 前置〕
- push M4a 的 64c9841+413ab96 + M4b 本批（weekly.yml/run_local/gitignore/README/checklist）
- **验证**：`git log origin/main` 含 weekly.yml 提交（workflow 文件在远程 Actions 才识别）

### S5 停下给用户网页操作指引〔用户亲自操作〕
- 停靠点：给用户逐步指引——①Settings→Pages→Source→GitHub Actions ②Actions→Weekly data update→Run workflow
- 用户执行后回传首跑结果（或我方读 gh run 查看日志）

### S6 首跑验证连通性 + 汇报
- 读首跑日志：CHINACDC_REACHABLE 值、三源 step 状态、commit、deploy、Pages 链接
- 判定：通→全自动达成；不通→兜底模式（本地抓+推送），README 已写明用户后续操作
- trellis-check 复核 + 汇报 M4b 完成（= 全项目完成）

## 停靠点
S5（等用户网页操作）+ S6（等首跑结果）。首跑连通性是外部事实，通/不通都算 M4b 交付成功（不通走兜底，非代码缺陷）。

## 回滚〔momus B2：分 push 前/后〕
- **push 前**（S4 未推）：删 `.github/workflows/weekly.yml`；`git checkout run_local.bat .gitignore src/build_site.py`；删本次新建 README.md。基线=413ab96。
- **push 后**（S4 已推）：`git revert` 或 `git checkout 413ab96 -- run_local.bat .gitignore src/build_site.py` 重新 commit+push；**远程 weekly.yml 必须从仓库删除并 push（或网页 Actions 禁用）**才能停定时任务；bot 已 commit 的 data/ 保留。判据=远程无 weekly.yml（或禁用）+ 相关文件回 413ab96 版。

## 验收（对应 deploy prd M4b 部分 + metis/momus 消解）
- [ ] weekly.yml 语法正确、cron=0 2 * * 5、三权限齐、连通性标志+条件抓取+写 run_status.json+兜底恒构建+bot commit data/+artifact 部署
- [ ] build_site 读 run_status.json：chinacdc 源本次未成功→显"本次未获取最新"横幅、旧数据不标"数据正常"（两场景本地验过）〔momus B1〕
- [ ] run_local 扩三源；site/ 已 gitignore 且取消跟踪
- [ ] README 覆盖四件事+Pages启用顺序+首跑两结果路径
- [ ] publish-checklist 两❓已核查记录
- [ ] M4a+M4b 已 push，weekly.yml 在远程可被 Actions 识别
- [ ] 首跑完成：日志连通性标志明确、Pages 链接可访问（通=最新无横幅/不通=旧数据+横幅均算成功）

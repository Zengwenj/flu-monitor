# Design：M4a 跨平台改造 + 依赖标准化

> M4 拆为 M4a（本地改造，本地可验）/ M4b（云端 Actions 首跑，需 GitHub 网页操作）。本文档是 M4a。
> M4a 目标：让现有脚本在"非本机环境（GitHub Ubuntu runner）"也能跑，并补齐 update_sichuan 半自动脚本——全部本地可验证，不碰 GitHub 网页。基于 metis 缺口分析（2026-11-09，GAP-1/3/6/7/9）+ 用户三决策。M4b 另行规划。

## 用户已定（三决策）
- runner 不通兜底 = 本地抓+云端发布（M4b 的 workflow 设计点，M4a 先保证本地抓取链路跨平台可跑）
- 四川识别 = update_sichuan 纯本地输入（零 API）
- M4 拆 M4a/M4b

## M4a 范围

1. **requirements.txt**〔GAP-1〕：声明 Python 依赖（beautifulsoup4；其余 urllib/csv/re 为标准库）。runner 与新机器据此 `pip install`。
2. **pdftotext 跨平台**〔GAP-1〕：`fetch_flu_south.py` 的 `PDFTOTEXT` 改为平台感知——Windows 用现有 anaconda 绝对路径且 `shutil.which("pdftotext")` 兜底；非 Windows 直接 `shutil.which("pdftotext")`（runner 上由 poppler-utils 提供）。找不到则报明确错误。
3. **update_sichuan.bat + update_sichuan.py**〔GAP-3，D19〕：纯本地交互——列表页找当月四川流感指数文章 → 下载五区域图片到临时 → `start` 自动打开成都(平原)图 → 命令行 `input()` 让用户输入等级(I/II/III/IV/V)+等级名 → 写 `sichuan_monthly.csv`（主键 year+month+region 幂等，confirmed_by=人工）→ 询问是否 `git push`。零 API、零多模态依赖。
4. **run_local.bat 行为明确**〔GAP-7〕：维持写 `data/`（非 local_out），但**不自动 push**；README 说明"本地跑=看最新，要上云需手动 push 或等云端"。pdftotext 路径问题由 S2 的脚本跨平台改造覆盖。
5. **.gitattributes CSV 行尾**〔GAP-6〕：加 `data/*.csv text eol=lf`，避免 Windows(CRLF)↔runner(LF) 每周巨 diff。
6. **发布前核查 checklist**〔GAP-9 + B1〕：产出 `docs/publish-checklist.md`，两部分——①个人信息：逐文件列"是否公开+是否脱敏"；②资料使用条件〔prd:13/CONTEXT:72〕：逐数据源（中疾控周报/WHO FluNet/四川图片）核查能否公开再分发，记依据链接+结论（可公开/需署名/待确认）。

## M4a 不做（归 M4b）
- `.github/workflows/weekly.yml`（云端）
- Pages 启用与首跑
- 境外 runner 连通性实测
- cron 定时
- 云端 commit 回仓库策略

## 技术要点

### pdftotext 跨平台（GAP-1）
```
# fetch_flu_south.py 伪码
import shutil, sys
_WIN = r"C:/Users/zengw/anaconda3/Library/bin/pdftotext.exe"
PDFTOTEXT = (_WIN if sys.platform == "win32" and Path(_WIN).exists()
             else shutil.which("pdftotext"))
if not PDFTOTEXT: raise RuntimeError("未找到 pdftotext，请装 poppler-utils")
```
只改路径解析，不动已验证的解析逻辑。

### update_sichuan 纯本地（GAP-3/D19）
- 复用 fetch_sentinel 的列表页抓取范式找四川当月文章（sccdc.cn）
- 图片下载到 `.tmp_sichuan/`（gitignore）
- `input()` 校验只接受 I/II/III/IV/V；等级名可选默认映射（V=低水平活动…IV=活跃期…）
- 写 CSV 用与现有 sichuan_monthly.csv **完全相同的列头**（GAP-8 合约对齐）
- push 为可选（`input("是否推送到 GitHub? y/n")`），失败不崩（境内网络可能 reset，提示重试）

### requirements.txt
```
beautifulsoup4>=4.12
```
（urllib/csv/re/subprocess/datetime 标准库不列；pdftotext 是系统二进制非 pip 包，由 M4b workflow 的 apt 装）

## 验证方式（全本地）

1. `pip install -r requirements.txt` 成功
2. 模拟非 Windows：临时把 PDFTOTEXT 解析走 `shutil.which` 分支，确认逻辑正确（或 code review 分支）
3. `fetch_flu_south.py` 在本机仍正常（回归：W44 ILI%4.8/阳性率17.14）
4. `update_sichuan.bat` 跑一次：打开图、输入等级、写入 CSV 与现有格式一致、push 询问可取消
5. `.gitattributes` 生效：`git check-attr text eol data/flu_south.csv` 显示 eol=lf
6. publish-checklist.md 覆盖所有将公开文件
7. 回归：compute_index + build_site 仍生成正确 index.html（M3b 不回归）

## 回滚
M4a 改 src/fetch_flu_south.py（仅路径解析段）+ 新增 requirements.txt/update_sichuan.*/publish-checklist.md/.gitattributes 追加行。回滚（路径相对项目根）=`git checkout src/fetch_flu_south.py run_local.bat .gitattributes` + 删新增文件。数据/其他脚本不动。

## 与 M4b 边界
M4a 交付"跨平台就绪的脚本 + 本地 update_sichuan"；M4b 写 workflow 调这些脚本、首跑验证连通性、启用 Pages。M4a 不触碰 .github/。

---

# Design：M4b 云端 Actions 首跑（追加章节）

> M4b = deploy 任务第二阶段。基于 M4a 跨平台脚本 + metis M4b 缺口分析（GAP-1~12）+ 用户三决策（commit 回仓库 / run_local 扩三源 / site 加 gitignore）。

## 用户三决策
- weekly.yml commit data/*.csv 回仓库（github-actions bot，on 只 schedule+dispatch 防循环）
- run_local.bat 扩为三源（兜底完整）
- site/ 加 .gitignore（Pages 走 artifact，不进 git 历史）

## 范围
1. `.github/workflows/weekly.yml`（见下结构）
2. `run_local.bat` 扩三源
3. `.gitignore` 加 site/
4. `README.md`（非开发者）
5. publish-checklist 两❓核查记录（push 前 gate）

## weekly.yml 结构（单 job，metis GAP-2/4/5 消解）

```
name: Weekly data update
on:
  schedule: [{cron: "0 2 * * 5"}]   # UTC周五02:00=北京周五10:00（GAP-8笔误已修）
  workflow_dispatch:
permissions:
  contents: write      # commit data（GAP-4）
  pages: write
  id-token: write
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - checkout
      - setup-python
      - apt-get install -y poppler-utils   # pdftotext（M4a 跨平台 which 分支依赖，GAP-1）
      - pip install -r requirements.txt
      - 连通性探测：curl -I --max-time 15 chinacdc.cn → 写 CHINACDC_REACHABLE=true/false 到 $GITHUB_ENV（GAP-5/10）
      - FluNet: python fetch_flunet.py   # timeout-minutes:15 + continue-on-error（GAP-12，WHO 全球 CDN 大概率通）
      - 哨点(表1/2/3): if CHINACDC_REACHABLE==true 跑 fetch_sentinel；continue-on-error（GAP-5）
      - 流感周报: if CHINACDC_REACHABLE==true 跑 fetch_flu_south；continue-on-error
      - 写 data/run_status.json（run_at + chinacdc_reachable + 各源 ok/skipped/failed）〔momus B1〕
      - compute_index + build_site（恒跑：失败源用仓库已有 CSV 兜底；build 读 run_status.json 决定是否显"本次未获取最新"横幅）
      - commit data/*.csv + data/run_status.json（bot 身份，仅 git add data/ 不含 site/；无变更则 skip）（GAP-2/7）
      - upload-pages-artifact(site/) + deploy-pages（GAP-3）
```

## 关键设计点（metis 消解）

- **连通性显式标志**〔GAP-5/10〕：探测 step 输出 `CHINACDC_REACHABLE`，chinacdc 两源用 `if:` 跳过而非盲 continue-on-error——日志一眼区分"连通性"vs"代码bug"。FluNet 独立（WHO CDN）不受此标志约束。
- **兜底恒构建 + 本次运行状态传递**〔GAP-2 + momus B1〕：compute+build+deploy 恒跑。**新增 `data/run_status.json` 接口**解决"旧数据被标数据正常"的诚实性漏洞——
  - workflow 在抓取各步后写 `data/run_status.json`：`{run_at, chinacdc_reachable, sources:{flu_south:ok/skipped/failed, sentinel:…, flunet:…}}`
  - `build_site.py` 读 run_status.json：**任一 chinacdc 源本次 skipped/failed → 页面顶部显横幅"本次更新未能获取最新数据（{原因}），当前展示为上次成功的存量数据"**；该横幅独立于"CSV 里有更晚失败行"的原逻辑（后者仍保留）
  - 本地 run_local 跑时无 run_status.json（或标全 ok）→ 不显此横幅，正常展示
  - 效果：连通性 false 或抓取失败时，旧数据**永远带正确时效标注**，不会被标"数据正常"
- **commit 防循环**〔GAP-2〕：on 不含 push；bot commit 只 `git add data/`（site/ 已 gitignore 不会误提交，GAP-7）；无变更时跳过 commit 避免空提交。
- **Pages 鸡生蛋**〔GAP-3〕：顺序=push weekly.yml→用户网页启用 Pages(此时才有 GitHub Actions 选项)→Run workflow。首跑若 Pages 未启用则 deploy step 失败，**这不是 bug**——README 明示。
- **cron**〔GAP-8〕：`0 2 * * 5`（修 roadmap 周五/周六笔误）。
- **M4a 前置 push**〔GAP-6〕：weekly.yml 推送前先 push M4a 的 64c9841+413ab96（requirements.txt/脚本须在远程）。

## 验证方式（首跑，需用户网页操作）

1. push M4a + weekly.yml + run_local 扩源 + gitignore + README
2. 用户：Settings→Pages→Source→GitHub Actions
3. 用户：Actions→Run workflow 手动首跑
4. 看日志：CHINACDC_REACHABLE 值、三源各 step 状态、commit step、deploy step
5. Pages 链接打开：通→最新数据无横幅；不通→旧数据+"本次未获取最新"横幅（均算 M4b 成功，连通性是外部事实非代码问题）
6. **本地两场景验证〔momus B1〕**：造 run_status.json 标 chinacdc skipped → build 页面出现"本次未获取最新"横幅、旧数据不被标"数据正常"；标全 ok → 无横幅正常展示

## 回滚〔momus B2：分 push 前/后〕
- **push 前**（S1-S3 做完、S4 未推）：删 `.github/workflows/weekly.yml`；`git checkout run_local.bat .gitignore`；删本次新建 README.md。基线=M4a 后的 413ab96。
- **push 后**（S4 已推、workflow 已在远程）：① `git revert` M4b 提交或 `git checkout 413ab96 -- run_local.bat .gitignore` 后重新 commit+push ② **远程定时任务不会因本地删文件停止**——需从仓库删除 `.github/workflows/weekly.yml` 并 push（或 GitHub 网页 Actions→禁用 workflow）③ 保留 bot 已 commit 的 data/（历史数据有价值，不回滚）。回滚完成判据=远程无 weekly.yml（或已禁用）+ run_local/gitignore 恢复 413ab96 版。

## 不做（归 M5）
省市查询、支原体、多年曲线。四川分级云端用仓库存量值（update_sichuan 是本地月度，不进 weekly.yml）。

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

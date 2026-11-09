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

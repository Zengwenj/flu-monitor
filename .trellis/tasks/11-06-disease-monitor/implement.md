# Implement：M2 最小闭环执行清单——修订版 r2

> M2 纵切（流感一条线）有序步骤。技术契约见本目录 design.md r2（含 metis/momus 修订）。已获用户批准执行（含写代码授权）；momus 复审 APPROVE 后开工。

## 执行前

- [x] 用户批准 M2 修订版计划（2026-11-06，"批准执行计划"）
- [x] M1 已验证：pdftotext 路径可用、流感 PDF 南方片数值可提取
- [ ] momus 复审 r2 → APPROVE
- [ ] 父任务 implement.jsonl/check.jsonl 已填

## 有序步骤

### S1 建骨架
- 建 `data/`、`src/`、`site/`；依赖最小化（标准库 + pdftotext 子进程；HTTP 先 urllib 带 UA，失败切 curl 子进程〔G8〕）

### S2 抓+解析流感周报
- **S2.0 列表页预验**〔G1〕：抓 `chinacdc.cn/jksj/jksj04_14249/`，确认静态 HTML、记录首条链接与发布日期结构
- **S2.1**：按发布日期取最新文章页 → 提取 PDF 链接（相对→绝对）→ urllib 下载（失败切 curl）
- **S2.2**：pdftotext -layout（`encoding='utf-8'`〔G7〕）→ 多精度正则〔G2〕抽南方 ILI%、南方阳性率（优先正文高精度版）、周次、发布日；**另抽一期 2025 年样本验证格式**后才定稿正则
- **S2.3**：写 `data/flu_south.csv`（契约列，含 status=ok）；失败路径写 fetch_failed/parse_failed 行
- **验证**：S7 按可操作口径输出核对（见 S7），非自报通过

### S3 Goldstein 计算
- `src/compute_index.py`：读两数值列 → 直乘 → **写回 goldstein_index 列**〔B1〕；相对强度指数标注随页面呈现；无往年→标"无往年同期数据"
- **验证**：W44 基准 4.8×17.14=82.272≈82.3 手算一致；若当次抓到 W45 用实际值手算

### S4 四川手填
- `data/sichuan_monthly.csv`：2026-10 成都平原 IV 级活跃期、source_pubdate=2026-10-19、fetched_at=now、confirmed_by=人工、note="M1 multimodal+人工确认"
- **验证**：与 M1 报告一致；主键唯一

### S5 构建分块页（方式 A〔G4/G5/B2〕）
- `src/build_site.py`：读两个 CSV → 字符串插值渲染 `site/index.html`（无独立 JSON、无 fetch）
- 两块+状态文案**只用 design.md 附录枚举**；防护建议引官方原文标出处；四川块显示"10月已确认等级·本月待更新"
- **验证**：file:// 离线打开无白屏；两块真实数据；状态/口径标注齐全；手机宽度排版正常

### S6 本地入口〔G9〕
- `run_local.bat`：首行 `cd /d "%~dp0"`，依次 fetch→compute→build，完成后 `start site\index.html`
- **验证**：双击（或 cmd 模拟）一键产出并打开

### S7 端到端自检 + 汇报
- **异常验例×3**〔B2〕：①四川 CSV 只留 10 月行→页面显示"本月待更新"且不默认绿 ②四川 CSV 清空→"官方分级未获取·状态未知" ③**流感 W44 ok 行保留 + 造一行 W45 fetch_failed→页面仍显示 W44 数值与指数 + 失败横幅（验证失败不覆盖成功、回退链路成立）**
- 清空 data/ 重跑一次，确认从零可产出
- **可操作核对输出**〔G6〕："本次抓到 W__ 期，ILI%=X%，阳性率=Y%，来源 PDF={文件名}，验收步骤：打开官网该期 PDF 摘要节核对"
- 汇报：页面路径+CSV+核对输出，停下等 M2 验收与 M3 决策

## 停靠点

S7 完成即停（roadmap"最重要信心节点"）。用户看过成品后定 M3。

## 回滚点

全部新建文件；失败删 `data/ src/ site/ run_local.bat` 重来，不影响已提交文档。

## 验收（对应 roadmap M2 + B2 异常态）

- [ ] index.html file:// 离线显示真实南方流感 Goldstein 指数 + 成都 10 月分级（标"本月待更新"）
- [ ] 数据与官网当期 PDF 人工核对一致（按 S7 核对输出执行）
- [ ] 状态/口径标注只用枚举文案；不合成总分；不伪造缺失（异常验例×3 通过）
- [ ] run_local.bat 一键可复现

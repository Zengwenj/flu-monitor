# Implement：M3a 数据层执行清单

> data-fetch 完整实施。技术契约见本目录 design.md。继承 M2 r3 契约。写功能代码——momus APPROVE + 用户批准后执行。

## 执行前
- [ ] momus 复审 M3a design/implement → APPROVE
- [ ] 用户批准 M3a（写代码）
- [ ] 不改 M2 的 flu_south.csv 与四个脚本

## 有序步骤

### S1 哨点列表页分页先验〔G8〕（阻塞后续回补）
- 抓 `chinacdc.cn/jksj/jksj04_14275/` 及试探 `index_1.html`…确认分页是静态多页还是 JS 动态
- 结论写入 design 附注：静态多页可遍历回补 / JS 动态则转 S5 替代发现路径（不降级放行）
- **验证**：能列出全部历史期 URL（或确定替代发现路径）则通过

### S2 哨点表1 抓取（全国11病原）
- `src/fetch_sentinel.py`：取文章页 HTML（M1 实测表1在网页正文非PDF），解析 11 病原×门急诊/住院×[值+较上周]
- 写 `data/sentinel_national_rates.csv`（长表，每周22行），r3 周级覆盖；**写入前完整性校验：必须 22 行、键唯一、数值有效，否则判 parse_failed 不覆盖旧周**〔B2〕
- **验证**：某周22行，抽3病原与官网网页核对一致（如W44流感门急诊15.6/较上周+0.9）；另造一次"解析出21行"模拟→确认旧完整周不被覆盖〔B2〕

### S3 哨点表2/表3 抓取（排序）
- 同文章页解析表2（南北前三）、表3（4年龄组前三），写 `data/sentinel_rank.csv`
- 并列名直接存顿号串〔G7〕
- **验证**：找一期有并列的（如2024-W46南方门急诊第三"流感病毒、腺病毒"）正确存串

### S4 FluNet 入库〔G6〕
- `src/fetch_flunet.py`：curl 下全量→流式筛 CHN→按列映射表取字段→写 `data/flunet_china.csv`
- 先打印表头确认列名精确拼写，避开 NOTDEFINED 列
- **验证**〔B4〕：中国行数≈1021（M1基准）、最早周=2005年、最新周 inf_positive_pct 与 M1 吻合、无 NOTDEFINED 串入数值列

### S5 历史回补（依 S1 结论）〔B3〕
- 若静态分页：遍历各页 URL 批量回补哨点表1/表2/3 至 2024-W46（礼貌限速，已抓周次跳过但允许低频复核）
- 若动态加载：依 design B3 替代发现路径（构造文章页URL递推/站内检索）；仍不可枚举则**历史回补记为未完成阻塞项**，附已获期次清单+缺口，交用户决定，**不得标 M3a 验收通过**
- changes.log 留痕机制〔G5〕：模拟上游修订验证追加记录
- **验证**：回补后周次连续无重复、覆盖至 2024-W46 或有明确缺口清单；回补量与 S1 预估一致

### S6 端到端自检 + 汇报
- 清空新增 CSV 重跑；确认不触碰 M2 文件
- 可操作核对输出：本次各源抓到的最新周次+抽样值+来源
- 汇报：3 个 CSV 路径+行数+抽样核对，停下等 M3a 验收与 M3b 决策

## 停靠点
S6 完成即停。用户验收"数据齐了"后进 M3b 展示层。

## 回滚
删 `data/sentinel_national_rates.csv`、`sentinel_rank.csv`、`flunet_china.csv`、`changes.log`、`src/fetch_sentinel.py`、`src/fetch_flunet.py`。M2 文件不受影响。

## 验收（对应 data-fetch prd + metis 消解）
- [ ] 3 个新 CSV 生成，schema 符合 design（长表/排序串/FluNet列映射）
- [ ] 与官网人工核对一致（哨点表1抽3病原、FluNet最新周）
- [ ] 并列排序正确存储；分页先验有明确结论
- [ ] r3 周级覆盖+changes.log 留痕；失败不覆盖成功周
- [ ] 不改动任何 M2 文件

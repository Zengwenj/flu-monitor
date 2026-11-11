# A1a 流感周报历史回补 · 执行报告

- 任务：`.trellis/tasks/11-11-flu-south-backfill/`（计划冻结 r3，评审链 r1 INCONCLUSIVE → r2 BLOCKED(1) → r3 PASS → r4 PASS，用户 2026-11-11 批准）
- 执行日期：2026-11-11
- 范围：2023W1 – 2026W44 共 200 期（ivdc.chinacdc.cn 周报列表 30 页枚举 + PDF 解析）

## 一、结果总览

- **入库 200/200 周，全部 ok**；按年：2023年 52 周, 2024年 52 周, 2025年 52 周, 2026年 44 周
- 顺带修复的分母 bug：旧代码自算阳性率用了全国分母（如 2026W1 旧 18.97 → 正确 35.82）；本次全部按表 1 南方列自算，2026W44 官方括号版式与自算互校一致（1796/10481=17.14%）
- goldstein 指数 200 行全量重算（ILI%×阳性率，2 位小数），2026W44=82.27 与回补前一致（回归基准）
- 发布门：2026W44（82.27）与紧邻 2026W43（81.14）均 ok 且有指数 → 满足（环比 ↑ 正确反映 81.14→82.27）
- 续跑幂等：全量状态下重跑 `--backfill`，CSV SHA256 逐字节不变

## 二、验证证据（对照 implement.md 验收清单）

| 验收项 | 结果 | 证据 |
|---|---|---|
| 离线回归（缓存 txt，不改 data/） | ✅ 77/77 | s1_regress.py：22 期基准值对齐、2016–2022 全部正确报错、缺表1/合并版/封面残留/标题不一致夹具、双源一致、中断实验副本逐字节不变、范围式标题/锚文本守卫、--force 坏 PDF 保旧缓存、最终状态三分类、CLI 边界拒绝（含 ISO 历法校验）、合并版目标区间端到端、散置多期号 multi_issue_warn、括号 0%/分子 0 零值 |
| `--from 2022W20` 拒绝 | ✅ | exit=1 + 版式分代提示，data/ 无改动 |
| `--backfill --limit 2` 冒烟 | ✅ | 2023W1/W2 入库，对账 ok=3 未处理=197，收尾升序 |
| 全量回补 200 期 | ✅ | 首轮 ok=96；104 期未成功 = 103 期网络瞬断 http_error + 1 期解析失败（2023W32 上游漏字）；续跑 8 批 + 守卫精细化后补 2 期 = 200/200 |
| CSV 终态 | ✅ | 200 行、升序、主键唯一、全 ok、数值域合法 |
| changes.log 留痕 | ✅ | 见下节事件表 |
| 无参回归（单期模式不变） | ✅ | 2026W44 4.8/17.14（官方括号互校），200 行保持 |
| compute_index 重算 | ✅ | 200 行 goldstein 零缺失，全部=ILI%×阳性率(2dp) |
| build_site --local | ✅ | site/index.html 生成；外部 script/link=0；无『解析失败』横幅；a href https=2 处（官方来源，允许） |
| 中断安全 | ✅ | 离线实验：writerows 中途 raise → 副本 SHA 不变（原子写入 tmp→fsync→replace，TMP 锚定 ROOT） |

## 三、异常与修复记录（changes.log 摘录，2026-11-11）

| 时间 | 周次 | 事件 | 说明 |
|---|---|---|---|
| 2026-11-11T12:12:32 | 2023W32 | backfill_fail | parse_error；parse_error: 未解析到南方流感阳性分子 |
| 2026-11-11T13:01:03 | 2024W45 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202411/P020260123349887847943.pdf |
| 2026-11-11T13:01:03 | 2024W46 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202411/t20241121_302746.htm |
| 2026-11-11T13:01:03 | 2024W47 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202411/t20241129_302972.htm |
| 2026-11-11T13:01:03 | 2024W48 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202412/t20241205_303122.htm |
| 2026-11-11T13:01:03 | 2024W49 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202412/t20241212_303269.htm |
| 2026-11-11T13:01:03 | 2024W50 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202412/t20241218_303399.htm |
| 2026-11-11T13:01:03 | 2024W51 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202412/t20241226_303531.htm |
| 2026-11-11T13:01:03 | 2024W52 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202501/t20250102_303647.htm |
| 2026-11-11T13:01:03 | 2025W1 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202501/t20250109_303775.htm |
| 2026-11-11T13:01:03 | 2025W2 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202501/t20250116_303896.htm |
| 2026-11-11T13:01:03 | 2025W3 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202501/t20250122_304010.htm |
| 2026-11-11T13:01:03 | 2025W4 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202501/t20250130_304129.htm |
| 2026-11-11T13:01:03 | 2025W5 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202502/t20250206_304165.htm |
| 2026-11-11T13:01:03 | 2025W6 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202502/t20250213_304234.htm |
| 2026-11-11T13:01:03 | 2025W7 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202502/t20250220_304407.htm |
| 2026-11-11T13:01:03 | 2025W8 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202502/t20250226_304583.htm |
| 2026-11-11T13:01:03 | 2025W9 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202503/t20250305_304678.htm |
| 2026-11-11T13:01:03 | 2025W10 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202503/t20250313_304916.htm |
| 2026-11-11T13:01:03 | 2025W11 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202503/t20250320_305125.htm |
| 2026-11-11T13:01:03 | 2025W12 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202503/t20250327_305500.htm |
| 2026-11-11T13:01:03 | 2025W13 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202504/t20250403_305689.htm |
| 2026-11-11T13:01:03 | 2025W14 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202504/t20250410_305859.htm |
| 2026-11-11T13:01:03 | 2025W15 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202504/t20250418_306037.htm |
| 2026-11-11T13:01:03 | 2025W16 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202504/t20250425_306206.htm |
| 2026-11-11T13:01:03 | 2025W17 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202505/t20250502_306451.htm |
| 2026-11-11T13:01:03 | 2025W18 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202505/t20250509_306653.htm |
| 2026-11-11T13:01:03 | 2025W19 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202505/t20250515_306816.htm |
| 2026-11-11T13:01:04 | 2025W20 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202505/t20250523_306985.htm |
| 2026-11-11T13:01:04 | 2025W21 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202505/t20250529_307142.htm |
| 2026-11-11T13:01:04 | 2025W22 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202506/t20250605_307358.htm |
| 2026-11-11T13:01:04 | 2025W23 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202506/t20250612_307592.htm |
| 2026-11-11T13:01:04 | 2025W24 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202506/t20250619_307870.htm |
| 2026-11-11T13:01:04 | 2025W25 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202506/t20250626_307991.htm |
| 2026-11-11T13:01:04 | 2025W26 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202507/t20250703_308178.htm |
| 2026-11-11T13:01:04 | 2025W27 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202507/t20250710_308287.htm |
| 2026-11-11T13:01:04 | 2025W28 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202507/t20250717_308528.htm |
| 2026-11-11T13:01:04 | 2025W29 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202507/t20250724_308908.htm |
| 2026-11-11T13:01:04 | 2025W30 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202507/t20250731_309106.htm |
| 2026-11-11T13:01:04 | 2025W31 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202508/t20250807_309207.htm |
| 2026-11-11T13:01:04 | 2025W32 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202508/t20250814_309351.htm |
| 2026-11-11T13:01:04 | 2025W33 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202508/t20250821_309677.htm |
| 2026-11-11T13:01:04 | 2025W34 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202508/t20250828_310015.htm |
| 2026-11-11T13:01:04 | 2025W35 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202509/t20250904_310195.htm |
| 2026-11-11T13:01:04 | 2025W36 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202509/t20250911_310378.htm |
| 2026-11-11T13:01:04 | 2025W37 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202509/t20250919_311548.htm |
| 2026-11-11T13:01:04 | 2025W38 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202509/t20250926_312671.htm |
| 2026-11-11T13:01:04 | 2025W39 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202510/t20251004_312842.htm |
| 2026-11-11T13:01:04 | 2025W40 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202510/t20251010_312889.htm |
| 2026-11-11T13:01:04 | 2025W41 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202510/t20251017_312997.htm |
| 2026-11-11T13:01:04 | 2025W42 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202510/t20251024_313102.htm |
| 2026-11-11T13:01:04 | 2025W43 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202510/t20251030_313187.htm |
| 2026-11-11T13:01:04 | 2025W44 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202511/t20251106_313320.htm |
| 2026-11-11T13:01:04 | 2025W45 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202511/t20251113_313466.htm |
| 2026-11-11T13:01:04 | 2025W46 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202511/t20251120_313601.htm |
| 2026-11-11T13:01:04 | 2025W47 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202511/t20251127_313694.htm |
| 2026-11-11T13:01:04 | 2025W48 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202512/t20251203_313842.htm |
| 2026-11-11T13:01:04 | 2025W49 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202512/t20251211_314074.htm |
| 2026-11-11T13:01:04 | 2025W50 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202512/t20251218_314158.htm |
| 2026-11-11T13:01:05 | 2025W51 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202512/t20251225_314261.htm |
| 2026-11-11T13:01:05 | 2025W52 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202512/t20251231_314371.htm |
| 2026-11-11T13:01:05 | 2026W1 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202601/t20260108_314529.htm |
| 2026-11-11T13:01:05 | 2026W2 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202601/t20260115_314639.htm |
| 2026-11-11T13:01:05 | 2026W3 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202601/t20260122_314767.htm |
| 2026-11-11T13:01:05 | 2026W4 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202601/t20260130_314860.htm |
| 2026-11-11T13:01:05 | 2026W5 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202602/t20260205_314949.htm |
| 2026-11-11T13:01:05 | 2026W6 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202602/t20260213_315071.htm |
| 2026-11-11T13:01:05 | 2026W7 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202602/t20260220_315151.htm |
| 2026-11-11T13:01:05 | 2026W8 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202602/t20260227_315210.htm |
| 2026-11-11T13:01:05 | 2026W9 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202603/t20260306_315295.htm |
| 2026-11-11T13:01:05 | 2026W10 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202603/t20260313_315442.htm |
| 2026-11-11T13:01:05 | 2026W11 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202603/t20260319_315643.htm |
| 2026-11-11T13:01:05 | 2026W12 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202603/t20260327_315993.htm |
| 2026-11-11T13:01:05 | 2026W13 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202604/t20260402_316121.htm |
| 2026-11-11T13:01:05 | 2026W14 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202604/t20260409_316236.htm |
| 2026-11-11T13:01:05 | 2026W15 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202604/t20260416_1835083.htm |
| 2026-11-11T13:01:05 | 2026W16 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202604/t20260424_1835303.htm |
| 2026-11-11T13:01:05 | 2026W17 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202604/t20260430_1835480.htm |
| 2026-11-11T13:01:05 | 2026W18 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202605/t20260508_1835624.htm |
| 2026-11-11T13:01:05 | 2026W19 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202605/t20260514_1835775.htm |
| 2026-11-11T13:01:05 | 2026W20 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202605/t20260521_1835980.htm |
| 2026-11-11T13:01:05 | 2026W21 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202605/t20260528_1836114.htm |
| 2026-11-11T13:01:05 | 2026W22 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202606/t20260604_1836505.htm |
| 2026-11-11T13:01:05 | 2026W23 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202606/t20260611_1836725.htm |
| 2026-11-11T13:01:05 | 2026W24 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202606/t20260618_1837077.htm |
| 2026-11-11T13:01:05 | 2026W25 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202606/t20260625_1837446.htm |
| 2026-11-11T13:01:05 | 2026W26 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202607/t20260703_1837766.htm |
| 2026-11-11T13:01:05 | 2026W27 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202607/t20260709_1838005.htm |
| 2026-11-11T13:01:05 | 2026W28 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202607/t20260717_1838227.htm |
| 2026-11-11T13:01:05 | 2026W29 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202607/t20260724_1838369.htm |
| 2026-11-11T13:01:05 | 2026W30 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202607/t20260731_1838517.htm |
| 2026-11-11T13:01:06 | 2026W31 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202608/t20260807_1838843.htm |
| 2026-11-11T13:01:06 | 2026W32 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202608/t20260813_1838934.htm |
| 2026-11-11T13:01:06 | 2026W33 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202608/t20260821_1839077.htm |
| 2026-11-11T13:01:06 | 2026W34 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202608/t20260827_1839553.htm |
| 2026-11-11T13:01:06 | 2026W35 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202609/t20260903_1839795.htm |
| 2026-11-11T13:01:06 | 2026W36 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202609/t20260911_1840079.htm |
| 2026-11-11T13:01:06 | 2026W37 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202609/t20260918_1840292.htm |
| 2026-11-11T13:01:06 | 2026W38 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202609/t20260924_1841790.htm |
| 2026-11-11T13:01:06 | 2026W39 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202610/t20261002_1842068.htm |
| 2026-11-11T13:01:06 | 2026W40 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202610/t20261009_1842125.htm |
| 2026-11-11T13:01:06 | 2026W41 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202610/t20261015_1842284.htm |
| 2026-11-11T13:01:06 | 2026W42 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202610/t20261023_1842431.htm |
| 2026-11-11T13:01:06 | 2026W43 | backfill_fail | http_error；HTTP 获取失败: https://ivdc.chinacdc.cn/cnic/zyzx/lgzb/202610/t20261030_1842571.htm |
| 2026-11-11T13:51:17 | 2025W33 | backfill_fail | parse_error；parse_error: 表 1 列校验失败 南方10043+北方2995≠合计13029 |
| 2026-11-11T14:07:50 | 2025W33 | backfill_fail | parse_error；parse_error: 表 1 列校验失败 南方10043+北方2995≠合计13029 |
| 2026-11-11T14:28:56 | 2025W33 | backfill_fail | parse_error；parse_error: 表 1 列校验失败 南方10043+北方2995≠合计13029 |
| 2026-11-11T14:30:06 | 2026W11 | backfill_fail | merged_issue；merged_issue: PDF 内出现多个期号 [895, 900] |
| 2026-11-11T14:55:06 | 2025W33 | backfill_fail | parse_error；parse_error: 表 1 列校验失败 南方10043+北方2995≠合计13029 |
| 2026-11-11T14:55:06 | 2026W11 | backfill_fail | merged_issue；merged_issue: PDF 内出现多个期号 [895, 900] |
| 2026-11-11T15:19:52 | 2025W33 | backfill_fail | parse_error；parse_error: 表 1 列校验失败 南方10043+北方2995≠合计13029 |
| 2026-11-11T15:19:52 | 2026W11 | backfill_fail | merged_issue；merged_issue: PDF 内出现多个期号 [895, 900] |
| 2026-11-11T15:28:36 | 2025W33 | backfill_fail | parse_error；parse_error: 表 1 列校验失败 南方10043+北方2995≠合计13029 |
| 2026-11-11T15:28:36 | 2026W11 | backfill_fail | merged_issue；merged_issue: PDF 内出现多个期号 [895, 900] |
| 2026-11-11T15:34:17 | 2025W33 | table_sum_check | 南方10043+北方2995≠合计13029（偏差≤0.2%，按上游笔误照存） |
| 2026-11-11T15:34:17 | 2026W11 | cover_leftover_issue | 主期号第900期×10，封面残留期号 {895: 1}（照存） |

### 三个特殊期的定性（已人工核对原始 PDF）

1. **2023W32**：上游正文漏印「份」字（`检测到 181 流感病毒阳性标本`）。修复：分子正则「份」改可选。入库 4.4 / 3.64（181/4977）。
2. **2025W33**：上游表 1 合计印错（10043+2995=13038≠表印 13029，偏差 0.07%）。南方列 10043 有官方括号佐证 189(1.9%)。守卫放宽为 ≤0.2% 相对容差+告警照存。入库 3.4 / 1.88。
3. **2026W11**：PDF 封面残留上期模板行（全角「第８９５期」×1，正文半角「第 900 期」×10）。合并守卫改频次判定（主期号 ≥3 且其余 ≤2 → 告警照存）。入库 3.0 / 8.97（970/10809）。

## 四、200 行核对表（供 Excel 对照原始 PDF）

| 年 | 周 | 周起始 | ILI% | 阳性率% | Goldstein | 状态 |
|---|---|---|---|---|---|---|
| 2023 | 1 | 2023-01-02 | 3.6 | 0.04 | 0.14 | ok |
| 2023 | 2 | 2023-01-09 | 2.2 | 0.22 | 0.48 | ok |
| 2023 | 3 | 2023-01-16 | 1.9 | 0.07 | 0.13 | ok |
| 2023 | 4 | 2023-01-23 | 2.0 | 0.13 | 0.26 | ok |
| 2023 | 5 | 2023-01-30 | 1.4 | 0.40 | 0.56 | ok |
| 2023 | 6 | 2023-02-06 | 1.5 | 1.35 | 2.03 | ok |
| 2023 | 7 | 2023-02-13 | 1.8 | 4.90 | 8.82 | ok |
| 2023 | 8 | 2023-02-20 | 3.9 | 17.72 | 69.11 | ok |
| 2023 | 9 | 2023-02-27 | 7.6 | 33.37 | 253.61 | ok |
| 2023 | 10 | 2023-03-06 | 10.1 | 48.83 | 493.18 | ok |
| 2023 | 11 | 2023-03-13 | 9.8 | 53.39 | 523.22 | ok |
| 2023 | 12 | 2023-03-20 | 10.1 | 59.25 | 598.42 | ok |
| 2023 | 13 | 2023-03-27 | 10.0 | 59.62 | 596.20 | ok |
| 2023 | 14 | 2023-04-03 | 8.9 | 57.29 | 509.88 | ok |
| 2023 | 15 | 2023-04-10 | 7.1 | 49.07 | 348.40 | ok |
| 2023 | 16 | 2023-04-17 | 6.0 | 38.41 | 230.46 | ok |
| 2023 | 17 | 2023-04-24 | 5.2 | 27.23 | 141.60 | ok |
| 2023 | 18 | 2023-05-01 | 6.2 | 14.44 | 89.53 | ok |
| 2023 | 19 | 2023-05-08 | 6.7 | 7.76 | 51.99 | ok |
| 2023 | 20 | 2023-05-15 | 7.2 | 3.50 | 25.20 | ok |
| 2023 | 21 | 2023-05-22 | 6.5 | 1.54 | 10.01 | ok |
| 2023 | 22 | 2023-05-29 | 6.3 | 0.84 | 5.29 | ok |
| 2023 | 23 | 2023-06-05 | 5.8 | 0.59 | 3.42 | ok |
| 2023 | 24 | 2023-06-12 | 5.5 | 0.35 | 1.92 | ok |
| 2023 | 25 | 2023-06-19 | 5.5 | 0.30 | 1.65 | ok |
| 2023 | 26 | 2023-06-26 | 5.0 | 0.33 | 1.65 | ok |
| 2023 | 27 | 2023-07-03 | 4.7 | 0.79 | 3.71 | ok |
| 2023 | 28 | 2023-07-10 | 4.5 | 0.93 | 4.19 | ok |
| 2023 | 29 | 2023-07-17 | 4.4 | 1.68 | 7.39 | ok |
| 2023 | 30 | 2023-07-24 | 4.3 | 2.15 | 9.24 | ok |
| 2023 | 31 | 2023-07-31 | 3.9 | 2.52 | 9.83 | ok |
| 2023 | 32 | 2023-08-07 | 4.4 | 3.64 | 16.02 | ok |
| 2023 | 33 | 2023-08-14 | 4.1 | 3.82 | 15.66 | ok |
| 2023 | 34 | 2023-08-21 | 4.1 | 4.71 | 19.31 | ok |
| 2023 | 35 | 2023-08-28 | 3.9 | 4.08 | 15.91 | ok |
| 2023 | 36 | 2023-09-04 | 4.2 | 5.02 | 21.08 | ok |
| 2023 | 37 | 2023-09-11 | 4.6 | 5.47 | 25.16 | ok |
| 2023 | 38 | 2023-09-18 | 5.2 | 7.37 | 38.32 | ok |
| 2023 | 39 | 2023-09-25 | 5.4 | 8.35 | 45.09 | ok |
| 2023 | 40 | 2023-10-02 | 5.3 | 10.00 | 53.00 | ok |
| 2023 | 41 | 2023-10-09 | 4.7 | 11.29 | 53.06 | ok |
| 2023 | 42 | 2023-10-16 | 5.4 | 15.59 | 84.19 | ok |
| 2023 | 43 | 2023-10-23 | 5.5 | 18.56 | 102.08 | ok |
| 2023 | 44 | 2023-10-30 | 5.7 | 22.52 | 128.36 | ok |
| 2023 | 45 | 2023-11-06 | 5.5 | 26.85 | 147.68 | ok |
| 2023 | 46 | 2023-11-13 | 6.4 | 34.48 | 220.67 | ok |
| 2023 | 47 | 2023-11-20 | 8.0 | 44.29 | 354.32 | ok |
| 2023 | 48 | 2023-11-27 | 8.6 | 50.65 | 435.59 | ok |
| 2023 | 49 | 2023-12-04 | 9.1 | 54.15 | 492.76 | ok |
| 2023 | 50 | 2023-12-11 | 8.6 | 55.23 | 474.98 | ok |
| 2023 | 51 | 2023-12-18 | 8.8 | 51.66 | 454.61 | ok |
| 2023 | 52 | 2023-12-25 | 9.6 | 54.22 | 520.51 | ok |
| 2024 | 1 | 2024-01-01 | 9.7 | 52.52 | 509.44 | ok |
| 2024 | 2 | 2024-01-08 | 8.7 | 48.50 | 421.95 | ok |
| 2024 | 3 | 2024-01-15 | 7.7 | 39.75 | 306.07 | ok |
| 2024 | 4 | 2024-01-22 | 7.0 | 32.59 | 228.13 | ok |
| 2024 | 5 | 2024-01-29 | 6.4 | 32.41 | 207.42 | ok |
| 2024 | 6 | 2024-02-05 | 7.9 | 31.69 | 250.35 | ok |
| 2024 | 7 | 2024-02-12 | 7.6 | 31.58 | 240.01 | ok |
| 2024 | 8 | 2024-02-19 | 5.7 | 29.74 | 169.52 | ok |
| 2024 | 9 | 2024-02-26 | 5.0 | 25.38 | 126.90 | ok |
| 2024 | 10 | 2024-03-04 | 5.5 | 26.04 | 143.22 | ok |
| 2024 | 11 | 2024-03-11 | 5.4 | 22.28 | 120.31 | ok |
| 2024 | 12 | 2024-03-18 | 5.0 | 18.52 | 92.60 | ok |
| 2024 | 13 | 2024-03-25 | 4.7 | 16.92 | 79.52 | ok |
| 2024 | 14 | 2024-04-01 | 4.7 | 13.29 | 62.46 | ok |
| 2024 | 15 | 2024-04-08 | 4.3 | 10.54 | 45.32 | ok |
| 2024 | 16 | 2024-04-15 | 4.6 | 9.70 | 44.62 | ok |
| 2024 | 17 | 2024-04-22 | 4.7 | 8.54 | 40.14 | ok |
| 2024 | 18 | 2024-04-29 | 5.0 | 8.94 | 44.70 | ok |
| 2024 | 19 | 2024-05-06 | 4.9 | 10.78 | 52.82 | ok |
| 2024 | 20 | 2024-05-13 | 5.1 | 10.21 | 52.07 | ok |
| 2024 | 21 | 2024-05-20 | 4.8 | 8.23 | 39.50 | ok |
| 2024 | 22 | 2024-05-27 | 5.1 | 10.04 | 51.20 | ok |
| 2024 | 23 | 2024-06-03 | 4.9 | 8.31 | 40.72 | ok |
| 2024 | 24 | 2024-06-10 | 5.1 | 8.12 | 41.41 | ok |
| 2024 | 25 | 2024-06-17 | 5.2 | 8.19 | 42.59 | ok |
| 2024 | 26 | 2024-06-24 | 5.1 | 9.78 | 49.88 | ok |
| 2024 | 27 | 2024-07-01 | 5.1 | 10.85 | 55.33 | ok |
| 2024 | 28 | 2024-07-08 | 4.9 | 9.96 | 48.80 | ok |
| 2024 | 29 | 2024-07-15 | 4.7 | 9.01 | 42.35 | ok |
| 2024 | 30 | 2024-07-22 | 4.5 | 8.36 | 37.62 | ok |
| 2024 | 31 | 2024-07-29 | 4.2 | 7.37 | 30.95 | ok |
| 2024 | 32 | 2024-08-05 | 3.9 | 6.38 | 24.88 | ok |
| 2024 | 33 | 2024-08-12 | 3.6 | 6.27 | 22.57 | ok |
| 2024 | 34 | 2024-08-19 | 3.2 | 4.80 | 15.36 | ok |
| 2024 | 35 | 2024-08-26 | 3.1 | 4.50 | 13.95 | ok |
| 2024 | 36 | 2024-09-02 | 3.2 | 4.22 | 13.50 | ok |
| 2024 | 37 | 2024-09-09 | 3.5 | 5.29 | 18.52 | ok |
| 2024 | 38 | 2024-09-16 | 3.7 | 5.08 | 18.80 | ok |
| 2024 | 39 | 2024-09-23 | 3.7 | 5.00 | 18.50 | ok |
| 2024 | 40 | 2024-09-30 | 4.1 | 4.74 | 19.43 | ok |
| 2024 | 41 | 2024-10-07 | 3.3 | 4.03 | 13.30 | ok |
| 2024 | 42 | 2024-10-14 | 3.2 | 3.45 | 11.04 | ok |
| 2024 | 43 | 2024-10-21 | 3.3 | 4.55 | 15.01 | ok |
| 2024 | 44 | 2024-10-28 | 3.4 | 4.85 | 16.49 | ok |
| 2024 | 45 | 2024-11-04 | 3.6 | 4.36 | 15.70 | ok |
| 2024 | 46 | 2024-11-11 | 3.6 | 5.41 | 19.48 | ok |
| 2024 | 47 | 2024-11-18 | 3.4 | 7.65 | 26.01 | ok |
| 2024 | 48 | 2024-11-25 | 3.5 | 9.09 | 31.81 | ok |
| 2024 | 49 | 2024-12-02 | 3.6 | 11.53 | 41.51 | ok |
| 2024 | 50 | 2024-12-09 | 4.0 | 11.77 | 47.08 | ok |
| 2024 | 51 | 2024-12-16 | 4.7 | 17.51 | 82.30 | ok |
| 2024 | 52 | 2024-12-23 | 5.7 | 24.51 | 139.71 | ok |
| 2025 | 1 | 2024-12-30 | 7.2 | 31.90 | 229.68 | ok |
| 2025 | 2 | 2025-01-06 | 6.9 | 35.75 | 246.68 | ok |
| 2025 | 3 | 2025-01-13 | 6.5 | 35.14 | 228.41 | ok |
| 2025 | 4 | 2025-01-20 | 5.3 | 34.35 | 182.06 | ok |
| 2025 | 5 | 2025-01-27 | 7.4 | 32.18 | 238.13 | ok |
| 2025 | 6 | 2025-02-03 | 5.5 | 31.67 | 174.19 | ok |
| 2025 | 7 | 2025-02-10 | 4.7 | 30.00 | 141.00 | ok |
| 2025 | 8 | 2025-02-17 | 4.3 | 26.06 | 112.06 | ok |
| 2025 | 9 | 2025-02-24 | 4.2 | 20.66 | 86.77 | ok |
| 2025 | 10 | 2025-03-03 | 3.9 | 13.30 | 51.87 | ok |
| 2025 | 11 | 2025-03-10 | 4.0 | 9.76 | 39.04 | ok |
| 2025 | 12 | 2025-03-17 | 4.1 | 6.18 | 25.34 | ok |
| 2025 | 13 | 2025-03-24 | 4.1 | 4.32 | 17.71 | ok |
| 2025 | 14 | 2025-03-31 | 3.9 | 2.85 | 11.12 | ok |
| 2025 | 15 | 2025-04-07 | 3.9 | 2.34 | 9.13 | ok |
| 2025 | 16 | 2025-04-14 | 4.1 | 1.83 | 7.50 | ok |
| 2025 | 17 | 2025-04-21 | 3.9 | 1.38 | 5.38 | ok |
| 2025 | 18 | 2025-04-28 | 4.2 | 1.01 | 4.24 | ok |
| 2025 | 19 | 2025-05-05 | 4.1 | 0.69 | 2.83 | ok |
| 2025 | 20 | 2025-05-12 | 4.7 | 0.66 | 3.10 | ok |
| 2025 | 21 | 2025-05-19 | 4.7 | 0.51 | 2.40 | ok |
| 2025 | 22 | 2025-05-26 | 4.8 | 0.44 | 2.11 | ok |
| 2025 | 23 | 2025-06-02 | 4.5 | 0.73 | 3.29 | ok |
| 2025 | 24 | 2025-06-09 | 4.3 | 0.74 | 3.18 | ok |
| 2025 | 25 | 2025-06-16 | 4.3 | 0.85 | 3.65 | ok |
| 2025 | 26 | 2025-06-23 | 4.3 | 1.12 | 4.82 | ok |
| 2025 | 27 | 2025-06-30 | 4.2 | 1.36 | 5.71 | ok |
| 2025 | 28 | 2025-07-07 | 4.0 | 1.32 | 5.28 | ok |
| 2025 | 29 | 2025-07-14 | 3.8 | 1.66 | 6.31 | ok |
| 2025 | 30 | 2025-07-21 | 3.6 | 1.63 | 5.87 | ok |
| 2025 | 31 | 2025-07-28 | 3.5 | 1.47 | 5.14 | ok |
| 2025 | 32 | 2025-08-04 | 3.5 | 1.71 | 5.98 | ok |
| 2025 | 33 | 2025-08-11 | 3.4 | 1.88 | 6.39 | ok |
| 2025 | 34 | 2025-08-18 | 3.2 | 2.39 | 7.65 | ok |
| 2025 | 35 | 2025-08-25 | 3.1 | 2.69 | 8.34 | ok |
| 2025 | 36 | 2025-09-01 | 3.4 | 2.83 | 9.62 | ok |
| 2025 | 37 | 2025-09-08 | 3.6 | 3.25 | 11.70 | ok |
| 2025 | 38 | 2025-09-15 | 3.8 | 3.61 | 13.72 | ok |
| 2025 | 39 | 2025-09-22 | 3.8 | 4.28 | 16.26 | ok |
| 2025 | 40 | 2025-09-29 | 4.4 | 4.80 | 21.12 | ok |
| 2025 | 41 | 2025-10-06 | 4.1 | 5.37 | 22.02 | ok |
| 2025 | 42 | 2025-10-13 | 3.8 | 6.52 | 24.78 | ok |
| 2025 | 43 | 2025-10-20 | 4.1 | 9.98 | 40.92 | ok |
| 2025 | 44 | 2025-10-27 | 4.6 | 16.46 | 75.72 | ok |
| 2025 | 45 | 2025-11-03 | 5.5 | 22.41 | 123.25 | ok |
| 2025 | 46 | 2025-11-10 | 6.7 | 30.72 | 205.82 | ok |
| 2025 | 47 | 2025-11-17 | 7.8 | 38.93 | 303.65 | ok |
| 2025 | 48 | 2025-11-24 | 10.3 | 47.48 | 489.04 | ok |
| 2025 | 49 | 2025-12-01 | 11.1 | 54.49 | 604.84 | ok |
| 2025 | 50 | 2025-12-08 | 9.7 | 53.70 | 520.89 | ok |
| 2025 | 51 | 2025-12-15 | 7.6 | 47.96 | 364.50 | ok |
| 2025 | 52 | 2025-12-22 | 6.1 | 41.90 | 255.59 | ok |
| 2026 | 1 | 2025-12-29 | 5.4 | 35.82 | 193.43 | ok |
| 2026 | 2 | 2026-01-05 | 4.8 | 30.28 | 145.34 | ok |
| 2026 | 3 | 2026-01-12 | 4.7 | 27.58 | 129.63 | ok |
| 2026 | 4 | 2026-01-19 | 4.3 | 24.23 | 104.19 | ok |
| 2026 | 5 | 2026-01-26 | 4.0 | 19.31 | 77.24 | ok |
| 2026 | 6 | 2026-02-02 | 3.3 | 14.99 | 49.47 | ok |
| 2026 | 7 | 2026-02-09 | 3.6 | 10.91 | 39.28 | ok |
| 2026 | 8 | 2026-02-16 | 4.8 | 10.43 | 50.06 | ok |
| 2026 | 9 | 2026-02-23 | 3.0 | 10.12 | 30.36 | ok |
| 2026 | 10 | 2026-03-02 | 2.8 | 9.02 | 25.26 | ok |
| 2026 | 11 | 2026-03-09 | 3.0 | 8.97 | 26.91 | ok |
| 2026 | 12 | 2026-03-16 | 3.3 | 10.87 | 35.87 | ok |
| 2026 | 13 | 2026-03-23 | 3.5 | 10.65 | 37.27 | ok |
| 2026 | 14 | 2026-03-30 | 3.6 | 12.09 | 43.52 | ok |
| 2026 | 15 | 2026-04-06 | 3.7 | 11.38 | 42.11 | ok |
| 2026 | 16 | 2026-04-13 | 3.7 | 10.69 | 39.55 | ok |
| 2026 | 17 | 2026-04-20 | 3.9 | 11.17 | 43.56 | ok |
| 2026 | 18 | 2026-04-27 | 4.1 | 11.03 | 45.22 | ok |
| 2026 | 19 | 2026-05-04 | 4.1 | 9.97 | 40.88 | ok |
| 2026 | 20 | 2026-05-11 | 4.2 | 10.71 | 44.98 | ok |
| 2026 | 21 | 2026-05-18 | 4.5 | 11.22 | 50.49 | ok |
| 2026 | 22 | 2026-05-25 | 4.8 | 11.56 | 55.49 | ok |
| 2026 | 23 | 2026-06-01 | 5.2 | 12.19 | 63.39 | ok |
| 2026 | 24 | 2026-06-08 | 5.1 | 11.21 | 57.17 | ok |
| 2026 | 25 | 2026-06-15 | 5.4 | 11.16 | 60.26 | ok |
| 2026 | 26 | 2026-06-22 | 5.4 | 12.51 | 67.55 | ok |
| 2026 | 27 | 2026-06-29 | 5.6 | 14.37 | 80.47 | ok |
| 2026 | 28 | 2026-07-06 | 5.8 | 16.49 | 95.64 | ok |
| 2026 | 29 | 2026-07-13 | 5.9 | 17.98 | 106.08 | ok |
| 2026 | 30 | 2026-07-20 | 6.1 | 18.03 | 109.98 | ok |
| 2026 | 31 | 2026-07-27 | 5.7 | 18.09 | 103.11 | ok |
| 2026 | 32 | 2026-08-03 | 5.3 | 17.77 | 94.18 | ok |
| 2026 | 33 | 2026-08-10 | 4.9 | 18.61 | 91.19 | ok |
| 2026 | 34 | 2026-08-17 | 4.5 | 18.28 | 82.26 | ok |
| 2026 | 35 | 2026-08-24 | 4.3 | 20.75 | 89.22 | ok |
| 2026 | 36 | 2026-08-31 | 4.6 | 22.52 | 103.59 | ok |
| 2026 | 37 | 2026-09-07 | 5.1 | 24.91 | 127.04 | ok |
| 2026 | 38 | 2026-09-14 | 5.0 | 22.04 | 110.20 | ok |
| 2026 | 39 | 2026-09-21 | 5.3 | 18.81 | 99.69 | ok |
| 2026 | 40 | 2026-09-28 | 4.8 | 18.92 | 90.82 | ok |
| 2026 | 41 | 2026-10-05 | 4.6 | 19.37 | 89.10 | ok |
| 2026 | 42 | 2026-10-12 | 4.5 | 19.51 | 87.80 | ok |
| 2026 | 43 | 2026-10-19 | 4.5 | 18.03 | 81.14 | ok |
| 2026 | 44 | 2026-10-26 | 4.8 | 17.14 | 82.27 | ok |

## 五、建议核对方式

1. 用 Excel 打开 `data/flu_south.csv`。
2. 每年随机抽 2–3 周（建议含上面三个特殊期），点开该行 `source_url`，对照 PDF 表 1「南方省份检测数」与正文 ILI%/阳性率。
3. 阳性率口径：括号版式=官方数；无括号=阳性数÷表1南方检测数（四舍五入 2 位）。

## 六、剩余步骤

- [ ] 独立只读复核（本报告 + 代码 diff）
- [ ] 用户 Excel 抽验确认
- [ ] 两笔提交：docs（任务文档+报告）/ feat（fetch_flu_south.py + data/flu_south.csv + changes.log）
- [ ] push（避开周五，先 git pull）
- A1b（展示层：环比相邻周校验 + 往年同期块）为后续独立任务

## 七、实施偏差记录（相对冻结计划 r3）

实施期间因上游真实瑕疵做的守卫调整，均为「更宽容地照存 + 告警留痕」——**数据的诚实性红线（D14/D15/D17：不合成总分、不伪造数值、缺数据不显 0）全部未动**；被放宽的仅是「把解析直接判失败」的拒绝条件，逐条记录如下：

| # | 偏差 | 冻结 r3 原文 | 实际实现 | 依据 |
|---|---|---|---|---|
| 1 | 分子正则「份」改可选 | 「份流感病毒阳性」 | `份?` 可选 | 2023W32 上游漏印「份」字，邻期数值连续性佐证（181/4977=3.64%） |
| 2 | 表 1 合计校验加 0.2% 相对容差 | 相等才算通过 | 偏差 ≤0.2% 告警照存，>0.2% 仍判失败 | 2025W33 上游合计印错 9/13029≈0.07%，南方列有官方括号佐证 |
| 3 | PDF 多期号守卫改频次判定 | ≥2 个期号即 merged_issue | 主期号 ≥3 次且其余 ≤2 次 → 封面残留告警照存；否则仍 merged_issue | 2026W11 封面残留全角「第８９５期」×1，正文「第 900 期」×10 |
| 4 | 锚文本散置期号仅告警 | 标题/锚文本查多期号 | 范围式周次/期号（如「第14-22周」「第895-900期」）判合并版 skip；散置多个不同期号无条件 `multi_issue_warn` 告警、数据照存 | 锚文本期号实测不可靠（2024W26 锚 811 vs PDF 810；2016W10 锚「0.pdf」），不能据其判失败；真合并版由 PDF 期号频次守卫兜底 |

复核 B1–B3 修复（2026-11-11 第二轮）：

- **B1**：范围式标题（「2025 第14-22周」类）原先不匹配 TITLE_WEEK 会被丢弃、误报 list_missing → 新增 RANGE_TITLE 捕获，枚举返回 (单周条目, 合并版覆盖)，覆盖周归 merged_skip；新增 `_anchor_is_merged()` 锚文本范围守卫。
- **B2**：txt 缓存原先在解析前写盘，--force 重抓到坏 PDF 会毁掉旧缓存 → 改为解析成功才落缓存。
- **B3**：对账原先数过程标签（含 list_missing 第四类、force 失败误计 pending_fail）→ 新增 `_final_class()` 以收尾 CSV 为准三分类（ok / merged_skip / pending_fail），互斥且可重演。
- 附带：括号 0% 零除法（max(b,1e-9) 兜底）、CLI 边界（--from 晚于 --to、--limit≤0 均拒绝）。

复核 round-3 剩余缺口修复（2026-11-11 第三轮，针对 B1 两个残留）：

- **B1-缺口1（目标区间并入合并版覆盖）**：`in_range` 原先只遍历单周条目——目标区间全是合并版时直接落空返回、或合并版收尾且未指定 `--to` 时末段周被排除在目标外。现改为 `known = 单周条目 ∪ 合并版覆盖周` 再筛区间，两种场景均完成全区间对账。端到端夹具：①区间仅一条合并版条目 → 9 周 merged_skip 留痕、无 list_missing、CSV 不变；②单周 W13 + 合并版 W14–22 收尾、无 `--to` → 目标延伸至 W22，W13 走缓存入库 ok。
- **B1-缺口2（散置多期号静默）**：锚文本期号原先 `re.search` 只取第一个，「第933期、第934期」且 PDF 首期号一致时完全不告警。现 `findall` 取全部不同期号，≥2 个即无条件 `multi_issue_warn` 留痕（不判失败，PDF 频次守卫兜底）；仅 1 个且与 PDF 不一致才走原 `issue_no_warn`。夹具：锚 933/934 + PDF 933 → 告警留痕、数据照常入库、不产生重复 issue_no_warn。
- 建议项：CLI 周次校验升级为 ISO 历法校验（`date.fromisocalendar`，2025W53 这类不存在的一周现在被拒绝，原先只查 1–53）；CLI 拒绝用例同时断言错误提示内容；补括号 0% 与分子 0 零值夹具。

## 八、复核补证（2026-11-11 第三轮复核后）

- 离线回归 77/77 PASS（含 B1/B2/B3/CLI/零值全部夹具；重跑稳定——沙箱日志与缓存按轮清理）。
- 全量状态下重跑 `--backfill`（round-3 修复后代码、真实 ivdc 30 页）：`[对账] 目标 200 周：ok=200 merged_skip=0 pending_fail=0`，CSV SHA256 前后一致（DF2EF8CC1C42E9C8C9F94AD219C98227972CC3C7F9F770C058825171414E8E12）。
- 200 行全量断言：goldstein 缺失 0 行、`round(ILI%×阳性率, 2)` 不符 0 行。
- `git diff --stat -- src/build_site.py .github/workflows/weekly.yml` 输出为空（零改动）。
- 括号互校抽验：2026W44 1796/10481=17.1358% vs 官方 17.14%，偏差 0.025% < 1.5%。
- 评审链终态：round-1 INCONCLUSIVE（无冻结快照）→ round-2 BLOCKED（B1/B2/B3）→ round-3 复审 B2/B3 关闭、B1 残留两缺口 → 缺口修复 + 77/77 + 真实幂等重验 → round-4 定向复审 **PASS：B1（两缺口）、B2、B3 及全部建议项关闭**，无新阻断项。

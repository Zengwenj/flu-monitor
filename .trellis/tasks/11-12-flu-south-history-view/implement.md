# A1b 实施与验证计划

状态：待成稿评审与用户批准；本文件是将来步骤，不是已执行记录。

## 门与所有权

1. 计划前gap咨询已完成，证据见research/gap-analysis.md；视觉方案由designer咨询并补齐。
2. 主会话冻结 PRD/design/implement 为单一快照并记录SHA256，按review-1交plan-critic正式审核，默认最多两轮。不边审核边改快照。
3. PASS后仍须用户批准实施。当前task.json保持planning，不运行start，不提交推送部署。
4. 实施时主会话负责规范化/环比/模板接线；designer负责图表/局部CSS实现与聚焦视觉检查。二者同属src/build_site.py，必须串行写：主会话完成数据契约后停止写入，designer完成渲染后主会话只核对文案与接线。不得并行改该文件。
5. 最终验证由一个general测试执行专员负责整合命令及证据；独立只读复核另交oracle，不让写作者自批。用户负责最终显示验收。未实施前不派这些执行任务。

## S0 基线及可复现验证准备（批准后）

- 检查git状态保护既有改动，运行task.py validate后start。
- 在本任务validation/新增check_history.py，标准库unittest/importlib/tempfile，不依赖pytest。测试夹具全部写临时目录，mock FLU_CSV/SC_CSV/RUN_STATUS/OUT 并恢复；绝不在真实CSV中注入坏数据。
- 脚本提供 --capture-baseline 和 --check 参数。capture在改功能前保存 src/build_site.py/compute_index.py 的副本、全国trend_block/ranking_block/child_block/sichuan_block/run_banner两个模式输出、真实CSV与data所有文件SHA256，写 .tmp_a1b/baseline/。固定同一输入和日期；若日期或数据变动，基线副本在相同固定输入上重跑，不能把输入变化误判为回归或豁免差异。
- 可复现性：capture必须在基线commit a94591753f763351cb095fd3a813cfa69607ac1b的build_site上完成并记录hash；后续无需基线缓存时可只读 git show 此commit源码导入到隔离临时模块，不覆盖工作区。检查报告注明基线版本。
- 探查可用浏览器测试能力；Python playwright当前未安装。现有工具不能截图时，保留人工方案，不擅自安装。

预定命令（脚本将在实施时创建）：
```
python -X utf8 .trellis/tasks/11-12-flu-south-history-view/validation/check_history.py --capture-baseline
```

## S1 数据契约与环比（主会话）

- 依design §2构造共享内存视图；先写下面数据夹具使旧行为失败，再实现规范化与flu_block改造。
- 最新ok键先定锚，再检查数值；禁止用过滤后的最后有效点静默替代异常锚周。
- 精确ISO前一周比较，零有效、非有限无效；移除yoy固定标签并处理目标南方卡历史失败误横幅。保留run_banner及全国共享helper。
- 聚焦执行数据/环比测试组，记录命令和失败/通过数量。此阶段不得宣称页面完成。

## S2 图表及模板（designer串行写）

- 按design §4–5实现专用SVG/表格，不修改全国sparkline。
- 同年周差1分段、单点形状、全年历史与锚周灰区、1–53横轴、统一nice刻度、各年同周表、异常/不足态。
- 仅替换占位卡和流感目标文案；新CSS限作用域、双花括号；动态文字/URL安全转义。
- designer聚焦可视化/局部HTML检查，交回后主会话核文案/范围，不自行改视觉设计。

## S3 最终验证矩阵（单一验证owner整合执行）

| 组 | 输入/关键断言 |
|---|---|
| D1 周键与重复 | 乱序结果相同；非法ISO年周忽略且有计数；2025W53拒绝/2026W53有效；相同值重复合一点；冲突及混入坏成功行整周异常；失败不覆盖同周成功 |
| D2 数值 | 空/非数字/NaN/+Inf/-Inf/负值/百分数>100拒绝；0和0.00有效；最新ok坏值仍锚最新、不得回退；坏元数据不让有效指数消失但明确提示 |
| M 环比 | W44与W43为↑、↓、→三例；W44缺W43有W42不比较；W1准确找到上年W52或W53；W51跳W1不比较；上一周异常与缺失文案区分；比较不依赖CSV行序 |
| H 历史 | 数据锚2025时不随电脑2026变化；仅Y及前三自然年，不补更远年；无历史/单年/空集/全失败/锚年坏值有历史点；53周年对无53周年提示；未发布区不算内部缺口 |
| G 图形 | 单点可见；内部缺周不跨越连线；真零贴底、全零top10；604.84时top800；x固定1–53；锚周W1/W53标签不越界；多年度共用坐标而非各自缩放 |
| T 表格 | 4行W44与真实CSV全部字段对应；每项缺失有文字；ISO周起不一致注明；文本含<、&、引号正确转义；javascript/data URL不成链接，合法官方链接保留 |
| R 回归 | baseline的全国3函数/四川输出不变；_adjacent_week/svg_sparkline/trend_block源码及输出不变；run_banner本地忽略状态、云端failed/skipped有横幅；旧历史fail不伪报最新、晚于锚周失败仍提示 |
| E 端到端 | render只写隔离OUT；真实本地build成功；所有data文件SHA256不变；无script/fetch/外部加载资源（HTMLParser+CSS url/@import检查，允许a href）；真实200周无旧占位 |

真实数据基准（若实施前数据增加，固定此200行快照测试与实时数据测试分开）：2023/24/25各52点、2026有44点；2026W44=82.27，2025=75.72，2024=16.49，2023=128.36；上一周2026W43=81.14，环比↑；最大604.84。

最终命令由测试owner一次执行并报告exact command/exit/log，不以子代理一句通过替代证据：
```
python -X utf8 .trellis/tasks/11-12-flu-south-history-view/validation/check_history.py --check
python -X utf8 src/build_site.py --local
git diff --check
git diff --stat
```
日志写 .tmp_a1b/validation/，摘要及证据路径写 research/validation-report.md；后续代码更改使受影响检查失效，针对性重验，不无理由重跑全套。

## S4 浏览器与独立复核

- 浏览器以file://打开site/index.html，320/360/1024宽各截图存.tmp_a1b/screenshots/，核对图例、轴、W44近重合标记、全零夹具、表容器滚动而页面不横滚、键盘聚焦与来源链接可读。自动化读取documentElement.scrollWidth≤clientWidth，同时人工目视，不只看DOM。
- 若现有浏览器工具不可用：明确视觉验收未完成，请用户双击site/index.html；浏览器F12→设备工具栏→宽320与360分别截图，桌面正常窗截图，左右滑动表格并用Tab进入滚动区。用户不能完成则停在待验，不声称通过。
- 独立只读oracle核对实际diff、矩阵结果及截图，区分已验证与建议；有客观缺口修复后仅重验受影响项。
- 用户验收整页和同周表后才进入提交发布；如果需要修改已批准展示目标，重新确认范围。

## S5 文档、提交与回滚

- 更新本任务进度、实际验证报告和README必要使用说明（只解释新增卡片，不无关重写；README作为收尾文档写域）。任务归档按Trellis流程，先确认描述/验证齐全。
- 继承项目约定：docs与feat分笔提交，推送前pull整合bot数据。若远端更新data，重新以新输入构建与关键实时断言，保留固定夹具测试。未解决冲突不强推。
- 当前请求仅规划，后续提交/推送/部署需在实施批准及收尾确认的范围内，不能凭本文件自动发布。
- 回滚仅撤销本任务代码变更并重建site，保留CSV及其他用户工作；不reset --hard、不清空工作区。

## 验收停止条件

数据/环比/视觉/离线与回归全部有有效证据、独立复核无未关闭阻断、用户确认后才称实施完成。缺浏览器证据、对照数据不一致、最新周异常或越界改动必须明示状态，不能以生成HTML成功替代。

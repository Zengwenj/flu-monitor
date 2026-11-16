# A2 正式计划审核 round 1

- review_kind=plan; mode=formal; protocol_version=review-1
- reviewer_session=ses_e31450065ffe16VKVZZspiR3hh
- plan_path=D:/FluMonitor/.trellis/tasks/11-12-regional-monitor/research/plan-freeze-r1.md
- expected_digest=cb761b30bbc636b87512bdf054d3fe66a2c9bb436daab75978887261e20b62e9
- result=BLOCKED；完整只读核查，两次可见快照一致；原始字节hash由主会话见证，审核者未独立计算。

## 阻断及主会话核验

### A2-LEGACY-WRITE-PROTECTION

计划引入超时终止但未保护旧采集器整表写入。主会话直接读取确认：src/fetch_sentinel.py:263-268直接w写，:298/:313分别写两张表；src/fetch_flunet.py:83-87直接w写。终止在截断窗口可能损坏权威存储，失败横幅不能恢复历史。

r2修订：design §4、implement S1/C1及写域加入两旧脚本保存边界原子化，不改解析/22行守卫。逐文件提交，不要求两张哨点表事务；第一表已提交、第二表未提交时保留各自完整版本，卡片按实际周次显示。获批实施后用真实子进程屏障+强杀实验验证，不用普通异常代替硬终止。

### A2-A1B-VALIDATION-ENTRY

原命令缺--check；归档check_history.py:30的parents[4]指向.trellis/tasks，非仓库根；:88-118要求旧run_banner源码/输出相等，与新状态设计矛盾；:544-562从实时CSV取锚周却硬断言W44。主会话读取上述位置并AST列出49个测试方法确认。

r2修订：本任务新增计划内check_history_compat.py --check入口，向上找仓库标志定位ROOT；不改归档。S0/S5明确逐ID映射，Reg状态断言按有意新契约替代，T固定W44夹具与实时检查分离，E适配五页隔离输出，其余行为全保留。实施前只安排，不宣称测试已运行。

## 建议项

- A2-TEMP-STAGING-GUARD：finally不保证硬终止清理。r2明确目标父目录/.tmp_writes/唯一暂存，沿用.tmp_*/忽略，并用临时git仓库检验git add data/不会收暂存残留。
- A2-DEPENDENCY-MANIFEST：r2快照追加A1b实际验证脚本、fetch_sentinel.py、fetch_flunet.py及.gitignore路径/hash。

## 边界

评审未联网、未运行抓取/测试/构建/部署。来源历史/条款和境外runner仍按S0停靠。r2修订是否关闭由第二轮确认；本记录不代替复审，不授予实施/提交/发布权限。

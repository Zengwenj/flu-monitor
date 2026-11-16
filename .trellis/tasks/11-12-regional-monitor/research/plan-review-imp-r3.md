# A2 实施复核 round-3（定向关闭确认）

- 评审人：oracle ses_e2d5cda0bffehWejGKwPfsXI0I；review_kind=implementation；mode=advisory；round=3；review_scope=closure-only；protocol_version=review-1
- 用户授权：round-3 为协议两轮上限外的追加轮（Question 卡片确认「派一轮定向关闭确认」）
- 结论：**BLOCKED**。CLOSED：IMP-03、05、06、07、13。NOT-CLOSED：IMP-01、04、08、09、11、12、14。

## NOT-CLOSED 明细（含关闭条件）

1. **IMP-01** 双恢复者竞态：复读锁(:109)与 unlink(:112) 非原子——A 复读一致后暂停，B 删旧锁取新锁，A 恢复删掉 B 的新锁。R4 未测交错与空锁+force。关闭=强制恢复与取得锁同一互斥协议（或取消自动删锁改人工），同步屏障验证两恢复者不能同时进入。
2. **IMP-04** 显式状态校验只做了 run_id 一个分支（:1251 仅 dict+schema==2 时拒错 run_id）：schema=1/{} 绕过；origin 未验；坏 JSON 显式输入当提示状态继续构建而非拒绝。关闭=显式状态须完整满足 v2+run_id+origin+结构；补 schema/origin/坏结构拒绝测试。
3. **IMP-08 + NEW-BY-FIX** 最新候选失败回退旧周：errors 收集后丢弃（:438），只从成功集合取 max 周（:451-459）——标题 W46 失败+不可解析标题 W45 成功 → 写 W45 报成功；同周一败一成也忽略失败者。关闭=先定目标周；不能排除属于目标周或更新周的候选失败时整期失败保全；补两组不写入断言。
4. **IMP-09** 分页终点仍按长度判断（:647 无 news1 且 <200 字符=正常终点）——Bad Gateway/Access denied 同样短。:567 解包先于 None 检查未落实。关闭=短错误响应按失败处理；仅明确终点证据或已验证日期边界停止；补短错误页/缺正文/最新失败周测试。
5. **IMP-11** `--result-file --force` 会把 `--force` 当文件名（:895 只查空/到尾）；结果文件仍总含两产品（:981）。关闭=缺值且下一 token 是选项时联网前拒绝；输出只含请求产品；补离线断言。
6. **IMP-12** pdf_url 只查键存在：legacy 补建 meta pdf_url="" 后被当完整缓存永久复用（:624）；坏 JSON meta 静默跳过不留痕（:588）；D3_05 E 场景反而断言了这种零请求复用（check_regional.py:1072）。关闭=区分一次性旧缓存与完整绑定（pdf_url 须有效 http）；坏 meta 留痕；补空/非法 PDF URL、坏 metadata、force 失败保全测试。
7. **IMP-14** 矩阵缺口：D3_01 未调用 read_result/manifest CLI 新分支；R4 无两恢复者交错与空锁+force；R3 无最终状态写失败关 gate 断言；E2 无生成阶段/os.replace 失败整链；缺 B2 仅标本数修订留痕断言及本轮残余场景。关闭=在既有隔离测试补齐具体场景。

## CLOSED 项佐证（round-3 已核）
- IMP-03：write_run_status.py:60（顶层 dict 校验+schema/run_id/stage/origin）、:326（manifest 四重）、:48（step 类型）。
- IMP-05：run_pipeline.py:317（预聚合失败不构建/site_ready=false/return 2）、:350（最终成功才开门）；check_regional.py:1157。
- IMP-06：build_site.py:1283（唯一暂存目录）、:1307（全校验后替换）、:1328（单双引号 href）；E2 真实 render 保旧页。
- IMP-07：build_site.py:809/820（占位参与锚周）、:835（同周冲突）、:847（逐组链接）、:854（工具侧文案）；U5×3。非阻塞：来源"表2/表3"可收尾改"表2"。
- IMP-13：fetch_heilongjiang.py:370 签名含 sample_count/total_samples；尚缺仅标本数变化专项断言（归 IMP-14）。

## 采信
77 项测试通过（run_regional6.log:89）、管线冒烟 build_exit=0/pipeline_exit=1/site_ready=true（pipeline_smoke.log:934）等主会话见证记录。

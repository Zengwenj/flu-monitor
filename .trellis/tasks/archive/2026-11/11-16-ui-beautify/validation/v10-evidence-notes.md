# V10 复核补充证据说明

> **2026-11-17 用户裁定**：栅格偏离经用户问题卡裁定「**保留现在的并列布局**」——冻结计划 §5.1 的「12 / 5+7 / 5+7 / 12」被正式放弃，当前实现的三行 7+5 并列布局获得用户批准。授权缺口关闭（裁定记录：本会话 m01189 问题卡）。

回应 oracle（ses_e1ad935cdffeP3qP45JWvitqaK）INCONCLUSIVE 的三处「未能核实」与一条 MAJOR + 一条 ADVISORY。

## 1. [MAJOR] probe_style.py 未读 SVG fill —— 已修，V7 已重跑

oracle 指出 `.tmp_a4/probe_style.py:77-85` 用 `getComputedStyle(el).color` 作所有文本前景，且无 `--selftest`。属实，原实现无法证明 SVG 文本对比度。

修复内容：
- 采集器判定 SVG 命名空间（`el.namespaceURI` 含 `svg` 或 `el.closest('svg')` 命中）后改读 `cs.fill`，记录 `fgsrc: color|fill`；`fill` 为 `none`（alpha=0）时标 `fill-none` 并排除出对比度统计（不绘制即不构成可读性问题）。
- 新增 `--selftest`：内嵌页面两段 `<svg><text>`，同为继承 `color:#000`、`fill` 分别为 `#000000` / `#767676`，断言两者测得不同对比度且分别约为 21.0 / 4.54，否则探针判坏、V7 无效。
- 顺带修 `cls` 采集：SVG 元素 `className` 是 `SVGAnimatedString`，原先输出 `[object SVGAnimatedString]`，改为读 `getAttribute('class')`。

实测结果：

```
$ python -X utf8 .tmp_a4\probe_style.py --selftest
SELFTEST PASS: dark=21.0 (fill) mid=4.54 (fill)
exit=0
```

```
== 360px ==  inner=360 scrollW=360 scrollH=3470 cards=6 bigs=2
   文本节点=158  低于 AA=0  <12px=9  按 fill 计=20
   -- SVG 文本（fill）worst 5 --
    7.56 / 需4.5     12px  V（罗马数字刻度）
    8.67 / 需4.5     12px  0 / 200 / 400 / 600（Y 轴刻度）
   -- 字号 <12px --
      10px 2024W46 ×3、2026W45 ×3
      11px 18.8% / 0.8% / 1.2%
```

```
== 1280px ==  inner=1280 scrollW=1280 scrollH=3400 cards=6 bigs=2
   文本节点=157  低于 AA=0  <12px=9  按 fill 计=20
```

结论：V7 的两条要求（SVG 文本 computed ≥10px、按 fill 计对比度 ≥4.5）均成立。20 个 SVG 文本节点最差 7.56:1（历史图 Y 轴罗马数字刻度，源自 `svg text[fill="#c0392b"]` 重着色为 `#3D4E56` 前的原生 `#c0392b` 未被命中——该元素 fill 为 `#c0392b` 但被 CSS 属性选择器覆盖为 `#3D4E56`，实测值已达标）。9 处 <12px 全部为 `2024W46`/`2026W45`（10px）与三个末端百分比（11px），即 design V7 声明的 SVG 例外。

留档：`.tmp_a4/v7fill-360.txt`、`.tmp_a4/v7fill-1280.txt`、`validation/v7fill-360.txt`、`validation/v7fill-1280.txt`。

## 2. [ADVISORY] pin 漂移口径 —— 两件事已分开表述

oracle 指出 `validation/v3-pins.txt` 记录 10 pin 中 9 漂移，而 `v3-search-after.txt` 的 Q6 只报 flu_north——两个说法看似矛盾。

澄清：两者是**不同判据**。
- `check_search_query.py:371-377` 在同一 `for` 循环里逐文件 `assertEqual`，**首个失败即抛异常终止**，故测试报告只列出 `flu_north.csv` 一项。
- `enum_pins.py` 独立枚举全部 10 个 pin，得到 9 漂移 / 1 匹配（`sichuan_monthly.csv`）。

正确表述应为：**测试失败集合 = {flu_north.csv}（受首败中止限制）；实际 pin 漂移集合 = 9 个文件**。二者不矛盾，前者是后者的不完整呈现。

复跑（本次现场）：
```
$ python -X utf8 .tmp_a4\enum_pins.py
DRIFT changes.log / flu_north.csv / flu_south.csv / flunet_china.csv
      heilongjiang_flu.csv / heilongjiang_sentinel.csv / run_status.json
      sentinel_national_rates.csv / sentinel_rank.csv
OK    sichuan_monthly.csv
共 10 pin，漂移 9 个
```

漂移与 A4 无关的现场证据：
```
$ git status --porcelain -- data/
(空)
$ git log -1 --format=%h%x20%s -- data/flu_north.csv
deaefd9 chore(data): weekly update 2026-11-16
```
即 `data/` 工作树完全干净，所有漂移来自 A2 冻结（r4）之后 bot 每周回写并已提交，A4 的 diff 不含 `data/`。

## 3. A/B/C/F/G/H 的现场执行证据

oracle 无命令执行能力，以下由 `v10_recheck.py` 现场跑出并留档 `validation/v10-field-evidence.txt`：

| 项 | 命令 | 结果 |
|---|---|---|
| A 冻结函数 | `check_history_compat.py --check Reg` | `Ran 4 tests … OK`，exit=0 |
| C 搜索套件 | `check_search_query.py` | `Q-SUITE FAIL 55/56`，唯一失败 `test_freeze_pins_nine_files`（flu_north，见上） |
| C 视图切换 | `check_view_toggle.py` | `RESULT: PASS`，9/9（含 `A-default-display-none`、`B-default-restored display=grid`、清空后结果保留且 default 仍 hidden） |
| D 产物禁串 | 直接计数 `site/index.html` | `<script src`=0、`fetch(`=0、`@import`=0、`url(http`=0、`<script`=3、`  <div class="card">`=18、`class="rail"`=1、`四川官方流感分级`=1 |
| F 窄屏 | `probe_narrow.py measure 320/360/900` | 三档 `sw==cw==iw`，`over=[]` |
| H 编码 | 字节检查 | 98783 bytes、无 BOM、`CRLF=0`、`LF_total=2018`、UTF-8 解码 OK、含「四川官方流感分级」、sha256 `2fb8c697f2e0aa331d909d317aa8f52d8fad65b4e9e5230fffa493f8a91a3483` |
| 工作树 | `git status --porcelain` | `M src/build_site.py` + `?? .trellis/tasks/11-16-ui-beautify/`；`git diff --stat` = 173 insertions / 14 deletions |

## 4. [G] 栅格偏离 —— 事实与授权状态的分离表述

事实（不辩）：
- 冻结计划 `design.md:64-67` 规定首行四川卡全宽、末行儿童卡全宽，即 12 / 5+7 / 5+7 / 12。
- 实现为三行 7+5（`src/build_site.py:1026-1031`），偏离真实存在。

理由的两条依据：
- `design.md:114` 自身承诺 1280×900 首屏同时可见四川分级、Goldstein、排行、历年四块；冻结的 12/5+7/5+7/12 实际只做到 3 块（`probe_layout.py` 实测 rank top=1381 > 900）。
- `design.md:11-15` 记录用户决策②「双主角并列（四川官方分级 + 南方片指数）」；冻结的「四川卡独占首行」与之相悖。

授权状态：**该偏离未经用户单独批准**，属实施期发现计划自相矛盾后的调整。处置留待本轮复核结论与用户验收一并裁定——若用户不接受，回退为 12/5+7/5+7/12 是单条 CSS 改动（删除 `.card:has(.adv){span 7}` 并恢复 `:has(.adv){grid-column:1/-1}`、`:has(.childg){grid-column:1/-1}`），无连带影响。

## 5. 第二轮复核（oracle INCONCLUSIVE→BLOCKED）回应

oracle 第二轮（ses_e1ad1bbd7ffeAvoTxt6cmHF7LZ）指出三处：留档脚本与留档内容范围不一致（`v10_recheck.py` 不跑 probe_style 自检/V7 audit）、pin 枚举选错输入（读到 A4 的 `plan-freeze-r3.md` 而非 A2 的 `plan-freeze-r4.md`，导致 `pins found=0` 假零）、数据漂移的逐文件归因不足。三处均属实，已修：

1. `v10_recheck.py` 的 `pin_enum()` 改为直接调用 `enum_pins.py`（从 A2 `plan-freeze-r4.md` 解析 10 pin），并删除会误选 A4 r3 的宽泛正则。
2. `v10_recheck.py` 追加 `probe_style.py --selftest` 与 `audit 360/1280` 两组现场执行。
3. 追加 `frozen_docs()`（design.md / implement.md 的 SHA-256 复核）与 9 个漂移文件各自的 `git log -1`（逐文件归因）+ `git diff --name-only`（确认本次 diff 不含 data/）。

重跑留档：`validation/v10b-field-evidence.txt`。关键新增证据：

- **冻结文件未被改动**：design.md `9d4cce48…` MATCH、implement.md `e840a43d…` MATCH。
- **pin 枚举 10 项全部落到正确输入**：9 漂移 / 1 匹配（`sichuan_monthly.csv`）。
- **逐文件归因**：`changes.log` 最后改动是 `46b07fa 2026-11-16 feat(site): 成都默认+全国省市离线搜索单页…`（A2 自身的提交）；其余 8 个文件全部是 `deaefd9 2026-11-16 chore(data): weekly update 2026-11-16`（bot 周更）。两类都不是 A4。
- **本次 diff 只含 `src/build_site.py`**：`touches data/ = False`。
- **V7 现场执行**：`SELFTEST PASS: dark=21.0 (fill) mid=4.54 (fill)`；`audit 360` 与 `audit 1280` 均「低于 AA=0、<12px=9、按 fill 计=20」，最差 7.56:1。
- **V6 口径澄清**：design V6 只要求**非 SVG** 文本零个 <12px；那 9 个 SVG 节点依 V7 的 SVG 规则（computed ≥10px）获准，不构成 V6 例外清单。
- **fill-opacity 未处理**：探针不合成 `fill-opacity`/SVG 元素 `opacity`。当前产物内无 `fill-opacity`（已 grep），故不影响本次 20 个节点；但探针不是通用 SVG 透明度审计器，此为已知边界。

## 6. 边界声明

本文件是**我方提供的证据**，不是对 oracle 结论的替代。是否接受上述修复与偏离理由，仍由 oracle 与用户判断。

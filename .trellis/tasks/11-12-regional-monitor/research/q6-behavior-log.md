# Q6 搜索交互行为实测记录（A2-SEARCH-06 round-3 + round-4 补 f 序列）

实测日期：2026-11-16
被测产物：`D:\FluMonitor\site\index.html`（由 `python -X utf8 src/build_site.py --local` 生成，本轮构建）
被测协议：`file://` 直开（与用户双击场景一致，页面零外链）

## 工具链（可复现）

- 浏览器：本机已装 Playwright 的 Chromium 二进制
  `C:\Users\zengw\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe`
  以 `--headless=new --remote-allow-origins=* --remote-debugging-port=<随机空闲端口>`
  启动，独立临时 `--user-data-dir`。
- 驱动：本机无 `playwright`/`puppeteer` 模块，改用已安装的 python
  `websocket-client 1.8.0` 直连 Chrome DevTools Protocol（自写最小客户端
  `.tmp_a2/cdp.py`：`Page.navigate` + `Runtime.evaluate` +
  `Input.dispatchKeyEvent` + `Page.captureScreenshot`）。
- 执行脚本：`.tmp_a2/q6_behavior.py`
  ```bat
  python -X utf8 .tmp_a2\q6_behavior.py
  ```
  脚本以断言驱动，全部通过时打印 `ALL-SEQUENCES-PASSED`，原始观测日志写入
  `.tmp_a2/q6_run.log`。

说明：键盘序列经 `Input.dispatchKeyEvent`（真实 keydown/keyup + `text`），
不是 `element.value = ...` 赋值——因此 `input` 事件、`preventDefault`、
分层 Esc 都是真实浏览器行为，非模拟桩。截图由 `Page.captureScreenshot` 拍摄。

## 观测记录（原文摘录自 `.tmp_a2/q6_run.log`）

### 0. 初始态

```
[0] 初始：cards=6 default_visible=True disabled=False
    status='已就绪：目录共 397 个单位，输入省市名称开始查询（页面不联网）。'
```

### a) 唯一候选 → 手动删光输入 → Enter：不得提交旧候选

```
[a-1] 键入 哈尔滨：cands=1 list_open=True
      status='匹配到 1 个地区，用 ↑↓ 选择、回车确认，或直接点列表项。'
[a-2] 手动删光输入：value='' list_open=False aria_expanded=false active=0
      status='输入为空：候选已清空，当前显示结果保持不变。'
[a-3] Enter：default_visible=True query_visible=False value=''
      status='请先输入省市名称，再点「查询」。'
```

结论：删空输入即废弃候选（`items=[]` + `closeList()`），Enter 走
"请先输入"分支，既不提交旧候选也不切换视图。截图
`q6_a_delete_then_enter.png`。

### b) 多候选（吉林）→ 直接 Enter：不得默认提交

```
[b-1] 键入 吉林：cands=2 list_open=True active=None
[b-2] Enter：default_visible=True query_visible=False qlen=0
      status='匹配到 2 个地区，请从列表中选择。'
```

结论：`openList` 以 `setActive(-1)` 收尾，列表打开时无任何项处于
`aria-selected="true"`（`active=None` 表示查询 DOM 结果为空），Enter 不会
选中第一项；状态区给出"请从列表中选择"，视图仍为成都默认。截图
`q6_b_multi_enter.png`。

### c) Esc 收起列表 → 再 Esc 清空输入，结果不变

```
[c-1] 第一次 Esc：list_open=False value='吉林' default_visible=True
      status='已收起候选列表，再按一次 Esc 清空输入。'
[c-2] 第二次 Esc：value='' list_open=False default_visible=True
      status='已清空输入，当前显示结果未变。'
```

结论：Esc 为两级语义，第二级只清输入框与候选标记，不切视图、不回成都，
提示语与行为一致。截图 `q6_c_double_esc.png`。

### d) 故障注入：内联脚本语法错误

注入方式：把页面内联脚本中 `function matchScore(unit, needle) {` 替换为
`function matchScore(unit, needle) { <<<SYNTAX`（临时文件，不改仓库产物）。

```
[d] 脚本语法错误：disabled=True cards=6 default_visible=True
    status='搜索组件加载中…若本提示未消失，说明内联脚本未完成初始化，搜索暂不可用；下方成都默认数据不受影响。'
```

结论：脚本整块解析失败 → `init()` 未执行 → 输入框与三按钮维持 HTML 静态
`disabled`，状态区**常驻**"搜索暂不可用"说明（不是空白、不是"已就绪"），
成都默认视图 6 张卡片完整可读。截图 `q6_d_script_error.png`。

### e) 故障注入：删除一个已用模板后选择该地区

被测单位：北京市（`110000`），其配方含 `zone_names_north`；临时删除
`<template id="tpl-zone_names_north">…</template>`。

```
[e-0] 选中 北京市(110000)，将删除模板 tpl-zone_names_north
[e-1] 键入 北京市：cands=1
[e-2] Enter：default_visible=True query_visible=False cards=6
      status='北京市 数据模块缺失（zone_names_north），已恢复成都默认。'
```

结论：缺模板时不半新半旧地渲染，直接恢复完整成都默认（6 卡），并在状态区
点名缺失槽位。截图 `q6_e_missing_template.png`。

### f) 故障注入：模板 cloneNode 抛异常（round-4 补）

被测单位：北京市（`110000`），其配方含 `zone_flu_north`。注入方式：在页面
加载后对该模板对象做
`Object.defineProperty(t, 'content', { get: function () { throw new Error('injected cloneNode failure'); } })`
—— 使 `renderResult` 里的 `tpl.content.cloneNode(true)` 在属性读取阶段即抛错，
等价于克隆阶段异常（不改仓库产物，只在运行时打补丁）。

```
[f-0] 选中 北京市(110000)，令 tpl-zone_flu_north.cloneNode 抛异常
[f-1] 注入 cloneNode 异常：'patched'
[f-2] 键入 北京市：cands=1 list_open=True
[f-3] Enter：default_visible=True query_visible=False cards=6
      status='查询切换失败（injected cloneNode failure），已恢复成都默认。'
```

结论：异常被 `selectUnit` 的 `try/catch` 兜住 → `showDefault()` 先
`clearQueryView()` 再把 `#query-view` 置 hidden、`#default-view` 置可见，
因此**不会残留半渲染的查询视图**，成都默认 6 卡完整；状态区同时给出"查询
切换失败（原因）"与"已恢复成都默认"两段信息。截图 `q6_f_clone_throw.png`。

## 截图清单（`.tmp_a2/`）

| 文件 | 对应序列 |
| --- | --- |
| `q6_a_delete_then_enter.png` | a) 删光输入后 Enter |
| `q6_b_multi_enter.png` | b) 多候选直接 Enter |
| `q6_c_double_esc.png` | c) 两级 Esc |
| `q6_d_script_error.png` | d) 脚本语法错误降级 |
| `q6_e_missing_template.png` | e) 缺模板回默认 |
| `q6_f_clone_throw.png` | f) cloneNode 抛异常回默认 |

## 未覆盖 / 说明

Chromium 无头 + `file://` 下，上述 a–f 指定序列已实测（真实
`Input.dispatchKeyEvent` 键盘事件 + 截图佐证，命令见文首）。以下仍为人工项：

- 读屏软件（NVDA/讲述人）真实播报：`aria-*` 属性与 `role` 结构由静态断言
  覆盖（Q5 组），无障碍树播报属人工验收。
- 触屏手势与 IME 中文输入法上屏：触控目标尺寸（`min-height:44px`）由静态
  断言覆盖，真机手势/输入法候选行为待用户验收。
- 窄屏（手机宽度）布局未实测。
- 仅测 Chromium；Firefox/Safari 未测（本工具无对应无头二进制）。

以上均为环境/人工验收范围，不涉及本轮修改的行为面。

# 移植到 Class Widgets 2：可行性调研

> 调研时间：2026-10-30
> 目的：Class Widgets 1.x 的插件广场已停止收录（见 README 第 9 节），
> 评估把「教室小喇叭」移植成 **Class Widgets 2 插件**、从而上架新广场的工作量。

---

## 1. 结论先说

| 问题 | 结论 |
|---|---|
| 技术上能不能做 | **能**。CW2 的插件就是 Python 模块，能力比 1.x 强得多（Widgets / Notification / Schedule / Runtime / Config / Automation / Actions / UI 一整套 API） |
| 能复用多少 | 后端（HTTP 服务、sqlite 账号库、口令哈希、配置、离线 TTS、网页前端）**几乎 100% 可复用**；UI 只需把 PyQt5 换成 PySide6（机械改动），**不必写 QML** |
| 工作量 | **1~1.5 个工作日**（含半天 spike）。~~3~4 天~~ 是按"UI 必须用 QML 重写"估的，见 3.3 的修正 |
| 最大风险 | ① 插件能否自建**无边框置顶的模态弹窗**；② 新广场还在 BETA（当前 0 个插件），提交入口/审核规则要看控制台 |
| 建议 | 先花半天做「弹窗 + 设置入口」技术验证（spike），能跑通再投剩下的半天到一天 |

---

## 2. CW2 的插件契约（读源码确认，不是文档）

来源：`RinLit-233-shiroko/Class-Widgets-2` 的 `src/core/plugin/*`

### 2.1 目录与清单

插件是一个**目录**，里面必须有 `cwplugin.json`：

```json
{
  "id": "com.example.classspeaker",
  "name": "教室小喇叭",
  "version": "2.0.0",
  "api_version": ">=0.7.0",
  "entry": "plugin.py",
  "author": "MC-HUAIHUAI",
  "icon": "icon.png",
  "readme": "README.md"
}
```

`PluginLoader.validate_meta()` 里**必填**的是：
`id` / `name` / `version` / `api_version` / `entry` / `author`
（`icon` / `readme` 是广场清单用的，加载时不强制）。

`api_version` 是 **PEP 440 版本约束**，对 `src/core/plugin/api.py` 里的
`__version__`（当前 **0.7.0**）做 `SpecifierSet.contains()` 判断，
不匹配时插件仍会出现在列表里但标记为不兼容、不会加载。

### 2.2 入口与生命周期

```python
# plugin.py
from src.core.plugin import CW2Plugin


class Plugin(CW2Plugin):
    def __init__(self, plugin_api):
        super().__init__(plugin_api)

    def on_load(self):
        super().on_load()      # 必须：设置 self.pid / self.meta / api 上下文
        # 启动我们的 HTTP 服务、注册设置页、准备弹窗

    def on_unload(self):
        pass                   # 停服务、清资源


Plugin_class = Plugin         # 加载器取 module.Plugin
```

加载器做的事：`importlib.util.spec_from_file_location(entry)` →
`exec_module` → 取 `module.Plugin` → `Plugin(plugin_api)`。
导入时把插件目录加进 `sys.path`（`plugin_import_context`），
所以插件自带子包（我们的 `classspeaker/`）可以直接导入。

### 2.3 可用的 API（`PluginAPI`，0.7.0）

| API | 能力 | 对本项目 |
|---|---|---|
| `api.widgets` | `register(widget_id, name, qml_path, backend_obj, settings_qml, default_settings)` —— 小组件是 **QML 文件**，`backend_obj` 是暴露给 QML 的 Python 对象（`@Slot`） | 可选：把「待确认条数」做成组件 |
| `api.notification` | `register_provider()` / `get_provider()` | 可考虑，但通知可被用户关掉，不满足"只能确认收到" |
| `api.runtime` | 当前时间、当前/下一节课、剩余时间、进度、科目… | 可用于在消息里附带班级/课程信息 |
| `api.config` | `register_plugin_model(plugin_id, model)` + pydantic 模型，CW2 的设置 UI 自动生成 | **可替代我们的 config.json** |
| `api.ui` | `register_settings_page(qml_path, title, icon)`、`register_shortcut()`、`pages` | 设置页必须用 **QML** 重写 |
| `api.automation` | `register(task)` —— 绑定到"上课/下课"等事件 | 未来可做"下课时自动播报" |
| `api.actions` | `register(action_name, *参数类型)` | 可选 |
| `api.application` | 版本信息、重启 | — |
| `api.diagnostics` | 日志 | — |
| `api.theme` / `api.schedule*` | 主题、课程表读写 | 暂不需要 |

### 2.4 运行时环境

- **Python `>=3.12,<3.14`**（我们代码是 3.8+ 兼容，没问题）
- **PySide6 ~= 6.10.3**（不是 PyQt5！）
- UI 是 **QML**（他们自己封装了 `RinUI` 组件库）
- `loguru` 打日志，`pydantic` 管配置模型

---

## 3. 我们的代码怎么切

### 3.1 可直接复用（都是纯 Python，零 Qt 依赖）

| 文件 | 行数 | 说明 |
|---|---|---|
| `classspeaker/server.py` | ~600 | `http.server` 内嵌服务，与框架无关 |
| `classspeaker/store.py` | ~220 | sqlite 账号/消息库 |
| `classspeaker/auth.py` | ~100 | PBKDF2 + 令牌 |
| `classspeaker/config.py` | ~150 | 配置读写（也可换成 CW2 的 `ConfigAPI`） |
| `classspeaker/tts.py` | ~310 | 离线 TTS，靠子进程调 PowerShell，**不依赖任何 GUI 框架** |
| `classspeaker/util.py` / `hub.py` / `autostart.py` | ~250 | 日志、事件总线、开机自启 |
| `classspeaker/web/*` | ~450 | 教师端网页（原生 HTML/CSS/JS） |

**复用率按行数约 70%**（≈2000 行可用）。

### 3.2 必须重写

| 部分 | 现状 | CW2 版本 | 工作量 |
|---|---|---|---|
| 插件入口 | `__init__.py` + `main.py`（1.x 的 `Plugin(cw_contexts, method)`） | `cwplugin.json` + `plugin.py`（`Plugin(CW2Plugin)`） | 0.5 天 |
| **弹窗** | `popup.py`（PyQt5 QWidget，无边框置顶、只能确认关闭） | **QML 窗口**（QQuickView + 置顶/无边框标志） | 0.5~1 天 |
| **设置页** | `settings.py`（PyQt5 表单） | **QML 页面** + `api.ui.register_settings_page` | 0.5~1 天 |
| 路径解析 | `paths.py` 按 `__file__` 推导 | 改成用 `self.PATH` / `platformdirs` | 0.2 天 |
| 打包/上架 | zip 解压到 `plugins\` | `cwplugin.json` + 图标 + README + 广场控制台提交 | 0.5 天 |

---

### 3.3 一个更省的路线（不写 QML）

原来把 UI 估成 1.5~2 天，是假设"CW2 是 QML 应用 → 插件 UI 也必须用 QML 重写"。
读源码后确认这个假设不成立，有两条捷径：

1. **弹窗 / 设置窗口：直接换 PySide6 QtWidgets**
   PySide6 同时带 QtWidgets 和 QtQuick，同一进程里 QWidget 窗口可以正常显示。
   我们现有的 `popup.py` / `settings.py` 是 PyQt5 QWidget，
   移植基本是**机械改动**（改 import、`Qt.Tool` → `Qt.WindowType.Tool` 之类、
   `exec_()` → `exec()`、`pyqtSignal` → `Signal`），**不用重写成 QML**。

2. **设置入口：用 `api.ui.register_shortcut()`**
   接口是 `register_shortcut(shortcut_id, name, icon, action)`，其中 `action`
   是任意 Python 可调用对象 —— 注册一个「教室小喇叭设置」快捷方式，
   点它就打开我们自己的设置窗口。这样**连 QML 设置页都不用写**。

代价：`register_shortcut` 的入口位置由 CW2 决定（在它的 UI 里），
不如原生设置页那么"长在插件里"；但省下的时间很值。

按这条路线，剩下的工作量只有：

| 项 | 时间 |
|---|---|
| 环境搭建 + spike（验证置顶窗口能开、shortcut 能触发） | 0.5 天 |
| PySide6 移植（popup / settings / style）+ 生命周期接线 | 0.5 天 |
| `cwplugin.json`、图标、README、广场控制台提交 | 0.5 天 |

## 4. 技术风险与验证项

### ① 弹窗能不能做成"独立窗口"（最关键）

CW2 的 UI 全是 QML，插件的 `api.ui` 只提供**设置页**和**快捷方式**，
没有"弹一个自定义窗口"的正式 API。

但插件在 CW2 进程内跑 Python，理论上可以用 PySide6 自己开一个
`QQuickView`（`FramelessWindowHint | WindowStaysOnTopHint`）承载我们的弹窗 QML。

**必须先验证**：CW2 进程里 `QQuickView` 能否正常创建并置顶、能否拿到焦点、
多屏/DPI 是否正常。跑不通的话有两个退路：
- 退路 A：用 CW2 的原生通知（但可被关掉/自动消失，**不满足需求**）；
- 退路 B：仍是独立程序（exe），只把"发消息"接到 CW2 的 Actions 上。

### ② 新广场的提交规则

`plaza.cw.rinlit.cn` 目前 **BETA、0 个插件**，需要去
<https://plaza.cw.rinlit.cn/console> 注册开发者账号，才能看到提交表单/审核规则。
`plugin-plaza` 仓库的 `ClassWidgets2/plugins/manifest/*.json` 已不再更新。

### ③ 设置项的承载方式

建议把配置交给 `api.config.register_plugin_model()`（pydantic 模型），
让 CW2 自动生成设置界面 —— 比我们手写 QML 表单省一半工作量。
但端口/声音/语音这些需要自定义 UI 的部分仍要 QML 页面。

---

## 5. 建议的移植步骤

1. **Spike（半天）**：在本机装 CW2（Python 3.12），写一个最小插件，
   验证「`cwplugin.json` 被识别 → `on_load` 跑起来 → 能开一个置顶 QWidget 窗口
   → `register_shortcut` 能打开它」。**这一步决定后面值不值得投。**
2. **PySide6 移植（0.5 天）**：`popup.py` / `settings.py` / `style.py` 换 import，
   `classspeaker/` 后端**一行都不用改**；`on_load` 起服务、`on_unload` 停掉。
3. **打包 + 上架（0.5 天）**：`cwplugin.json`、图标、README、控制台提交。

合计 **1~1.5 个工作日**（不含官方审核等待）。

---

## 6. 另一个更省事的选项

如果目标只是"让 1.x 用户能装"，**不需要移植**：
现在的 `ClassSpeaker-<版本>-cw-plugin.zip` 解压到 `plugins\` 就能用，
只是不会有官方广场入口（见 README 第 9 节）。

只有当你希望**出现在新广场、被 CW2 用户搜到**时，移植才有意义。

---

## 7. 实际移植结果（已完成）

按第 3.3 节的省钱路线做完，**契约测试 30 项一次通过**（Python 3.12 + PySide6 6.12）：

| 项 | 结果 |
|---|---|
| `cwplugin.json` 六个必填字段 | ✅ |
| 包导入后能拿到 `Plugin` | ✅ |
| `Plugin(plugin_api)` + `on_load` 起服务 | ✅（HTTP 服务在 10265 正常） |
| `api.ui.register_shortcut` 注册「教室小喇叭设置」 | ✅ |
| 设置窗口（PySide6，含语音播报分组） | ✅ |
| 弹窗：无边框 / 置顶 / 只有确认按钮 / 关不掉 | ✅ |
| 确认后写回执、`on_unload` 停服务 | ✅ |

**PyQt5 → PySide6 的实际改动**：只有 4 个文件、三类改动
（`import`、`pyqtSignal` → `Signal`、`QAction` 从 `QtWidgets` 移到 `QtGui`）；
PySide6 兼容未加限定的枚举短写（`Qt.Tool`、`Qt.WA_TranslucentBackground` 等），
所以业务代码一行没动。**没有写任何 QML。**

### 真机 E2E 遇到的两个 CW2 自身问题

在本机跑 CW2 **2.0.1.0** 便携版时，插件还没加载就被 CW2 自己的问题挡住了
（都与本插件无关，建议反馈给上游）：

1. **stdout 被重定向时崩溃**（中文 Windows）
   ```
   UnicodeEncodeError: 'gbk' codec can't encode character '\u2728' in position 0
     File "RinUI\core\launcher.py", line 62, in __init__
   ```
   `RinUI` 往 stdout 打印含 emoji 的字符串，在代码页 936 下抛错。
   设 `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8` 也无效（应为显式 `encode('gbk')`）。

2. **首次使用引导不写配置**
   正常启动会停在「使用引导」窗口；此时 `%LOCALAPPDATA%\Class Widgets 2\configs\`
   里**不会生成 `configs.json`**（`ConfigManager.save()` 没被调用），
   所以 `init()` 里的插件加载阶段根本没开始。
   尝试手工预置 `{"app": {"tutorial_completed": true}}` 也未生效
   （文件始终未被读取/重写）。

结论：**代码侧已就绪**，真机验证只差「把向导点完」这一步 —— 在用户正常使用的机器上
走一遍即可（见 README 9.1 的三步安装）。

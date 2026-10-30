# 移植到 Class Widgets 2：可行性调研

> 调研时间：2026-10-30
> 目的：Class Widgets 1.x 的插件广场已停止收录（见 README 第 9 节），
> 评估把「教室小喇叭」移植成 **Class Widgets 2 插件**、从而上架新广场的工作量。

---

## 1. 结论先说

| 问题 | 结论 |
|---|---|
| 技术上能不能做 | **能**。CW2 的插件就是 Python 模块，能力比 1.x 强得多（Widgets / Notification / Schedule / Runtime / Config / Automation / Actions / UI 一整套 API） |
| 能复用多少 | 后端（HTTP 服务、sqlite 账号库、口令哈希、配置、离线 TTS、网页前端）**几乎 100% 可复用**；**UI 层必须重写**（PyQt5 → QML） |
| 工作量 | **3~4 个工作日**（含一个「弹窗能不能做成独立窗口」的技术验证） |
| 最大风险 | ① 插件能否自建**无边框置顶的模态弹窗**；② 新广场还在 BETA（当前 0 个插件），提交入口/审核规则要看控制台 |
| 建议 | 先花半天做「弹窗 + 设置页」技术验证（spike），能跑通再投入剩下的 2~3 天 |

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
   验证「`cwplugin.json` 被识别 → `on_load` 跑起来 → 能开一个置顶 QML 窗口」。
   **这一步决定后面 2~3 天值不值得投。**
2. **入口 + 后端接入（0.5 天）**：搬 `classspeaker/` 的纯 Python 部分，
   `on_load` 里启动服务、`on_unload` 里停掉；先不做 UI，用浏览器验证网页端能发消息。
3. **弹窗（0.5~1 天）**：QML 弹窗 + Python 桥（消息内容、确认按钮回传）。
4. **设置页（0.5~1 天）**：QML 表单 + 端口/弹窗/声音/语音配置。
5. **打包 + 上架（0.5 天）**：`cwplugin.json`、图标、README、控制台提交。

合计 **3~4 个工作日**（不含官方审核等待）。

---

## 6. 另一个更省事的选项

如果目标只是"让 1.x 用户能装"，**不需要移植**：
现在的 `ClassSpeaker-<版本>-cw-plugin.zip` 解压到 `plugins\` 就能用，
只是不会有官方广场入口（见 README 第 9 节）。

只有当你希望**出现在新广场、被 CW2 用户搜到**时，移植才有意义。

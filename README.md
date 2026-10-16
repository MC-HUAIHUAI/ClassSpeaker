# 教室小喇叭（ClassSpeaker）

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/MC-HUAIHUAI/ClassSpeaker/actions/workflows/ci.yml/badge.svg)](https://github.com/MC-HUAIHUAI/ClassSpeaker/actions/workflows/ci.yml)
[![Release](https://github.com/MC-HUAIHUAI/ClassSpeaker/actions/workflows/release.yml/badge.svg)](https://github.com/MC-HUAIHUAI/ClassSpeaker/actions/workflows/release.yml)
[![Platform](https://img.shields.io/badge/platform-Windows%2032%2F64-lightgrey.svg)](#)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](#)

老师在**浏览器**里发一句话，教室电脑立刻弹出**无边框置顶窗口**：

> 张三老师发来的消息
> 请第三排同学上讲台领取试卷。  **\[ 确认收到 ]**

只有点「确认收到」才能关掉；老师那边网页会实时显示「已确认收到」。

- 运行在**校园局域网**内，不依赖外网、不需要服务器机房。
- 一台教室电脑 = 一个独立服务：注册、审批、消息记录都放在本机。
- 纯 **Python 标准库 + PyQt5**，没有任何第三方依赖。
- 两种形态：**独立版**（托盘常驻）、**Class Widgets 插件版**，以及打包好的
  **exe / 安装包**（32 / 64 位）。

---

## 1. 目录结构

```
ClassSpeaker/
├─ run.py                    独立版入口（pythonw run.py）
├─ main.py                   Class Widgets 插件入口
├─ __init__.py               CW 插件包入口（**必须有**：导出 Plugin / Settings）
├─ plugin.json               CW 插件清单
├─ start_classroom.bat       独立版快捷启动
├─ requirements.txt          运行时依赖（PyQt5）
├─ requirements-dev.txt      开发 / 打包依赖（+ pyinstaller）
├─ LICENSE                   MIT 许可证
├─ .github/                  CI 与自动发布流水线 + Release 正文模板
├─ classspeaker/             代码本体（故意用独立包名，避免和 CW 的 ui/ 等目录冲突）│   ├─ paths.py              路径解析（独立 / 插件 / exe 三种形态通用）
│   ├─ util.py               日志、JSON、取本机内网 IP
│   ├─ config.py             配置读写（data/config.json）
│   ├─ store.py              sqlite3 存储（users / messages）
│   ├─ auth.py               口令哈希（PBKDF2）与登录令牌
│   ├─ autostart.py          开机自启（HKCU\...\Run，无需管理员）
│   ├─ hub.py                进程内事件总线（HTTP 线程 → 界面线程）
│   ├─ server.py             内嵌 HTTP 服务（http.server，纯标准库）
│   ├─ app.py                SpeakerCore，把上面这些串起来
│   ├─ ui/                   PyQt5 界面
│   │   ├─ popup.py          无边框弹窗（只能确认收到）
│   │   ├─ settings.py       设置/调试窗口
│   │   ├─ desktop.py        托盘、弹窗队列、重启补弹、首次运行
│   │   └─ style.py          样式表与代码生成的喇叭图标
│   ├─ web/                  教师端网页（原生 HTML/CSS/JS）
│   └─ assets/               自带提示音 notify.wav + 打包用图标 app.ico
└─ tools/
    ├─ smoke_test.py         后端接口端到端自测
    ├─ gui_test.py           PyQt 界面自测（offscreen 跑）
    ├─ plugin_test.py        CW 插件入口自测
    ├─ make_sound.py         重新生成自带提示音
    ├─ make_icon.py          生成 exe 用的 app.ico（含 --preview）
    ├─ build_exe.py          打包 exe（--arch 32/64，单文件 / 目录版）
    ├─ build_installer.ps1   一键出 exe + Inno Setup 安装包
    ├─ deploy_to_cw.ps1      部署到 Class Widgets 的 plugins 目录
    └─ innosetup/            Inno Setup 脚本 + 官方简体中文语言文件
```

打包后还会出现 `dist\`（64 位 exe）、`dist32\`（32 位 exe）、`installer\`（安装包）、
`build*\`（PyInstaller 中间文件，可随时删）。

运行后会生成 `data/`：`config.json`（设置）、`speaker.db`（账号与消息）、`server.log`（日志）。
如果程序目录不可写（例如装在 Program Files），会自动改用 `%LOCALAPPDATA%\ClassSpeaker`；
也可以用环境变量 `CLASSSPEAKER_DATA_DIR=D:\ClassSpeakerData` 强制指定数据目录
（做测试、或想让配置和程序分开存放时很有用）。

---

## 2. 快速开始

### 方式 A：独立版（普通版，托盘后台运行）

```bat
:: 首次需要装 PyQt5（Python 3.8 及以上）
pip install PyQt5

:: 双击 start_classroom.bat，或：
pythonw run.py
```

- 启动后任务栏右下角出现**喇叭图标**（无控制台窗口）。
- 首次运行会**自动弹出一次设置窗口**（以后不再自动弹）。
- 右键托盘图标 → 设置… / 测试弹窗 / 复制访问地址 / 为作者充电 / 退出。

### 方式 B：Class Widgets 插件版（推荐给已经在用 CW 的教室）

```powershell
powershell -ExecutionPolicy Bypass -File tools\deploy_to_cw.ps1
# 或指定路径：-CwDir "D:\ClassWidgets-Windows-x64"
```

脚本会把插件需要的文件复制到 `<ClassWidgets>\plugins\ClassSpeaker\`：

```
plugins\ClassSpeaker\
├─ __init__.py      ← **必须有**：CW 把插件目录当包导入，由它导出 Plugin / Settings
├─ plugin.json      插件清单
├─ main.py          插件入口（CW 调它）
└─ classspeaker\    核心代码 + 网页 + 声音
```

随后（**两步都不能省**）：

1. 启动 `ClassWidgets.exe`；
2. 在 CW **「设置 → 插件」里把「教室小喇叭」设为启用**
   （CW 只加载 `config\plugin.json → enabled_plugins` 里列出的插件；
   也可以手动把 `"ClassSpeaker"` 写进这个文件）；
3. 在 CW 的**小组件列表里添加「教室小喇叭」**，它会显示「待确认 N 条 + 教师端地址」；
4. 首次运行会**自动弹出一次设置窗口**；之后可以在 CW 的插件管理里点设置，
   或（若把 `show_tray_icon` 设为 true）用托盘图标右键 → 设置…。

> 插件模式的托盘图标跟随 `data\config.json` 里的 `show_tray_icon`（默认 `true`，
> 任务栏会出现一个喇叭图标，右键可设置/测试弹窗/复制地址/开机自启）；
> 不想要就把它改成 `false` 再重启 CW，设置入口改用 CW 插件管理里的设置页。
>
> 已在本机部署并验证过：`F:\develop_class_call\ClassWidgets-Windows-x64\plugins\ClassSpeaker\`。
> 重新部署重复执行上面的命令即可（会覆盖，但**保留 `data/` 目录**，不会清掉已有账号）。
> 想连独立版一起拷进去，加 `-WithStandalone`。
>
> 完整说明（安装 / 更新 / 卸载 / 排查）见 [第 10 节](#10-class-widgets-插件版完整说明)。

### 方式 C：直接用打包好的 exe / 安装包（教室电脑没装 Python 时用这个）

```powershell
python tools\make_icon.py            # 生成图标（只需一次）
python tools\build_exe.py            # 64 位单文件 -> dist\ClassSpeaker.exe
python tools\build_exe.py --arch 32  # 32 位单文件 -> dist32\ClassSpeaker.exe
```

一键出 **exe + 安装包**（需要已安装 Inno Setup 6）：

```powershell
powershell -ExecutionPolicy Bypass -File tools\build_installer.ps1
# 产物：
#   dist\ClassSpeaker.exe                              64 位单文件
#   dist32\ClassSpeaker.exe                            32 位单文件（32/64 位 Windows 都能跑）
#   installer\ClassSpeaker-1.0.0-x64-setup.exe         64 位安装包
#   installer\ClassSpeaker-1.0.0-x86-setup.exe         32 位安装包
```

- **单文件 exe**：拷到教室电脑任意目录双击即可，不需要装 Python / PyQt5。
  数据（账号、消息、设置）生成在 exe 同级的 `data\` 目录里。
- **安装包**：默认「仅为我安装」（`%LOCALAPPDATA%\Programs\ClassSpeaker`，**不弹 UAC**），
  安装向导里可勾选「开机自动启动」和「创建桌面快捷方式」，开始菜单有快捷方式和卸载项；
  卸载时会把 `data\` 一起清掉。安装过程中会自动关闭正在运行的旧版本。
- **32 位 exe 在 64 位 Windows 上也能跑**，想一个包通吃就发 32 位那版。

| 形态 | 32 位 Windows | 64 位 Windows |
|---|---|---|
| CW 插件版 | ✅（借用 CW 自带的 Python/PyQt5，代码零改动） | ✅ |
| 独立版 `run.py` | ✅（装对应位数的 Python + PyQt5） | ✅ |
| `dist32\ClassSpeaker.exe` | ✅ | ✅ |
| `dist\ClassSpeaker.exe` | ❌ | ✅ |

---

## 3. 教师端怎么用

1. 浏览器打开教室电脑的地址，例如 `http://192.168.1.39:10265`
   （地址在设置窗口里点「复制访问地址」即可，或看 CW 小组件）。
2. 首次使用点「注册教师账号」填用户名/显示名/密码 → 提交。
   - **显示名就是弹窗里的「XXX老师」**，建议填「张老师」。
   - 账号默认需要管理员审批（可关闭）。
3. 管理员在教室电脑上审批：
   用 `admin` 登录教师端 → 页面下方「账号管理（管理员）」→ 点「批准」。
4. 教师登录 → 输入内容 → 「发送到教室」。
5. 教室电脑弹出无边框窗口，学生点「确认收到」；教师网页上该条消息立即变成
   **教室已确认收到**，并弹出提示与确认时间。

### 内置管理员账号

| 用户名 | 初始密码 |
|---|---|
| `admin` | `admin123` |

第一次使用后请在「设置 → 账号」里重置密码，或登录教师端后自行修改。

---

## 4. 设置窗口（调试窗口）内容

按需求实现，打开方式：**托盘图标右键 → 设置…**，或**首次运行自动弹出（仅一次）**。

| 分组 | 项目 |
|---|---|
| 教室标识 | 教室显示名（留空用计算机名）；自动上报计算机名、内网 IP、访问地址；复制地址 / 浏览器打开 |
| 局域网服务 | **监听端口**（默认 10265，保存后立即重启服务；若被占用或落在系统保留段，会自动顺延并提示新地址）；新账号是否需要管理员审批；运行状态与待确认条数 |
| 启动与后台运行 | **开机自动启动**（写 HKCU 注册表 Run 项，不需要管理员权限；打开设置时会回显当前实际注册的命令，位置变了保存后会自动修正） |
| 弹窗外观 | **弹窗宽度 / 高度**、**正文字体大小**、**窗口透明度**（30%–100%）、标题模板、允许拖动、未确认前保持置顶 |
| 提示音 | **是否播放声音**（默认关闭）、**声音文件路径**（留空=自带 `notify.wav`，可浏览选择 wav/mp3/wma/ogg）、重复播放次数、试听 |
| 其他 | **测试弹窗**（按当前设置立即预览）、打开数据目录、**为作者充电**（打开 B 站主页）、重置管理员密码 |

弹窗相关特性（固定行为，不提供开关）：

- **无边框**、置顶、不占任务栏；
- 右下角只有「**确认收到**」一个按钮，**没有关闭按钮**；
- `Alt+F4`、`Esc`、系统关闭一律被忽略，**只能确认收到才能关闭**；
- 多条消息**排队串行**显示，确认一条再弹下一条。

---

## 5. 接口一览（二次开发 / 对接）

所有接口都是 JSON，令牌通过请求头 `X-Auth-Token` 传递。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/info` | 教室名、主机名、内网 IP、访问地址、版本（公开） |
| GET | `/api/health` | 健康检查（公开） |
| POST | `/api/register` | 注册教师账号 → `pending` 或 `approved` |
| POST | `/api/login` | 登录，返回 `token` |
| POST | `/api/logout` | 注销 |
| GET | `/api/me` | 当前账号信息 |
| POST | `/api/send` | 发送消息 `{content}`（弹窗 + 入队） |
| GET | `/api/messages?limit=100` | 消息列表与「确认收到」状态 |
| POST | `/api/password` | 修改自己的密码 |
| GET | `/api/users` | 账号列表（管理员） |
| POST | `/api/users/approve` `\|` `/reject` `\|` `/delete` | 审批 / 拒绝 / 删除账号（管理员） |
| POST | `/api/ack` | 由外部程序代为确认收到 `{message_id}` |

安全措施：口令 PBKDF2-SHA256（12 万次迭代 + 随机盐）、令牌 12 小时过期、
同 IP 5 分钟内密码错误 8 次即锁定、静态资源目录穿越拦截、请求体大小限制。

---

## 6. 自测

```bat
python tools\smoke_test.py      :: 后端接口
python tools\gui_test.py        :: 界面（会自动切到 offscreen，无需显示器）
python tools\plugin_test.py     :: CW 插件入口
```

三个脚本都会把数据目录切到系统临时目录，**不会动正式配置和数据库**，也不会碰注册表里的正式自启项
（自启用的是临时项名，测完自动删掉）。

---

## 7. 常见问题

**老师打不开网页 / 页面转圈**
1. 确认教室电脑上程序在运行（托盘图标 + 设置里显示「运行中」）；
2. Windows 防火墙首次会弹窗询问，要选**允许访问**（专用网络）。
   也可以手动放行：`netsh advfirewall firewall add rule name="ClassSpeaker" dir=in action=allow protocol=TCP localport=10265`；
3. 确认老师和教室电脑在同一网段（校园网经常把无线和有线划到不同 VLAN，这种要请网络管理员处理）。

**端口被占用 / 提示"以一种访问权限不允许的方式…(10013)"**
- 被别的程序占用：程序会**自动顺延**到空闲端口并在托盘气泡里告诉你新地址，也可以在设置里手动改；
- 报 `10013` 说明端口落在 **Windows 保留段**里（Hyper-V / WSL / Docker 会成段保留，用
  `netsh int ipv4 show excludedportrange protocol=tcp` 可以看）。换一个不在保留段里的端口即可。

**弹窗不弹**：确认是「教室端」电脑；消息发出去后如果托盘提示「待确认」一直在涨，说明没有界面在消费队列，重启一次程序即可。

**想换提示音**：设置 → 提示音 → 浏览选择音频文件；点「试听」确认能听到，再勾选「播放提示音」。

**忘记管理员密码**：设置 → 账号 → 输入新密码 → 重置管理员密码（需要有本机操作权限）。

**普通版想开机自启**：不用手动拖快捷方式了 —— 托盘图标右键 →「开机自动启动」，
或在设置窗口「启动与后台运行」里勾选即可（写当前用户注册表 `Run` 项，不需要管理员权限）。

---

## 8. 已知限制

- 单机部署模式：**每间教室各自的账号体系独立**，老师在不同教室需要各注册一次
  （这是按"每教室独立模式"确定的架构；若以后想统一管理，可再加一个中心服务器汇聚）。
- 教师端网页登录态存在浏览器 localStorage，服务重启后需要重新登录。
- 提示音使用 `winsound`（Windows 专用）；非 Windows 下退化为系统提示音。
- 弹窗中「未确认前保持置顶」每 2 秒重新置顶一次，若遇到全屏程序仍被遮挡，
  可把该开关关掉改用普通置顶。

## 9. 发布为 CW 插件广场（可选）

按官方文档，上架插件广场需要：

1. 把本目录推到自己的 GitHub 仓库，**先打一个 Release**（否则用户无法下载）；
   —— 本仓库地址已经是 `https://github.com/MC-HUAIHUAI/ClassSpeaker`，
   `plugin.json` 的 `author` / `url` / `branch` 已填好；
2. 复刻 `Class-Widgets/plugin-plaza`，在 `Plugins/plugin_list.json` 里按格式追加条目；
3. 提交 Pull Request。

> `plugin.json` 的 `plugin_ver` 已按 Class Widgets 的
> `config.ini → [Plugin] → version` 填为 `2`（对应 Class Widgets v1.2.x）。
>
> 本仓库根目录同时是**合法的 CW 插件目录**（`plugin.json` + `main.py` 都在根目录），
> 所以既可以用 `deploy_to_cw.ps1` 从源码部署，也可以直接
> `git clone` 到 `<CW>\plugins\ClassSpeaker\`。

---

## 10. Class Widgets 插件版完整说明

插件版和独立版是**同一套代码的两个入口**，插件版没有独立进程 —— 服务跑在 Class Widgets 进程里面。

### 10.1 CW 的插件机制（照着实现，别照过时文档）

CW 的 `PluginLoader.load_plugins()` 实际做的是：

```python
for folder in PLUGIN_HOME.iterdir():                  # <CW>\plugins\<目录名>
    if folder.is_dir() and (folder / 'plugin.json').exists():
        if folder.name not in plugin_config['enabled_plugins']:
            continue                                  # 未启用 → 直接跳过
        module = importlib.import_module(f"plugins.{folder.name}")   # 当「包」导入
        if hasattr(module, 'Settings'): ...Settings(插件路径)...      # 可选设置页
        if hasattr(module, 'Plugin'):  ...Plugin(cw_contexts, method)...
        logger.success(f"加载插件成功：{module_name}")               # 没找到 Plugin 也照样打 SUCCESS
```

由此推出三条硬性要求：

1. **插件目录必须是一个 Python 包** —— 根目录要有 `__init__.py` 并由它 `from .main import Plugin, Settings`。
   少了它，`import_module` 会把目录当成 PEP 420 命名空间包：**导入不报错、也找不到 Plugin，
   日志却照样打「加载插件成功」**，插件实际不会运行（我们就踩过这个坑）。
2. **必须在 `config\plugin.json` 的 `enabled_plugins` 里**，CW 才会加载它（可在 CW 界面里启用）。
3. `Plugin.__init__(cw_contexts, method)` / `execute()` / `update(cw_contexts)` 就是被调用的三个方法。

### 10.2 安装

```powershell
powershell -ExecutionPolicy Bypass -File tools\deploy_to_cw.ps1
# 换目录： -CwDir "D:\ClassWidgets-Windows-x64"
# 连独立版一起拷： -WithStandalone
```

会复制 `__init__.py`、`main.py`、`plugin.json`、`classspeaker\` 到
`<CW>\plugins\ClassSpeaker\`。**重复执行 = 更新**（保留 `data\`，不清账号）。

手动部署也一样：把上面四样拷进去，目录名建议保持 `ClassSpeaker`。

### 10.3 第一次使用

1. 启动 `ClassWidgets.exe`，在 **「设置 → 插件」里启用「教室小喇叭」**
   （等价于把 `"ClassSpeaker"` 写进 `<CW>\config\plugin.json` 的 `enabled_plugins`）；
2. 在 CW 里**添加小组件「教室小喇叭」**，它会实时显示 `待确认 N 条　http://192.168.1.39:10265`；
3. 首次运行会**自动弹出一次设置窗口**（端口、弹窗大小/字体/透明度、提示音、开机自启、测试弹窗）；
4. 之后想改设置：CW 插件管理里点设置，或点任务栏的喇叭托盘图标右键 → 设置…
   （插件模式的托盘图标可用 `data\config.json` 的 `show_tray_icon: false` 关掉）。

### 10.4 老师怎么用

浏览器打开 `http://教室电脑IP:10265` → 注册教师账号（显示名会出现在弹窗上）→
管理员用 `admin` / `admin123` 在页面下方「账号管理」批准 → 老师登录即可发消息。
详见 [第 3 节](#3-教师端怎么用)。

### 10.5 更新 / 卸载 / 数据位置

| 操作 | 做法 |
|---|---|
| 更新插件 | 重新跑 `deploy_to_cw.ps1`，或覆盖 `__init__.py` + `main.py` + `classspeaker\`，然后重启 CW |
| 临时停用 | CW 的「设置 → 插件」里关掉，或删掉 `plugins\ClassSpeaker` 整个目录 |
| 彻底卸载 | 关掉 CW → 删除 `plugins\ClassSpeaker` 目录（`data\` 里是账号和消息，一并删即彻底清理） |
| 账号数据在哪 | `<CW>\plugins\ClassSpeaker\data\`（`config.json`、`speaker.db`、`server.log`） |

### 10.6 排查：插件"看起来加载了"但没反应

先看 `<CW>\plugins\ClassSpeaker\data\server.log`。里面有我们启动时自报的运行形态，一眼就能看出问题：

```
运行形态：frozen=True meipass=<CW安装目录> executable=<CW>\ClassWidgets.exe
目录：程序=<CW>\plugins\ClassSpeaker 包=...\classspeaker 资源=...\web 数据=...\data
```

| 现象 | 原因 |
|---|---|
| CW 日志有「加载插件成功」但没有 `data\` 目录 | 缺 `__init__.py`（见 10.1），或插件没在 `enabled_plugins` 里 |
| 网页打开是 404、`/api/health` 却正常 | 资源目录被指到了宿主的 `_MEIPASS`。CW 是 **onedir** 打包，它的 `sys._MEIPASS` 就等于 CW 安装目录，插件正好在其下 —— 不能用 `sys.frozen` 判断"我是不是被打包的"（已修，判定条件收紧为「本包既在 `_MEIPASS` 里、又在系统临时目录里」） |
| `data\` 出现在 `<CW>\data\` 里 | 同上，数据目录被误判成 CW 的安装目录 |
| 端口被占用 | 会自动顺延并在小组件/托盘提示新地址，老师要用**新的**那个地址 |
| CW 开了安全模式 | `config\config.ini → [Other] → safe_mode`，插件可能被禁用，关掉再启动 |

### 10.7 插件版特有的注意点

- **和独立版 / exe 版不能同时运行**：三者共用同一个单实例互斥体和同一个默认端口，
  先后启动会提示「教室小喇叭已在运行」。一台教室电脑只跑一种形态即可。
- **网页由 CW 进程提供**，所以 CW 必须处于运行状态，老师才连得上。
- 小组件若没有对应主题 `.ui`，CW 会自动回退用 `widget-base.ui` 渲染，属正常现象。

---

## 11. 自动构建（GitHub Actions）

仓库内置两条流水线，**不用在本地跑构建**：

| 流水线 | 触发条件 | 做什么 |
|---|---|---|
| `CI` (`.github/workflows/ci.yml`) | push 到 `main`、PR、手动 | 在 **x64 和 x86 两种 Python** 下各跑一遍 103 项自动测试 + 编译检查 |
| `Release` (`.github/workflows/release.yml`) | 推送 `v*` 标签、手动 | 构建 32/64 位 exe + 中文安装包，自动创建 Release 并挂上 4 个附件 |

**发新版本只要两行命令**：

```bat
git tag v1.0.1
git push origin v1.0.1
```

流水线会并发跑两个架构的任务（约 5 分钟），产物命名成
`ClassSpeaker-1.0.1-x86-setup.exe` / `-x64-setup.exe` / `-x86.exe` / `-x64.exe`
自动挂到 Release，正文用 `.github/release-body.md` 模板。

**只想验证流水线、不想发版**：在 Actions 页面手动触发 `Release`（workflow_dispatch），
它会照常构建并上传 artifacts，但**不会**创建 Release。

**发版前记得改版本号**：`plugin.json` 的 `version`（流水线用它的值给产物命名），
如需同步可一并改 `README` 与 `tools/innosetup/ClassSpeaker.iss` 里的 `MyAppVersion`。

> **推送报 `schannel: failed to receive handshake` 怎么办**
> 这是国内网络链路被干扰（`git ls-remote` 能通、`git push` 握手失败，就是这个特征）。
> 让 git 走本地代理即可，用完取消：
> ```bat
> git config --global http.proxy http://127.0.0.1:7897   :: 换成你自己的代理端口
> git config --global --unset http.proxy
> ```
> 本文档所在环境就是用这种方式推上去的（Clash Verge 默认 7897）。

## 12. 许可证

[MIT](LICENSE) © 2026 MC-HUAIHUAI

仓库：<https://github.com/MC-HUAIHUAI/ClassSpeaker>

`tools/innosetup/ChineseSimplified.isl` 来自 Inno Setup 官方仓库
（`jrsoftware/issrc` 的 `Files/Languages/ChineseSimplified.isl`），
仅用于编译中文安装向导，版权归其原作者所有。

# 教室小喇叭（ClassSpeaker）

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
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
├─ plugin.json               CW 插件清单
├─ start_classroom.bat       独立版快捷启动
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
├─ plugin.json      插件清单
├─ main.py          插件入口（CW 调它）
└─ classspeaker\    核心代码 + 网页 + 声音
```

随后：

1. 启动 `ClassWidgets.exe`（插件自动加载并起服务，**不需要你另外开程序**）；
2. 在 Class Widgets 的「小组件」里添加 **教室小喇叭**，它会显示「待确认 N 条 + 教师端地址」；
3. 托盘图标右键 → 设置… 修改端口、弹窗大小等（首次运行同样会自动弹出一次）。

> 已在本机部署过一次：`F:\develop_class_call\ClassWidgets-Windows-x64\plugins\ClassSpeaker\`。
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

### 10.1 安装

**推荐：一键部署脚本**

```powershell
powershell -ExecutionPolicy Bypass -File tools\deploy_to_cw.ps1
# 换目录： -CwDir "D:\ClassWidgets-Windows-x64"
# 连独立版一起拷： -WithStandalone
```

脚本会自动找到同级目录下的 `ClassWidgets-Windows-x64` / `-x86`，把
`main.py`、`plugin.json`、`classspeaker\` 复制到 `<CW>\plugins\ClassSpeaker\`。
**重复执行 = 更新**（会保留 `data\`，不会清掉账号）。

**手动部署**：把 `ClassSpeaker` 文件夹里的 `main.py`、`plugin.json`、`classspeaker\`
拷进 `ClassWidgets-Windows-x64\plugins\ClassSpeaker\` 即可（目录名随意，但建议保持一致）。

### 10.2 第一次使用

1. 启动 `ClassWidgets.exe`。插件的 `plugin_ver` 是 2，对应 CW 1.2.x，
   默认 `auto_enable_plugin=1`，**插件会被自动加载**（无需手动启用）。
2. 加载后插件会：
   - 启动内嵌 HTTP 服务（默认端口 10265）；
   - 首次运行**自动弹出一次设置窗口**，之后不再自动弹；
   - 在任务栏托盘多出一个**喇叭图标**（CW 自己的图标仍在）。
3. 在 Class Widgets 里**添加小组件「教室小喇叭」**（CW 的「小组件」/「添加组件」里找），
   它会实时显示：`待确认 N 条　http://192.168.1.39:10265` —— 这个地址就是给老师用的。
4. 右键托盘喇叭图标 → **设置…**，可改端口、弹窗大小/字体/透明度、提示音、**开机自动启动**，
   以及点「测试弹窗」先看效果。

### 10.3 老师怎么用

浏览器打开 `http://教室电脑IP:10265` → 注册教师账号（显示名会出现在弹窗上）→
管理员用 `admin` / `admin123` 在页面下方「账号管理」批准 → 老师登录即可发消息。
详见 [第 3 节](#3-教师端怎么用)。

### 10.4 更新 / 卸载

| 操作 | 做法 |
|---|---|
| 更新插件 | 重新跑 `deploy_to_cw.ps1`，或手动覆盖 `main.py` + `classspeaker\`，然后重启 CW |
| 临时停用 | CW 设置里关掉这个插件，或删掉 `plugins\ClassSpeaker` 整个目录 |
| 彻底卸载 | 关掉 CW → 删除 `plugins\ClassSpeaker` 目录（其中 `data\` 存着账号和消息，一并删掉即彻底清理） |
| 账号数据在哪 | `<CW>\plugins\ClassSpeaker\data\`（`config.json`、`speaker.db`、`server.log`） |

### 10.5 插件版特有的注意点

- **和独立版 / exe 版不能同时运行**：三者共用同一个单实例互斥体和同一个默认端口，
  先后启动会提示「教室小喇叭已在运行」。一台教室电脑只跑一种形态即可。
- **插件版的设置窗口也是从托盘图标打开的**（CW 的插件 API 没提供"设置菜单"钩子），
  所以托盘里会多一个我们的图标；如果不想有第二个图标，点 CW 的插件设置关掉本插件即可。
- **插件版的网页由 CW 进程提供**，所以 CW 必须处于运行状态，老师才连得上。
- 端口被别的程序占用时，插件会自动顺延并在小组件/托盘提示新地址，
  老师要用**新的**那个地址。
- 如果 CW 开了「安全模式」（`config.ini → [Other] → safe_mode`），插件可能被禁用，
  关掉安全模式再启动。

---

## 11. 许可证

[MIT](LICENSE) © 2026 MC-HUAIHUAI

仓库：<https://github.com/MC-HUAIHUAI/ClassSpeaker>

`tools/innosetup/ChineseSimplified.isl` 来自 Inno Setup 官方仓库
（`jrsoftware/issrc` 的 `Files/Languages/ChineseSimplified.isl`），
仅用于编译中文安装向导，版权归其原作者所有。

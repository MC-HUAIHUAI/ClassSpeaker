# 教室小喇叭（Class Widgets 2 插件）

老师用浏览器发消息，教室电脑弹出**无边框提醒**，学生点「确认收到」后教师端立刻看到回执。
支持**离线语音播报**（中文/英文自动切换）。

这是 **Class Widgets 2** 版本（`cwplugin.json` + `Plugin(CW2Plugin)`）。
Class Widgets 1.x 版本见仓库根目录（`plugin.json` + `main.py`）。

## 安装

把整个 `ClassSpeaker` 文件夹放到 CW2 的插件目录：

```
%LOCALAPPDATA%\Class_Widgets_2\plugins\ClassSpeaker\
```

便携版则是：

```
<ClassWidgets-2>\data\plugins\ClassSpeaker\
```

然后在 CW2 的「设置 → 插件」里启用它。启用后：

- 内嵌 HTTP 服务会自动启动（默认端口 `10265`）；
- 托盘/快捷方式里会出现 **「教室小喇叭设置」**，点开就是完整设置窗口。

## 老师怎么用

浏览器打开 `http://教室电脑IP:10265` → 注册教师账号 → 管理员用
`admin` / `admin123` 批准 → 登录后发消息。详见主仓库 README。

## 与 1.x 版本的差异

| | 1.x 版本 | 2.0 版本（本目录） |
|---|---|---|
| 入口 | `plugin.json` + `main.py` | `cwplugin.json` + `plugin.py`（`Plugin(CW2Plugin)`） |
| 生命周期 | `__init__` / `execute` / `update` | `on_load` / `on_unload` |
| UI 框架 | PyQt5 | **PySide6**（代码基本一致，只换 import） |
| 设置入口 | 自己的托盘图标 | CW2 快捷方式 `api.ui.register_shortcut` |
| 小组件 | CW1 组件栏 | 暂未提供（CW2 组件需要 QML） |

核心（HTTP 服务 / sqlite 账号库 / 口令哈希 / 配置 / 离线 TTS / 教师端网页）
两个版本完全共用，没有重复实现。

## 数据位置

```
<插件目录>\data\
├─ config.json     设置
├─ speaker.db      账号与消息
└─ server.log      日志
```

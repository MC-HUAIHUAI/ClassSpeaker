# 上架「插件广场」提交清单

> 广场地址：<https://plaza.cw.rinlit.cn>（BETA，当前 0 个插件）
> 控制台：<https://plaza.cw.rinlit.cn/console>（**需要登录**，没有公开 API）
>
> 老的 `Class-Widgets/plugin-plaza` 仓库已于 2026-07-14 停止收录（见 README 第 9 节），
> 现在只能走这个控制台。

---

## 0. 提交前自检（都已完成 ✅）

| 检查项 | 状态 |
|---|---|
| 插件仓库公开可访问 | ✅ <https://github.com/MC-HUAIHUAI/ClassSpeaker> |
| 有 Release（广场要求先有 Release） | ✅ v1.1.0，含 `.cwplugin` 附件 |
| 插件归档可被 CW2 导入器接受 | ✅ `tools/cw2_archive_test.py` 23 项全过 |
| 插件在真机 CW2 里能加载运行 | ✅ 已实测（服务起在 10265、设置入口可用） |
| 图标 256×256 PNG | ✅ `icon.png` |
| README | ✅ 仓库根目录 + 插件目录内各一份 |

**要上传的文件**（同一个文件，三个位置任选）：

```
C:\Users\32284\Desktop\ClassSpeaker-2.0.0.cwplugin
F:\develop_class_call\ClassSpeaker-2.0.0.cwplugin
F:\develop_class_call\ClassSpeaker\dist\ClassSpeaker-2.0.0.cwplugin
```

在线下载：<https://github.com/MC-HUAIHUAI/ClassSpeaker/releases/download/v1.1.0/ClassSpeaker-2.0.0.cwplugin>

---

## 1. 表单字段（直接复制）

| 字段 | 值 |
|---|---|
| **id / 插件 ID** | `com.mchuaihuai.classspeaker` |
| **名称** | `教室小喇叭` |
| **版本** | `2.0.0` |
| **api_version / 适用 API** | `>=0.6.0` |
| **作者** | `MC_HUAIHUAI` |
| **仓库地址** | `https://github.com/MC-HUAIHUAI/ClassSpeaker` |
| **分支** | `main` |
| **图标** | `icon.png`（随归档一起上传；如需单独上传，用桌面插件目录里的 `icon.png`） |
| **README** | `README.md` |

**简介（短，约 50 字）**

```
老师用浏览器发消息，教室电脑弹出无边框提醒并回执「确认收到」，支持离线语音播报。
```

**详细说明（长）**

```
教室小喇叭把「老师通知教室」这件事做成一个网页：

· 老师在浏览器打开 http://教室电脑IP:10265，注册账号（管理员 admin 审批后即可用）
· 输入消息点发送 → 教室电脑立刻弹出无边框置顶窗口
· 窗口没有关闭按钮，Alt+F4 / Esc 都无效，学生只能点「确认收到」
· 老师那边网页马上变成「教室已确认收到」，并显示确认时间
· 支持把消息念出来：Windows 自带语音、完全离线、中英文自动切换，确认后立即停止
· 弹窗宽高、字体、透明度、提示音、语音音色与语速都可调，可开机自启
· 纯局域网运行，不联网；口令 PBKDF2 哈希存储

数据放在插件目录的 data/ 里（账号、消息、设置），卸载插件即清理。
```

**标签（建议，按广场支持的数量取舍）**

```
课堂, 通知, 语音, 局域网, 工具
```

---

## 2. 操作步骤

1. 打开 <https://plaza.cw.rinlit.cn/console>，**注册/登录开发者账号**
2. 找到「提交插件 / 新建」入口
3. 按上表填字段，**上传 `ClassSpeaker-2.0.0.cwplugin`**
4. 提交后等审核（BETA 阶段，规则以控制台提示为准）

## 3. 如果表单要求的东西不一样

| 它的要求 | 怎么应对 |
|---|---|
| 只让填**仓库地址**，不给上传 | 填 `https://github.com/MC-HUAIHUAI/ClassSpeaker`，分支 `main`。若它按仓库根目录找 `cwplugin.json` 会失败 —— 告诉我，我另开一个仓库把插件放到**根目录**（`cw2p-com.mchuaihuai.classspeaker` 那种命名） |
| 要求 `.zip` 而不是 `.cwplugin` | `.cwplugin` 本质就是 zip，直接改扩展名为 `.zip` 再传即可（结构不变） |
| 要求截图 | 我可以补：教师端网页、教室端弹窗、设置窗口三张 |
| 要求英文描述 | 告诉我，我补一版英文简介 |

## 4. 以后发新版本

1. 改 `cw2/ClassSpeaker/cwplugin.json` 的 `version`（例如 `2.0.1`）
2. `python tools\build_cw2_plugin_zip.py` 重新打包
3. `python tools\cw2_archive_test.py dist\ClassSpeaker-2.0.1.cwplugin` 自检
4. 到控制台上传新版本（同一个 id，广场会自动更新）
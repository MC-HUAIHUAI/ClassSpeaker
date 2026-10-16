; ============================================================
;  教室小喇叭 (ClassSpeaker) —— Inno Setup 安装脚本
;
;  用法（由 tools\build_installer.ps1 自动调用，也可手动）：
;    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" ^
;        /DMySourceDir="F:\...\dist32" /DMyArch="x86" tools\innosetup\ClassSpeaker.iss
;
;  可覆盖的宏：
;    MySourceDir  打包产物目录（默认 ..\..\dist）
;    MyArch       架构标签，用于文件名（默认 x64）
;    MyOutputDir  安装包输出目录（默认 ..\..\installer）
; ============================================================

#ifndef MySourceDir
  #define MySourceDir "..\..\dist"
#endif
#ifndef MyArch
  #define MyArch "x64"
#endif
#ifndef MyOutputDir
  #define MyOutputDir "..\..\installer"
#endif

#define MyAppName "教室小喇叭"
#define MyAppNameEn "ClassSpeaker"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "ClassSpeaker"
#define MyAppExeName "ClassSpeaker.exe"
#define MyAppId "{{B7C3A1E4-5D2F-4A8B-9E6C-1F0D3A7B5C92}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion=1.0.1.0
DefaultDirName={autopf}\{#MyAppNameEn}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
OutputDir={#MyOutputDir}
OutputBaseFilename={#MyAppNameEn}-{#MyAppVersion}-{#MyArch}-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; 默认按"仅为我安装"（不需要管理员权限，数据就写在程序目录旁边）
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
SetupIconFile=..\..\classspeaker\assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
; 安装/卸载时自动关掉正在运行的程序（Restart Manager）
CloseApplications=yes
RestartApplications=no
#if MyArch == "x64"
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
#else
ArchitecturesAllowed=x86compatible
#endif

[Languages]
Name: "chinese"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "开机自动启动（登录 Windows 后自动在后台运行）"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "{#MySourceDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; 勾选"开机自动启动"时写入当前用户的 Run 项；卸载时自动删除
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "ClassSpeaker"; \
    ValueData: """{app}\{#MyAppExeName}"""; \
    Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 卸载时清掉运行期数据（账号库、配置、日志）
Type: filesandordirs; Name: "{app}\data"

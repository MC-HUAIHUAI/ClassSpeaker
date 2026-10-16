# ============================================================
#  ClassSpeaker -> Class Widgets plugin deploy script
#
#  Usage (PowerShell):
#     powershell -ExecutionPolicy Bypass -File tools\deploy_to_cw.ps1
#     powershell -ExecutionPolicy Bypass -File tools\deploy_to_cw.ps1 -CwDir "D:\ClassWidgets-Windows-x64"
#     powershell -ExecutionPolicy Bypass -File tools\deploy_to_cw.ps1 -WithStandalone
#
#  只拷贝插件真正需要的文件：
#     main.py, plugin.json, classspeaker/  （-WithStandalone 时再加 run.py / start_classroom.bat）
#
#  (messages are ASCII on purpose, to avoid console encoding issues)
# ============================================================
param(
    [string]$CwDir = "",
    [switch]$WithStandalone
)

$ErrorActionPreference = "Stop"
$Src = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Find-Cw {
    param([string]$Explicit)
    if ($Explicit) {
        if (Test-Path (Join-Path $Explicit "ClassWidgets.exe")) { return (Resolve-Path $Explicit).Path }
        Write-Host "[ERROR] ClassWidgets.exe not found in: $Explicit"
        exit 1
    }
    $parent = Split-Path $Src -Parent
    foreach ($name in @("ClassWidgets-Windows-x64", "ClassWidgets-Windows-x86")) {
        $candidate = Join-Path $parent $name
        if (Test-Path (Join-Path $candidate "ClassWidgets.exe")) { return $candidate }
    }
    Get-ChildItem -Path $parent -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        if (Test-Path (Join-Path $_.FullName "ClassWidgets.exe")) { return $_.FullName }
    }
    return ""
}

$cw = Find-Cw -Explicit $CwDir
if (-not $cw) {
    Write-Host "[ERROR] Class Widgets folder not found."
    Write-Host "        Run: tools\deploy_to_cw.ps1 -CwDir ""D:\ClassWidgets-Windows-x64"""
    exit 1
}

$dst = Join-Path $cw "plugins\ClassSpeaker"
Write-Host "Source : $Src"
Write-Host "Target : $dst"

New-Item -ItemType Directory -Force -Path (Join-Path $cw "plugins") | Out-Null
New-Item -ItemType Directory -Force -Path $dst | Out-Null

# 清掉上一次部署留下的垃圾（保留 data，免得把账号库删了）
Get-ChildItem -Path $dst -Force | Where-Object { $_.Name -notin @("data") } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

$items = @("main.py", "plugin.json", "classspeaker")
if ($WithStandalone) { $items += @("run.py", "start_classroom.bat", "README.md", "tools") }

$excludeDirs = @("data", "__pycache__", ".git", ".idea", ".vscode", "build", "dist")

foreach ($item in $items) {
    $source = Join-Path $Src $item
    if (-not (Test-Path $source)) { continue }
    if (Test-Path $source -PathType Container) {
        Get-ChildItem -Path $source -Recurse -Force | ForEach-Object {
            $relative = $_.FullName.Substring($Src.Length).TrimStart("\")
            $parts = $relative.Split("\")
            if ($parts | Where-Object { $excludeDirs -contains $_ }) { return }
            $target = Join-Path $dst $relative
            if ($_.PSIsContainer) {
                New-Item -ItemType Directory -Force -Path $target | Out-Null
            } else {
                if ($_.Extension -in @(".pyc", ".pyo")) { return }
                $targetDir = Split-Path $target -Parent
                if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Force -Path $targetDir | Out-Null }
                Copy-Item -LiteralPath $_.FullName -Destination $target -Force
            }
        }
    } else {
        Copy-Item -LiteralPath $source -Destination (Join-Path $dst $item) -Force
    }
}

Write-Host ""
Write-Host "Deployed files:"
Get-ChildItem -Path $dst -Force | ForEach-Object { Write-Host ("  " + $_.Name) }
Write-Host ""
Write-Host "Done. Start ClassWidgets.exe and add the widget 'Jiao Shi Xiao La Ba' (ClassSpeaker)."
Write-Host "Right-click the tray icon -> Settings to change port / popup size / font / sound / opacity."

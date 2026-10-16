# ============================================================
#  教室小喇叭 —— 一键出 exe + Inno Setup 安装包
#
#  用法（PowerShell）：
#     powershell -ExecutionPolicy Bypass -File tools\build_installer.ps1
#     powershell -ExecutionPolicy Bypass -File tools\build_installer.ps1 -Arch both
#
#  -Arch 可选：64 / 32 / both（默认 both）
#  产物：
#     dist\ClassSpeaker.exe            64 位单文件
#     dist32\ClassSpeaker.exe          32 位单文件（32/64 位 Windows 都能跑）
#     installer\ClassSpeaker-1.0.0-x64-setup.exe
#     installer\ClassSpeaker-1.0.0-x86-setup.exe
# ============================================================
param(
    [ValidateSet("64", "32", "both")]
    [string]$Arch = "both",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Iscc)) { $Iscc = "C:\Program Files\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $Iscc)) {
    Write-Host "[ERROR] Inno Setup 6 not found. Install it from https://jrsoftware.org/isdl.php"
    exit 1
}

$targets = @()
if ($Arch -eq "64" -or $Arch -eq "both") { $targets += @{ Bits = "64"; Tag = "x64"; Dist = "dist" } }
if ($Arch -eq "32" -or $Arch -eq "both") { $targets += @{ Bits = "32"; Tag = "x86"; Dist = "dist32" } }

if (-not $SkipBuild) {
    foreach ($t in $targets) {
        Write-Host ("=" * 60)
        Write-Host ("Building exe ({0} bit)" -f $t.Bits)
        Write-Host ("=" * 60)
        & python (Join-Path $Root "tools\build_exe.py") --arch $t.Bits
        if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] build_exe failed ($($t.Bits) bit)"; exit 1 }
    }
}

$installerDir = Join-Path $Root "installer"
New-Item -ItemType Directory -Force -Path $installerDir | Out-Null

foreach ($t in $targets) {
    $source = Join-Path $Root $t.Dist
    $exe = Join-Path $source "ClassSpeaker.exe"
    if (-not (Test-Path $exe)) {
        Write-Host "[ERROR] Not found: $exe  (run build_exe.py --arch $($t.Bits) first)"
        exit 1
    }
    Write-Host ("=" * 60)
    Write-Host ("Building installer ({0})" -f $t.Tag)
    Write-Host ("=" * 60)
    $iss = Join-Path $Root "tools\innosetup\ClassSpeaker.iss"
    & $Iscc "/DMySourceDir=$source" "/DMyArch=$($t.Tag)" "/DMyOutputDir=$installerDir" $iss
    if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] ISCC failed ($($t.Tag))"; exit 1 }
}

Write-Host ""
Write-Host "Done. Artifacts:"
Get-ChildItem $installerDir -Filter "*.exe" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host ("  {0}  ({1:N1} MB)" -f $_.FullName, ($_.Length / 1MB))
}

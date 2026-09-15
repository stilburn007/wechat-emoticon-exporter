$ErrorActionPreference = "Stop"

$AppRoot = $PSScriptRoot
$ProjectRoot = if (Test-Path -LiteralPath (Join-Path $AppRoot "src\wechat_emoticon_exporter")) {
    $AppRoot
} else {
    Split-Path -Parent $AppRoot
}
$VenvPython = Join-Path $AppRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    python -m venv (Join-Path $AppRoot ".venv")
}

$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"

& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to prepare pip." }

& $VenvPython -m pip install setuptools wheel
if ($LASTEXITCODE -ne 0) { throw "Failed to install build tools." }

& $VenvPython -m pip install --no-build-isolation -e $ProjectRoot
if ($LASTEXITCODE -ne 0) { throw "Failed to install the exporter package." }

& $VenvPython -m pip install -r (Join-Path $AppRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Failed to install Studio dependencies." }

& $VenvPython -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) { throw "Failed to install PyInstaller." }

& $VenvPython (Join-Path $AppRoot "scripts\generate_icon.py")
if ($LASTEXITCODE -ne 0) { throw "Failed to generate the application icon." }

$Arguments = @(
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "WeChatEmoticonStudio",
    "--paths", $AppRoot,
    "--icon", "$AppRoot\assets\app.ico",
    "--add-data", "$AppRoot\frontend;frontend",
    "--collect-all", "webview",
    "--collect-all", "clr_loader",
    "--collect-all", "pythonnet",
    "--collect-all", "imageio_ffmpeg",
    "--collect-submodules", "wechat_emoticon_exporter",
    "--hidden-import", "webview.platforms.edgechromium",
    "--hidden-import", "clr",
    "--hidden-import", "PIL._tkinter_finder",
    (Join-Path $AppRoot "run_studio.py")
)

& $VenvPython -m PyInstaller @Arguments
$DistRoot = Join-Path $AppRoot "dist\WeChatEmoticonStudio"
$PortableZip = Join-Path $AppRoot "dist\WeChatEmoticonStudio-portable.zip"
$RootLauncher = Join-Path $AppRoot "dist\WeChatEmoticonStudio.exe"
$LauncherBuild = Join-Path $AppRoot "dist\WeChatEmoticonStudioLauncher.exe"

if (Test-Path -LiteralPath $RootLauncher) {
    Remove-Item -LiteralPath $RootLauncher -Force
}

$LauncherArguments = @(
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "WeChatEmoticonStudioLauncher",
    "--paths", $AppRoot,
    "--icon", "$AppRoot\assets\app.ico",
    (Join-Path $AppRoot "launcher.py")
)
& $VenvPython -m PyInstaller @LauncherArguments
if ($LASTEXITCODE -ne 0) { throw "Failed to build the root launcher." }

Move-Item -LiteralPath $LauncherBuild -Destination $RootLauncher

if (Test-Path -LiteralPath $PortableZip) {
    Remove-Item -LiteralPath $PortableZip -Force
}
Compress-Archive -Path (Join-Path $DistRoot "*") -DestinationPath $PortableZip

Write-Host "Built: $DistRoot\WeChatEmoticonStudio.exe"
Write-Host "Launcher: $RootLauncher"
Write-Host "Portable archive: $PortableZip"

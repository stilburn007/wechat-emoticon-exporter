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

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e $ProjectRoot
& $VenvPython -m pip install -r (Join-Path $AppRoot "requirements.txt")
& $VenvPython (Join-Path $AppRoot "run_studio.py")

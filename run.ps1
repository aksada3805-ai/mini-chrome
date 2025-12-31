# PowerShell launcher for Mini Chrome
# Uses project .venv Python if present, otherwise falls back to system python.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$venv = Join-Path $ScriptDir '.venv\Scripts\python.exe'
$script = Join-Path $ScriptDir 'mini_chrome_full.py'
if (Test-Path $venv) {
    & $venv $script @args
} else {
    & python $script @args
}  

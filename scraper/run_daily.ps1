# Script chay boi Windows Task Scheduler "xoso-mn-daily" luc 17:15 hang ngay
$PythonExe = "C:\Users\Quoc_\miniconda3\envs\gpu\python.exe"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SyncScript = Join-Path $ScriptDir "daily_sync.py"
$LogFile = Join-Path (Split-Path -Parent $ScriptDir) "logs\daily_sync.log"

Set-Location (Split-Path -Parent $ScriptDir)
& $PythonExe $SyncScript >> $LogFile 2>&1

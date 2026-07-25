' JAMES Swing Lite — 창 없는 자동 런처 v2
Option Explicit

Dim oShell, oFSO, scriptDir, psFile, logDir

Set oShell = CreateObject("WScript.Shell")
Set oFSO   = CreateObject("Scripting.FileSystemObject")

scriptDir = oFSO.GetParentFolderName(WScript.ScriptFullName)
logDir    = scriptDir & "\logs"

If Not oFSO.FolderExists(logDir) Then oFSO.CreateFolder(logDir)

' ── PowerShell runner 스크립트 생성 ─────────────────────────
psFile = scriptDir & "\james_bg_runner.ps1"
Dim f : Set f = oFSO.CreateTextFile(psFile, True, True)
f.WriteLine "Set-Location '" & scriptDir & "'"
f.WriteLine "$ErrorActionPreference = 'SilentlyContinue'"
f.WriteLine ""
f.WriteLine "# 1. Python 탐색"
f.WriteLine "$py = $null"
f.WriteLine "$checks = @("
f.WriteLine "  '.venv\Scripts\python.exe',"
f.WriteLine "  ""$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"","
f.WriteLine "  ""$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"","
f.WriteLine "  ""$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"","
f.WriteLine "  ""$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"","
f.WriteLine "  'C:\Python313\python.exe','C:\Python312\python.exe'"
f.WriteLine ")"
f.WriteLine "foreach ($c in $checks) { if (Test-Path $c) { $py = (Resolve-Path $c).Path; break } }"
f.WriteLine "if (-not $py) {"
f.WriteLine "  Start-Process 'winget' 'install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements' -Wait -NoNewWindow"
f.WriteLine "  $py = ""$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"""
f.WriteLine "}"
f.WriteLine ""
f.WriteLine "# 2. 가상환경 없으면 생성 + 패키지 설치"
f.WriteLine "if (-not (Test-Path '.venv\Scripts\python.exe')) {"
f.WriteLine "  & $py -m venv .venv"
f.WriteLine "  & '.venv\Scripts\pip.exe' install --upgrade pip --quiet"
f.WriteLine "  & '.venv\Scripts\pip.exe' install -r requirements.txt --quiet"
f.WriteLine "} else {"
f.WriteLine "  # uvicorn 누락 시 재설치"
f.WriteLine "  $check = & '.venv\Scripts\python.exe' -c 'import uvicorn' 2>&1"
f.WriteLine "  if ($LASTEXITCODE -ne 0) {"
f.WriteLine "    & '.venv\Scripts\pip.exe' install -r requirements.txt --quiet"
f.WriteLine "  }"
f.WriteLine "}"
f.WriteLine ""
f.WriteLine "# 3. 기존 서버 프로세스 정리"
f.WriteLine "Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue"
f.WriteLine "Start-Sleep -Seconds 1"
f.WriteLine ""
f.WriteLine "# 4. 백그라운드 서버 실행"
f.WriteLine "Start-Process '.venv\Scripts\python.exe' -ArgumentList 'lite_app.py' -WindowStyle Hidden -RedirectStandardOutput 'logs\server.log' -RedirectStandardError 'logs\server_err.log'"
f.WriteLine ""
f.WriteLine "# 5. 서버 준비 대기 (최대 30초)"
f.WriteLine "$ready = $false"
f.WriteLine "for ($i = 0; $i -lt 30; $i++) {"
f.WriteLine "  Start-Sleep -Seconds 1"
f.WriteLine "  try {"
f.WriteLine "    $r = Invoke-WebRequest 'http://127.0.0.1:8780' -TimeoutSec 1 -UseBasicParsing"
f.WriteLine "    if ($r.StatusCode -eq 200) { $ready = $true; break }"
f.WriteLine "  } catch {}"
f.WriteLine "}"
f.WriteLine ""
f.WriteLine "# 6. 브라우저 오픈"
f.WriteLine "Start-Process 'http://127.0.0.1:8780'"
f.Close

' ── 창 없이 실행 ─────────────────────────────────────────────
oShell.Run "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File """ & psFile & """", 0, False

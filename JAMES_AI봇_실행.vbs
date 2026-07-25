Set oShell = CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")
scriptDir = oFSO.GetParentFolderName(WScript.ScriptFullName)
py = scriptDir & "\.venv\Scripts\python.exe"
bot = scriptDir & "\james_ai_bot.py"

' PowerShell로 완전히 숨겨서 실행
oShell.Run "powershell.exe -WindowStyle Hidden -Command ""Start-Process '" & py & "' -ArgumentList '" & bot & "' -WindowStyle Hidden -WorkingDirectory '" & scriptDir & "'""", 0, False

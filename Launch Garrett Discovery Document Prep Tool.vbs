Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
PythonExe = ScriptDir & "\venv\Scripts\pythonw.exe"
MainScript = ScriptDir & "\src\main.py"

' Check if virtual environment exists
If FSO.FileExists(PythonExe) Then
    WshShell.Run """" & PythonExe & """ """ & MainScript & """", 0, False
Else
    ' Fallback to system Python if venv doesn't exist
    WshShell.Run "python """ & MainScript & """", 0, False
End If

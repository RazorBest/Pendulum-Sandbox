import sys
import win32com.client 
import os
import sys
import win32com.shell.shell as shell
ASADMIN = 'asadmin'

if sys.argv[-1] != ASADMIN:
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([script] + sys.argv[1:] + [ASADMIN])
    shell.ShellExecuteEx(lpVerb='runas', lpFile=sys.executable, lpParameters=params)

shell = win32com.client.Dispatch("WScript.Shell")
shortcut = shell.CreateShortCut("Pendulum Sandbox.lnk")
shortcut.WorkingDirectory = "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs"
#shortcut.IconLocation = "pendulum.ico,1"
print shortcut.TargetPath
shortcut.save()
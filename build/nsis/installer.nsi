!define PRODUCT_NAME "Pendulum Sandbox"
!define PRODUCT_VERSION "1.0"
!define PY_VERSION "2.7.16"
!define PY_MAJOR_VERSION "2.7"
!define BITNESS "64"
!define ARCH_TAG ".amd64"
!define INSTALLER_NAME "Pendulum_Sandbox_1.0.exe"
!define PRODUCT_ICON "glossyorb.ico"
 
SetCompressor lzma

RequestExecutionLevel admin

; Modern UI installer stuff 
!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"

; UI pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "English"

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "${INSTALLER_NAME}"
InstallDir "$PROGRAMFILES${BITNESS}\${PRODUCT_NAME}"
ShowInstDetails show

Section -SETTINGS
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
SectionEnd

Section "PyLauncher" sec_pylauncher
    ; Check for the existence of the pyw command, skip installing if it exists
    nsExec::Exec 'where pyw'
    Pop $0
    IntCmp $0 0 SkipPylauncher
    ; Extract the py/pyw launcher msi and run it.
    File "launchwin${ARCH_TAG}.msi"
    ExecWait 'msiexec /i "$INSTDIR\launchwin${ARCH_TAG}.msi" /qb ALLUSERS=1'
    Delete "$INSTDIR\launchwin${ARCH_TAG}.msi"
    SkipPylauncher:
SectionEnd

Section "Python ${PY_VERSION}" sec_py

  DetailPrint "Installing Python ${PY_MAJOR_VERSION}, ${BITNESS} bit"
    File "python-2.7.16.amd64.msi"
    ExecWait 'msiexec /i "$INSTDIR\python-2.7.16.amd64.msi" \
            /qb ALLUSERS=1 TARGETDIR="$COMMONFILES${BITNESS}\Python\${PY_MAJOR_VERSION}"'
  Delete "$INSTDIR\python-2.7.16.amd64.msi"
SectionEnd


Section "!${PRODUCT_NAME}" sec_app
  SetRegView 64
  SectionIn RO
  SetShellVarContext all
  File ${PRODUCT_ICON}
  SetOutPath "$INSTDIR\pkgs"
  File /r "pkgs\*.*"
  SetOutPath "$INSTDIR"

  ; Install files
    SetOutPath "$INSTDIR"
      File "Pendulum_Sandbox.launch.py"
      File "glossyorb.ico"
      File "LICENSE.txt"
      File "README.md"
      File "README.doc"
  
  ; Install directories
    SetOutPath "$INSTDIR\icons"
    File /r "icons\*.*"
  
  ; Install shortcuts
  ; The output path becomes the working directory for shortcuts
  SetOutPath "%HOMEDRIVE%\%HOMEPATH%"
    CreateShortCut "$SMPROGRAMS\Pendulum Sandbox.lnk" "py" \
      '"$INSTDIR\Pendulum_Sandbox.launch.py"' "$INSTDIR\glossyorb.ico"
  SetOutPath "$INSTDIR"

  
  ; Byte-compile Python files.
  DetailPrint "Byte-compiling Python modules..."
  nsExec::ExecToLog 'py -2.7 -m compileall -q "$INSTDIR\pkgs"'
  WriteUninstaller $INSTDIR\uninstall.exe
  ; Add ourselves to Add/remove programs
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "DisplayIcon" "$INSTDIR\${PRODUCT_ICON}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "NoRepair" 1

  ; Check if we need to reboot
  IfRebootFlag 0 noreboot
    MessageBox MB_YESNO "A reboot is required to finish the installation. Do you wish to reboot now?" \
                /SD IDNO IDNO noreboot
      Reboot
  noreboot:
SectionEnd

Section "Uninstall"
  SetRegView 64
  SetShellVarContext all
  Delete $INSTDIR\uninstall.exe
  Delete "$INSTDIR\${PRODUCT_ICON}"
  RMDir /r "$INSTDIR\pkgs"

  ; Remove ourselves from %PATH%

  ; Uninstall files
    Delete "$INSTDIR\Pendulum_Sandbox.launch.py"
    Delete "$INSTDIR\glossyorb.ico"
    Delete "$INSTDIR\LICENSE.txt"
    Delete "$INSTDIR\README.md"
    Delete "$INSTDIR\README.doc"
  ; Uninstall directories
    RMDir /r "$INSTDIR\icons"

  ; Uninstall shortcuts
      Delete "$SMPROGRAMS\Pendulum Sandbox.lnk"
  RMDir $INSTDIR
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
SectionEnd




; Functions

Function .onMouseOverSection
    ; Find which section the mouse is over, and set the corresponding description.
    FindWindow $R0 "#32770" "" $HWNDPARENT
    GetDlgItem $R0 $R0 1043 ; description item (must be added to the UI)

    StrCmp $0 ${sec_py} 0 +2
      SendMessage $R0 ${WM_SETTEXT} 0 "STR:The Python interpreter. \
            This is required for ${PRODUCT_NAME} to run."

    StrCmp $0 ${sec_app} "" +2
      SendMessage $R0 ${WM_SETTEXT} 0 "STR:${PRODUCT_NAME}"
    


    StrCmp $0 ${sec_app} "" +2
      SendMessage $R0 ${WM_SETTEXT} 0 "STR:The Python launcher. \
          This is required for ${PRODUCT_NAME} to run."
FunctionEnd
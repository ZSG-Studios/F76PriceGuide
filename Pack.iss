[Setup]
AppName=F76TradeGuide
AppVersion=1.0.0
AppId={{B6D8C9F1-1234-4A7B-9D5A-ABCDEF012345}}
WizardStyle=modern
PrivilegesRequired=lowest
DefaultDirName={localappdata}\F76TradeGuide
DefaultGroupName=F76TradeGuide
OutputDir=Output
OutputBaseFilename=F76TradeGuide_Installer
Compression=lzma
SolidCompression=yes

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; EXE — pulled from dist\ (PyInstaller output)
Source: "dist\F76PriceGuide.exe"; DestDir: "{app}"; Flags: ignoreversion

; Data folder only — all contents recursively
Source: "Data\*"; DestDir: "{app}\Data"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcut
Name: "{group}\F76TradeGuide"; Filename: "{app}\F76PriceGuide.exe"; WorkingDir: "{app}"
; Desktop shortcut (optional)
Name: "{autodesktop}\F76TradeGuide"; Filename: "{app}\F76PriceGuide.exe"; WorkingDir: "{app}"; Tasks: desktopicon
; Uninstall shortcut
Name: "{group}\Uninstall F76TradeGuide"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\F76PriceGuide.exe"; Description: "Launch F76TradeGuide"; Flags: postinstall nowait skipifsilent

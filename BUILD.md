## Windows

## build cli
```bash
python -m PyInstaller --onefile --name openlucky --distpath bin cmd/openlucky.py
```

## build desktop app
```bash
yarn build:win:portable
```

## build installer package
```
ISCC.exe OpenLucky.iss
```

## Inno Setup Configuration
```ini
[Setup]
AppName=OpenLucky
AppVersion=1.1.0-pre
DefaultDirName={pf}\OpenLucky
DefaultGroupName=OpenLucky
OutputDir=dist-installer
OutputBaseFilename=OpenLucky-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
CreateAppDir=yes
CreateUninstallRegKey=yes
UninstallDisplayIcon={app}\OpenLucky.exe

[Files]
Source: "app\dist-electron\win-unpacked\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\OpenLucky"; Filename: "{app}\OpenLucky.exe"
Name: "{group}\OpenLucky"; Filename: "{app}\OpenLucky.exe"
Name: "{group}\Uninstall OpenLucky"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\OpenLucky.exe"; Description: "Launch OpenLucky"; Flags: nowait postinstall skipifsilent
```

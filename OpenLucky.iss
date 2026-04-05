; --- Inno Setup 脚本 (修复版) ---
#define MyAppName "OpenLucky"
#define MyAppVersion "v1.2.2-rc2"
#define MyAppPublisher "Ares"
#define MyAppExeName "openlucky.exe"

[Setup]
AppId={{8B3C9A52-7F12-4B6A-9D3E-A5F1E2C5B4D9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
LicenseFile=LICENSE
; 必须要求管理员权限才能修改 HKLM 注册表
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
OutputDir=.
OutputBaseFilename=OpenLucky_{#MyAppVersion}_windows-x64_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; 允许用户自定义安装目录
DisableDirPage=no
DisableProgramGroupPage=no

[Files]
; 3. 释放 bin 目录下的所有 exe
Source: "bin\*.exe"; DestDir: "{app}\bin"; Flags: ignoreversion
; 5. 释放 config.yaml 到用户主目录下的 .openlucky (读取当前登录用户的 Profile)
Source: "config.yaml"; DestDir: "{%USERPROFILE}\.openlucky"; Flags: ignoreversion
; 6. 释放 Electron 桌面应用的所有文件
Source: "app\dist-electron\win-unpacked\*"; DestDir: "{app}\"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 创建桌面快捷方式
Name: "{userdesktop}\OpenLucky"; Filename: "{app}\OpenLuckyApp.exe"; IconFilename: "{app}\OpenLuckyApp.exe"
; 创建开始菜单快捷方式
Name: "{group}\OpenLucky"; Filename: "{app}\OpenLuckyApp.exe"; IconFilename: "{app}\OpenLuckyApp.exe"

[Registry]
; 4. 系统级 PATH 变量
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; \
    ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}\bin"; \
    Check: NeedsAddPath(ExpandConstant('{app}\bin'))

[Code]
// --- 必要的 Windows API 声明 ---
#ifdef UNICODE
  #define AW "W"
#else
  #define AW "A"
#endif

const
  WM_SETTINGCHANGE = $001A;
  SMTO_ABORTIFHUNG = $0002;

function SendMessageTimeout(hWnd: HWND; Msg: UINT; wParam: LongInt; lParam: String; fuFlags: UINT; uTimeout: UINT; var lpdwResult: LongInt): LongInt;
  external 'SendMessageTimeout{#AW}@user32.dll stdcall';

// 检查路径是否已存在
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  // 加上分号进行匹配，防止子串误判
  Result := Pos(';' + Uppercase(Param) + ';', ';' + Uppercase(OrigPath) + ';') = 0;
end;

// 安装完成后通知系统刷新环境变量
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultAddr: LongInt;
begin
  if CurStep = ssPostInstall then
  begin
    // 发送全局广播，通知 Environment 变量已变更
    SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE, 0, 'Environment', SMTO_ABORTIFHUNG, 5000, ResultAddr);
  end;
end;
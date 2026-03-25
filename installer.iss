; Inno Setup script for SimTelemetry Pro
; Compile with: iscc installer.iss
; Or: python build.py --installer

#define MyAppName      "SimTelemetry Pro"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "SimTelemetry"
#define MyAppURL       "https://github.com/simtelemetry/simtelemetrypro"
#define MyAppExeName   "SimTelemetryPro.exe"
#define MyAppDirName   "SimTelemetry Pro"
#define SourceDir      "dist\SimTelemetryPro"
#define OutputDir      "dist"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppDirName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
OutputDir={#OutputDir}
OutputBaseFilename=SimTelemetryPro_Setup
SetupIconFile=assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
WizardResizable=yes
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}
VersionInfoDescription=Racing Telemetry for AC, ACC and Le Mans Ultimate

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french";  MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon";   Description: "{cm:CreateDesktopIcon}";   GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunch";   Description: "Create a Quick Launch shortcut"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; Main application files
Source: "{#SourceDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";          Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";    Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Dirs]
; Create recordings directory in user Documents
Name: "{userdocs}\SimTelemetry\recordings"

[Registry]
; File association: open .csv telemetry files with SimTelemetry Pro
Root: HKCU; Subkey: "Software\Classes\.simtel"; ValueType: string; ValueName: ""; ValueData: "SimTelemetryPro.Document"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\SimTelemetryPro.Document"; ValueType: string; ValueName: ""; ValueData: "SimTelemetry Lap File"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SimTelemetryPro.Document\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\SimTelemetryPro.Document\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// Check for existing installation and offer to uninstall first
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  RecDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Create default recordings directory
    RecDir := ExpandConstant('{userdocs}\SimTelemetry\recordings');
    if not DirExists(RecDir) then
      CreateDir(RecDir);
  end;
end;

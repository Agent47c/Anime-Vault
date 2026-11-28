; Build using Inno Setup 7 (6.4+ is also supported).
#ifndef AppVersion
  #define AppVersion "1.2.3"
#endif
#define ProjectRoot SourcePath + ".."
#define VaultAppId "BB4AB6A4-91CC-4BBF-B367-BC22D14E8C37"

[Setup]
AppId={{{#VaultAppId}}
AppName=Anime Vault
AppVersion={#AppVersion}
AppPublisher=Agent47c
AppPublisherURL=https://github.com/Agent47c/Anime-Vault
AppSupportURL=https://github.com/Agent47c/Anime-Vault/issues
AppUpdatesURL=https://github.com/Agent47c/Anime-Vault
DefaultDirName=C:\Program Files\Anime Vault
UsePreviousAppDir=yes
DisableDirPage=no
DefaultGroupName=Anime Vault
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir={#ProjectRoot}\dist\installer
OutputBaseFilename=AnimeVault-Setup-{#AppVersion}-windows-x64
SetupIconFile={#ProjectRoot}\assets\app.ico
UninstallDisplayIcon={app}\_internal\assets\app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110
WizardSmallImageFile=artwork\wizard-icon.png
WizardImageFile=artwork\wizard-panel.png
AppMutex=Global\AnimeVault.Installed.Desktop,AnimeVault.Installed.Desktop
CloseApplications=yes
CloseApplicationsFilter=*.exe,*.dll
RestartApplications=no
AlwaysRestart=no
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#ProjectRoot}\dist\AnimeVault\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectRoot}\docs\INSTALLER_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Anime Vault"; Filename: "{app}\AnimeVault.exe"; WorkingDir: "{app}"; IconFilename: "{app}\_internal\assets\app.ico"; AppUserModelID: "AnimeVault.Desktop.MediaManager"
Name: "{autodesktop}\Anime Vault"; Filename: "{app}\AnimeVault.exe"; WorkingDir: "{app}"; IconFilename: "{app}\_internal\assets\app.ico"; AppUserModelID: "AnimeVault.Desktop.MediaManager"; Tasks: desktopicon

[Run]
Filename: "{app}\AnimeVault.exe"; Description: "Launch Anime Vault"; Flags: nowait postinstall skipifsilent unchecked runasoriginaluser

[Code]
const
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{{#VaultAppId}}_is1';

var
  InstallMode: TInputOptionWizardPage;
  ExistingDirectory: String;

function ContainsAnimeVault(Directory: String): Boolean;
begin
  Result := (Directory <> '') and
    FileExists(AddBackslash(Directory) + 'AnimeVault.exe') and
    FileExists(AddBackslash(Directory) + '_internal\assets\app.ico');
end;

function RegisteredDirectory(RootKey: Integer): String;
var
  Directory: String;
begin
  Result := '';
  if RegQueryStringValue(RootKey, UninstallKey, 'Inno Setup: App Path', Directory) and
     ContainsAnimeVault(Directory) then
    Result := Directory
  else if RegQueryStringValue(RootKey, UninstallKey, 'InstallLocation', Directory) and
          ContainsAnimeVault(Directory) then
    Result := Directory;
end;

procedure InitializeWizard;
begin
  ExistingDirectory := RegisteredDirectory(HKLM64);
  if ExistingDirectory = '' then ExistingDirectory := RegisteredDirectory(HKLM32);
  if ExistingDirectory = '' then ExistingDirectory := RegisteredDirectory(HKCU);
  if (ExistingDirectory = '') and ContainsAnimeVault(WizardDirValue) then
    ExistingDirectory := WizardDirValue;

  InstallMode := CreateInputOptionPage(wpWelcome, 'Install or update Anime Vault',
    'Choose where Setup should install Anime Vault.',
    'An Anime Vault installation was found at:' + #13#10 + ExistingDirectory, True, False);
  InstallMode.Add('Update the existing installation');
  InstallMode.Add('Choose an installation folder');
  InstallMode.SelectedValueIndex := 0;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if PageID = InstallMode.ID then
    Result := (ExistingDirectory = '') or WizardSilent
  else if PageID = wpSelectDir then
    Result := (ExistingDirectory <> '') and not WizardSilent and (InstallMode.SelectedValueIndex = 0);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  if (CurPageID = InstallMode.ID) and (InstallMode.SelectedValueIndex = 0) then
    WizardForm.DirEdit.Text := ExistingDirectory;
  Result := True;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (CurPageID = wpReady) and ContainsAnimeVault(WizardDirValue) then
    WizardForm.ReadyLabel.Caption := 'Setup is ready to update the existing Anime Vault installation.'
  else if CurPageID = wpReady then
    WizardForm.ReadyLabel.Caption := 'Setup is ready to install Anime Vault.';
end;

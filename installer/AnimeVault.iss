; Build using Inno Setup 7 (6.4+ is also supported).
#ifndef AppVersion
  #define AppVersion "1.2.0"
#endif
#define ProjectRoot SourcePath + ".."

[Setup]
AppId={{BB4AB6A4-91CC-4BBF-B367-BC22D14E8C37}
AppName=Anime Vault
AppVersion={#AppVersion}
AppPublisher=Agent47c
AppPublisherURL=https://github.com/Agent47c/Anime-Vault
AppSupportURL=https://github.com/Agent47c/Anime-Vault/issues
AppUpdatesURL=https://github.com/Agent47c/Anime-Vault
DefaultDirName=C:\Program Files\Anime Vault
UsePreviousAppDir=no
DisableDirPage=yes
DefaultGroupName=Anime Vault
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir={#ProjectRoot}\dist\installer
OutputBaseFilename=AnimeVault-Setup-{#AppVersion}-windows-x64
SetupIconFile={#ProjectRoot}\assets\app.ico
UninstallDisplayIcon={app}\AnimeVault.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110
AppMutex=Global\AnimeVault.Installed.Desktop,AnimeVault.Installed.Desktop
CloseApplications=yes
CloseApplicationsFilter=*.exe,*.dll
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#ProjectRoot}\dist\AnimeVault\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs restartreplace
Source: "{#ProjectRoot}\docs\INSTALLER_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion restartreplace

[Icons]
Name: "{autoprograms}\Anime Vault"; Filename: "{app}\AnimeVault.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Anime Vault"; Filename: "{app}\AnimeVault.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\AnimeVault.exe"; Description: "Launch Anime Vault"; Flags: nowait postinstall skipifsilent unchecked runasoriginaluser

[Code]
procedure KillProcess(const ExeName: String);
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM ' + ExeName, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function IsFileLocked(const FileName: String): Boolean;
var
  TestName: String;
begin
  Result := False;
  if not FileExists(FileName) then Exit;
  TestName := FileName + '.upgrade_lock_test';
  if FileExists(TestName) then
    DeleteFile(TestName);
  if RenameFile(FileName, TestName) then
  begin
    RenameFile(TestName, FileName);
    Result := False;
  end
  else
  begin
    Result := True;
  end;
end;

function EnsureAppClosed(): Boolean;
var
  TargetExe, HostExe: String;
  Retries: Integer;
  MsgResult: Integer;
begin
  Result := True;
  TargetExe := ExpandConstant('{app}\AnimeVault.exe');
  HostExe := ExpandConstant('{app}\engine\AnimeVaultTorrentHost.exe');

  repeat
    KillProcess('AnimeVault.exe');
    KillProcess('AnimeVaultTorrentHost.exe');
    
    Retries := 0;
    while (IsFileLocked(TargetExe) or IsFileLocked(HostExe)) and (Retries < 20) do
    begin
      Sleep(250);
      KillProcess('AnimeVault.exe');
      KillProcess('AnimeVaultTorrentHost.exe');
      Retries := Retries + 1;
    end;

    if IsFileLocked(TargetExe) or IsFileLocked(HostExe) then
    begin
      MsgResult := MsgBox(
        'Anime Vault is currently running or locked by Windows.' + #13#10 + #13#10 +
        'Please close Anime Vault (or end task in Task Manager), then click Retry to continue the upgrade.',
        mbError, MB_RETRYCANCEL
      );
      if MsgResult <> IDRETRY then
      begin
        Result := False;
        Exit;
      end;
    end
    else
      Break;
  until False;
end;

procedure StopRunningProcesses();
begin
  EnsureAppClosed();
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  KillProcess('AnimeVault.exe');
  KillProcess('AnimeVaultTorrentHost.exe');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if CompareText(ExpandConstant('{app}'), 'C:\Program Files\Anime Vault') <> 0 then
    Result := 'This setup installs Anime Vault in C:\Program Files\Anime Vault. Please use the default location.';
  if not EnsureAppClosed() then
    Result := 'Installation cancelled: Anime Vault executable is in use and could not be closed.';
end;

// No user-data files, migration tasks, URL handlers, native-host registration or
// user-data deletion rules are installed. Uninstall removes program files only.

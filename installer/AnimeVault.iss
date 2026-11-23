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
UninstallDisplayIcon={app}\AnimeVault.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110
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
Name: "{autoprograms}\Anime Vault"; Filename: "{app}\AnimeVault.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Anime Vault"; Filename: "{app}\AnimeVault.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\AnimeVault.exe"; Description: "Launch Anime Vault"; Flags: nowait postinstall skipifsilent unchecked runasoriginaluser

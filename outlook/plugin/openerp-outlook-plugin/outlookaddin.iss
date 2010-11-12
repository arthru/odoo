; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{AF02E62E-3A5A-4E86-B4CF-03F2B2AC25BF}
AppName=Openerp Outlook Addin
AppVersion=1.0
AppVerName=Openerp Outlook Addin 1.0
AppPublisher=Openerp SA
AppPublisherURL=http://www.openerp.com/
AppSupportURL=http://www.openerp.com/
AppUpdatesURL=http://www.openerp.com/
DefaultDirName={pf}\Openerp Outlook Addin
DefaultGroupName=Openerp Outlook Addin
DisableProgramGroupPage=true
OutputBaseFilename=openerp-outlook-addin
Compression=lzma
SolidCompression=true
UserInfoPage=true
UninstallDisplayIcon={app}\*
VersionInfoVersion=1.0
VersionInfoCompany=OpenERP
VersionInfoDescription=OpenERP Outlook Addin
VersionInfoProductName=OpenERP
VersionInfoProductVersion=1.0
ChangesAssociations=true

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "basque"; MessagesFile: "compiler:Languages\Basque.isl"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "catalan"; MessagesFile: "compiler:Languages\Catalan.isl"
Name: "czech"; MessagesFile: "compiler:Languages\Czech.isl"
Name: "danish"; MessagesFile: "compiler:Languages\Danish.isl"
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "finnish"; MessagesFile: "compiler:Languages\Finnish.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "hebrew"; MessagesFile: "compiler:Languages\Hebrew.isl"
Name: "hungarian"; MessagesFile: "compiler:Languages\Hungarian.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "norwegian"; MessagesFile: "compiler:Languages\Norwegian.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "slovak"; MessagesFile: "compiler:Languages\Slovak.isl"
Name: "slovenian"; MessagesFile: "compiler:Languages\Slovenian.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "C:\workspace\openerp-outlook-plugin\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Messages]
AboutSetupNote=Inno Setup Preprocessor home page:%nhttp://ispp.sourceforge.net/


[Run]
Filename: "{app}\Register-plugin.bat"; StatusMsg: "Registering Outlook Addin";
[UninstallDelete]
Type: files; Name: "{app}\Openerp Outlook Addin\*"
Type: dirifempty; Name: "{app}\Openerp Outlook Addin"

[UninstallRun]
Filename: "{app}\Unregister-plugin.bat"; StatusMsg: "Unregistering Outlook Addin";


[Code]
function InitializeSetup(): Boolean;
begin
    Result := true;

    if not RegKeyExists( HKLM, 'Software\Python\PythonCore') then begin
        Result := MsgBox(
              'Python appears to not be installed.' + #13 + #13 +
              'This addin requires Python 2.5 or above installed with compatible pywin32 for python for working.'+ #13 + #13 +
              'If you know that Python is installed, you may with to continue.' + #13 + #13 +
              'Continue with installation?',
              mbConfirmation, MB_YESNO) = idYes;
    end;
    if not RegKeyExists( HKCU, 'Software\Microsoft\Office\Outlook') then begin
        Result := MsgBox(
              'Outlook appears to not be installed.' + #13 + #13 +
              'This addin only works with Microsoft Outlook 2000 and later - it' + #13 +
              'does not work with Outlook express.' + #13 + #13 +
              'If you know that Outlook is installed, you may with to continue.' + #13 + #13 +
              'Continue with installation?',
              mbConfirmation, MB_YESNO) = idYes;
    end;
    while Result  do begin
        if not CheckForMutexes('_outlook_mutex_') then
            break;

          Result := MsgBox(
              'You must close Outlook before OpenERP Outlook Addin can be installed.' + #13 + #13 +
              'Please close all Outlook Windows (using "File->Exit and Log off"' + #13 +
              'if available) and click Retry, or click Cancel to exit the installation.'+ #13 + #13 +
              'If this message persists after closing all Outlook windows, you may' + #13 +
              'need to log off from Windows, and try again.',
              mbConfirmation, MB_RETRYCANCEL) = idRetry;
    end;
end;


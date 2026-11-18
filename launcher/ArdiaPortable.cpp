#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <filesystem>
#include <string>
#include <vector>
#include <cwctype>
#include <cstdint>
#include <cwchar>
#include "ArdiaLaunchFlags.h"
#pragma comment(lib,"advapi32.lib")
#pragma comment(lib,"shell32.lib")
namespace fs=std::filesystem;
static std::wstring q(const std::wstring &v){
  std::wstring r=L"\"";unsigned slashes=0;
  for(wchar_t c:v){if(c==L'\\'){++slashes;continue;}
    if(c==L'\"'){r.append(slashes*2+1,L'\\');r+=c;slashes=0;continue;}
    r.append(slashes,L'\\');slashes=0;r+=c;}
  r.append(slashes*2,L'\\');r+=L'\"';return r;
}
static int fail(const std::wstring &message){MessageBoxW(nullptr,message.c_str(),L"Ardia Portable",MB_OK|MB_ICONERROR);return 2;}
int WINAPI wWinMain(HINSTANCE,HINSTANCE,PWSTR,int){
 try{
  std::wstring location(32768,L'\0'); DWORD n=GetModuleFileNameW(nullptr,location.data(),DWORD(location.size()));
  if(!n||n>=location.size())return fail(L"Cannot determine portable launcher location.");
  location.resize(n);fs::path root=fs::path(location).parent_path();
  fs::path app=root/L"App"/L"Ardia"/L"Ardia.exe", data=root/L"Data"/L"Ardia";
  if(!fs::is_regular_file(app)||!fs::is_regular_file(app.parent_path()/L"ArdiaApp.dll")||!fs::is_regular_file(app.parent_path()/L"chrome.dll"))
    return fail(L"The Ardia application files are incomplete. Reinstall the binaries without removing Data.");
  // Do not follow a Data junction/symlink that redirects browser writes into host directories.
  for(const auto &dir:{root/L"Data",data}){
    DWORD attr=GetFileAttributesW(dir.c_str());
    if(attr!=INVALID_FILE_ATTRIBUTES && (attr&FILE_ATTRIBUTE_REPARSE_POINT))return fail(L"Portable Data is a junction/symlink; refusing host redirection.");
  }
  std::error_code ec;fs::create_directories(data,ec);if(ec)return fail(L"Cannot create portable data folder: "+data.wstring());
  if(!fs::is_directory(data))return fail(L"Portable Data path is not a directory.");
  int argc=0;LPWSTR* argv=CommandLineToArgvW(GetCommandLineW(),&argc);
  if(!argv)return fail(L"Cannot parse command line.");
  std::vector<std::wstring> forwarded; bool coexistenceTest=false; bool useDefaultFlags=true;
  for(int i=1;i<argc;i++){
    std::wstring arg=argv[i],lower=arg;
    for(auto &c:lower)c=std::towlower(c);
    // Enforced profile ownership: do not permit arbitrary Chromium profile overrides.
    if(lower==L"--user-data-dir"||lower.rfind(L"--user-data-dir=",0)==0||
       lower==L"--disk-cache-dir"||lower.rfind(L"--disk-cache-dir=",0)==0){LocalFree(argv);return fail(L"External profile/cache overrides are disabled to protect portable data.");}
    if(arg==L"--allow-installed-coexistence-test"){coexistenceTest=true;continue;}
    // Launcher-only troubleshooting switch; never forward it to Ardia itself.
    if(lower==L"--portable-no-default-flags"){useDefaultFlags=false;continue;}
    if(arg==L"--portable-healthcheck"){
      fs::path health=data/L"portable-launcher.check";
      HANDLE f=CreateFileW(health.c_str(),GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
      if(f==INVALID_HANDLE_VALUE){LocalFree(argv);return 3;} DWORD written=0;const char* check="portable-root-ok\n";
      BOOL ok=WriteFile(f,check,17,&written,nullptr);CloseHandle(f);LocalFree(argv);
      return (ok && written==17)?0:4;
    }
    forwarded.push_back(arg);
  }
  LocalFree(argv);
  // Experimental options are supplied by default, ahead of user arguments.
  // Known/unknown switch behavior depends on the exact upstream browser build.
  const auto browserArgs=ardia_portable::BuildBrowserArguments(forwarded,useDefaultFlags);
  std::wstring args;
  for(const auto& flag:browserArgs)args+=L" "+q(flag);
  // The installed app uses this verified HKCU browser capability key. Avoid collisions by default.
  HKEY installed=nullptr;
  if(RegOpenKeyExW(HKEY_CURRENT_USER,L"Software\\Clients\\StartMenuInternet\\Ardia",0,KEY_READ,&installed)==ERROR_SUCCESS){
    RegCloseKey(installed);
    if(!coexistenceTest)return fail(L"An installed Ardia browser is registered on this account. Portable coexistence is not validated; refusing to risk its browser registrations. Only test --allow-installed-coexistence-test on a disposable VM.");
  }
  // Prevent concurrent launchers from opening the same portable profile directory.
  uint64_t hash=14695981039346656037ull;
  for(wchar_t c:root.wstring()){hash^=uint64_t(std::towlower(c));hash*=1099511628211ull;}
  std::wstring name=L"Local\\ArdiaPortable_"+std::to_wstring(hash);
  HANDLE single=CreateMutexW(nullptr,TRUE,name.c_str());
  if(!single)return fail(L"Cannot reserve the portable browser profile lock.");
  if(GetLastError()==ERROR_ALREADY_EXISTS){CloseHandle(single);return fail(L"This portable Ardia folder is already running. Reuse the existing browser window or close it first.");}
  // Only inherited by this application and its children: unrelated host processes are not modified.
  if(!SetEnvironmentVariableW(L"ARDIA_DATA_DIR",data.c_str())||
     !SetEnvironmentVariableW(L"ARDIA_CONFIG_DIR",data.c_str()))return fail(L"Cannot configure Ardia portable profile.");
  // Keep app-owned files in portable Data; don't alter global USERPROFILE/APPDATA/TEMP.
  std::wstring command=q(app.wstring())+args;
  STARTUPINFOW si{};si.cb=sizeof(si);PROCESS_INFORMATION pi{};
  std::vector<wchar_t> buffer(command.begin(),command.end());buffer.push_back(0);
  if(!CreateProcessW(app.c_str(),buffer.data(),nullptr,nullptr,FALSE,0,nullptr,app.parent_path().c_str(),&si,&pi)){
    DWORD code=GetLastError();ReleaseMutex(single);CloseHandle(single);
    return fail(L"Ardia could not launch (Windows error "+std::to_wstring(code)+L").");
  }
  CloseHandle(pi.hThread);
  // No kill-on-close: preserving an active browser session is safer than force-killing children.
  WaitForSingleObject(pi.hProcess,INFINITE);
  DWORD exit=0;GetExitCodeProcess(pi.hProcess,&exit);CloseHandle(pi.hProcess);
  ReleaseMutex(single);CloseHandle(single);
  return int(exit);
 }catch(const std::exception&){return fail(L"Ardia Portable launcher failed unexpectedly. Data was not deleted.");}
}

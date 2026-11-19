// Ardia Portable (community launcher). Original code, no shell registrations.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <tlhelp32.h>
#include <string>
#include <vector>
#include <cwctype>
#include <cwchar>
#include <cstdint>
#include <initializer_list>
#include "launch_flags.h"
#include "data_layout.h"

static void fail(const std::wstring& reason) {
    MessageBoxW(nullptr, reason.c_str(), L"Ardia Portable", MB_OK | MB_ICONERROR);
}
static std::wstring quote(const std::wstring& s) {
    std::wstring out = L"\"";
    unsigned backslashes = 0;
    for (wchar_t ch : s) {
        if (ch == L'\\') { ++backslashes; continue; }
        if (ch == L'"') { out.append(backslashes * 2 + 1, L'\\'); out.push_back(L'"'); backslashes = 0; continue; }
        out.append(backslashes, L'\\'); backslashes = 0; out.push_back(ch);
    }
    out.append(backslashes * 2, L'\\'); out.push_back(L'"');
    return out;
}
static std::wstring lower(std::wstring s) {
    for (auto &c : s) c = static_cast<wchar_t>(towlower(c));
    return s;
}
static std::wstring executablePath() {
    std::vector<wchar_t> buffer(32768);
    DWORD n = GetModuleFileNameW(nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
    if (!n || n >= buffer.size()) return L"";
    return std::wstring(buffer.data(), n);
}
static bool isFile(const std::wstring& name) {
    DWORD att = GetFileAttributesW(name.c_str());
    return att != INVALID_FILE_ATTRIBUTES && !(att & FILE_ATTRIBUTE_DIRECTORY);
}
static bool isDir(const std::wstring& name) {
    DWORD att = GetFileAttributesW(name.c_str());
    return att != INVALID_FILE_ATTRIBUTES && (att & FILE_ATTRIBUTE_DIRECTORY);
}
// Never allow an existing file, junction or symbolic link as an owned data folder.
// Links in the *installed* AppData tree pointing TO these real folders are external,
// user-approved host integration; this launcher neither creates nor removes them.
static bool mkRealDir(const std::wstring& name) {
    DWORD attr = GetFileAttributesW(name.c_str());
    if (attr != INVALID_FILE_ATTRIBUTES) {
        return (attr & FILE_ATTRIBUTE_DIRECTORY) != 0 && (attr & FILE_ATTRIBUTE_REPARSE_POINT) == 0;
    }
    if (!CreateDirectoryW(name.c_str(), nullptr)) return false;
    attr = GetFileAttributesW(name.c_str());
    return attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY)
           && !(attr & FILE_ATTRIBUTE_REPARSE_POINT);
}
// A legacy directory containing *even an empty subfolder* is considered user data.
// Errors fail closed to avoid accidentally initializing an unrelated fresh profile.
static bool hasContents(const std::wstring& directory, bool& hasData) {
    hasData = false;
    WIN32_FIND_DATAW entry = {};
    const std::wstring mask = directory + L"\\*";
    HANDLE find = FindFirstFileW(mask.c_str(), &entry);
    if (find == INVALID_HANDLE_VALUE) {
        DWORD code = GetLastError();
        return code == ERROR_FILE_NOT_FOUND || code == ERROR_NO_MORE_FILES;
    }
    do {
        if (wcscmp(entry.cFileName, L".") && wcscmp(entry.cFileName, L"..")) {
            hasData = true;
            break;
        }
    } while (FindNextFileW(find, &entry));
    DWORD status = GetLastError();
    FindClose(find);
    return hasData || status == ERROR_NO_MORE_FILES;
}
// Detect application state outside the Chromium User Data subfolder.
// An empty directory itself counts as user state, even when it has no files.
static bool hasOtherContents(const std::wstring& directory, const wchar_t* exceptName, bool& hasData) {
    hasData = false;
    WIN32_FIND_DATAW item = {};
    HANDLE find = FindFirstFileW((directory + L"\\*").c_str(), &item);
    if (find == INVALID_HANDLE_VALUE) {
        DWORD error = GetLastError();
        return error == ERROR_FILE_NOT_FOUND || error == ERROR_NO_MORE_FILES;
    }
    do {
        if (wcscmp(item.cFileName, L".") && wcscmp(item.cFileName, L"..")
                && _wcsicmp(item.cFileName, exceptName) != 0) {
            hasData = true; break;
        }
    } while (FindNextFileW(find, &item));
    DWORD error = GetLastError();
    FindClose(find);
    return hasData || error == ERROR_NO_MORE_FILES;
}
static uint64_t fnv(const std::wstring& s) {
    uint64_t hash = 14695981039346656037ull;
    for (wchar_t c : lower(s)) { hash ^= static_cast<uint16_t>(c); hash *= 1099511628211ull; }
    return hash;
}
static std::wstring environmentPath(const wchar_t* key) {
    DWORD needed = GetEnvironmentVariableW(key, nullptr, 0);
    if (!needed || needed > 32768) return L"";
    std::vector<wchar_t> buf(needed);
    DWORD size = GetEnvironmentVariableW(key, buf.data(), needed);
    if (!size || size >= needed) return L"";
    return std::wstring(buf.data(), size);
}
static bool isReparseDir(const std::wstring& path) {
    DWORD attr = GetFileAttributesW(path.c_str());
    return attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY)
           && (attr & FILE_ATTRIBUTE_REPARSE_POINT);
}
static bool anotherArdiaRunning(const std::wstring& ownImage) {
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE) return true; // fail closed if shared host path
    PROCESSENTRY32W e = {}; e.dwSize = sizeof(e);
    bool found = false;
    if (Process32FirstW(snap, &e)) do {
        if (_wcsicmp(e.szExeFile, L"Ardia.exe") != 0) continue;
        HANDLE p = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, e.th32ProcessID);
        if (!p) { found = true; break; } // could be installed: conservative
        wchar_t path[32768]; DWORD cap = 32768;
        if (!QueryFullProcessImageNameW(p, 0, path, &cap) || lower(path) != lower(ownImage)) found = true;
        CloseHandle(p);
        if (found) break;
    } while (Process32NextW(snap, &e));
    CloseHandle(snap);
    return found;
}
static bool hasRunningApp(const std::wstring& expected) {
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE) return true; // conservative: don't release lock early
    PROCESSENTRY32W e = {}; e.dwSize = sizeof(e);
    bool found = false;
    if (Process32FirstW(snap, &e)) do {
        // Ignore processes from other Ardia installations; exact image path check.
        if (_wcsicmp(e.szExeFile, L"Ardia.exe") != 0 && _wcsicmp(e.szExeFile, L"chrome.exe") != 0) continue;
        HANDLE p = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, FALSE, e.th32ProcessID);
        if (!p) continue;
        wchar_t name[32768]; DWORD cap = 32768;
        if (GetExitCodeProcess(p, &cap) && cap == STILL_ACTIVE) {
            cap = 32768;
            if (QueryFullProcessImageNameW(p, 0, name, &cap) && lower(name) == lower(expected)) found = true;
        }
        CloseHandle(p);
        if (found) break;
    } while (Process32NextW(snap, &e));
    CloseHandle(snap);
    return found;
}
int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    std::wstring launcher = executablePath();
    if (launcher.empty()) { fail(L"Cannot resolve launcher location."); return 1; }
    size_t slash = launcher.find_last_of(L"\\/");
    if (slash == std::wstring::npos) { fail(L"Invalid executable path."); return 1; }
    std::wstring root = launcher.substr(0, slash);
    std::wstring app = root + L"\\App\\Ardia\\Ardia.exe";
    const std::wstring data = root + L"\\Data";
    const std::wstring localRoot = data + L"\\Local";
    const std::wstring localArdia = localRoot + L"\\Ardia";
    const std::wstring newProfile = localArdia + L"\\User Data";
    const std::wstring roamingRoot = data + L"\\Roaming";
    const std::wstring roamingArdia = roamingRoot + L"\\Ardia";
    const std::wstring legacyProfile = data + L"\\Profile";
    if (!isFile(app)) { fail(L"Missing App\\Ardia\\Ardia.exe. Reinstall without deleting Data."); return 2; }
    if (!mkRealDir(data)) {
        fail(L"Portable Data is unwritable or is a junction/symlink. No files removed."); return 3;
    }
    const bool windowsMirror = ARDIA_PORTABLE_WINDOWS_DATA_LAYOUT;
    // Legacy profile takes priority when a mirror build upgrades a populated b1r5 profile.
    // A legacy-selected build will NEVER silently redirect a populated mirror profile.
    DWORD legacyAttrs = GetFileAttributesW(legacyProfile.c_str());
    if (legacyAttrs != INVALID_FILE_ATTRIBUTES &&
        ((legacyAttrs & FILE_ATTRIBUTE_DIRECTORY) == 0 || (legacyAttrs & FILE_ATTRIBUTE_REPARSE_POINT))) {
        fail(L"Data\\Profile is not a real directory. Refusing to follow a link."); return 3;
    }
    bool legacyHasData = false;
    if (legacyAttrs != INVALID_FILE_ATTRIBUTES && !hasContents(legacyProfile, legacyHasData)) {
        fail(L"Cannot inspect the legacy profile safely. No changes made."); return 3;
    }
    // Check the other layout without creating anything under it. Existing reparse
    // points at any level are rejected, never traversed into installed user data.
    for (const std::wstring& part : {localRoot, localArdia, newProfile, roamingRoot, roamingArdia}) {
        DWORD attrs = GetFileAttributesW(part.c_str());
        if (attrs != INVALID_FILE_ATTRIBUTES &&
            ((attrs & FILE_ATTRIBUTE_DIRECTORY) == 0 || (attrs & FILE_ATTRIBUTE_REPARSE_POINT))) {
            fail(L"Existing portable Data layout contains a file or junction/symlink: " + part);
            return 3;
        }
    }
    bool newHasData = false;
    if (isDir(newProfile) && !hasContents(newProfile, newHasData)) {
        fail(L"Cannot safely inspect the existing Windows-style browser profile."); return 3;
    }
    bool mirrorAppState = false, mirrorRoamingState = false;
    if ((isDir(localArdia) && !hasOtherContents(localArdia, L"User Data", mirrorAppState)) ||
        (isDir(roamingArdia) && !hasContents(roamingArdia, mirrorRoamingState))) {
        fail(L"Cannot inspect the other layout's application data safely."); return 3;
    }
    const bool mirrorHasData = newHasData || mirrorAppState || mirrorRoamingState;
    if (legacyHasData && mirrorHasData) {
        fail(L"Both legacy Data\\Profile and Windows-style Data\\Local/Ardia or Roaming/Ardia contain data.\n"
             L"Refusing to merge them. Back up Data and read UPGRADE-AND-LINKS.md."); return 3;
    }
    if (!windowsMirror && mirrorHasData) {
        fail(L"This launcher was built for Data\\Profile, but a populated Windows-style profile exists.\n"
             L"Use the Windows-style build or back up Data and migrate manually."); return 3;
    }
    if (windowsMirror) {
        if (!mkRealDir(localRoot) || !mkRealDir(localArdia) || !mkRealDir(newProfile)
                || !mkRealDir(roamingRoot) || !mkRealDir(roamingArdia)) {
            fail(L"Cannot create the Windows-style portable Data folders."); return 3;
        }
    } else if (!mkRealDir(legacyProfile)) {
        fail(L"Cannot create Data\\Profile as a real directory."); return 3;
    }
    const bool useLegacy = !windowsMirror || legacyHasData;
    const std::wstring profile = useLegacy ? legacyProfile : newProfile;
    const std::wstring ardiaData = useLegacy ? legacyProfile : localArdia;
    wchar_t mutexName[100]; swprintf_s(mutexName, L"Local\\ArdiaPortable-%016llX", static_cast<unsigned long long>(fnv(root)));
    HANDLE guard = CreateMutexW(nullptr, FALSE, mutexName);
    if (!guard) { fail(L"Cannot create instance lock."); return 4; }
    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        fail(L"This ArdiaPortable folder already has an active launcher. Close it before starting another.");
        CloseHandle(guard); return 5;
    }
    // Manual links at the *installed* Ardia path may intentionally share this profile.
    // If such host links exist, do not START our browser while another Ardia.exe runs.
    // This cannot stop someone later starting the installed app; still require discipline.
    if (!useLegacy) {
        std::wstring hostLocal = environmentPath(L"LOCALAPPDATA");
        std::wstring hostRoaming = environmentPath(L"APPDATA");
        bool sharedHostProfile = (!hostLocal.empty() && isReparseDir(hostLocal + L"\\Ardia"))
                              || (!hostRoaming.empty() && isReparseDir(hostRoaming + L"\\Ardia"));
        if (sharedHostProfile && anotherArdiaRunning(app)) {
            fail(L"An installed Ardia is running while an Ardia AppData link may share its profile.\n"
                 L"Close all installed Ardia processes before starting this portable copy.");
            CloseHandle(guard); return 8;
        }
    }
    // Expose the COMPILED layout name to the launched browser for diagnostic proof.
    // This is not an OS registration and is inherited only by this process tree.
    if (!SetEnvironmentVariableW(L"ARDIA_PORTABLE_DATA_LAYOUT", ARDIA_PORTABLE_LAYOUT_NAME)) {
        fail(L"Cannot set compiled portable data layout marker."); CloseHandle(guard); return 4;
    }
    // Chromium user-data-dir path is selected BEFORE browser initialization.
    if (!SetEnvironmentVariableW(L"ARDIA_DATA_DIR", ardiaData.c_str())) {
        fail(L"Cannot set Ardia's portable data folder before startup."); CloseHandle(guard); return 4;
    }
    if (!useLegacy) {
        // Only this launcher's own process and its descendants receive these values.
        // These environment variables DO NOT override every Windows Known Folder API;
        // actual roaming and notification writes require real Windows runtime auditing.
        if (!SetEnvironmentVariableW(L"LOCALAPPDATA", localRoot.c_str()) ||
            !SetEnvironmentVariableW(L"APPDATA", roamingRoot.c_str())) {
            fail(L"Cannot set per-child APPDATA/LOCALAPPDATA layout."); CloseHandle(guard); return 4;
        }
    }
    std::wstring cmd = quote(app) + L" --user-data-dir=" + quote(profile)
                     + ARDIA_PORTABLE_DEFAULT_FLAGS;
    // Pass all additional command line arguments verbatim (Windows provides raw UTF-16 string).
    const wchar_t* tail = GetCommandLineW();
    // GetCommandLineW includes our executable; skip the first token while respecting quotes.
    if (*tail == L'"') { ++tail; while (*tail && *tail != L'"') ++tail; if (*tail) ++tail; }
    else { while (*tail && !iswspace(*tail)) ++tail; }
    while (*tail && iswspace(*tail)) ++tail;
    if (*tail) {
        // Forbid overrides of the storage destination supplied by the launcher.
        std::wstring supplied = lower(tail);
        if (supplied.find(L"--user-data-dir") != std::wstring::npos) {
            fail(L"Cannot override --user-data-dir; ArdiaPortable controls its selected profile path.");
            CloseHandle(guard); return 7;
        }
        cmd += L" "; cmd += tail;
    }
    std::vector<wchar_t> command(cmd.begin(), cmd.end()); command.push_back(0);
    STARTUPINFOW si = {}; si.cb = sizeof(si);
    PROCESS_INFORMATION pi = {};
    BOOL ok = CreateProcessW(app.c_str(), command.data(), nullptr, nullptr, FALSE,
                             CREATE_UNICODE_ENVIRONMENT, nullptr, (root + L"\\App\\Ardia").c_str(), &si, &pi);
    if (!ok) {
        DWORD err = GetLastError();
        fail(L"Cannot launch Ardia.exe (Windows error " + std::to_wstring(err) + L").");
        CloseHandle(guard); return 6;
    }
    CloseHandle(pi.hThread);
    WaitForSingleObject(pi.hProcess, INFINITE);
    CloseHandle(pi.hProcess);
    // Let Chromium subprocesses exit naturally; never kill installed or portable processes.
    // Wait until no further processes with this EXACT application image path remain.
    while (hasRunningApp(app)) Sleep(800);
    CloseHandle(guard);
    return 0;
}

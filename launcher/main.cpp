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
static bool mkDir(const std::wstring& name) {
    return CreateDirectoryW(name.c_str(), nullptr) || GetLastError() == ERROR_ALREADY_EXISTS;
}
static uint64_t fnv(const std::wstring& s) {
    uint64_t hash = 14695981039346656037ull;
    for (wchar_t c : lower(s)) { hash ^= static_cast<uint16_t>(c); hash *= 1099511628211ull; }
    return hash;
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
    std::wstring data = root + L"\\Data";
    std::wstring profile = data + L"\\Profile";
    if (!isFile(app)) { fail(L"Missing App\\Ardia\\Ardia.exe. Reinstall without deleting Data."); return 2; }
    if (!mkDir(data) || !mkDir(profile) || !isDir(profile)) { fail(L"Cannot create portable Data\\Profile. Check write permissions."); return 3; }
    DWORD dataAttrs = GetFileAttributesW(data.c_str());
    if (dataAttrs == INVALID_FILE_ATTRIBUTES || (dataAttrs & FILE_ATTRIBUTE_REPARSE_POINT)) {
        fail(L"Data must be a real folder, not a junction or symbolic link."); return 3;
    }
    // Prevent link/junction reparse redirection of browser profile outside the package.
    DWORD attrs = GetFileAttributesW(profile.c_str());
    if (attrs == INVALID_FILE_ATTRIBUTES || (attrs & FILE_ATTRIBUTE_REPARSE_POINT)) {
        fail(L"Data\\Profile must be a real directory, not a junction or symbolic link."); return 3;
    }
    wchar_t mutexName[100]; swprintf_s(mutexName, L"Local\\ArdiaPortable-%016llX", static_cast<unsigned long long>(fnv(root)));
    HANDLE guard = CreateMutexW(nullptr, FALSE, mutexName);
    if (!guard) { fail(L"Cannot create instance lock."); return 4; }
    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        fail(L"This ArdiaPortable folder already has an active launcher. Close it before starting another.");
        CloseHandle(guard); return 5;
    }
    // Chromium user-data-dir path is selected BEFORE browser initialization.
    if (!SetEnvironmentVariableW(L"ARDIA_DATA_DIR", profile.c_str())) {
        fail(L"Cannot prepare the per-process portable profile variable."); CloseHandle(guard); return 4;
    }
    std::wstring cmd = quote(app) + L" --user-data-dir=" + quote(profile)
                     + L" --no-default-browser-check --disable-background-mode";
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
            fail(L"Cannot override --user-data-dir; ArdiaPortable always uses Data\\Profile.");
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

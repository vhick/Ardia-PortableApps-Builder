// Platform-independent unit tests for the same C++ argument helper compiled
// into ArdiaPortable.exe. No browser, installed profile, or Windows GUI needed.
#include "../launcher/ArdiaLaunchFlags.h"
#include <algorithm>
#include <cassert>
#include <iostream>
#include <string>
#include <vector>

int main() {
    using namespace ardia_portable;
    const auto defaults = BuildBrowserArguments({});
    assert(defaults.size() == 6);
    const std::vector<std::wstring> expected = {
        L"--disable-ardia-update",
        L"--no-default-browser-check",
        L"--disable-logging",
        L"--disable-breakpad",
        L"--disable-machine-id",
        L"--disable-encryption-win"
    };
    assert(defaults == expected);
    assert(BuildBrowserArguments({L"https://example.org/path?q=two words", L"--new-window"}) ==
           (std::vector<std::wstring>{expected[0], expected[1], expected[2],
           expected[3], expected[4], expected[5],
           L"https://example.org/path?q=two words", L"--new-window"}));
    const auto user = BuildBrowserArguments({L"--DISABLE-LOGGING", L"--disable-breakpad=1", L"https://example.org"});
    assert(user.size() == 7);  // Four added defaults + three exact forwarded arguments.
    assert(std::count(user.begin(), user.end(), L"--disable-logging") == 0);
    assert(std::count(user.begin(), user.end(), L"--disable-breakpad") == 0);
    assert(user[4] == L"--DISABLE-LOGGING");
    assert(user[5] == L"--disable-breakpad=1");
    assert(user[6] == L"https://example.org");
    assert(BuildBrowserArguments({L"--disable-encryption-win"}, false) ==
           (std::vector<std::wstring>{L"--disable-encryption-win"}));
    assert(BuildBrowserArguments({}, false).empty());
    assert(SameSwitch(L"--Disable-Machine-Id", L"--disable-machine-id"));
    assert(!SameSwitch(L"--disable-machine-identity", L"--disable-machine-id"));
    std::cout << "PASS: six defaults, order, passthrough, deduplication, opt-out\n";
    return 0;
}

#pragma once
// Ardia portable launch flags. These are intentionally forwarded to the
// browser without claiming that the exact upstream build implements them.
// In particular, the machine-ID and Windows-encryption flags have been used
// by *patched* Chromium/Brave builds and have not been proven in Ardia.
#include <array>
#include <cwctype>
#include <string>
#include <vector>

namespace ardia_portable {
inline constexpr std::array<const wchar_t*, 6> kDefaultBrowserFlags = {
    L"--disable-ardia-update",
    L"--no-default-browser-check",
    L"--disable-logging",
    L"--disable-breakpad",
    L"--disable-machine-id",
    L"--disable-encryption-win"
};

// A flag supplied by the caller is left in its original order and form;
// don't add a second copy of a default flag. Accept --flag=value syntax.
inline bool SameSwitch(const std::wstring& supplied, const std::wstring& flag) {
    auto end = supplied.find(L'=');
    auto name = supplied.substr(0, end);
    if (name.size() != flag.size()) return false;
    for (size_t i = 0; i < name.size(); ++i)
        if (std::towlower(name[i]) != std::towlower(flag[i])) return false;
    return true;
}

inline std::vector<std::wstring> BuildBrowserArguments(
    const std::vector<std::wstring>& userArguments, bool includeDefaults = true) {
    std::vector<std::wstring> result;
    if (includeDefaults) {
        for (const auto* literal : kDefaultBrowserFlags) {
            const std::wstring flag(literal);
            bool userSupplied = false;
            for (const auto& supplied : userArguments) {
                if (SameSwitch(supplied, flag)) { userSupplied = true; break; }
            }
            if (!userSupplied) result.push_back(flag);
        }
    }
    result.insert(result.end(), userArguments.begin(), userArguments.end());
    return result;
}
}  // namespace ardia_portable

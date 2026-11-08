"""List processes locking a Windows file via Restart Manager."""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from pathlib import Path


CCH_RM_SESSION_KEY = 32
CCH_RM_MAX_APP_NAME = 255
CCH_RM_MAX_SVC_NAME = 63
ERROR_MORE_DATA = 234


class RM_UNIQUE_PROCESS(ctypes.Structure):
    _fields_ = (("dwProcessId", wintypes.DWORD), ("ProcessStartTime", wintypes.FILETIME))


class RM_PROCESS_INFO(ctypes.Structure):
    _fields_ = (
        ("Process", RM_UNIQUE_PROCESS),
        ("strAppName", wintypes.WCHAR * (CCH_RM_MAX_APP_NAME + 1)),
        ("strServiceShortName", wintypes.WCHAR * (CCH_RM_MAX_SVC_NAME + 1)),
        ("ApplicationType", wintypes.DWORD),
        ("AppStatus", wintypes.ULONG),
        ("TSSessionId", wintypes.DWORD),
        ("bRestartable", wintypes.BOOL),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    target = str(args.path.resolve())
    restart_manager = ctypes.WinDLL("Rstrtmgr")
    session = wintypes.DWORD()
    key = ctypes.create_unicode_buffer(CCH_RM_SESSION_KEY + 1)
    result = restart_manager.RmStartSession(ctypes.byref(session), 0, key)
    if result != 0:
        raise OSError(result, "RmStartSession failed")
    try:
        resources = (wintypes.LPCWSTR * 1)(target)
        result = restart_manager.RmRegisterResources(session, 1, resources, 0, None, 0, None)
        if result != 0:
            raise OSError(result, "RmRegisterResources failed")
        needed = wintypes.UINT()
        count = wintypes.UINT()
        reasons = wintypes.DWORD()
        result = restart_manager.RmGetList(
            session, ctypes.byref(needed), ctypes.byref(count), None, ctypes.byref(reasons)
        )
        if result == 0:
            print("No locking process reported")
            return
        if result != ERROR_MORE_DATA:
            raise OSError(result, "RmGetList size query failed")
        process_array = (RM_PROCESS_INFO * needed.value)()
        count.value = needed.value
        result = restart_manager.RmGetList(
            session,
            ctypes.byref(needed),
            ctypes.byref(count),
            process_array,
            ctypes.byref(reasons),
        )
        if result != 0:
            raise OSError(result, "RmGetList failed")
        for process in process_array[: count.value]:
            print(
                f"pid={process.Process.dwProcessId}\tapp={process.strAppName}\t"
                f"service={process.strServiceShortName}\trestartable={bool(process.bRestartable)}"
            )
    finally:
        restart_manager.RmEndSession(session)


if __name__ == "__main__":
    main()

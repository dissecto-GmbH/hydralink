#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ctypes import WinError, sizeof, GetLastError
from ctypes.wintypes import BYTE, DWORD, PDWORD, BOOL, ULONG, PULONG, HANDLE, LPCSTR, LPVOID, PBYTE
import ctypes
import re
from typing import Any, Iterable, List, NamedTuple, Tuple

DIGCF_PRESENT = 2
DIGCF_DEVICEINTERFACE = 16
INVALID_HANDLE_VALUE = 0
SPDRP_DRIVER = 9
ERROR_NO_MORE_ITEMS = 259


class GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', ctypes.c_ulong),
        ('Data2', ctypes.c_ushort),
        ('Data3', ctypes.c_ushort),
        ('Data4', ctypes.c_ubyte*8),
    ]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ('cbSize', DWORD),
        ('InterfaceClassGuid', GUID),
        ('Flags', DWORD),
        ('Reserved', PULONG),
    ]


class SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ('cbSize', DWORD),
        ('ClassGuid', GUID),
        ('DevInst', DWORD),
        ('Reserved', PULONG)
    ]


class DEVPROPKEY(ctypes.Structure):
    _fields_ = [
        ('fmtid', GUID),
        ('pid', ULONG)
    ]


CreateFile = ctypes.windll.kernel32.CreateFileA
CreateFile.argtypes = [LPCSTR, DWORD, DWORD, LPVOID, DWORD, DWORD, HANDLE]
CreateFile.restype = HANDLE

CloseHandle = ctypes.windll.kernel32.CloseHandle
CloseHandle.argtypes = [HANDLE]
CloseHandle.restype = BOOL

DeviceIoControl = ctypes.windll.kernel32.DeviceIoControl
DeviceIoControl.argtypes = [HANDLE, DWORD, LPVOID, DWORD, LPVOID, DWORD, PDWORD, LPVOID]
DeviceIoControl.restype = BOOL

SetupDiDestroyDeviceInfoList = ctypes.windll.setupapi.SetupDiDestroyDeviceInfoList
SetupDiDestroyDeviceInfoList.argtypes = [LPVOID]
SetupDiDestroyDeviceInfoList.restype = BOOL

SetupDiGetClassDevs = ctypes.windll.setupapi.SetupDiGetClassDevsA
SetupDiGetClassDevs.argtypes = [ctypes.POINTER(GUID), LPCSTR, DWORD, DWORD]
SetupDiGetClassDevs.restype = LPVOID

SetupDiEnumDeviceInterfaces = ctypes.windll.setupapi.SetupDiEnumDeviceInterfaces
SetupDiEnumDeviceInterfaces.argtypes = [LPVOID, ctypes.POINTER(SP_DEVINFO_DATA),
                                        ctypes.POINTER(GUID), DWORD,
                                        ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)]
SetupDiEnumDeviceInterfaces.restype = BOOL

SetupDiGetDeviceInterfaceDetail = ctypes.windll.setupapi.SetupDiGetDeviceInterfaceDetailA
SetupDiGetDeviceInterfaceDetail.argtypes = [LPVOID, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA), LPVOID,
                                            DWORD, PDWORD, ctypes.POINTER(SP_DEVINFO_DATA)]
SetupDiGetDeviceInterfaceDetail.restype = BOOL

SetupDiGetDeviceInterfacePropertyKeys = ctypes.windll.setupapi.SetupDiGetDeviceInterfacePropertyKeys
SetupDiGetDeviceInterfacePropertyKeys.argtypes = [LPVOID, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
                                                  ctypes.POINTER(DEVPROPKEY), DWORD, PDWORD, DWORD]
SetupDiGetDeviceInterfacePropertyKeys.restype = BOOL

SetupDiGetDeviceRegistryProperty = ctypes.windll.setupapi.SetupDiGetDeviceRegistryPropertyA
SetupDiGetDeviceRegistryProperty.argtypes = [LPVOID, ctypes.POINTER(SP_DEVINFO_DATA),
                                             DWORD, PDWORD, PBYTE, DWORD, PDWORD]
SetupDiGetDeviceRegistryProperty.restype = BOOL

GUID_DEVINTERFACE_USB_DEVICE = GUID(
    0xa5dcbf10, 0x6530, 0x11d2, (ctypes.c_ubyte*8)(0x90, 0x1f, 0x00, 0xc0, 0x4f, 0xb9, 0x51, 0xed))


def wSetupDiGetDeviceInterfaceDetail(g_hdi: Any, did: SP_DEVICE_INTERFACE_DATA) -> Tuple[bytes, SP_DEVINFO_DATA]:
    dwNeeded = DWORD()
    if not SetupDiGetDeviceInterfaceDetail(
        g_hdi, ctypes.byref(did),
        None, 0, ctypes.byref(dwNeeded),
        None
    ):
        if GetLastError() != 122:
            raise WinError()

    devinfo = SP_DEVINFO_DATA()
    devinfo.cbSize = sizeof(devinfo)
    detailData = (ctypes.c_ubyte*dwNeeded.value)()
    detailDataD = ctypes.cast(detailData, PDWORD)
    detailDataD[0] = 8 if sizeof(PDWORD) == 8 else 6
    devinfo.cbSize = sizeof(devinfo)
    if not SetupDiGetDeviceInterfaceDetail(
        g_hdi, ctypes.byref(did),
        detailData, sizeof(detailData), ctypes.byref(dwNeeded),
        ctypes.byref(devinfo)
    ):
        raise WinError()
    assert dwNeeded.value == sizeof(detailData)
    return bytes(detailData), devinfo


def wSetupDiGetDeviceInterfacePropertyKeys(g_hdi: Any, did: SP_DEVICE_INTERFACE_DATA) -> List[DEVPROPKEY]:
    devpropscount = DWORD()
    if not SetupDiGetDeviceInterfacePropertyKeys(
            g_hdi, ctypes.byref(did), None, 0,
            ctypes.byref(devpropscount), 0):
        if ctypes.GetLastError() != 122:
            raise ctypes.WinError()
    PropertyKeyArray = (DEVPROPKEY * devpropscount.value)()
    if not SetupDiGetDeviceInterfacePropertyKeys(
            g_hdi, ctypes.byref(did), PropertyKeyArray, 4,
            ctypes.byref(devpropscount), 0):
        raise ctypes.WinError()
    assert devpropscount.value == len(PropertyKeyArray)
    return list(PropertyKeyArray)


def wSetupDiGetDeviceRegistryProperty(g_hdi: Any, devinfo: SP_DEVINFO_DATA, property_id: int) -> Tuple[bytes, int]:
    RequiredSize = DWORD()
    PropertyRegDataType = DWORD()
    if not SetupDiGetDeviceRegistryProperty(
            g_hdi, ctypes.byref(devinfo), property_id,
            ctypes.byref(PropertyRegDataType),
            None, 0,
            ctypes.byref(RequiredSize)
    ):
        if ctypes.GetLastError() != 122:
            raise ctypes.WinError()
    PropertyBuffer = (BYTE * RequiredSize.value)()
    if not SetupDiGetDeviceRegistryProperty(
            g_hdi, ctypes.byref(devinfo), property_id,
            ctypes.byref(PropertyRegDataType),
            PropertyBuffer, len(PropertyBuffer),
            ctypes.byref(RequiredSize)
    ):
        raise ctypes.WinError()
    assert RequiredSize.value == len(PropertyBuffer)
    return bytes(PropertyBuffer), PropertyRegDataType.value


def wSetupDiEnumDeviceInterfaces(guid: GUID) -> Iterable[Tuple[Any, SP_DEVICE_INTERFACE_DATA]]:
    guidref = ctypes.byref(guid)
    if (g_hdi := SetupDiGetClassDevs(
        guidref,
        None,
        0,
        DIGCF_DEVICEINTERFACE | DIGCF_PRESENT
    )) == INVALID_HANDLE_VALUE:
        raise WinError()

    dwIndex = 0
    while 1:
        did = SP_DEVICE_INTERFACE_DATA()
        did.cbSize = sizeof(did)

        if not SetupDiEnumDeviceInterfaces(
            g_hdi, None, guidref,
            dwIndex, ctypes.byref(did)
        ):
            if GetLastError() != ERROR_NO_MORE_ITEMS:
                raise WinError()
            break

        yield (g_hdi, did)

        dwIndex += 1

    SetupDiDestroyDeviceInfoList(g_hdi)


class FoundUsbDevice(NamedTuple):
    vid: int
    pid: int
    serialnum: str
    path: str
    software_key: str


def list_usb_devices() -> Iterable[FoundUsbDevice]:
    regex = re.compile(r'^\\\\\?\\usb#vid_([a-f0-9]{4})&pid_([a-f0-9]{4})#([^#]*)' +
                       r'#\{a5dcbf10-6530-11d2-901f-00c04fb951ed\}')
    for g_hdi, did in wSetupDiEnumDeviceInterfaces(GUID_DEVINTERFACE_USB_DEVICE):

        detailData, devinfo = wSetupDiGetDeviceInterfaceDetail(g_hdi, did)
        details = detailData[4:]
        devicePath = details[:details.index(b'\x00')].decode('latin1')

        PropertyBuffer, _ = wSetupDiGetDeviceRegistryProperty(g_hdi, devinfo, SPDRP_DRIVER)

        software_key = PropertyBuffer.decode('latin1')
        software_key = software_key[:software_key.find('\x00')]

        m = regex.match(devicePath)
        assert m is not None
        vid, pid, serialnum = int(m[1], 16), int(m[2], 16), m[3]
        yield FoundUsbDevice(
            vid=vid,
            pid=pid,
            serialnum=serialnum,
            software_key=software_key,
            path=devicePath
        )

    SetupDiDestroyDeviceInfoList(g_hdi)

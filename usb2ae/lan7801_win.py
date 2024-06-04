from ctypes import WinError, GetLastError
from ctypes.wintypes import DWORD, HANDLE, LPCSTR, BOOL, LPVOID, LPDWORD
from typing import cast
import ctypes
import struct

from lan7801 import LAN7801_LL

CreateFile = ctypes.windll.kernel32.CreateFileA
CreateFile.argtypes = [LPCSTR, DWORD, DWORD, LPVOID, DWORD, DWORD, HANDLE]
CreateFile.restype = HANDLE

DeviceIoControl = ctypes.windll.kernel32.DeviceIoControl
DeviceIoControl.argtypes = [HANDLE, DWORD, LPVOID, DWORD, LPVOID, DWORD, LPDWORD, LPVOID]
DeviceIoControl.restype = BOOL


class LAN7801_Win(LAN7801_LL):
    def __init__(self) -> None:
        self.handle = CreateFile(b"\\\\.\\LAN7800_IOCTL", 0xc0000000, 3, 0, 3, 0x80, 0)
        if GetLastError():
            raise WinError()

        self.buffer = bytearray(0x1000)
        self.buffer_c = (ctypes.c_char * 0x1000).from_buffer(self.buffer)
        self.DAT_00435984 = 0x10002
        self.DAT_00435980 = 0

    def write_reg(self, address: int, value: int) -> None:
        if value != value & 0xffffffff:
            raise ValueError("Value must be an unsigned 32-bit integer")
        if address != address & 0xfff:
            raise ValueError("Address must be an unsigned 12-bit integer")

        self.buffer[0:4] = struct.pack("<I", self.DAT_00435984)
        self.buffer[4] = 9
        self.buffer[5] = 0
        self.buffer[6] = 0
        self.buffer[7] = 0
        self.buffer[8:12] = struct.pack("<I", self.DAT_00435980)
        self.buffer[12:16] = struct.pack("<I", address)
        self.buffer[16:20] = struct.pack("<I", value)

        outsize = DWORD(0)
        if not DeviceIoControl(
                self.handle, 0x122400,
                self.buffer_c, 20,
                self.buffer_c, 0x1000, ctypes.byref(outsize),
                0):
            raise WinError()

        err = struct.unpack("<I", self.buffer[8:12])[0]
        if err != 0:
            raise IOError(f"WRITE_REGISTER failed with error {err}")

    def read_reg(self, address: int) -> int:
        if address != address & 0xffffffff:
            raise ValueError("Address must be an unsigned 32-bit integer")

        self.buffer[0:4] = struct.pack("<I", self.DAT_00435984)
        self.buffer[4] = 8
        self.buffer[5] = 0
        self.buffer[6] = 0
        self.buffer[7] = 0
        self.buffer[8:12] = struct.pack("<I", self.DAT_00435980)
        self.buffer[12:16] = struct.pack("<I", address)

        outsize = DWORD(0)
        if not DeviceIoControl(
                self.handle, 0x122400,
                self.buffer_c, 18,
                self.buffer_c, 0x1000, ctypes.byref(outsize),
                0):
            raise WinError()

        err = struct.unpack("<I", self.buffer[8:12])[0]
        if err != 0:
            raise IOError(f"READ_REGISTER failed with error {err}")

        res = cast(int, struct.unpack("<I", self.buffer[16:20])[0])
        return res

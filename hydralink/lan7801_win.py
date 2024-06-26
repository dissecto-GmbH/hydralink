from ctypes.wintypes import DWORD, HANDLE, LPCSTR, BOOL, LPVOID, LPDWORD
from typing import Optional, cast
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
    def __init__(self, interface_idx: Optional[int] = None) -> None:
        self.handle = CreateFile(b"\\\\.\\LAN7800_IOCTL", 0xc0000000, 3, 0, 3, 0x80, 0)
        if ctypes.GetLastError():
            raise ctypes.WinError()

        self._buffer = bytearray(0x1000)
        self._buffer_c = (ctypes.c_char * 0x1000).from_buffer(self._buffer)
        self.iidx = 0
        self.oidx = 0x10002
        if interface_idx is not None:
            self.iidx = interface_idx
            self.oidx = 0x20001

    def _xfer(self, buffer: bytes) -> bytes:
        if len(buffer) > len(self._buffer):
            raise ValueError("Too much data to transfer")
        self._buffer[:len(buffer)] = buffer

        outsize = DWORD(0)
        if not DeviceIoControl(
                self.handle, 0x122400,
                self._buffer_c, len(buffer),
                self._buffer_c, len(self._buffer), ctypes.byref(outsize),
                0):
            raise ctypes.WinError()

        if outsize.value > len(self._buffer):
            raise OverflowError(f"Response too large ({outsize.value} > {len(self._buffer)})")

        return bytes(self._buffer[:outsize.value])

    def write_reg(self, address: int, value: int) -> None:
        if value != value & 0xffffffff:
            raise ValueError("Value must be an unsigned 32-bit integer")
        if address != address & 0xfff:
            raise ValueError("Address must be an unsigned 12-bit integer")

        resbuf = self._xfer(struct.pack("<IIIII", self.oidx, 9, self.iidx, address, value))

        err = struct.unpack("<I", resbuf[8:12])[0]
        if err != 0:
            raise IOError(f"WRITE_REGISTER failed with error {err}")

        if len(resbuf) != 17:
            raise IOError(f"Unexpected response length ({len(resbuf)} != 17) to WRITE_REGISTER")

    def read_reg(self, address: int) -> int:
        if address != address & 0xfff:
            raise ValueError("Address must be an unsigned 12-bit integer")

        resbuf = self._xfer(struct.pack("<IIII", self.oidx, 8, self.iidx, address))

        err = struct.unpack("<I", resbuf[8:12])[0]
        if err != 0:
            raise IOError(f"READ_REGISTER failed with error {err}")

        if len(resbuf) != 20:
            raise IOError(f"Unexpected response length ({len(resbuf)} != 20) to READ_REGISTER")

        res = cast(int, struct.unpack("<I", resbuf[16:])[0])
        return res

#! /usr/bin/env python
import ctypes
import struct

from typing import Optional, cast
from hydralink.windows_apis import CloseHandle, CreateFile, DeviceIoControl

from hydralink.lan7801 import LAN7801_LL


class LAN7801_Win(LAN7801_LL):
    class DriverError(Exception):
        pass

    class Busy(DriverError):
        pass

    def __init__(self, interface_idx: Optional[int] = None) -> None:
        self.handle = CreateFile(b"\\\\.\\LAN7800_IOCTL", 0xc0000000, 3, 0, 3, 0x80, 0)
        err = ctypes.GetLastError()
        if err == 2:
            raise FileNotFoundError("Device not found!")
        elif err:
            raise ctypes.WinError()

        self._buffer = bytearray(0x1000)
        self._buffer_c = (ctypes.c_char * 0x1000).from_buffer(self._buffer)
        self.iidx = 0
        self.oidx = 0x10002
        if interface_idx is not None:
            self.iidx = interface_idx
            self.oidx = 0x20001

    def __del__(self) -> None:
        CloseHandle(self.handle)

    def _xfer(self, buffer: bytes) -> bytes:
        if len(buffer) > len(self._buffer):
            raise ValueError("Too much data to transfer")
        self._buffer[:len(buffer)] = buffer

        outsize = ctypes.c_uint32(0)
        if not DeviceIoControl(
                self.handle, 0x122400,
                self._buffer_c, len(buffer),
                self._buffer_c, len(self._buffer), ctypes.byref(outsize),
                0):
            raise ctypes.WinError()

        if outsize.value > len(self._buffer):
            raise OverflowError(f"LAN7801 response too large ({outsize.value} > {len(self._buffer)})")
        if outsize.value < 16:
            raise IOError(f"LAN7801 response too small ({outsize.value} < 16))")

        err = struct.unpack("<I", self._buffer[8:12])[0]
        if err == 4:
            raise LAN7801_Win.Busy("LAN7801 is busy, please retry later or reconnect the device")
        if err != 0:
            raise LAN7801_Win.DriverError(f"LAN7801 DeviceIoControl failed with error {err}")

        return bytes(self._buffer[16:outsize.value])

    def write_reg(self, address: int, value: int) -> None:
        if value != value & 0xffffffff:
            raise ValueError("Value must be an unsigned 32-bit integer")
        if address != address & 0xfff:
            raise ValueError("Address must be an unsigned 12-bit integer")

        resbuf = self._xfer(struct.pack("<IIIII", self.oidx, 9, self.iidx, address, value))

        if len(resbuf) != 1:
            raise IOError(f"Unexpected response length ({len(resbuf)} != 1) to WRITE_REGISTER")

    def read_reg(self, address: int) -> int:
        if address != address & 0xfff:
            raise ValueError("Address must be an unsigned 12-bit integer")

        resbuf = self._xfer(struct.pack("<IIII", self.oidx, 8, self.iidx, address))

        if len(resbuf) != 4:
            raise IOError(f"Unexpected response length ({len(resbuf)} != 4) to READ_REGISTER")

        res = cast(int, struct.unpack("<I", resbuf)[0])
        return res

    def get_adapter_registry_key(self) -> str:
        resbuf = self._xfer(struct.pack("<III", self.oidx, 0x12, self.iidx))
        s = resbuf.decode('UTF-16')
        assert s[-1] == '\x00'
        return s[:-1]

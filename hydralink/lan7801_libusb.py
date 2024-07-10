#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

import usb.core
import struct

from typing import Union, cast

from hydralink.lan7801 import LAN7801_LL


class LAN7801_LibUSB(LAN7801_LL):
    def __init__(self, d: Union[None, int, usb.core.Device] = None) -> None:
        if isinstance(d, usb.core.Device):
            dev = d
        elif isinstance(d, int):
            dev = list(usb.core.find(find_all=True, idVendor=0x0424, idProduct=0x7801))[d]
        else:
            dev = usb.core.find(idVendor=0x0424, idProduct=0x7801)

        if dev is None:
            raise FileNotFoundError("Device not found!")
        self.dev = dev

    def write_reg(self, address: int, value: int) -> None:
        if value != value & 0xffffffff:
            raise ValueError("Value must be an unsigned 32-bit integer")
        if address != address & 0xfff:
            raise ValueError("Address must be an unsigned 12-bit integer")
        msg = struct.pack("<I", value)
        ret = self.dev.ctrl_transfer(0x40, 0xa0, 0, address, msg)
        if ret != 4:
            raise IOError("Written bytes is not 4")

    def read_reg(self, address: int) -> int:
        if address != address & 0xfff:
            raise ValueError("Address must be an unsigned 12-bit integer")
        ret = self.dev.ctrl_transfer(0xc0, 0xa1, 0, address, 4)
        if len(ret) != 4:
            raise IOError("Received response is not 4 bytes")
        val, = struct.unpack("<I", bytes(ret))
        return cast(int, val)

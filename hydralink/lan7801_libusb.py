#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

import usb.core
import struct
import sys
import re

from glob import glob
from typing import Union, cast, Optional

from hydralink.lan7801 import LAN7801_LL


class LAN7801_LibUSB(LAN7801_LL):
    def __init__(self, d: Union[None, int, usb.core.Device, str] = None) -> None:
        dev: Optional[usb.core.Device] = None
        if isinstance(d, usb.core.Device):
            dev = d
        elif isinstance(d, int):
            dev = list(usb.core.find(find_all=True, idVendor=0x0424, idProduct=0x7801))[d]
        elif isinstance(d, str):
            if sys.platform == 'linux':
                globies = glob(f'/sys/bus/usb/drivers/lan78xx/**/net/{d}')
                assert len(globies) == 1
                matches = [re.match(r'^/sys/bus/usb/drivers/lan78xx/([^/]+)/net/([^/]+)', g) for g in globies]
                assert len(matches) == 1
                usbpaths = [m[1] for m in matches if m[2] == d]
                assert len(usbpaths) == 1
                usbpath = re.match(r'(\d)+-(\d+)(?:\.(\d+))?:(\d+)\.(\d+)', usbpaths[0])
                assert usbpath
                bus = int(usbpath[1])
                port = int(usbpath[2])
                port_numbers = (port, )
                if usbpath[3]:
                    hubport = int(usbpath[3])
                    port_numbers = (port, hubport)
                dev = usb.core.find(idVendor=0x0424, idProduct=0x7801, bus=bus, port_numbers=port_numbers)
                assert dev
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

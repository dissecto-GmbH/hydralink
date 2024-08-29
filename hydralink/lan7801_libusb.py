#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

import usb.core
import struct
import sys
import re

from glob import glob
from typing import Tuple, Union, cast, Optional

from hydralink.lan7801 import LAN7801_LL


def get_lan78xx_usb_dev_by_interface_name(name: str) -> usb.core.Device:
    if sys.platform == 'linux':
        globies = glob(f'/sys/bus/usb/drivers/**/**/net/{name}/')
        if len(globies) == 0:
            raise FileNotFoundError("Network interface not found")
        if len(globies) > 1:
            raise Exception("More than one Hydralink matches the same interface?")
        g = globies[0]
        m = re.match(r'^/sys/bus/usb/drivers/([^/]+)/([^/]+)/net/([^/]+)/$', g)
        if not m or m[3] != name:
            raise FileNotFoundError("Network interface name does not match")
        driver, usbdir = m[1], m[2]
        if driver != 'lan78xx':
            raise IOError(f"Network interface is associated to driver {driver} instead of lan78xx")
        m = re.match(r'(\d)+-(\d+)(?:\.(\d+))?:(\d+)\.(\d+)', usbdir)
        if not m:
            raise Exception("USB path string does not match")
        bus = int(m[1])
        port = int(m[2])
        port_numbers: Union[Tuple[int, int], Tuple[int]] = (port, )
        if m[3]:
            hubport = int(m[3])
            port_numbers = (port, hubport)
        dev = usb.core.find(idVendor=0x0424, idProduct=0x7801, bus=bus, port_numbers=port_numbers)
        assert dev
        assert isinstance(dev, usb.core.Device)
        return dev
    raise NotImplementedError(f"Search by interface name not implemented for platform {sys.platform}")


class LAN7801_LibUSB(LAN7801_LL):
    def __init__(self, d: Union[None, int, usb.core.Device, str] = None) -> None:
        dev: Optional[usb.core.Device] = None
        if isinstance(d, usb.core.Device):
            dev = d
        elif isinstance(d, int):
            dev = list(usb.core.find(find_all=True, idVendor=0x0424, idProduct=0x7801))[d]
        elif isinstance(d, str):
            dev = usb.core.find(idVendor=0x0424, idProduct=0x7801, serial_number=d)
            if dev is None and sys.platform == 'linux':
                dev = get_lan78xx_usb_dev_by_interface_name(d)
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

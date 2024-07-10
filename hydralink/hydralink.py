#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

import struct
import sys

from typing import Union, Optional

from hydralink.lan7801 import LAN7801, LAN7801_LL
from hydralink.bcm89881 import BCM89881


def is_windows() -> bool:
    return sys.platform in ['win32', 'cygwin', 'msys']


def get_lan7801(ll: Union[None, int, LAN7801_LL] = None) -> LAN7801:
    if isinstance(ll, LAN7801_LL):
        return LAN7801(ll)

    if is_windows():
        from hydralink.lan7801_win import LAN7801_Win
        return LAN7801(LAN7801_Win(ll))
    else:
        from hydralink.lan7801_libusb import LAN7801_LibUSB
        return LAN7801(LAN7801_LibUSB(ll))


class HydraLink:
    def __init__(self, ll: Union[None, int, LAN7801_LL] = None) -> None:
        self.mac = get_lan7801(ll)

        # Read MAC register
        identifier = self.mac[0]
        if (identifier >> 16) != 0x7801:
            raise IOError(f"Wrong MAC identifier: 0x{identifier:x}")

        # Access clause 45 registers
        self.phy = BCM89881(self.mac, 0)
        identifier = self.phy[1, 2]
        if identifier != 0xae02:
            raise IOError(f"Wrong PHY identifier: 0x{identifier:x}")

    def setup(self,
              master: Optional[bool] = None,
              speed: Optional[int] = None,
              mac_addr: Optional[str] = None,
              promiscuous: Optional[bool] = None
              ) -> None:
        mac = self.mac
        phy = self.phy

        phy.reset(True)

        # Enable internal 125MHz clock
        mac[0x010] |= 0x02000000
        # PHY RGMII setup
        phy[1, 0xa010] = 0x0001
        phy[1, 0xa015] = 0x0000
        # PHY LEDs setup
        phy[1, 0xa027] = 0x0f15
        phy[1, 0x931d] = 0x0010
        phy[1, 0x931e] = 0x0063

        if promiscuous is not None:
            if promiscuous:
                mac[0x0b0] = 0x1f80
                print("Enabled promiscuous mode")
            else:
                mac[0x0b0] = 0x1c8a
                print("Disabled promiscuous mode")

        if mac_addr is not None:
            mac_addr_bytes = b''
            for b in mac_addr.split(':'):
                bb = bytes.fromhex(b)
                if len(bb) != 1:
                    raise ValueError("Malformed MAC address")
                mac_addr_bytes += bb
            if len(mac_addr_bytes) != 6:
                raise ValueError("Malformed MAC address")
            hi, lo = struct.unpack(">HI", mac_addr_bytes)
            mac[0x118] = hi
            mac[0x11c] = lo

        if speed is not None:
            # Disable Automatic Speed Detection
            mac.set_ads(False)
            if speed == 1000:
                mac.set_speed(2)
                phy.set_speed(1000)
                print("Set hydralink speed to 1 Gb/s")
            elif speed == 100:
                mac.set_speed(1)
                phy.set_speed(100)
                print("Set hydralink speed to 100 Mb/s")
            else:
                raise ValueError("Speed should be either 100 or 1000")

        if master is not None:
            phy.set_master(master)
            print("Set hydralink to operate as %s" % ("master" if master else "slave"))

        # Deassert reset, resume operation
        phy.reset(False)

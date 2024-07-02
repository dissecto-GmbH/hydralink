#! /usr/bin/env python
import struct
import sys

from typing import Union, Optional

from hydralink.lan7801 import LAN7801, LAN7801_LL
from hydralink.bcm89881 import BCM89881


def get_lan7801(ll: Union[None, int, LAN7801_LL] = None) -> LAN7801:
    if isinstance(ll, LAN7801_LL):
        return LAN7801(ll)

    is_windows = sys.platform in ['win32', 'cygwin', 'msys']

    if is_windows:
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
              mac_addr: Optional[str] = None
              ) -> None:
        mac = self.mac
        phy = self.phy

        phy.reset(True)

        # Set appropriate phase shifts in RGMII clocks
        phy[1, 0xa010] = 0x0001
        # Set RGMII interface to 3.3V
        phy[1, 0xa015] = 0x0000

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
            elif speed == 100:
                mac.set_speed(1)
                phy.set_speed(100)
            else:
                raise ValueError("Speed should be either 100 or 1000")

        if master is not None:
            phy.set_master(master)

        # Deassert reset, resume operation
        phy.reset(False)

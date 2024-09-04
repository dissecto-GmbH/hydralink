#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

import struct
import sys

import time
from typing import Union, Optional

from hydralink.lan7801 import LAN7801, LAN7801_LL
from hydralink.bcm89881 import BCM89881


def is_windows() -> bool:
    return sys.platform in ['win32', 'cygwin', 'msys']


def get_lan7801_driver(spec: Union[None, int, str] = None) -> LAN7801_LL:
    """Returns a LAN7801 driver object specified by index or interface name,
    which can be used to read and write the internal configuration registers of
    the LAN7801.

    If no argument is specified, the first LAN7801 found will be returned. If
    an `int` is specified, a driver to the n-th LAN7801 found will be returned.
    A USB serial number can be specified (e.g. dscthl_12345).
    An interface name (example: eth1) can be specified on linux.

    This function throws `FileNotFoundError` if the specified device is not
    found.
    """
    if isinstance(spec, LAN7801_LL):
        return spec
    elif is_windows():
        from hydralink.lan7801_win import LAN7801_Win
        if isinstance(spec, str):
            d = LAN7801_Win.by_serial(spec)
            if not d:
                raise FileNotFoundError(f"HydraLink '{spec}' not found")
            return d
        else:
            return LAN7801_Win(spec)
    else:
        from hydralink.lan7801_libusb import LAN7801_LibUSB
        return LAN7801_LibUSB(spec)


class HydraLink:
    """A class used to configure a dissecto HydraLink"""
    def __init__(self,
                 spec: Union[None, int, str, LAN7801_LL] = None
                 ) -> None:
        """Initializes the HydraLink configuration class.

        The function `get_lan7801_driver` can be used to obtain a `LAN7801_LL`
        handle to be used as an argument to indicate a specific device if
        multiple LAN7801 are connected.

        If the product identifiers of the MAC or the PHY are unexpected, this
        constructor will throw `IOError`.
        If the specified device is not found, `FileNotFoundError` is thrown.
        """
        if isinstance(spec, LAN7801_LL):
            ll = spec
        else:
            ll = get_lan7801_driver(spec)
        self.mac = LAN7801(ll)
        self.verbose = True

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
        """All-in-one function to setup the HydraLink.

        Parameters
        ----------
        master : bool
            optional, set to True or False to switch between master and slave
            operating modes of Automotive Ethernet.
        speed : int
            optional, set to 100 for 100Base-T1 speed, or 1000 for 1000Base-T1
            speed.
        mac_addr : str
            optional, set to a mac address in the form 01:23:45:ab:cd:ef to set
            the mac address of the device.
        promiscuous : bool
            optional, set to True to enable promiscuous mode (for example, to
            be able to sniff all packets on wireshark).
        """
        mac = self.mac
        phy = self.phy

        # Stop operation
        phy.reset(True)

        # Enable clocks
        mac[0x010] |= 0x02000000
        mac[0x128] = 0x00000002
        # MAC-PHY RGMII clock delay setup
        phy[1, 0xa010] = 0x0001
        phy[1, 0xa015] = 0x0000
        # PHY LEDs setup
        phy[1, 0xa027] = 0x0f15
        phy[1, 0x931d] = 0x0010
        phy[1, 0x931e] = 0x0063

        if promiscuous is not None:
            if promiscuous:
                mac[0x0b0] = 0x1f80
                if self.verbose:
                    print("Enabled promiscuous mode")
            else:
                mac[0x0b0] = 0x1c8a
                if self.verbose:
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
            # Unlock registers by disabling TXEN and TXEN
            mac[0x104] = (mac[0x104] | 2) & 0xfffffffe
            mac[0x108] = (mac[0x108] | 2) & 0xfffffffe
            while mac[0x104] & 1:
                time.sleep(.001)
            while mac[0x108] & 1:
                time.sleep(.001)
            mac[0x104] |= 2
            mac[0x108] |= 2

            # Disable Automatic Speed Detection
            mac.set_ads(False)
            if speed == 1000:
                mac.set_speed(2)
                phy.set_speed(1000)
                if self.verbose:
                    print("Set hydralink speed to 1 Gb/s")
            elif speed == 100:
                mac.set_speed(1)
                phy.set_speed(100)
                if self.verbose:
                    print("Set hydralink speed to 100 Mb/s")
            else:
                raise ValueError("Speed should be either 100 or 1000")

            # Lock registers by enabling TXEN and TXEN
            mac[0x104] |= 1
            mac[0x108] |= 1
            while not mac[0x104] & 1:
                time.sleep(.001)
            while not mac[0x108] & 1:
                time.sleep(.001)

        if master is not None:
            phy.set_master(master)
            if self.verbose:
                print("Set hydralink to operate as %s" % ("master" if master else "slave"))

        # Resume operation
        phy.reset(False)

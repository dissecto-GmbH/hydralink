#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

import struct
import sys

from typing import Union, Optional, Dict, Any

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
              promiscuous: Optional[bool] = None,
              reset: bool = False
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
        reset : bool
            defaults to False, set to True to force resetting and
            reconfiguring the PHY
        """
        mac = self.mac
        phy = self.phy

        mac.fix_hardware_config()
        phy.init_hardware_config(reset)

        if promiscuous is not None:
            mac.set_promiscuous(promiscuous)
            if self.verbose:
                if promiscuous:
                    print("Enabled promiscuous mode")
                else:
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
            mac.set_mac_addr(mac_addr_bytes)

        if speed is not None:
            if speed == 1000:
                if self.verbose:
                    print("Setting hydralink speed to 1 Gb/s")
            elif speed == 100:
                if self.verbose:
                    print("Setting hydralink speed to 100 Mb/s")
            else:
                raise ValueError("Speed should be either 100 or 1000")

            # TODO: Ensure this is not needed anymore on any platform
            #
            # asd = mac.get_asd()
            # mspeed = mac.get_speed()
            # if mspeed != speed or asd:
            #     # Unlock registers by disabling TXEN and RXEN
            #     mac.disable_trx()
            #     # Disable Automatic Speed Detection
            #     mac.set_asd(False)
            #     mac.set_speed(speed)
            #     # Lock registers by enabling TXEN and TXEN
            #     mac.enable_trx()

            pspeed = phy.get_speed()
            if pspeed != speed:
                phy.set_speed(speed)
            else:
                if self.verbose:
                    print("PHY speed was already correct")

        if master is not None:
            phy.set_master(master)
            if self.verbose:
                print("Set hydralink to operate as %s" % ("master" if master else "slave"))


if is_windows():
    from hydralink.windows_apis import list_usb_devices
    from hydralink.lan7801_win import LAN7801_Win

    def get_hydralinks() -> Dict[str, Any]:
        return {t.serialnum: t for t in list_usb_devices() if t.vid == 0x0424 and t.pid == 0x7801}

    def hydralink_by_serial(serial: str) -> Optional[HydraLink]:
        devices = get_hydralinks()
        if serial not in devices:
            return None
        key = devices[serial].software_key
        mac = LAN7801_Win.by_key(key)
        if mac:
            return HydraLink(mac)
        return None

else:
    import usb.core
    from hydralink.lan7801_libusb import LAN7801_LibUSB

    def get_hydralinks() -> Dict[str, Any]:
        return {"%d.%d" % (dev.bus, dev.address) if dev.serial_number is None else dev.serial_number: dev
                for dev in usb.core.find(find_all=True, idVendor=0x0424, idProduct=0x7801)}

    def hydralink_by_serial(serial: str) -> Optional[HydraLink]:
        devices = get_hydralinks()
        if serial in devices:
            dev: usb.core.Device = devices[serial]
            return HydraLink(LAN7801_LibUSB(dev))
        else:
            return None

from typing import Optional
import usb.core
import usb.util
from lan7801 import LAN7801, LAN7801_LL
from bcm89881 import BCM89881
import sys


class HydraLink:
    def __init__(self, ll: Optional[LAN7801_LL] = None) -> None:

        # find our device
        if ll is None:
            if sys.platform in ['win32', 'cygwin', 'msys']:
                from lan7801_win import LAN7801_Win
                ll = LAN7801_Win()
            else:
                from lan7801_libusb import LAN7801_LibUSB
                dev = usb.core.find(idVendor=0x0424, idProduct=0x7801)
                ll = LAN7801_LibUSB(dev)

        self.mac = LAN7801(ll)

        # Read MAC register
        identifier = self.mac[0]
        print(f"MAC identifier: {identifier:x}")
        assert (identifier >> 16) == 0x7801

        # Access clause 45 registers
        self.phy = BCM89881(self.mac, 0)
        identifier = self.phy[1, 2]
        print(f"PHY identifier: {identifier:x}")
        assert identifier == 0xae02

    def setup(self,
              master: Optional[bool] = None,
              speed: Optional[int] = None
              ) -> None:
        mac = self.mac
        phy = self.phy

        phy.reset(True)

        # Disable Automatic Speed Detection
        mac.set_ads(False)

        # Set appropriate phase shifts in RGMII clocks
        phy[1, 0xa010] = 0x0001
        # Set RGMII interface to 3.3V
        phy[1, 0xa015] = 0x0000

        if speed is not None:
            # Set speed
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

        phy.reset(False)

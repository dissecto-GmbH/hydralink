from typing import Optional
from hydralink.lan7801 import LAN7801, LAN7801_LL
from hydralink.bcm89881 import BCM89881
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
                ll = LAN7801_LibUSB()

        self.mac = LAN7801(ll)

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
              speed: Optional[int] = None
              ) -> None:
        mac = self.mac
        phy = self.phy

        phy.reset(True)

        # Set appropriate phase shifts in RGMII clocks
        phy[1, 0xa010] = 0x0001
        # Set RGMII interface to 3.3V
        phy[1, 0xa015] = 0x0000

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

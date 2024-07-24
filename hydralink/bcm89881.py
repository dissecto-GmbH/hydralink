#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from typing import Optional
from hydralink.lan7801 import LAN7801


class BCM89881:
    def __init__(self, mac: LAN7801, phy_addr: int):
        if phy_addr & 0x1f != phy_addr:
            raise ValueError('PHY address must be a 5-bit unsigned integer')
        self.mac = mac
        self.phy_addr = phy_addr

    def __getitem__(self, key: tuple[int, int]) -> int:
        return self.mac.read_mdio_reg_c45(self.phy_addr, *key)

    def __setitem__(self, key: tuple[int, int], value: int) -> None:
        self.mac.write_mdio_reg_c45(self.phy_addr, *key, value)

    def edit_register(self, devaddr: int, miiaddr: int, set: int, clr: int) -> int:
        if set & 0xffff != set:
            raise ValueError("set mask bust be a 16-bit unsigned integer")
        if clr & 0xffff != clr:
            raise ValueError("set mask bust be a 16-bit unsigned integer")
        if clr & set:
            raise ValueError("set and clr masks are conflicting")
        reg = self.mac.read_mdio_reg_c45(self.phy_addr, devaddr, miiaddr)
        old_reg = reg
        reg &= (~clr) & 0xffff
        reg |= set
        if old_reg != reg:
            self.mac.write_mdio_reg_c45(self.phy_addr, devaddr, miiaddr, reg)
        return reg

    def reset(self, rst: bool) -> None:
        if rst:
            self.edit_register(1, 0x0000, 0x8000, 0x0000)
        else:
            self.edit_register(1, 0x0000, 0x0000, 0x8000)

    def set_speed(self, speed: int) -> None:
        if speed == 100:
            self.edit_register(1, 0x0000, 0x2000, 0x0040)
        elif speed == 1000:
            self.edit_register(1, 0x0000, 0x0040, 0x2000)
        else:
            raise ValueError("Speed must be 100 or 1000")

    def set_master(self, master: bool) -> None:
        if master:
            self.edit_register(1, 0x0834, 0x4000, 0x0000)
        else:
            self.edit_register(1, 0x0834, 0x0000, 0x4000)

    def get_speed(self) -> Optional[int]:
        s = self[1, 0]
        if (s & 0x2040) == 0x0040:
            return 1000
        elif (s & 0x2040) == 0x2000:
            return 100
        else:
            return None

    def get_master(self) -> bool:
        return (self[1, 0x0834] & 0x4000) == 0x4000

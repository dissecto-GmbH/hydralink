#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

class LAN7801_LL:

    def write_reg(self, address: int, value: int) -> None:
        raise NotImplementedError()

    def read_reg(self, address: int) -> int:
        raise NotImplementedError()


class LAN7801:
    def __init__(self, dev: LAN7801_LL) -> None:
        self.dev = dev
        self.write_reg = dev.write_reg
        self.read_reg = dev.read_reg

    def read_mdio_reg(self, phy_addr: int, miirinda: int) -> int:
        if phy_addr != phy_addr & 0x1f:
            raise ValueError("PHY address must be a 5-bit unsigned integer")
        if miirinda != miirinda & 0x1f:
            raise ValueError("MII Register Index must be a 5-bit unsigned integer")
        miibzy = 1
        while miibzy:
            mii_access = self.read_reg(0x120)
            miibzy = mii_access & 1
        self.write_reg(0x120, (phy_addr << 11) | (miirinda << 6) | 1)
        while miibzy:
            mii_access = self.read_reg(0x120)
            miibzy = mii_access & 1
        return self.read_reg(0x124)

    def write_mdio_reg(self, phy_addr: int, miirinda: int, data: int) -> None:
        if data != data & 0xffff:
            raise ValueError("MII data must be a 16-bit unsigned integer")
        if phy_addr != phy_addr & 0x1f:
            raise ValueError("PHY address must be a 5-bit unsigned integer")
        if miirinda != miirinda & 0x1f:
            raise ValueError("MII Register Index must be a 5-bit unsigned integer")
        miibzy = 1
        while miibzy:
            mii_access = self.read_reg(0x120)
            miibzy = mii_access & 1
        self.write_reg(0x124, data)
        self.write_reg(0x120, (phy_addr << 11) | (miirinda << 6) | 3)
        while miibzy:
            mii_access = self.read_reg(0x120)
            miibzy = mii_access & 1

    def read_mdio_reg_c45(self, phy_addr: int, devad: int, miirinda: int) -> int:
        if phy_addr != phy_addr & 0x1f:
            raise ValueError("PHY address must be a 5-bit unsigned integer")
        if devad != devad & 0x1f:
            raise ValueError("DEVAD must be a 5-bit unsigned integer")
        if miirinda != miirinda & 0xffff:
            raise ValueError("MII Register Index must be a 16-bit unsigned integer")
        self.write_mdio_reg(phy_addr, 0xd, 0x0000 | devad)
        self.write_mdio_reg(phy_addr, 0xe, miirinda)
        self.write_mdio_reg(phy_addr, 0xd, 0x4000 | devad)
        return self.read_mdio_reg(phy_addr, 0xe)

    def write_mdio_reg_c45(self, phy_addr: int, devad: int, miirinda: int, data: int) -> None:
        if data != data & 0xffff:
            raise ValueError("MII data must be a 16-bit unsigned integer")
        if phy_addr != phy_addr & 0x1f:
            raise ValueError("PHY address must be a 5-bit unsigned integer")
        if devad != devad & 0x1f:
            raise ValueError("DEVAD must be a 5-bit unsigned integer")
        if miirinda != miirinda & 0xffff:
            raise ValueError("MII Register Index must be a 16-bit unsigned integer")
        self.write_mdio_reg(phy_addr, 0xd, 0x0000 | devad)
        self.write_mdio_reg(phy_addr, 0xe, miirinda)
        self.write_mdio_reg(phy_addr, 0xd, 0x4000 | devad)
        self.write_mdio_reg(phy_addr, 0xe, data)

    def _eeprom_cmd(self, cmd: int, addr: int) -> None:
        if (cmd & 0b111) != cmd:
            raise ValueError("EPC command must be a 3-bit unsigned integer")
        if (addr & 0x1ff) != addr:
            raise ValueError("EPC address must be a 9-bit unsigned integer")

        e2p_cmd = 0x80000000
        while e2p_cmd & 0x80000000:
            e2p_cmd = self.dev.read_reg(0x040)

        self.dev.write_reg(0x040, 0x80000000 | (cmd << 28) | addr)

        e2p_cmd = 0x80000000
        while e2p_cmd & 0x80000000:
            e2p_cmd = self.dev.read_reg(0x040)

    def eeprom_write(self, addr: int, data: int) -> None:
        if (data & 0xff) != data:
            raise ValueError("EPC data must be a 8-bit unsigned integer")
        if (addr & 0x1ff) != addr:
            raise ValueError("EPC address must be a 9-bit unsigned integer")

        self._eeprom_cmd(0b010, 0)  # EWEN
        self.write_reg(0x044, data)
        self._eeprom_cmd(0b011, addr)  # WRITE
        self._eeprom_cmd(0b001, 0)  # EWDS

    def eeprom_read(self, addr: int) -> int:
        if (addr & 0x1ff) != addr:
            raise ValueError("EPC address must be a 9-bit unsigned integer")

        self._eeprom_cmd(0b000, addr)  # READ
        return self.read_reg(0x044)

    def eeprom_erase_all(self) -> None:
        self._eeprom_cmd(0b010, 0)  # EWEN
        self._eeprom_cmd(0b110, 0)  # ERAL
        self._eeprom_cmd(0b001, 0)  # EWDS

    def __getitem__(self, key: int) -> int:
        if isinstance(key, int):
            return self.read_reg(key)
        else:
            raise ValueError("Unsupported key type")

    def __setitem__(self, key: int, value: int) -> None:
        if isinstance(key, int):
            return self.write_reg(key, value)
        else:
            raise ValueError("Unsupported key type")

    def set_ads(self, ads_enabled: bool) -> None:
        p = self[0x100]
        p &= ~0x0800
        if ads_enabled:
            p |= 0x0800
        self[0x100] = p

    def set_speed(self, speed: int) -> None:
        if speed & 3 != speed:
            raise ValueError("MAC Configuration must be a 2-bit unsigned integer")
        old_reg = self[0x100]
        p = old_reg
        p &= ~0x0006
        p |= (speed & 3) << 1
        if old_reg != p:
            self[0x100] = p

    def get_speed(self) -> int:
        reg = self[0x100]
        return (reg & 0x0006) >> 1

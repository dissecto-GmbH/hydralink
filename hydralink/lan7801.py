#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

import struct
import time


class LAN7801_LL:

    def write_reg(self, address: int, value: int) -> None:
        raise NotImplementedError()

    def read_reg(self, address: int) -> int:
        raise NotImplementedError()


class LAN7801:
    def __init__(self, dev: LAN7801_LL) -> None:
        self._dev = dev

    def __getitem__(self, key: int) -> int:
        if isinstance(key, int):
            return self._dev.read_reg(key)
        else:
            raise ValueError("Unsupported key type")

    def __setitem__(self, key: int, value: int) -> None:
        if isinstance(key, int):
            return self._dev.write_reg(key, value)
        else:
            raise ValueError("Unsupported key type")

    def read_mdio_reg(self, phy_addr: int, miirinda: int) -> int:
        if phy_addr != phy_addr & 0x1f:
            raise ValueError("PHY address must be a 5-bit unsigned integer")
        if miirinda != miirinda & 0x1f:
            raise ValueError("MII Register Index must be a 5-bit unsigned integer")
        miibzy = 1
        while miibzy:
            mii_access = self[0x120]
            miibzy = mii_access & 1
        self[0x120] = (phy_addr << 11) | (miirinda << 6) | 1
        while miibzy:
            mii_access = self[0x120]
            miibzy = mii_access & 1
        return self[0x124]

    def write_mdio_reg(self, phy_addr: int, miirinda: int, data: int) -> None:
        if data != data & 0xffff:
            raise ValueError("MII data must be a 16-bit unsigned integer")
        if phy_addr != phy_addr & 0x1f:
            raise ValueError("PHY address must be a 5-bit unsigned integer")
        if miirinda != miirinda & 0x1f:
            raise ValueError("MII Register Index must be a 5-bit unsigned integer")
        miibzy = 1
        while miibzy:
            mii_access = self[0x120]
            miibzy = mii_access & 1
        self[0x124] = data
        self[0x120] = (phy_addr << 11) | (miirinda << 6) | 3
        while miibzy:
            mii_access = self[0x120]
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
            e2p_cmd = self[0x040]

        self[0x040] = 0x80000000 | (cmd << 28) | addr

        e2p_cmd = 0x80000000
        while e2p_cmd & 0x80000000:
            e2p_cmd = self[0x040]

    def eeprom_write(self, addr: int, data: int) -> None:
        if (data & 0xff) != data:
            raise ValueError("EPC data must be a 8-bit unsigned integer")
        if (addr & 0x1ff) != addr:
            raise ValueError("EPC address must be a 9-bit unsigned integer")

        self._eeprom_cmd(0b010, 0)  # EWEN
        self[0x044] = data
        self._eeprom_cmd(0b011, addr)  # WRITE
        self._eeprom_cmd(0b001, 0)  # EWDS

    def eeprom_read(self, addr: int) -> int:
        if (addr & 0x1ff) != addr:
            raise ValueError("EPC address must be a 9-bit unsigned integer")

        self._eeprom_cmd(0b000, addr)  # READ
        return self[0x044]

    def eeprom_erase_all(self) -> None:
        self._eeprom_cmd(0b010, 0)  # EWEN
        self._eeprom_cmd(0b110, 0)  # ERAL
        self._eeprom_cmd(0b001, 0)  # EWDS

    def fix_hardware_config(self) -> None:
        # Enable clocks
        hw_cfg = self[0x010]
        if (hw_cfg & 0x02000000) == 0:
            self[0x010] = hw_cfg | 0x02000000
            print('WARNING: 125MHz clock was disabled, is not enabled')

        # MAC-PHY RGMII: clock delay setup
        mac_rgmii_id = self[0x128]
        if (mac_rgmii_id & 3) != 2:
            self[0x128] = 2
            print('WARNING: RGMII clock delay was wrong, it is now correct')

    def set_asd(self, asd_enabled: bool) -> None:
        p = self[0x100]
        p &= ~0x0800
        if asd_enabled:
            p |= 0x0800
        self[0x100] = p

    def get_asd(self) -> bool:
        p = self[0x100]
        return p & 0x800 != 0

    def set_speed(self, speed: int) -> None:
        speed_to_maccfg = {10: 0, 100: 2, 1000: 4}
        if speed not in speed_to_maccfg:
            raise ValueError("MAC speed can be either 10, 100 or 1000")
        old_reg = self[0x100]
        p = old_reg
        p &= ~0x0006
        p |= speed_to_maccfg[speed]
        if old_reg != p:
            self[0x100] = p

    def get_speed(self) -> int:
        reg = self[0x100]
        maccfg = reg & 0x0006
        maccfg_to_speed = {0: 10, 2: 100, 4: 1000, 6: 1000}
        return maccfg_to_speed[maccfg]

    def disable_trx(self) -> None:
        self[0x104] = (self[0x104] | 2) & 0xfffffffe
        self[0x108] = (self[0x108] | 2) & 0xfffffffe
        while self[0x104] & 1:
            time.sleep(.001)
        while self[0x108] & 1:
            time.sleep(.001)
        self[0x104] |= 2
        self[0x108] |= 2

    def enable_trx(self) -> None:
        if self[0x104] & 1 == 0:
            self[0x104] |= 1
            while not self[0x104] & 1:
                time.sleep(.001)
        if self[0x108] & 1 == 0:
            self[0x108] |= 1
            while not self[0x108] & 1:
                time.sleep(.001)

    def set_promiscuous(self, promiscuous: bool) -> None:
        # Normally when promiscuous mode is enabled by wireshark:
        # - Windows 11 does 0x1c8a -> 0x1f80  (Works fine out of the box)
        # - Linux does 0x7ca2 -> 0x7fa2  Note: the VF tag is not disabled!
        # This means, on linux promiscuous mode doesn't work out of the box.
        # This could be fixed manually by the user with the command:
        #   `sudo ethtool --features enp11s0u2 rx-vlan-filter off`
        # Or we enable it manually, which is why this method exists.

        rfe_ctl = self[0x0b0]
        if promiscuous:
            # According to the manual, 5 bits need to be changed to ensure
            # packets are received without filtering:
            # - bits 0x0700 (AB, AM, AU) need to be set
            # - bits 0x0060 (VF, UF) need to be cleared
            rfe_ctl = (rfe_ctl | 0x0700) & 0xff9f
        else:
            # To disable promiscuous mode we just disable AM and AU
            rfe_ctl = (rfe_ctl & 0xfcff)
        self[0x0b0] = rfe_ctl

    def get_promiscuous(self) -> bool:
        rfe_ctl = self[0x0b0]
        return (rfe_ctl & 0x0760) == 0x0700

    def set_mac_addr(self, mac_addr_bytes: bytes) -> None:
        lo, hi = struct.unpack("<IH", mac_addr_bytes)
        self[0x118] = hi
        self[0x11c] = lo

    def get_mac_addr(self) -> bytes:
        hi = self[0x118] & 0xffff
        lo = self[0x11c]
        return struct.pack("<IH", lo, hi)

from lan7801 import LAN7801


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

    def set_speed(self, speed: int) -> None:
        if speed == 1000:
            self[1, 0x0000] = self[1, 0x0000] & ~0x0040 | 0x2000
            self[1, 0x0834] = self[1, 0x0834] | 1
        elif speed == 100:
            self[1, 0x0000] = self[1, 0x0000] & ~0x2000 | 0x0040
            self[1, 0x0834] = self[1, 0x0834] | 1
        else:
            raise ValueError("Speed must be 100 or 1000")

    def set_master(self, master: bool) -> None:
        if master:
            self[1, 0x0834] = self[1, 0x0834] | 0x4000
        else:
            self[1, 0x0834] = self[1, 0x0834] & ~0x4000

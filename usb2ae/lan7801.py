import usb.core
import usb.util
import struct
from typing import cast


class LAN7801:
    def __init__(self, dev: usb.core.Device) -> None:
        self.out_ep: (usb.Endpoint | None) = None
        self.dev = dev

    def open_out_endpoint(self) -> None:
        if self.out_ep is not None:
            return
        self.dev.set_configuration()
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]
        out_ep = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: (
                    usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
        )
        assert out_ep.bEndpointAddress == 2
        self.out_ep = out_ep

    def send_pkt(self, buf: bytes) -> None:
        self.open_out_endpoint()
        assert self.out_ep is not None
        buf = bytes.fromhex("deadbeef")
        buf = buf + b"\x00" * max(0, 32 - len(buf))
        self.out_ep.write(struct.pack("<II", (0xfffff & len(buf)), 0) + buf)

    def write_reg(self, address: int, value: int) -> None:
        if value != value & 0xffffffff:
            raise ValueError("Value must be an unsigned 32-bit integer")
        if address != address & 0xfff:
            raise ValueError("Value must be an unsigned 12-bit integer")
        msg = struct.pack("<I", value)
        ret = self.dev.ctrl_transfer(0x40, 0xa0, 0, address, msg)
        if ret != 4:
            raise IOError("Written bytes is not 4")

    def read_reg(self, address: int) -> int:
        if address != address & 0xfff:
            raise ValueError("Value must be an unsigned 12-bit integer")
        ret = self.dev.ctrl_transfer(0xc0, 0xa1, 0, address, 4)
        if len(ret) != 4:
            raise IOError("Received response is not 4 bytes")
        val, = struct.unpack("<I", bytes(ret))
        return cast(int, val)

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
            raise ValueError("MII Register Index must be a 5-bit unsigned integer")
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
            raise ValueError("MII Register Index must be a 5-bit unsigned integer")
        self.write_mdio_reg(phy_addr, 0xd, 0x0000 | devad)
        self.write_mdio_reg(phy_addr, 0xe, miirinda)
        self.write_mdio_reg(phy_addr, 0xd, 0x4000 | devad)
        self.write_mdio_reg(phy_addr, 0xe, data)

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

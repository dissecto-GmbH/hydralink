import usb.core
import usb.util
from lan7801_libusb import LAN7801_LibUSB
from lan7801_win import LAN7801_Win
from lan7801 import LAN7801
from bcm89881 import BCM89881
import argparse


def main() -> None:

    parser = argparse.ArgumentParser(
                        prog='usb2ae_config',
                        description='Configures the USB2AE MAC and PHY interfaces')
    parser.add_argument('-g', '--gigabit', action='store_true')
    parser.add_argument('-m', '--master',  action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-b', '--blink', default="0")
    args = parser.parse_args()

    # find our device
    if 0:
        dev = usb.core.find(idVendor=0x0424, idProduct=0x7801)
        mac = LAN7801(LAN7801_LibUSB(dev))
    else:
        mac = LAN7801(LAN7801_Win())

    # Read MAC register
    identifier = mac[0]
    print(f"MAC identifier: {identifier:x}")
    assert (identifier >> 16) == 0x7801
    # Enable GPIO4
    mac[0x01c] = 0x10100
    print("HW_CFG=0x%08x" % mac[0x010])

    # Access clause 45 registers
    phy = BCM89881(mac, 0)
    identifier = phy[1, 2]
    assert identifier == 0xae02
    print(f"PHY identifier: {identifier:x}")

    # Disable Automatic Speed Detection
    mac.set_ads(False)

    phy.reset(True)
    # Set speed
    if args.gigabit:
        mac.set_speed(2)
        phy.set_speed(1000)
    else:
        mac.set_speed(1)
        phy.set_speed(100)

    phy.set_master(args.master)
    phy.reset(False)

    # Set appropriate phase shifts in RGMII clocks
    phy[1, 0xa010] = 0x0001

    if args.verbose:

        print("PMA_PMD_CONTROL_1=0x%04x" % phy[1, 0])
        print("PMA_PMD_STATUS_1=0x%04x" % phy[1, 1])
        print("PMA_PMD_IEEE_DEVICE_ID_REG0=0x%04x" % phy[1, 2])
        print("PMA_PMD_IEEE_DEVICE_ID_REG1=0x%04x" % phy[1, 3])
        print("PMA_PMD_IEEE_PMA_PMD_SPEED_ABILITY=0x%04x" % phy[1, 4])
        print("PMA_PMD_IEEE_STATUS_REG2=0x%04x" % phy[1, 8])
        print("PMA_PMD_IEEE_BASET1_PMA_PMD_CONTROL=0x%04x" % phy[1, 0x0834])
        print("RGMII_CONTROL=0x%04x" % phy[1, 0xa010])

    i = int(args.blink, 0)
    while i != 0:
        i -= 1
        # Blink LEDs and toggle GPIO4
        phy[1, 0x931e] = 0x006f
        phy[1, 0x931d] = 0x00ef
        phy[1, 0x931d] = 0x00ff
        print(hex(mac[0x01c]))
        mac[0x01c] = 0x10101
        phy[1, 0x931e] = 0x006e
        phy[1, 0x931d] = 0x00fe
        phy[1, 0x931d] = 0x00ee
        print(hex(mac[0x01c]))
        mac[0x01c] = 0x10100

    # Set LEDS
    phy[1, 0x931e] = 0x0010
    phy[1, 0x931d] = 0x0063


if __name__ == '__main__':
    main()

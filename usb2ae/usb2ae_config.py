import usb.core
import usb.util
from lan7801 import LAN7801
from bcm89881 import BCM89881
import argparse
import sys


def main() -> None:

    parser = argparse.ArgumentParser(
                        prog='usb2ae_config',
                        description='Configures the USB2AE MAC and PHY interfaces')
    parser.add_argument('-g', '--gigabit', action='store_true')
    parser.add_argument('-m', '--master',  action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-b', '--blink', default="0")
    parser.add_argument('-r', '--readonly', action='store_true')
    args = parser.parse_args()

    # find our device
    print(sys.platform)
    if sys.platform in ['win32', 'cygwin', 'msys']:
        from lan7801_win import LAN7801_Win
        mac = LAN7801(LAN7801_Win())
    else:
        from lan7801_libusb import LAN7801_LibUSB
        dev = usb.core.find(idVendor=0x0424, idProduct=0x7801)
        mac = LAN7801(LAN7801_LibUSB(dev))

    # Read MAC register
    identifier = mac[0]
    print(f"MAC identifier: {identifier:x}")
    assert (identifier >> 16) == 0x7801

    # Access clause 45 registers
    phy = BCM89881(mac, 0)
    identifier = phy[1, 2]
    assert identifier == 0xae02

    print(f"PHY identifier: {identifier:x}")
    if not args.readonly:
        # Enable GPIO4
        mac[0x01c] = 0x10100
        print("HW_CFG=0x%08x" % mac[0x010])

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
        # Set RGMII interface to 3.3V
        phy[1, 0xa015] = 0x0000

    if args.verbose:
        print("PMA_PMD_CONTROL_1 = 0x%04x" % phy[1, 0])
        print("PMA_PMD_STATUS_1 = 0x%04x" % phy[1, 1])
        print("PMA_PMD_IEEE_DEVICE_ID_REG = 0x%04x%04x" % (phy[1, 2], phy[1, 3]))
        print("PMA_PMD_IEEE_PMA_PMD_SPEED_ABILITY = 0x%04x" % phy[1, 4])
        print("PMA_PMD_IEEE_DEVICE_IN_PACKAGE_REG0 = 0x%04x" % phy[1, 5])
        print("PMA_PMD_IEEE_DEVICE_IN_PACKAGE_REG1 = 0x%04x" % phy[1, 6])
        print("PMA_PMD_IEEE_CONTROL_REG2 = 0x%04x" % phy[1, 7])
        print("PMA_PMD_IEEE_STATUS_REG2 = 0x%04x" % phy[1, 8])
        print("PMA_PMD_IEEE_TRANSMIT_DISABLE_REG = 0x%04x" % phy[1, 9])
        print("PMA_PMD_IEEE_RECEIVE_SIGNAL_DET_REG = 0x%04x" % phy[1, 10])
        print("PMA_PMD_IEEE_EXTENDED_ABILITY_REG = 0x%04x" % phy[1, 11])
        print("PMA_PMD_IEEE_PACKAGE_ID_REG = 0x%04x%04x" % (phy[1, 14], phy[1, 15]))
        print("STRAP_SGMII_REGISTER_1 = 0x%04x" % phy[0x1e, 16])
        print("PMA_PMD_IEEE_BASET1_PMA_PMD_EXTENDED_ABILITY = 0x%04x" % phy[1, 18])
        print("PMA_PMD_IEEE_BASET1_PMA_PMD_CONTROL = 0x%04x" % phy[1, 0x0834])
        print("PMA_PMD_IEEE_BASE100T1_PMA_PMD = 0x%04x" % phy[1, 0x0836])
        print("PMA_PMD_IEEE_BASE1000T1_PMA_CONTROL = 0x%04x" % phy[1, 0x0900])
        print("PMA_PMD_IEEE_BASE1000T1_PMA_STATUS = 0x%04x" % phy[1, 0x0901])
        print("PMA_PMD_IEEE_BASE1000T1_TRAINING = 0x%04x" % phy[1, 0x0902])
        print("PMA_PMD_IEEE_BASE1000T1_LINK_PARTNER_TRAINING = 0x%04x" % phy[1, 0x0903])
        print("PMA_PMD_IEEE_BASE1000T1_TEST_MODE_CONTROL = 0x%04x" % phy[1, 0x0904])
        print("PHYCONTROL_CURRENT_MSE = 0x%04x" % phy[1, 0x8007])
        print("RGMII_CONTROL = 0x%04x" % phy[1, 0xa010])
        print("RGMII_CONTROL_2 = 0x%04x" % phy[1, 0xa011])
        print("SWREG_CONTROL_RGMII_SGMII_SEL = 0x%04x" % phy[1, 0xa015])
        print("LED and INTR Control = 0x%04x" % phy[1, 0xa027])

    if args.blink and not args.readonly:
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

            # Set LEDS to default state
            phy[1, 0x931e] = 0x0010
            phy[1, 0x931d] = 0x0063


if __name__ == '__main__':
    main()

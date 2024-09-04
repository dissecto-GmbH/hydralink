#!/usr/bin/env python3

# This test needs to be executed as root on a linux system with 2 HydraLink
# devices connected. REFERENCE_HYDRALINK must be the serial number of a known
# working HydraLink.

import json
import os
import pytest
import time
from typing import Optional, cast
from hydralink.hydralink import HydraLink
from hydralink.gui import get_hydralinks, hydralink_by_serial
from hydralink.lan7801_libusb import LAN7801_LibUSB
from glob import glob
import subprocess


REFERENCE_HYDRALINK = 'dscthl_00000'  # known working


def get_netif_by_hydralink(hl: HydraLink) -> Optional[str]:
    dev = cast(LAN7801_LibUSB, hl.mac.dev).dev
    nets = glob('/sys/bus/usb/drivers/lan78xx/'+(
            str(dev.bus)+'-'+'.'.join([str(n) for n in dev.port_numbers])
            )+':**/net/**/')
    if len(nets) > 1:
        raise Exception("More than one LAN78xx has the same interface name!")
    if len(nets) == 0:
        return None
    net = nets[0]
    return net.split('/')[-2]


def reset_hydralink(hl: HydraLink) -> Optional[str]:
    dev = cast(LAN7801_LibUSB, hl.mac.dev).dev
    name = str(dev.bus)+'-'+'.'.join([str(n) for n in dev.port_numbers])
    name += ":1.0"
    with open('/sys/bus/usb/drivers/lan78xx/unbind', 'w') as fd:
        fd.write(name)
    with open('/sys/bus/usb/drivers/lan78xx/bind', 'w') as fd:
        fd.write(name)


class TestFailedError(Exception):
    pass


class TestEnv:
    def __init__(self) -> None:
        devs = get_hydralinks()
        hl0 = HydraLink(REFERENCE_HYDRALINK)

        testable_hydralinks = [k for k in devs.keys() if k != REFERENCE_HYDRALINK]
        if len(testable_hydralinks) == 0:
            raise TestFailedError("HydraLink USB device not found")
        hl1 = hydralink_by_serial([k for k in devs.keys() if k != REFERENCE_HYDRALINK][0])
        assert hl1

        # Delete namespaces if they exist to start from a clean state
        subprocess.call(['ip', 'netns', 'del', 'ns0'])
        subprocess.call(['ip', 'netns', 'del', 'ns1'])
        time.sleep(.3)  # Wait for them to be released from the namespace

        netif0 = get_netif_by_hydralink(hl0)
        netif1 = get_netif_by_hydralink(hl1)
        if netif0 is None:
            reset_hydralink(hl0)
            netif0 = get_netif_by_hydralink(hl0)
            if netif0 is None:
                raise Exception("Reference HydraLink network interface not found")
        if netif1 is None:
            raise TestFailedError("Tested HydraLink network interface not found")

        subprocess.check_call(['ip', 'netns', 'add', 'ns0'])
        subprocess.check_call(['nmcli', 'dev', 'set', netif0, 'managed', 'no'])
        subprocess.check_call(['ip', 'link', 'set', 'dev', netif0, 'netns', 'ns0'])
        PFX = ['ip', 'netns', 'exec', 'ns0']
        subprocess.check_call(PFX + ['ip', 'a', 'add', '10.0.0.100/24', 'dev', netif0])
        subprocess.check_call(PFX + ['ip', 'link', 'set', 'dev', netif0, 'up'])
        p = subprocess.Popen(PFX + ['iperf3', '-s'], stdout=subprocess.DEVNULL)

        subprocess.check_call(['ip', 'netns', 'add', 'ns1'])
        subprocess.check_call(['nmcli', 'dev', 'set', netif1, 'managed', 'no'])
        subprocess.check_call(['ip', 'link', 'set', 'dev', netif1, 'netns', 'ns1'])
        PFX = ['ip', 'netns', 'exec', 'ns1']
        subprocess.check_call(PFX + ['ip', 'a', 'add', '10.0.0.101/24', 'dev', netif1])
        subprocess.check_call(PFX + ['ip', 'link', 'set', 'dev', netif1, 'up'])
        time.sleep(.1)

        self.iperf3p = p
        self.hl0 = hl0
        self.hl1 = hl1
        self.netif0 = netif0
        self.netif1 = netif1

    def runtest(self, master: bool, speed: int, size: int = -1) -> float:
        if size < 0:
            size = speed*100000
        self.hl0.verbose = False
        self.hl1.verbose = False
        self.hl0.setup(master=not master, speed=speed)
        self.hl1.setup(master=master, speed=speed)
        eff_speed = speed*93//100
        time.sleep(0.1)
        FILENAME = '/tmp/hydralink_test_results.json'
        with open(FILENAME, 'w+') as fd:
            subprocess.check_call(
                    ['ip', 'netns', 'exec', 'ns1',
                     'iperf3', '-c', '10.0.0.100', '--bidir',
                     '-n', str(size),
                     '-u', '-b', f'{eff_speed}M', '-J'],
                    stdout=fd)
            fd.seek(0)
            test_results = json.load(fd)
        os.unlink(FILENAME)

        end = test_results['end']
        sum_sent = end['sum_sent']
        s12_packets = sum_sent['packets']
        s12_bps = sum_sent['bits_per_second']
        s12_lost = sum_sent['lost_packets']
        sum_received = end['sum_received']
        r12_packets = sum_received['packets']
        r12_bps = sum_received['bits_per_second']
        r12_lost = sum_received['lost_packets']
        sum_sent_bidir_reverse = end['sum_sent_bidir_reverse']
        s21_packets = sum_sent_bidir_reverse['packets']
        s21_bps = sum_sent_bidir_reverse['bits_per_second']
        s21_lost = sum_sent_bidir_reverse['lost_packets']
        sum_received_bidir_reverse = end['sum_received_bidir_reverse']
        r21_packets = sum_received_bidir_reverse['packets']
        r21_bps = sum_received_bidir_reverse['bits_per_second']
        r21_lost = sum_received_bidir_reverse['lost_packets']

        total_packets = s12_packets + r12_packets + s21_packets + r21_packets
        min_speed = min([s12_bps, r12_bps, s21_bps, r21_bps]) / 1000000
        total_lost = s12_lost + r12_lost + s21_lost + r21_lost

        speed_ratio = min_speed / eff_speed
        percent_lost = total_lost * 100.0 / total_packets
        assert isinstance(percent_lost, float)
        print("\r")
        print("%d %.3f%% %f" % (total_packets, percent_lost, min_speed))
        print("\r")

        if speed_ratio < .98:
            raise TestFailedError("Insufficient speed: %dmbps/%dmbps" % (min_speed, speed))

        return percent_lost


singleton_env: Optional[TestEnv] = None
@pytest.fixture
def env() -> TestEnv:
    global singleton_env
    if singleton_env is None:
        singleton_env = TestEnv()
    return singleton_env


def test_slave_100M(env: TestEnv) -> None:
    if 0 < env.runtest(False, 100):
        raise TestFailedError("Packet lost at 100mbps, slave")


def test_master_100M(env: TestEnv) -> None:
    if 0 < env.runtest(True, 100):
        raise TestFailedError("Packet lost at 100mbps, master")


def test_slave_1000M(env: TestEnv) -> None:
    # At gigabit speed, raspberry pi tends to miss a few packets even when the
    # HydraLink is working perfectly, so if testing on a pi you might want to
    # allow up to 0.1% packet loss.
    if 0 < env.runtest(False, 1000):
        raise TestFailedError("Packet lost at 1gbps, slave")


def test_master_1000M(env: TestEnv) -> None:
    if 0 < env.runtest(True, 1000):
        raise TestFailedError("Packet lost at 1gbps, master")


def main() -> None:
    e = TestEnv()
    test_slave_100M(e)
    test_slave_1000M(e)
    test_master_100M(e)
    test_master_1000M(e)


if __name__ == '__main__':
    main()

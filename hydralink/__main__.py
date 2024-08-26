#! /usr/bin/env python

#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse

from typing import Union
from hydralink import HydraLink


def main() -> None:

    parser = argparse.ArgumentParser(
                        prog='hydralink_config',
                        description='Configures the dissecto HydraLink MAC and PHY')
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('-g', '--gigabit', action='store_true')
    parser.add_argument('-m', '--master',  action='store_true')
    parser.add_argument('-d', '--device', type=str)
    parser.add_argument('-p', '--promiscuous', type=bool)
    parser.add_argument('--dump', type=str, help="Dump all MAC registers to file")
    args = parser.parse_args()

    if args.gui:
        import hydralink.gui
        return hydralink.gui.main()

    devid: Union[None, int, str] = None
    try:
        devid = int(args.device, 10)
    except Exception:
        devid = args.device

    hl = HydraLink(devid)

    if args.dump is not None:
        with open(args.dump, "w") as of:
            for i in range(0, 0x1000, 4):
                print("%03x: %08x" % (i, hl.mac[i]), file=of)
        return

    hl.setup(master=args.master,
             speed=(1000 if args.gigabit else 100),
             promiscuous=args.promiscuous)


if __name__ == '__main__':
    main()

#! /usr/bin/env python

#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse

from hydralink import HydraLink


def main() -> None:

    parser = argparse.ArgumentParser(
                        prog='hydralink_config',
                        description='Configures the dissecto HydraLink MAC and PHY')
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('-g', '--gigabit', action='store_true')
    parser.add_argument('-m', '--master',  action='store_true')
    parser.add_argument('-d', '--device', type=int)
    parser.add_argument('-p', '--promiscuous', action='store_true')
    args = parser.parse_args()

    if args.gui:
        import hydralink.gui
        return hydralink.gui.main()

    hl = HydraLink(args.device)
    hl.setup(master=args.master,
             speed=(1000 if args.gigabit else 100),
             promiscuous=args.promiscuous)


if __name__ == '__main__':
    main()

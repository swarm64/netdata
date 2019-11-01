#!/usr/bin/env python3

import os
import shutil
import argparse


CHART = './fpga.chart.py'
CONF = './fpga.conf'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get possible non-default paths for config and driver')
    parser.add_argument('--config', default='/etc/netdata/python.d', help='Where the netdata config file is located')
    parser.add_argument('--python-chart', default='/usr/libexec/netdata/python.d', help='Where the python chart file is located')
    args = parser.parse_args()

    netdata_bin = shutil.which('netdata')

    if netdata_bin is not None and os.stat(netdata_bin).st_uid == 0:
        if os.path.isdir(args.python_chart):
            shutil.copy(CHART, args.python_chart)
        else:
            print("Couldn't copy chart file to {}".format(args.python_chart))

        if os.path.isdir(args.config):
            shutil.copy(CONF, args.config)
        else:
            print("Couldn't copy conf file to {}".format(args.config))

    else:
        print("Netdata is not installed, please install it first.")


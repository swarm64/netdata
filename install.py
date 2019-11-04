#!/usr/bin/env python3

import os
import shutil
import argparse


CHART = 'fpga.chart.py'
CONF = 'fpga.conf'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get possible non-default paths for config and driver')
    parser.add_argument('--config', default='/etc/netdata/python.d', help='Where the netdata config file is located')
    parser.add_argument('--python-chart', default='/usr/libexec/netdata/python.d', help='Where the python chart file is located')
    parser.add_argument('--force', action='store_true', default=False, help='overwrite existing versions of the files if they exist')
    args = parser.parse_args()

    netdata_bin = shutil.which('netdata')
    login_user = os.getlogin()
    chart_path = args.python_chart + '/' + CHART
    conf_path = args.config + '/' + CONF

    if netdata_bin is not None and login_user == 'root':
        if os.path.isdir(args.python_chart) and os.path.isdir(args.config):
            if (os.path.isfile(chart_path) or os.path.isfile(conf_path)) and not args.force:
                print("{} or {} are already present, use --force to overwrite".format(CHART, CONF))
            else:
                shutil.copy(CHART, args.python_chart)
                shutil.copy(CONF, args.config)

        else:
            print("Couldn't copy files to desired directories. Make sure that {} and {} exist".format(args.python_chart, args.config))

    else:
        print("Please check that Netdata is installed and run this script as root")


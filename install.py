#!/usr/bin/env python

import os
import sys
import argparse
import distutils.spawn
import imp
import sys
import shutil


CHART = 'fpga.chart.py'
CONF = 'fpga.conf'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get possible non-default paths for config and driver')
    parser.add_argument('--config', default='/etc/netdata/python.d', help='Where the netdata config file is located')
    parser.add_argument('--python-chart', default='/usr/libexec/netdata/python.d', help='Where the python chart file is located')
    parser.add_argument('--force', action='store_true', default=False, help='overwrite existing versions of the files if they exist')
    args = parser.parse_args()

    netdata_bin = distutils.spawn.find_executable('netdata')
    login_user = os.geteuid()
    chart_path = os.path.join(args.python_chart, CHART)
    conf_path = os.path.join(args.config, CONF)

    try:
        imp.find_module('psycopg2')
    except ImportError:
        print 'The psycopg2 python module needs to be installed for the fpga netdata module to work'
        sys.exit(1)

    if netdata_bin is not None and login_user == 0:
        if os.path.isdir(args.python_chart) and os.path.isdir(args.config):
            if (os.path.isfile(chart_path) or os.path.isfile(conf_path)) and not args.force:
                print "%s or %s are already present, use --force to overwrite" % (CHART, CONF)
            else:
                shutil.copy(CHART, args.python_chart)
                shutil.copy(CONF, args.config)
                print 'Please restart netdata now that the scripts have been installed.'

        else:
            print "Couldn't copy files to desired directories. Make sure that %s and %s exist" % (args.python_chart, args.config)
            sys.exit(1)

    else:
        print 'Please check that Netdata is installed and run this script as root'
        sys.exit(1)

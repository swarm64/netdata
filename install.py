#!/usr/bin/env python3

import re
import os
import subprocess
import shutil
import argparse


CHART = './fpga.chart.py'
CONF = './fpga.conf'


def get_flavour():
    flavour_line = subprocess.check_output('cat /etc/os-release | grep -E \'^NAME="\'', shell=True)
    flavour = re.match(r'^NAME=\"(\w+)', flavour_line.decode('UTF-8'))

    return flavour.group(1)


def check_for_package(cmd):
    try:
        DEVNULL = open(os.devnull, 'w')
        out = subprocess.check_output(cmd + ' | grep netdata', stderr=DEVNULL, shell=True)
        DEVNULL.close()
        return True
    except subprocess.CalledProcessError as exc:
        return False

def netdata_is_installed(linux_flavour):
    if linux_flavour == "Debian":
        cmd = 'dpkg -l | grep netdata'
        return check_for_package(cmd)
    elif linux_flavour == "CentOS":
        cmd = 'yum list installed | grep netdata'
        return check_for_package(cmd)
    else:
        print("Supported Linux flavour not in use")
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get possible non-default paths for config and driver')
    parser.add_argument('--config', default='/etc/netdata/python.d', help='Where the netdata config file is located')
    parser.add_argument('--python-chart', default='/usr/libexec/netdata/python.d', help='Where the python chart file is located')
    args = parser.parse_args()

    linux_flavour = get_flavour()

    if netdata_is_installed(linux_flavour):
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


#!/usr/bin/env python3

import re
import os
import subprocess
import shutil


CHART_DIR = '/usr/ibexec/netdata/python.d'
CHART = './fpga.chart.py'
CONF_DIR = '/etc/etdata/python.d'
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
    linux_flavour = get_flavour()

    if netdata_is_installed(linux_flavour):
        if os.path.isdir(CHART_DIR):
            shutil.copy(CHART, CHART_DIR)
        else:
            print("Couldn't copy chart file to {}".format(CHART_DIR))

        if os.path.isdir(CONF_DIR):
            shutil.copy(CONF, CONF_DIR)
        else:
            print("Couldn't copy conf file to {}".format(CONF_DIR))

    else:
        print("Netdata is not installed, please install it first.")


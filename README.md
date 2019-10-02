# Summary

The configuration file and python file needed to read data from a local
FPGA


# Prerequisites

- psycopg2


# Configuration and file locations

In `/etc/netdata/netdata.conf` in the `plugins` section the following line should be present: `python.d = yes`  
The configuration file `fpga.conf` should be placed in `/etc/netdata/conf.d/python.d/`  
The python file `fpga.chart.py` should be placed in `/usr/libexec/netdata/python.d/`  

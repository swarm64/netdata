# Summary

The configuration file and python file needed to read out and display statistics for FPGAs in the system


# Prerequisites

- Python2 package psycopg2. Install eg. with `python -m pip install psycopg2`


# Configuration and file locations

In `/etc/netdata/netdata.conf` in the `plugins` section the following line should be present: `python.d = yes`  

In order to install the Swarm64 FPGA monitoring scripts for Netdata, run the `install.py` script included in
this repository. It will do some basic checks and then attempt to install the configuration script and the
chart script either in the default directories or optionally to other locations specified by the user.
Please run the script with `--help` to see this usage.
The script will not overwrite existing Swarm64 scripts that happen to be in the locations specified unless the
`--force` option is specified. This is also detailed with the running of `--help`.

If the Swarm64 DA extension is not already loaded into the target PostgreSQL database, the script will do it
in order to get the statistics. The chart script attempts to connect to the database. You therefore have to ensure the 
configuration information in the `fpga.conf` file is correct for the database in question.
Once the scripts are successfully installed restart Netdata in order to see the FPGA statistics displayed.

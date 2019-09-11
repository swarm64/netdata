# -*- coding: utf-8 -*-
# Description: example netdata python.d module
# Author: Put your name here (your github login)
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from bases.FrameworkServices.SimpleService import SimpleService

import psycopg2
import copy
import subprocess
import re

priority = 90000

FPGA_COUNT = 2

BYTE_DEFINITION = {
    'options': [None, 'Transfered data', 'MB/sec', 'fpga', 'fpga', 'line'],
    'lines': [['host_to_fpga_byte_count', 'sent to fpga', 'incremental', 1, 1024*1024],
              ['fpga_to_host_byte_count', 'received from fpga', 'incremental', -1, 1024*1024]]
}
JOB_DEFINITION = {
    'options': [None, 'Processed jobs', 'Jobs/sec', 'fpga', 'fpga', 'line'],
    'lines': [['compression_job_count', 'compressed jobs', 'incremental'],
              ['decompression_job_count', 'decompressed jobs', 'incremental'],
              ['decompression_and_filter_job_count', 'decompressed and filtered jobs', 'incremental'],
              ['filter_job_count', 'filtered jobs', 'incremental']
             ]
}
MAX_DEFINITION = {
    'options': [None, 'Max outstanding jobs', 'max oustanding', 'fpga', 'fpga', 'line'],
    'lines': [['max_outstanding_compression_jobs', 'compression', 'absolute'],
              ['max_outstanding_decompression_and_filter_jobs', 'decompress and filter', 'absolute'],
              ['max_outstanding_filter_jobs', 'filter', 'absolute']
             ]
}
TEMP_DEFINITION = {
    'options': [None, 'FPGA Temperature', '°C', 'fpga', 'fpga', 'line'],
    'lines': [['temperature', 'Degrees Celcius', 'absolute']
             ]
}

DSNS = [
    'postgresql://postgres@localhost:5432/postgres'
]

class Service(SimpleService):
    def __init__(self, configuration=None, name=None):
        SimpleService.__init__(self, configuration=configuration, name=name)
        self.conn = None
        self.default_data = dict()
        self.order = []
        self.definitions = dict()
        self.keys = []
        self.fpga_mapping = dict()
        self.next_fpga = 0
        self.dsn = self.configuration.get('dsn')

        for i in range(FPGA_COUNT):
            name = 'fpga-' + str(i)
            bytes = name + '-bytes'
            jobs = name + '-jobs'
            maxes = name + '-max'
            temps = name + '-temp'
            self.order.append(bytes)
            self.order.append(jobs)
            self.order.append(maxes)
            self.order.append(temps)
            self.definitions[bytes] = copy.deepcopy(BYTE_DEFINITION)
            self.definitions[bytes]['options'][3] = name
            self.definitions[jobs] = copy.deepcopy(JOB_DEFINITION)
            self.definitions[jobs]['options'][3] = name
            self.definitions[maxes] = copy.deepcopy(MAX_DEFINITION)
            self.definitions[maxes]['options'][3] = name
            self.definitions[temps] = copy.deepcopy(TEMP_DEFINITION)
            self.definitions[temps]['options'][3] = name

            for key in self.definitions[bytes]['lines']:
                key[0] = name + '-' + key[0]
                self.keys.append(key[0])
            for key in self.definitions[jobs]['lines']:
                key[0] = name + '-' + key[0]
                self.keys.append(key[0])
            for key in self.definitions[maxes]['lines']:
                key[0] = name + '-' + key[0]
                self.keys.append(key[0])
            for key in self.definitions[temps]['lines']:
                key[0] = name + '-' + key[0]
                self.keys.append(key[0])
 
        for key in self.keys:
            self.default_data[key] = 0

    @staticmethod
    def check():
        return True

    def _connect(self, dsn):
        try:
            self.conn = psycopg2.connect(dsn)
            self.conn.autocommit = True
            with self.conn.cursor() as cursor:
                cursor.execute('CREATE EXTENSION IF NOT EXISTS swarm64da')

        except Exception:
            self.conn = None
            return False

        return True

    def _parse_fpgainfo(self, cmd, re_string):
        fpga_info_res = subprocess.check_output(cmd, shell=True)
        fpga_info_out = fpga_info_res.split(b'\n')

        for line in fpga_info_out:
            info_line = re.match(re_string, line.decode('UTF-8'))
            if info_line is not None:
                return info_line.group(1)

    def _get_fpga_temp(self):
        FPGA_TEMPERATURE_CMD = "/usr/bin/fpgainfo temp"
        RE_TEMP_STRING = r'^.*FPGA Core TEMP \s+: (\d+)\,'
        return _parse_fpgainfo(FPGA_TEMPERATURE_CMD, RE_TEMP_STRING)

    def _get_fpga_power(self):
        FPGA_POWER_CMD = "/usr/bin/fpgainfo power"
        RE_POWER_STRING = r'^.*Total Input Power \s+: (\d+)\.'
        return _parse_fpgainfo(FPGA_POWER_CMD, RE_POWER_STRING)

    def get_data(self):
        self._connect(self.dsn)

        # It might be that no connection could be established at all
        if not self.conn:
            return self.default_data

        try:
            data = copy.deepcopy(self.default_data)
            data['temperature'] = self._get_fpga_temp()
            data['power'] = self._get_fpga_power()


            with self.conn.cursor() as cursor:
                cursor.execute('SELECT * FROM swarm64da.get_fpga_stats()')
                result = cursor.fetchall()
                columns = dict()

                idx = 0
                for column in cursor.description:
                    columns[column.name] = idx
                    idx += 1

                for row in result:
                    fpga_id = row[columns['fpga_id']] if 'fpga_id' in columns else '0'
                    if not fpga_id in self.fpga_mapping:
                        self.fpga_mapping[fpga_id] = 'fpga-' + str(self.next_fpga)
                        self.next_fpga += 1

                    fpga_key = self.fpga_mapping[fpga_id]

                    for column in cursor.description:
                        name = fpga_key + '-' + column.name
                        if name in self.keys:
                            data[name] = row[columns[column.name]]


                return data

        except Exception:
            self.conn = None
            raise

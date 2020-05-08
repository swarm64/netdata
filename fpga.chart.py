# -*- coding: utf-8 -*-
# Description: python module to read data from local FPGAs
# Author: Sebastian Dressler, Luc Vlaming, Ashley Fraser
# SPDX-License-Identifier: MIT

from bases.FrameworkServices.SimpleService import SimpleService

import psycopg2
import copy

priority = 90000

DEFINITIONS = {
    'bytes': {
        'options': [None, 'Transfered data', 'MB/sec', 'fpga', 'fpga', 'line'],
        'lines': [['host_to_fpga_byte_count', 'sent to fpga', 'incremental', 1, 1024*1024],
                  ['fpga_to_host_byte_count', 'received from fpga', 'incremental', -1, 1024*1024]]
    },
    'jobs': {
        'options': [None, 'Processed jobs', 'Jobs/sec', 'fpga', 'fpga', 'line'],
        'lines': [['compression_job_count', 'compressed jobs', 'incremental'],
                  ['decompression_job_count', 'decompressed jobs', 'incremental'],
                  ['decompression_and_filter_job_count', 'decompressed and filtered jobs', 'incremental'],
                  ['filter_job_count', 'filtered jobs', 'incremental']
                 ]
    },
    'max': {
        'options': [None, 'Max outstanding jobs', 'max oustanding', 'fpga', 'fpga', 'line'],
        'lines': [['max_outstanding_compression_jobs', 'compression', 'absolute'],
                  ['max_outstanding_decompression_and_filter_jobs', 'decompress and filter', 'absolute'],
                  ['max_outstanding_filter_jobs', 'filter', 'absolute']
                 ]
    },
    'pu_stats': {
        'options': [None, 'PUs utilisation', 'PU utilised', 'fpga', 'fpga', 'line'],
        'lines': [['current_pu_utilised_comp_percent', 'current compress PUs (%)', 'absolute'],
                  ['current_pu_utilised_decomp_percent', 'current decompress PUs (%)', 'absolute'],
                  ['avg_pu_utilised_comp_percent', 'avg compress PUs (%)', 'absolute'],
                  ['avg_pu_utilised_decomp_percent', 'avg decompress PUs (%)', 'absolute'],
                  ['max_pu_utilised_comp', 'max. compress PUs', 'absolute'],
                  ['max_pu_utilised_decomp', 'max. decompress PUs', 'absolute']
                 ]
    },
    'ddr_stats': {
        'options': [None, 'Successful and denied DDR transfers', 'Transfers', 'fpga', 'fpga', 'line'],
        'lines': [['avg_memory_write_transactions_percent', 'successful write transfers (%)', 'absolute'],
                  ['avg_memory_read_transactions_percent', 'successful read transfers (%)', 'absolute'],
                  ['avg_memory_write_denied_percent', 'denied write transfers (%)', 'absolute'],
                  ['avg_memory_read_denied_percent', 'denied read transfers (%)', 'absolute']
                 ]
    }
}

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
        self.fpga_count = 1
        self.dsn = self.configuration.get('dsn')
        self.pu_ddr_stats_enable = self.configuration.get('pu_ddr_stats_enable')
        self.metrics = [ 'bytes', 'jobs', 'max' ]

        conn = self._connect(self.dsn)
        with conn.cursor() as cursor:
            cursor.execute('CREATE EXTENSION IF NOT EXISTS swarm64da')
            cursor.execute('SELECT COUNT(*) FROM swarm64da.get_fpga_stats()')
            self.fpga_count = cursor.fetchone()[0]

        if self.fpga_count > 1:
            for metric in self.metrics:
                self.init_fpga_metrics(metric, 'fpga-total')

        for i in range(self.fpga_count):
            name = 'fpga-' + str(i)

            if self.pu_ddr_stats_enable:
                self.metrics.extend([ 'pu_stats', 'ddr_stats' ])

            for metric in self.metrics:
                self.init_fpga_metrics(metric, name)

        for key in self.keys:
            self.default_data[key] = 0

    def init_fpga_metrics(self, component, name):
        component_name = name + '-' + component
        component_definition = DEFINITIONS[component]
        self.order.append(component_name)
        self.definitions[component_name] = copy.deepcopy(component_definition)
        self.definitions[component_name]['options'][3] = name

        for key in self.definitions[component_name]['lines']:
            key[0] = name + '-' + key[0]
            self.keys.append(key[0])


    @staticmethod
    def check():
        return True

    def _connect(self, dsn):
        if not self.conn:
            self.conn = psycopg2.connect(dsn)
            self.conn.autocommit = True

        return self.conn

    def get_data(self):
        # It might be that no connection could be established at all
        conn = self._connect(self.dsn)

        try:
            data = copy.deepcopy(self.default_data)

            with conn.cursor() as cursor:
                cursor.execute('CREATE EXTENSION IF NOT EXISTS swarm64da')
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
                        if self.fpga_count > 1:
                            tot_name = 'fpga-total-' + column.name
                        if name in self.keys:
                            data[name] = row[columns[column.name]]
                            if self.fpga_count > 1:
                                if 'percent' in name:
                                    data[tot_name] += row[columns[column.name]]/self.fpga_count
                                else:
                                    data[tot_name] += row[columns[column.name]]

                return data

        except Exception:
            self.conn = None
            raise

# -*- coding: utf-8 -*-
# Description: python module to read data from local FPGAs
# Author: Sebastian Dressler, Luc Vlaming, Ashley Fraser
# SPDX-License-Identifier: MIT

from bases.FrameworkServices.SimpleService import SimpleService

import copy
import psycopg2

priority = 90000

DIMENSION_NAME_IDX = 3

DEFINITIONS = {
    'bytes': {
        'options': [None, 'Transfered data', 'MB/sec', 'fpga', 'fpga', 'line'],
        'lines': [
            ['host_to_fpga_byte_count', 'sent to fpga', 'incremental', 1, 1024*1024],
            ['fpga_to_host_byte_count', 'received from fpga', 'incremental', -1, 1024*1024]
        ]
    },
    'jobs': {
        'options': [None, 'Processed jobs', 'Jobs/sec', 'fpga', 'fpga', 'line'],
        'lines': [
            ['compression_job_count', 'compressed jobs', 'incremental'],
            ['decompression_job_count', 'decompressed jobs', 'incremental'],
            ['decompression_and_filter_job_count', 'decompressed and filtered jobs', 'incremental'],
            ['filter_job_count', 'filtered jobs', 'incremental']
        ]
    },
    'max': {
        'options': [None, 'Max outstanding jobs', 'max oustanding', 'fpga', 'fpga', 'line'],
        'lines': [
            ['max_outstanding_compression_jobs', 'compression', 'absolute'],
            ['max_outstanding_decompression_and_filter_jobs', 'decompress and filter', 'absolute'],
            ['max_outstanding_filter_jobs', 'filter', 'absolute']
        ]
    },
    'pu_stats': {
        'options': [None, 'PUs utilisation', 'PU utilised', 'fpga', 'fpga', 'line'],
        'lines': [
            ['current_pu_utilised_comp_percent', 'current compress PUs (%)', 'absolute'],
            ['current_pu_utilised_decomp_percent', 'current decompress PUs (%)', 'absolute'],
            ['avg_pu_utilised_comp_percent', 'avg compress PUs (%)', 'absolute'],
            ['avg_pu_utilised_decomp_percent', 'avg decompress PUs (%)', 'absolute'],
            ['max_pu_utilised_comp', 'max. compress PUs', 'absolute'],
            ['max_pu_utilised_decomp', 'max. decompress PUs', 'absolute']
        ]
    },
    'ddr_stats': {
        'options': [None, 'Successful and denied DDR transfers', 'Transfers', 'fpga', 'fpga', 'line'],
        'lines': [
            ['avg_memory_write_transactions_percent', 'successful write transfers (%)', 'absolute'],
            ['avg_memory_read_transactions_percent', 'successful read transfers (%)', 'absolute'],
            ['avg_memory_write_denied_percent', 'denied write transfers (%)', 'absolute'],
            ['avg_memory_read_denied_percent', 'denied read transfers (%)', 'absolute']
        ]
    }
}

def make_name(prefix, postfix):
    return prefix + '-' + postfix

class Service(SimpleService):
    def __init__(self, configuration=None, name=None):
        SimpleService.__init__(self, configuration=configuration, name=name)

        self.conn = None
        self.default_data = {}
        self.order = []
        self.definitions = {}
        self.dsn = self.configuration.get('dsn')

        self.fpga_mapping = {}
        fpga_ids = self.get_fpga_ids()
        for idx, fpga_id in enumerate(fpga_ids):
            self.fpga_mapping[fpga_id] = 'fpga-' + str(idx)

        self.fpga_count = len(self.fpga_mapping)
        self.columns_to_query = self._make_metrics()
        self.stats_sql = 'SELECT %s FROM swarm64da.get_fpga_stats()' % ','.join(self.columns_to_query)

    def _make_metrics(self):
        all_metrics = ['bytes', 'jobs', 'max']
        columns_to_query = set()

        # If more than 1 FPGAs available, add "total" charts for base metrics
        if self.fpga_count > 1:
            for metric in all_metrics:
                self._init_fpga_metric(metric, 'fpga-total', columns_to_query)

        # Detail charts for each FPGA
        if self.configuration.get('pu_ddr_stats_enable'):
            all_metrics.extend(['pu_stats', 'ddr_stats'])

        for _, fpga_name in self.fpga_mapping.items():
            for metric in all_metrics:
                self._init_fpga_metric(metric, fpga_name, columns_to_query)

        return ['fpga_id'] + list(columns_to_query)

    def _init_fpga_metric(self, component, name, columns_to_query):
        component_name = make_name(name, component)
        component_definition = DEFINITIONS[component]
        self.order.append(component_name)
        self.definitions[component_name] = copy.deepcopy(component_definition)
        self.definitions[component_name]['options'][DIMENSION_NAME_IDX] = name

        for dimension in self.definitions[component_name]['lines']:
            column_name = dimension[0]
            columns_to_query.add(column_name)

            unique_dimension_name = make_name(name, column_name)
            dimension[0] = unique_dimension_name
            self.default_data[unique_dimension_name] = 0

    @staticmethod
    def check():
        return True

    def get_conn(self):
        if not self.conn:
            self.conn = psycopg2.connect(self.dsn)
            self.conn.autocommit = True

            with self.conn.cursor() as cursor:
                # Might throw an exception here when extension is missing
                cursor.execute('CREATE EXTENSION IF NOT EXISTS swarm64da')

        return self.conn

    def get_fpga_ids(self):
        with self.get_conn().cursor() as cursor:
            # Might throw an exception here when extension is missing
            cursor.execute('SELECT fpga_id FROM swarm64da.get_fpga_stats()')
            return [item[0] for item in cursor.fetchall()]

    def get_data(self):
        # It might be that no connection could be established at all
        conn = self.get_conn()

        try:
            data = copy.deepcopy(self.default_data)

            with conn.cursor() as cursor:
                cursor.execute(self.stats_sql)
                result = cursor.fetchall()

            for row in result:
                fpga_key = self.fpga_mapping[row[0]]
                for idx, column_name in enumerate(self.columns_to_query[1:], start=1):
                    name = make_name(fpga_key, column_name)
                    data[name] = row[idx]

                    if self.fpga_count > 1:
                        fpga_total_name = make_name('fpga-total', column_name)
                        if 'percent' in name:
                            data[fpga_total_name] += row[idx] / self.fpga_count
                        else:
                            data[fpga_total_name] += row[idx]

            return data

        except Exception:
            self.conn = None
            return None

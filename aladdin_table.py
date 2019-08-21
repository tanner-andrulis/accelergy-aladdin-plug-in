# -*- coding: utf-8 -*-
ALADDIN_ACCURACY = 70  # in your metric, please set the accuracy you think Aladdin's estimations are
# MIT License
#
# Copyright (c) 2019 Yannan (Nellie) Wu
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import csv, os, sys, math
from accelergy.helper_functions import oneD_linear_interpolation

class AladdinTable(object):
    """
    A dummy estimation plug-in
    Note that this plug-in is just a placeholder to illustrate the estimation plug-in interface
    It can be used as a template for creating user-defined plug-ins
    The energy values returned by this plug-in is not meaningful
    """
    # -------------------------------------------------------------------------------------
    # Interface functions, function name, input arguments, and output have to adhere
    # -------------------------------------------------------------------------------------
    def __init__(self):
        self.estimator_name =  "Aladdin_table"

        # example primitive classes supported by this estimator
        self.supported_pc = ['regfile',
                             'bitwise', 'adder', 'multiplier', 'mac',
                            'fp32adder', 'fp32multiplier', 'fp32mac',
                            'fp64adder', 'fp64multiplier', 'fp64mac']

    def primitive_action_supported(self, interface):
        """
        :param interface:
        - contains four keys:
        1. class_name : string
        2. attributes: dictionary of name: value
        3. action_name: string
        4. arguments: dictionary of name: value

        :type interface: dict

        :return return the accuracy if supported, return 0 if not
        :rtype: int

        """
        if 'technology' not in interface['attributes']:
            print('ALADDIN WARN: no technology specified in the request, cannot perform estimation')
        class_name = interface['class_name']
        technology = interface['attributes']['technology']
        if (technology == 40  or technology == '40' or technology == '40nm') and class_name in self.supported_pc:
            return ALADDIN_ACCURACY
        return 0  # if not supported, accuracy is 0


    def estimate_energy(self, interface):
        """
        :param interface:
        - contains four keys:
        1. class_name : string
        2. attributes: dictionary of name: value
        3. action_name: string
        4. arguments: dictionary of name: value

       :return the estimated energy
       :rtype float

        """
        class_name = interface['class_name']
        query_function_name = class_name + '_estimate_energy'
        energy = getattr(self, query_function_name)(interface)
        return energy

    # ============================================================
    # User's functions, purely user-defined
    # ============================================================
    @staticmethod
    def query_csv_using_latency(interface, csv_file_path):
        # default latency for Aladdin estimation is 5ns
        latency = interface['attributes']['latency'] if 'latency' in interface['attributes'] else 5
        # round to an existing latency (can perform linear interpolation as well)
        latency = math.ceil(latency)
        if latency > 10:
            latency = 10
        elif latency > 6:
            latency = 6
        # there are only two types of energy in Aladdin tables
        action_name = 'idle energy(pJ)' if interface['action_name'] == 'idle' else 'dynamic energy(pJ)'
        with open(csv_file_path) as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                if row['latency(ns)'] == str(latency):
                    energy = float(row[action_name])
                    break
        return energy

    def regFile_estimate_energy(self, interface):
        # register file access is naively modeled as vector access of registers
        # register energy consumption is generated according to latency

        width = interface['attributes']['width']
        this_dir, this_filename = os.path.split(__file__)
        csv_file_path = os.path.join(this_dir, 'data/reg.csv')
        reg_energy = AladdinTable.query_csv_using_latency(interface, csv_file_path)
        reg_file_energy = reg_energy * width  # register file access is naively modeled as vector access of registers
        return reg_file_energy

    # ----------------- mac related ---------------------------
    
    def mac_estimate_energy(self, interface):
        # mac is naively modeled as adder and multiplier
        adder_energy = self.adder_estimate_energy(interface)
        multiplier_energy = self.multiplier_estimate_energy(interface)
        energy = adder_energy + multiplier_energy
        return energy

    def fp32mac_estimate_energy(self, interface):
        # fpmac is naively modeled as fpadder and fpmultiplier
        fpadder_energy = self.fp32adder_estimate_energy(interface)
        fpmultiplier_energy = self.fp32multiplier_estimate_energy(interface)
        energy = fpadder_energy + fpmultiplier_energy
        return energy

    def fp64mac_estimate_energy(self, interface):
        # fpmac is naively modeled as fpadder and fpmultiplier
        fpadder_energy = self.fp64adder_estimate_energy(interface)
        fpmultiplier_energy = self.fp64multiplier_estimate_energy(interface)
        energy = fpadder_energy + fpmultiplier_energy
        return energy

    def adder_estimate_energy(self, interface):
        this_dir, this_filename = os.path.split(__file__)
        csv_file_path = os.path.join(this_dir, 'data/adder.csv')
        csv_energy = AladdinTable.query_csv_using_latency(interface, csv_file_path)
        # since Aladdin only provides 32 bit adder energy, perform linear interpolation in terms of datawidth
        energy = oneD_linear_interpolation(interface['attributes']['datawidth'], [{'x' : 0, 'y' : 0 }, {'x': 32, 'y': csv_energy}])
        return energy

    def fp32adder_estimate_energy(self, interface):
        this_dir, this_filename = os.path.split(__file__)
        # Aladdin plug-in uses the double precision table for floating point adders
        csv_file_path = os.path.join(this_dir, 'data/fp_sp_adder.csv')
        csv_energy = AladdinTable.query_csv_using_latency(interface, csv_file_path)
        # since Aladdin only provides 32 bit adder energy, perform linear interpolation in terms of datawidth
        energy = oneD_linear_interpolation(interface['attributes']['datawidth'], [{'x' : 0, 'y' : 0 }, {'x': 32, 'y': csv_energy}])
        return energy

    def fp64adder_estimate_energy(self, interface):
        this_dir, this_filename = os.path.split(__file__)
        # Aladdin plug-in uses the double precision table for floating point adders
        csv_file_path = os.path.join(this_dir, 'data/fp_dp_adder.csv')
        csv_energy = AladdinTable.query_csv_using_latency(interface, csv_file_path)
        # since Aladdin only provides 32 bit adder energy, perform linear interpolation in terms of datawidth
        energy = oneD_linear_interpolation(interface['attributes']['datawidth'], [{'x' : 0, 'y' : 0 }, {'x': 32, 'y': csv_energy}])
        return energy

    def multiplier_estimate_energy(self, interface):
        this_dir, this_filename = os.path.split(__file__)
        csv_file_path = os.path.join(this_dir, 'data/multiplier.csv')
        csv_energy = AladdinTable.query_csv_using_latency(interface, csv_file_path)
        # since Aladdin only provides 32 bit adder energy, perform quadratic interpolation in terms of datawidth
        energy = oneD_quadratic_interpolation(interface['attributes']['datawidth'], [{'x' : 0, 'y' : 0 }, {'x': 32, 'y': csv_energy}])
        return energy

    def fp32multiplier_estimate_energy(self, interface):
        this_dir, this_filename = os.path.split(__file__)
        # Aladdin plug-in uses the double precision table for floating point multipliers
        csv_file_path = os.path.join(this_dir, 'data/fp_sp_multiplier.csv')
        csv_energy = AladdinTable.query_csv_using_latency(interface, csv_file_path)
        # since Aladdin only provides 32 bit adder energy, perform quadratic interpolation in terms of datawidth
        energy = oneD_quadratic_interpolation(interface['attributes']['datawidth'], [{'x' : 0, 'y' : 0 }, {'x': 32, 'y': csv_energy}])
        return energy

    def fp64multiplier_estimate_energy(self, interface):
        this_dir, this_filename = os.path.split(__file__)
        # Aladdin plug-in uses the double precision table for floating point multipliers
        csv_file_path = os.path.join(this_dir, 'data/fp_dp_multiplier.csv')
        csv_energy = AladdinTable.query_csv_using_latency(interface, csv_file_path)
        # since Aladdin only provides 32 bit adder energy, perform quadratic interpolation in terms of datawidth
        energy = oneD_quadratic_interpolation(interface['attributes']['datawidth'], [{'x' : 0, 'y' : 0 }, {'x': 32, 'y': csv_energy}])
        return energy

    def bitwise_estimate_energy(self, interface):
        this_dir, this_filename = os.path.split(__file__)
        csv_file_path = os.path.join(this_dir, 'data/bitwise.csv')
        csv_energy = AladdinTable.query_csv_using_latency(interface, csv_file_path)
        # since Aladdin only provides 32 bit adder energy, perform quadratic interpolation in terms of datawidth
        energy = csv_energy * interface['attributes']['num']
        return energy

# helper function
def oneD_quadratic_interpolation(desired_x, known):
    """
    utility function that performs 1D linear interpolation with a known energy value
    :param desired_x: integer value of the desired attribute/argument
    :param known: list of dictionary [{x: <value>, y: <energy>}]

    :return energy value with desired attribute/argument

    """
    ordered_list = []
    if known[1]['x'] < known[0]['x']:
        ordered_list[0] = known[1]['x']
    else:
        ordered_list = known

    slope = (known[1]['y'] - known[0]['y']) / (known[1]['x'] - known[0]['x'])
    desired_energy = slope**2 * (desired_x - ordered_list[0]['x']) + ordered_list[0]['y']
    return desired_energy

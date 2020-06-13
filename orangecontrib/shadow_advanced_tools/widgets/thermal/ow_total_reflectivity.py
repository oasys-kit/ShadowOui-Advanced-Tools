#!/usr/bin/env python
# -*- coding: utf-8 -*-
# #########################################################################
# Copyright (c) 2020, UChicago Argonne, LLC. All rights reserved.         #
#                                                                         #
# Copyright 2020. UChicago Argonne, LLC. This software was produced       #
# under U.S. Government contract DE-AC02-06CH11357 for Argonne National   #
# Laboratory (ANL), which is operated by UChicago Argonne, LLC for the    #
# U.S. Department of Energy. The U.S. Government has rights to use,       #
# reproduce, and distribute this software.  NEITHER THE GOVERNMENT NOR    #
# UChicago Argonne, LLC MAKES ANY WARRANTY, EXPRESS OR IMPLIED, OR        #
# ASSUMES ANY LIABILITY FOR THE USE OF THIS SOFTWARE.  If software is     #
# modified to produce derivative works, such modified software should     #
# be clearly marked, so as not to confuse it with the version available   #
# from ANL.                                                               #
#                                                                         #
# Additionally, redistribution and use in source and binary forms, with   #
# or without modification, are permitted provided that the following      #
# conditions are met:                                                     #
#                                                                         #
#     * Redistributions of source code must retain the above copyright    #
#       notice, this list of conditions and the following disclaimer.     #
#                                                                         #
#     * Redistributions in binary form must reproduce the above copyright #
#       notice, this list of conditions and the following disclaimer in   #
#       the documentation and/or other materials provided with the        #
#       distribution.                                                     #
#                                                                         #
#     * Neither the name of UChicago Argonne, LLC, Argonne National       #
#       Laboratory, ANL, the U.S. Government, nor the names of its        #
#       contributors may be used to endorse or promote products derived   #
#       from this software without specific prior written permission.     #
#                                                                         #
# THIS SOFTWARE IS PROVIDED BY UChicago Argonne, LLC AND CONTRIBUTORS     #
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT       #
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS       #
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL UChicago     #
# Argonne, LLC OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,        #
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,    #
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;        #
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER        #
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT      #
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN       #
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE         #
# POSSIBILITY OF SUCH DAMAGE.                                             #
# #########################################################################

import sys, numpy, os

from PyQt5.QtWidgets import QMessageBox

from orangewidget import gui
from orangewidget.widget import OWAction
from orangewidget.settings import Setting

from oasys.widgets.exchange import DataExchangeObject
from oasys.widgets import gui as oasysgui

from orangecontrib.shadow.util.shadow_util import ShadowCongruence
from orangecontrib.shadow.widgets.gui.ow_automatic_element import AutomaticElement

class TotalReflectivityCalculator(AutomaticElement):

    name = "Total Reflectivity Calculator"
    description = "Total Reflectivity Calculator"
    icon = "icons/total_reflectivity.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 5.01
    category = "User Defined"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Mirror Reflectivity #1", DataExchangeObject, "set_ref_1"),
              ("Mirror Reflectivity #2", DataExchangeObject, "set_ref_2"),
              ("Mirror Reflectivity #3", DataExchangeObject, "set_ref_3"),
              ("Diffraction Profile #1", DataExchangeObject, "set_dif_1"),
              ("Diffraction Profile #2", DataExchangeObject, "set_dif_2"),
              ("MultiLayer Reflectivity #1", DataExchangeObject, "set_mul_1"),
              ("MultiLayer Reflectivity #2", DataExchangeObject, "set_mul_2"),
              ("Power Output #1", DataExchangeObject, "set_pow_1")]

    outputs = [{"name":"Total Reflectivity",
                "type":DataExchangeObject,
                "doc":"Total Reflectivity",
                "id":"total_reflectivity"}]

    want_main_area = 1

    ref_1 = None
    ref_2 = None
    ref_3 = None
    dif_1 = None
    dif_2 = None
    mul_1 = None
    mul_2 = None
    pow_1 = None
    
    n_ref_1 = Setting(1)
    n_ref_2 = Setting(1)
    n_ref_3 = Setting(1)
    n_dif_1 = Setting(1)
    n_dif_2 = Setting(1)
    n_mul_1 = Setting(1)
    n_mul_2 = Setting(1)

    energy_from = Setting(1000.0)
    energy_to   = Setting(51000.0)
    energy_nr = Setting(5000)

    def __init__(self):
        super(TotalReflectivityCalculator, self).__init__(show_automatic_box=False)

        self.runaction = OWAction("Calculate Total Reflectivity", self)
        self.runaction.triggered.connect(self.calculate_total_reflectivity)
        self.addAction(self.runaction)

        self.setFixedWidth(1200)
        self.setFixedHeight(710)

        box0 = gui.widgetBox(self.controlArea, "", orientation="horizontal")
        gui.button(box0, self, "Calculate Total Reflectivity", callback=self.calculate_total_reflectivity, height=45)

        box1 = gui.widgetBox(self.controlArea, "Input Data", orientation="vertical")
        
        items = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
        
        self.cb_ref_1 = gui.comboBox(box1, self, "n_ref_1", label="Nr. of Mirror Reflectivity #1", items=items, labelWidth=350, sendSelectedValue=False, orientation="horizontal")
        self.cb_ref_2 = gui.comboBox(box1, self, "n_ref_2", label="Nr. of Mirror Reflectivity #2", items=items, labelWidth=350, sendSelectedValue=False, orientation="horizontal")
        self.cb_ref_3 = gui.comboBox(box1, self, "n_ref_3", label="Nr. of Mirror Reflectivity #3", items=items, labelWidth=350, sendSelectedValue=False, orientation="horizontal")
        self.cb_ref_1.setEnabled(False)
        self.cb_ref_2.setEnabled(False)
        self.cb_ref_3.setEnabled(False)

        gui.separator(box1)

        self.cb_dif_1 = gui.comboBox(box1, self, "n_dif_1", label="Nr. of Diffraction Profile #1", items=items, labelWidth=350, sendSelectedValue=False, orientation="horizontal")
        self.cb_dif_2 = gui.comboBox(box1, self, "n_dif_2", label="Nr. of Diffraction Profile #2", items=items, labelWidth=350, sendSelectedValue=False, orientation="horizontal")
        self.cb_dif_1.setEnabled(False)
        self.cb_dif_2.setEnabled(False)

        gui.separator(box1)

        self.cb_mul_1 = gui.comboBox(box1, self, "n_mul_1", label="Nr. of MultiLayer Reflectivity #1", items=items, labelWidth=350, sendSelectedValue=False, orientation="horizontal")
        self.cb_mul_2 = gui.comboBox(box1, self, "n_mul_2", label="Nr. of MultiLayer Reflectivity #2", items=items, labelWidth=350, sendSelectedValue=False, orientation="horizontal")
        self.cb_mul_1.setEnabled(False)
        self.cb_mul_2.setEnabled(False)

        gui.rubber(self.controlArea)

    def __get_mirror_reflectivity(self, exchange_data):
        if not exchange_data.get_program_name() == "XOPPY": raise ValueError("Only XOPPY widgets are accepted")
        if not exchange_data.get_widget_name() == "XF1F2": raise ValueError("Only XF1F2 widgets are accepted")

        return exchange_data.get_content("xoppy_data")

    def __get_diffraction_profile(self, exchange_data):
        if not exchange_data.get_program_name() == "XOPPY": raise ValueError("Only XOPPY widgets are accepted")
        if not exchange_data.get_widget_name() == "XCRYSTAL": raise ValueError("Only XCRYSTAL widgets are accepted")

        xoppy_data = exchange_data.get_content("xoppy_data")

        energies = xoppy_data[:, 0]

        reflectivity_s = xoppy_data[:, 3]
        reflectivity_p = xoppy_data[:, 4]

        data = numpy.zeros((len(energies), 2))
        data[:, 0] = energies
        data[:, 1] = 0.5 * (reflectivity_p + reflectivity_s)
        
        return data
    
    def __get_multilayer_reflectivity(self, exchange_data):
        if not exchange_data.get_program_name() == "XOPPY": raise ValueError("Only XOPPY widgets are accepted")
        if not exchange_data.get_widget_name() == "MULTILAYER": raise ValueError("Only MULTILAYER widgets are accepted")

        xoppy_data = exchange_data.get_content("xoppy_data")

        energies = xoppy_data[:, 0]

        reflectivity_s = xoppy_data[:, 1]
        reflectivity_p = xoppy_data[:, 2]

        data = numpy.zeros((len(energies), 2))
        data[:, 0] = energies
        data[:, 1] = 0.5 * (reflectivity_p + reflectivity_s)

        return data    
    
    def __get_power_data(self, exchange_data):
        if not exchange_data.get_program_name() == "XOPPY": raise ValueError("Only XOPPY widgets are accepted")
        if not exchange_data.get_widget_name() == "POWER": raise ValueError("Only POWER widgets are accepted")

        xoppy_data = exchange_data.get_content("xoppy_data")

        energies = xoppy_data[:, 0]

        data = numpy.zeros((len(energies), 2))
        data[:, 0] = energies
        data[:, 1] = xoppy_data[:, -1] / xoppy_data[:, 1]
        
        return data
 
    def __set_data(self, exchange_data, getter_method, field, combobox):
        if exchange_data is None: 
            setattr(self, field, None)
            if not combobox is None: combobox.setEnabled(False)
        else:
            try:
                setattr(self, field, getter_method(exchange_data))
                if not combobox is None: combobox.setEnabled(True)
            except Exception as e:
                if not combobox is None: combobox.setEnabled(False)
                
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)
                
                if self.IS_DEVELOP: raise e

    def set_ref_1(self, exchange_data): self.__set_data(exchange_data, self.__get_mirror_reflectivity,     "ref_1", self.cb_ref_1)
    def set_ref_2(self, exchange_data): self.__set_data(exchange_data, self.__get_mirror_reflectivity,     "ref_2", self.cb_ref_2)
    def set_ref_3(self, exchange_data): self.__set_data(exchange_data, self.__get_mirror_reflectivity,     "ref_3", self.cb_ref_3)
    def set_dif_1(self, exchange_data): self.__set_data(exchange_data, self.__get_diffraction_profile,     "dif_1", self.cb_dif_1)
    def set_dif_2(self, exchange_data): self.__set_data(exchange_data, self.__get_diffraction_profile,     "dif_2", self.cb_dif_2)
    def set_mul_1(self, exchange_data): self.__set_data(exchange_data, self.__get_multilayer_reflectivity, "mul_1", self.cb_mul_1)
    def set_mul_2(self, exchange_data): self.__set_data(exchange_data, self.__get_multilayer_reflectivity, "mul_2", self.cb_mul_2)
    def set_pow_1(self, exchange_data): self.__set_data(exchange_data, self.__get_power_data,              "pow_1", None)

    def __add_data_to_total_reflectivity(self, total_reflectivity, data, nr_data):
        if not data is None: total_reflectivity[:, 1] *= numpy.interp(total_reflectivity[:, 0], data[:, 0], data[:, 1])**nr_data

    def calculate_total_reflectivity(self):
        energies = numpy.linspace(self.energy_from, self.energy_to, self.energy_nr)

        total_reflectivity = numpy.ones((self.energy_nr, 2))
        total_reflectivity[:, 0] = energies

        self.__add_data_to_total_reflectivity(total_reflectivity, self.ref_1, self.n_ref_1)
        self.__add_data_to_total_reflectivity(total_reflectivity, self.ref_2, self.n_ref_2)
        self.__add_data_to_total_reflectivity(total_reflectivity, self.ref_3, self.n_ref_3)

        self.__add_data_to_total_reflectivity(total_reflectivity, self.dif_1, self.n_dif_1)
        self.__add_data_to_total_reflectivity(total_reflectivity, self.dif_2, self.n_dif_2)

        self.__add_data_to_total_reflectivity(total_reflectivity, self.mul_1, self.n_mul_1)
        self.__add_data_to_total_reflectivity(total_reflectivity, self.mul_2, self.n_mul_2)

        self.__add_data_to_total_reflectivity(total_reflectivity, self.pow_1, 1)

        calculated_data = DataExchangeObject("ShadowOui_Thermal", "TOTAL_REFLECTIVITY")
        calculated_data.add_content("total_reflectivity", total_reflectivity)

        self.send("Total Reflectivity", calculated_data)


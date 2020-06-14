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
from oasys.widgets import widget, congruence

class TotalFilterCalculator(widget.OWWidget):

    name = "Total Filter Calculator"
    description = "Total Filter Calculator"
    icon = "icons/total_filter.png"
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

    outputs = [{"name":"Total Filter",
                "type":DataExchangeObject,
                "doc":"Total Filter",
                "id":"total_filter"}]

    want_main_area = 1

    ref_1 = None
    ref_2 = None
    ref_3 = None
    dif_1 = None
    dif_2 = None
    mul_1 = None
    mul_2 = None
    pow_1 = None

    check_ref_1 = Setting(0)
    check_ref_2 = Setting(0)
    check_ref_3 = Setting(0)
    check_dif_1 = Setting(0)
    check_dif_2 = Setting(0)
    check_mul_1 = Setting(0)
    check_mul_2 = Setting(0)
    check_pow_1 = Setting(0)

    n_ref_1 = Setting(0)
    n_ref_2 = Setting(0)
    n_ref_3 = Setting(0)
    n_dif_1 = Setting(0)
    n_dif_2 = Setting(0)
    n_mul_1 = Setting(0)
    n_mul_2 = Setting(0)

    energy_from = Setting(1000.0)
    energy_to   = Setting(51000.0)
    energy_nr = Setting(5000)

    CONTROL_AREA_WIDTH = 405

    def __init__(self):
        super(TotalFilterCalculator, self).__init__()

        self.runaction = OWAction("Calculate Total Filter", self)
        self.runaction.triggered.connect(self.calculate_total_filter)
        self.addAction(self.runaction)

        self.setFixedWidth(1200)
        self.setFixedHeight(710)

        self.controlArea.setFixedWidth(self.CONTROL_AREA_WIDTH)

        box0 = oasysgui.widgetBox(self.controlArea, "", orientation="horizontal", width=self.CONTROL_AREA_WIDTH-5)
        gui.button(box0, self, "Calculate Total Filter", callback=self.calculate_total_filter, height=45)

        box1 = oasysgui.widgetBox(self.controlArea, "Energy Range", orientation="vertical", width=self.CONTROL_AREA_WIDTH-5)

        oasysgui.lineEdit(box1, self, "energy_from", "Energy From [eV]", labelWidth=250, orientation="horizontal", valueType=float)
        oasysgui.lineEdit(box1, self, "energy_to", "Energy to [eV]", labelWidth=250, orientation="horizontal", valueType=float)
        oasysgui.lineEdit(box1, self, "energy_nr", "Nr. of energies", labelWidth=250, orientation="horizontal", valueType=int)

        box1 = oasysgui.widgetBox(self.controlArea, "Input Data", orientation="vertical", width=self.CONTROL_AREA_WIDTH-5)

        items = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

        def build_combo(container, master, field_name, label, has_combo=True):
            box = gui.widgetBox(container, "", orientation="horizontal")
            gui.checkBox(box, master, "check_" + field_name[2:], label="" if has_combo else label)
            if has_combo: gui.comboBox(box, master, field_name, label=label, items=items, labelWidth=350, sendSelectedValue=False, orientation="horizontal")
            box.setEnabled(False)

            return box

        self.cb_ref_1 = build_combo(box1, self, "n_ref_1", label="Nr. of Mirror Reflectivity #1")
        self.cb_ref_2 = build_combo(box1, self, "n_ref_2", label="Nr. of Mirror Reflectivity #2")
        self.cb_ref_3 = build_combo(box1, self, "n_ref_3", label="Nr. of Mirror Reflectivity #3")

        gui.separator(box1)

        self.cb_dif_1 = build_combo(box1, self, "n_dif_1", label="Nr. of Diffraction Profile #1")
        self.cb_dif_2 = build_combo(box1, self, "n_dif_2", label="Nr. of Diffraction Profile #2")

        gui.separator(box1)

        self.cb_mul_1 = build_combo(box1, self, "n_mul_1", label="Nr. of MultiLayer Reflectivity #1")
        self.cb_mul_2 = build_combo(box1, self, "n_mul_2", label="Nr. of MultiLayer Reflectivity #2")

        gui.separator(box1)

        self.cb_pow_1 = build_combo(box1, self, "n_pow_1", label="Power Widget Input", has_combo=False)

        gui.rubber(self.controlArea)

        tabs = oasysgui.tabWidget(self.mainArea)
        tabs.setFixedHeight(self.height()-15)
        tabs.setFixedWidth(770)

        tab_fil = oasysgui.createTabPage(tabs, "Total Filter")

        self.filter_plot = oasysgui.plotWindow(tab_fil, position=True)
        self.filter_plot.setFixedHeight(self.height()-60)
        self.filter_plot.setFixedWidth(760)
        self.filter_plot.setGraphXLabel("Energy [eV]")
        self.filter_plot.setGraphYLabel("Intensity Factor")
        self.filter_plot.setGraphTitle("Total Filter")


    def __get_mirror_reflectivity(self, exchange_data):
        try:
            if not exchange_data.get_program_name() == "XOPPY": raise ValueError("Only XOPPY widgets are accepted")
            if not exchange_data.get_widget_name() == "XF1F2": raise ValueError("Only XF1F2 widgets are accepted")

            return exchange_data.get_content("xoppy_data")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

            if self.IS_DEVELOP: raise e

    def __get_diffraction_profile(self, exchange_data):
        try:
            if not exchange_data.get_program_name() == "XOPPY": raise ValueError("Only XOPPY widgets are accepted")
            if not exchange_data.get_widget_name() == "XCRYSTAL": raise ValueError("Only XCRYSTAL widgets are accepted")

            xoppy_data = exchange_data.get_content("xoppy_data")

            energies = xoppy_data[:, 0]

            reflectivity_s = xoppy_data[:, 5]
            reflectivity_p = xoppy_data[:, 6]

            reflectivity_s[numpy.where(numpy.isnan(reflectivity_s))] = 0.0
            reflectivity_p[numpy.where(numpy.isnan(reflectivity_p))] = 0.0

            data = numpy.zeros((len(energies), 2))
            data[:, 0] = energies
            data[:, 1] = 0.5 * (reflectivity_p + reflectivity_s)

            return data
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

            if self.IS_DEVELOP: raise e

    def __get_multilayer_reflectivity(self, exchange_data):
        try:
            if not exchange_data.get_program_name() == "XOPPY": raise ValueError("Only XOPPY widgets are accepted")
            if not exchange_data.get_widget_name() == "MULTILAYER": raise ValueError("Only MULTILAYER widgets are accepted")

            xoppy_data = exchange_data.get_content("xoppy_data")

            energies = xoppy_data[:, 0]

            reflectivity_s = xoppy_data[:, 1]
            reflectivity_p = xoppy_data[:, 2]

            reflectivity_s[numpy.where(numpy.isnan(reflectivity_s))] = 0
            reflectivity_p[numpy.where(numpy.isnan(reflectivity_p))] = 0

            data = numpy.zeros((len(energies), 2))
            data[:, 0] = energies
            data[:, 1] = 0.5 * (reflectivity_p + reflectivity_s)

            return data
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

            if self.IS_DEVELOP: raise e

    def __get_power_data(self, exchange_data):
        try:
            if not exchange_data.get_program_name() == "XOPPY": raise ValueError("Only XOPPY widgets are accepted")
            if not exchange_data.get_widget_name() == "POWER": raise ValueError("Only POWER widgets are accepted")

            xoppy_data = exchange_data.get_content("xoppy_data")

            energies = xoppy_data[:, 0]

            data = numpy.zeros((len(energies), 2))
            data[:, 0] = energies
            data[:, 1] = xoppy_data[:, -1] / xoppy_data[:, 1]

            return data
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

            if self.IS_DEVELOP: raise e

    def __set_data(self, exchange_data, getter_method, field, combobox):
        if exchange_data is None: 
            setattr(self, field, None)
            setattr(self, "check_" + field, 0)
            combobox.setEnabled(False)
        else:
            try:
                setattr(self, field, getter_method(exchange_data))
                setattr(self, "check_" + field, 1)
                combobox.setEnabled(True)
            except Exception as e:
                combobox.setEnabled(False)
                
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)
                
                if self.IS_DEVELOP: raise e

    def set_ref_1(self, exchange_data): self.__set_data(exchange_data, self.__get_mirror_reflectivity,     "ref_1", self.cb_ref_1)
    def set_ref_2(self, exchange_data): self.__set_data(exchange_data, self.__get_mirror_reflectivity,     "ref_2", self.cb_ref_2)
    def set_ref_3(self, exchange_data): self.__set_data(exchange_data, self.__get_mirror_reflectivity,     "ref_3", self.cb_ref_3)
    def set_dif_1(self, exchange_data): self.__set_data(exchange_data, self.__get_diffraction_profile,     "dif_1", self.cb_dif_1)
    def set_dif_2(self, exchange_data): self.__set_data(exchange_data, self.__get_diffraction_profile,     "dif_2", self.cb_dif_2)
    def set_mul_1(self, exchange_data): self.__set_data(exchange_data, self.__get_multilayer_reflectivity, "mul_1", self.cb_mul_1)
    def set_mul_2(self, exchange_data): self.__set_data(exchange_data, self.__get_multilayer_reflectivity, "mul_2", self.cb_mul_2)
    def set_pow_1(self, exchange_data): self.__set_data(exchange_data, self.__get_power_data,              "pow_1", self.cb_pow_1)

    def __add_data_to_total_filter(self, total_reflectivity, data, nr_data, check):
        if not data is None and check==1: total_reflectivity[:, 1] *= numpy.interp(total_reflectivity[:, 0], data[:, 0], data[:, 1])**(nr_data+1)

    def calculate_total_filter(self):
        try:
            congruence.checkStrictlyPositiveNumber(self.energy_from, "Energy From")
            congruence.checkStrictlyPositiveNumber(self.energy_to, "Energy to")
            congruence.checkStrictlyPositiveNumber(self.energy_nr, "Nr. of energies")
            congruence.checkLessThan(self.energy_from, self.energy_to, "Energy From", "Energy to")

            energies = numpy.linspace(self.energy_from, self.energy_to, self.energy_nr)

            total_filter = numpy.ones((self.energy_nr, 2))
            total_filter[:, 0] = energies

            self.__add_data_to_total_filter(total_filter, self.ref_1, self.n_ref_1, self.check_ref_1)
            self.__add_data_to_total_filter(total_filter, self.ref_2, self.n_ref_2, self.check_ref_2)
            self.__add_data_to_total_filter(total_filter, self.ref_3, self.n_ref_3, self.check_ref_3)

            self.__add_data_to_total_filter(total_filter, self.dif_1, self.n_dif_1, self.check_dif_1)
            self.__add_data_to_total_filter(total_filter, self.dif_2, self.n_dif_2, self.check_dif_2)

            self.__add_data_to_total_filter(total_filter, self.mul_1, self.n_mul_1, self.check_mul_1)
            self.__add_data_to_total_filter(total_filter, self.mul_2, self.n_mul_2, self.check_mul_2)

            self.__add_data_to_total_filter(total_filter, self.pow_1, 1, self.check_pow_1)

            total_filter[numpy.where(numpy.isnan(total_filter))] = 0.0

            if not total_filter[:, 1].sum() == total_filter.shape[0]:
                self.filter_plot.clear()
                self.filter_plot.addCurve(total_filter[:, 0], total_filter[:, 1], replace=True, legend="Total Filter")
                self.filter_plot.setGraphXLabel("Energy [eV]")
                self.filter_plot.setGraphYLabel("Intensity Factor")
                self.filter_plot.setGraphTitle("Total Filter")

                calculated_data = DataExchangeObject("ShadowOui_Thermal", "TOTAL_FILTER")
                calculated_data.add_content("total_filter", total_filter)

                self.send("Total Filter", calculated_data)
            else:
                raise ValueError("Calculation not possibile: no input data")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

            if self.IS_DEVELOP: raise e




#!/usr/bin/env python
# -*- coding: utf-8 -*-
# #########################################################################
# Copyright (c) 2018, UChicago Argonne, LLC. All rights reserved.         #
#                                                                         #
# Copyright 2018. UChicago Argonne, LLC. This software was produced       #
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

import scipy.constants as codata
m2ev = codata.c * codata.h / codata.e

from PyQt5.QtGui import QPalette, QFont, QColor
from PyQt5.QtWidgets import QApplication, QMessageBox

from orangewidget.widget import OWAction
from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets import widget
from oasys.widgets import gui as oasysgui
from oasys.widgets.gui import ConfirmDialog
from oasys.widgets import congruence

from oasys.util.oasys_util import TriggerIn, TriggerOut
from oasys.widgets.exchange import DataExchangeObject

from syned.storage_ring.light_source import LightSource
from syned.widget.widget_decorator import WidgetDecorator

class EnergyBinning(object):
    def __init__(self,
                 energy_value = 0.0,
                 energy_value_to = None,
                 energy_step       = 0.0,
                 power_step        = None):
        self.energy_value    = energy_value
        self.energy_value_to = energy_value_to
        self.energy_step     = energy_step
        self.power_step      = power_step

    def __str__(self):
        return str(self.energy_value) + ", " + str(self.energy_value_to) + ", " + str(self.energy_step) + ", " + str(self.power_step)

class PowerLoopPoint(widget.OWWidget):

    name = "Power Density Loop Point"
    description = "Tools: LoopPoint"
    icon = "icons/cycle.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 5
    category = "User Defined"
    keywords = ["data", "file", "load", "read"]

    inputs = WidgetDecorator.syned_input_data()
    inputs.append(("Trigger", TriggerIn, "passTrigger"))
    inputs.append(("Energy Spectrum", DataExchangeObject, "acceptEnergySpectrum" ))
    inputs.append(("Filters", DataExchangeObject, "acceptFilters" ))

    outputs = [{"name":"Trigger",
                "type":TriggerOut,
                "doc":"Trigger",
                "id":"Trigger"}]
    want_main_area = 1

    current_new_object = 0
    number_of_new_objects = 0
    
    total_current_new_object = 0
    total_new_objects = Setting(0)

    run_loop = True
    suspend_loop = False

    energies = Setting("")

    seed_increment=Setting(1)

    autobinning = Setting(1)

    auto_n_step = Setting(1001)
    auto_perc_total_power = Setting(99)

    send_power_step = Setting(0)

    electron_energy = Setting(6.0)
    K_vertical = Setting(1.943722)
    K_horizontal = Setting(0.0)
    period_length = Setting(0.025)
    number_of_periods = Setting(184)
    theta_x=Setting(0.0)
    theta_z=Setting(0.0)

    current_energy_binning = -1
    current_energy_value = None
    current_energy_step = None
    current_power_step = None

    energy_binnings = None

    external_binning = False

    filters = None
    spectrum_data = None

    #################################
    process_last = True
    #################################

    def __init__(self):
        self.runaction = OWAction("Start", self)
        self.runaction.triggered.connect(self.startLoop)
        self.addAction(self.runaction)

        self.runaction = OWAction("Stop", self)
        self.runaction.triggered.connect(self.stopLoop)
        self.addAction(self.runaction)

        self.runaction = OWAction("Suspend", self)
        self.runaction.triggered.connect(self.suspendLoop)
        self.addAction(self.runaction)

        self.runaction = OWAction("Restart", self)
        self.runaction.triggered.connect(self.restartLoop)
        self.addAction(self.runaction)

        self.setFixedWidth(1200)
        self.setFixedHeight(710)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=True, orientation="horizontal")

        self.start_button = gui.button(button_box, self, "Start", callback=self.startLoop)
        self.start_button.setFixedHeight(35)

        stop_button = gui.button(button_box, self, "Stop", callback=self.stopLoop)
        stop_button.setFixedHeight(35)
        font = QFont(stop_button.font())
        font.setBold(True)
        stop_button.setFont(font)
        palette = QPalette(stop_button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('red'))
        stop_button.setPalette(palette) # assign new palette

        self.stop_button = stop_button

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=True, orientation="horizontal")

        suspend_button = gui.button(button_box, self, "Suspend", callback=self.suspendLoop)
        suspend_button.setFixedHeight(35)
        font = QFont(suspend_button.font())
        font.setBold(True)
        suspend_button.setFont(font)
        palette = QPalette(suspend_button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('orange'))
        suspend_button.setPalette(palette) # assign new palette

        self.re_start_button = gui.button(button_box, self, "Restart", callback=self.restartLoop)
        self.re_start_button.setFixedHeight(35)
        self.re_start_button.setEnabled(False)

        tabs = oasysgui.tabWidget(self.controlArea)
        tab_loop = oasysgui.createTabPage(tabs, "Loop Management")
        tab_und = oasysgui.createTabPage(tabs, "Undulator")

        left_box_2 = oasysgui.widgetBox(tab_und, "Parameters From Syned", addSpace=False, orientation="vertical", width=385, height=560)

        oasysgui.lineEdit(left_box_2, self, "electron_energy", "Ring Energy [GeV]", labelWidth=260, valueType=float, orientation="horizontal").setReadOnly(True)
        oasysgui.lineEdit(left_box_2, self, "number_of_periods", "Number of Periods", labelWidth=260,  valueType=float, orientation="horizontal").setReadOnly(True)
        oasysgui.lineEdit(left_box_2, self, "period_length", "Undulator Period [m]", labelWidth=260,  valueType=float, orientation="horizontal").setReadOnly(True)
        oasysgui.lineEdit(left_box_2, self, "K_vertical", "K Vertical", labelWidth=260,  valueType=float, orientation="horizontal").setReadOnly(True)
        oasysgui.lineEdit(left_box_2, self, "K_horizontal", "K Horizontal", labelWidth=260,  valueType=float, orientation="horizontal").setReadOnly(True)

        left_box_1 = oasysgui.widgetBox(tab_loop, "", addSpace=False, orientation="vertical", width=385, height=560)

        oasysgui.lineEdit(left_box_1, self, "seed_increment", "Source Montecarlo Seed Increment", labelWidth=250, valueType=int, orientation="horizontal")

        gui.separator(left_box_1)

        gui.comboBox(left_box_1, self, "autobinning", label="Energy Binning",
                     items=["Manual", "Automatic (Constant Power)", "Automatic (Constant Energy)"], labelWidth=150,
                     callback=self.set_Autobinning, sendSelectedValue=False, orientation="horizontal")

        self.autobinning_box_1 = oasysgui.widgetBox(left_box_1, "", addSpace=False, orientation="vertical", height=50)
        self.autobinning_box_2 = oasysgui.widgetBox(left_box_1, "", addSpace=False, orientation="vertical", height=140)

        # ----------------------------------------------

        gui.button(self.autobinning_box_1, self, "Compute Bins", callback=self.calculate_energy_binnings)

        oasysgui.widgetLabel(self.autobinning_box_1, "Energy From, Energy To, Energy Step [eV]")

        # ----------------------------------------------

        oasysgui.lineEdit(self.autobinning_box_2, self, "auto_n_step", "Number of Steps", labelWidth=250, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(self.autobinning_box_2, self, "auto_perc_total_power", "% Total Power", labelWidth=250, valueType=float, orientation="horizontal")
        gui.comboBox(self.autobinning_box_2, self, "send_power_step", label="Send Power Step", items=["No", "Yes"], labelWidth=350, sendSelectedValue=False, orientation="horizontal")

        button_box = oasysgui.widgetBox(self.autobinning_box_2, "", addSpace=False, orientation="horizontal")

        gui.button(button_box, self, "Reload Spectrum and Filters", callback=self.read_spectrum_and_filters_file)
        gui.button(button_box, self, "Reload Spectrum Only", callback=self.read_spectrum_file_only)

        oasysgui.widgetLabel(self.autobinning_box_2, "Energy Value [eV], Energy Step [eV], Power Step [W]")

        def write_text():
            self.energies = self.text_area.toPlainText()

        self.text_area = oasysgui.textArea(height=95, width=385, readOnly=False)
        self.text_area.setText(self.energies)
        self.text_area.setStyleSheet("background-color: white; font-family: Courier, monospace;")
        self.text_area.textChanged.connect(write_text)

        left_box_1.layout().addWidget(self.text_area)

        gui.separator(left_box_1)

        self.le_number_of_new_objects = oasysgui.lineEdit(left_box_1, self, "total_new_objects", "Total Energy Values", labelWidth=250, valueType=int, orientation="horizontal")
        self.le_number_of_new_objects.setReadOnly(True)
        font = QFont(self.le_number_of_new_objects.font())
        font.setBold(True)
        self.le_number_of_new_objects.setFont(font)
        palette = QPalette(self.le_number_of_new_objects.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_number_of_new_objects.setPalette(palette)

        self.le_number_of_new_objects = oasysgui.lineEdit(left_box_1, self, "number_of_new_objects", "Current Binning Energy Values", labelWidth=250, valueType=int, orientation="horizontal")
        self.le_number_of_new_objects.setReadOnly(True)
        font = QFont(self.le_number_of_new_objects.font())
        font.setBold(True)
        self.le_number_of_new_objects.setFont(font)
        palette = QPalette(self.le_number_of_new_objects.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_number_of_new_objects.setPalette(palette)

        gui.separator(left_box_1)

        le_current_value = oasysgui.lineEdit(left_box_1, self, "total_current_new_object", "Total New " + self.get_object_name(), labelWidth=250, valueType=int, orientation="horizontal")
        le_current_value.setReadOnly(True)
        font = QFont(le_current_value.font())
        font.setBold(True)
        le_current_value.setFont(font)
        palette = QPalette(le_current_value.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        le_current_value.setPalette(palette)

        le_current_value = oasysgui.lineEdit(left_box_1, self, "current_new_object", "Current Binning New " + self.get_object_name(), labelWidth=250, valueType=int, orientation="horizontal")
        le_current_value.setReadOnly(True)
        font = QFont(le_current_value.font())
        font.setBold(True)
        le_current_value.setFont(font)
        palette = QPalette(le_current_value.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        le_current_value.setPalette(palette)

        le_current_value = oasysgui.lineEdit(left_box_1, self, "current_energy_value", "Current Energy Value", labelWidth=250, valueType=float, orientation="horizontal")
        le_current_value.setReadOnly(True)
        font = QFont(le_current_value.font())
        font.setBold(True)
        le_current_value.setFont(font)
        palette = QPalette(le_current_value.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        le_current_value.setPalette(palette)

        gui.rubber(self.controlArea)

        tabs = oasysgui.tabWidget(self.mainArea)
        tabs.setFixedHeight(self.height()-15)
        tabs.setFixedWidth(775)

        tab_plot = oasysgui.createTabPage(tabs, "Cumulated Power")
        tab_flux = oasysgui.createTabPage(tabs, "Spectral Flux")
        tab_fil = oasysgui.createTabPage(tabs, "Filter")

        self.cumulated_power_plot = oasysgui.plotWindow(tab_plot, position=True)
        self.cumulated_power_plot.setFixedHeight(self.height()-20)
        self.cumulated_power_plot.setFixedWidth(775)
        self.cumulated_power_plot.setGraphXLabel("Energy [eV]")
        self.cumulated_power_plot.setGraphYLabel("Cumulated Power [W]")
        self.cumulated_power_plot.setGraphTitle("Cumulated Power")

        self.spectral_flux_plot = oasysgui.plotWindow(tab_flux, position=True)
        self.spectral_flux_plot.setFixedHeight(self.height()-20)
        self.spectral_flux_plot.setFixedWidth(775)
        self.spectral_flux_plot.setGraphXLabel("Energy [eV]")
        self.spectral_flux_plot.setGraphYLabel("Flux [ph/s/.1%bw]")
        self.spectral_flux_plot.setGraphTitle("Spectral Flux")

        self.filter_plot = oasysgui.plotWindow(tab_fil, position=True)
        self.filter_plot.setFixedHeight(self.height()-20)
        self.filter_plot.setFixedWidth(775)
        self.filter_plot.setGraphXLabel("Energy [eV]")
        self.filter_plot.setGraphYLabel("Intensity Factor")
        self.filter_plot.setGraphTitle("Filter on Flux")

        self.set_Autobinning()

    def set_Autobinning(self):
        self.autobinning_box_1.setVisible(self.autobinning==0)
        self.autobinning_box_2.setVisible(self.autobinning==1 or self.autobinning==2)
        self.text_area.setReadOnly(self.autobinning>=1)
        self.text_area.setFixedHeight(201 if self.autobinning>=1 else 290)

    def read_spectrum_file(self, reset_filters=True):
        try:
            if reset_filters:
                self.filters=None
                self.filter_plot.clear()

            data = numpy.loadtxt("autobinning.dat", skiprows=1)

            calculated_data = DataExchangeObject(program_name="ShadowOui", widget_name="PowerLoopPoint")
            calculated_data.add_content("spectrum_data", data)

            self.acceptEnergySpectrum(calculated_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

            if self.IS_DEVELOP: raise e

    def read_spectrum_file_only(self):
        self.read_spectrum_file(True)

    def read_spectrum_and_filters_file(self):
        try:
            data = numpy.loadtxt("filters.dat", skiprows=1)

            calculated_data = DataExchangeObject(program_name="ShadowOui", widget_name="PowerLoopPoint")
            calculated_data.add_content("filters_data", data)

            self.acceptFilters(calculated_data)
        except Exception:
            self.filters = None

        self.read_spectrum_file(False)

    def receive_syned_data(self, data):
        if not data is None:
            try:
                if not data._light_source is None and isinstance(data._light_source, LightSource):
                    light_source = data._light_source

                    self.electron_energy = light_source._electron_beam._energy_in_GeV

                    self.K_horizontal = light_source._magnetic_structure._K_horizontal
                    self.K_vertical = light_source._magnetic_structure._K_vertical
                    self.period_length = light_source._magnetic_structure._period_length
                    self.number_of_periods = light_source._magnetic_structure._number_of_periods
                else:
                    raise ValueError("Syned data not correct")
            except Exception as exception:
                QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

                if self.IS_DEVELOP: raise exception

    def receive_specific_syned_data(self, data):
        raise NotImplementedError()

    def acceptFilters(self, exchange_data):
        if not exchange_data is None:
            try: # FROM XOPPY F1F2
                write_file = True

                try:
                    data = exchange_data.get_content("filters_data")
                    write_file = False
                except:
                    if not exchange_data.get_program_name() == "XOPPY": raise ValueError("Only XOPPY F1F2 and CRYSTAL widgets are accepted")

                    if exchange_data.get_widget_name() == "XF1F2":
                        data = exchange_data.get_content("xoppy_data")
                    elif exchange_data.get_widget_name() == "XCRYSTAL":
                        data = exchange_data.get_content("xoppy_data")
                        cols = data.shape[1]
                        data = exchange_data.get_content("xoppy_data")[0:cols:cols-1, 0:cols:cols-1]
                    elif exchange_data.get_widget_name() == "MLAYER":
                        data = exchange_data.get_content("xoppy_data")[0:3:2, 0:3:2]

                self.filters = data

                energies     = self.filters[:, 0]
                intensity_factors = self.filters[:, 1]

                if write_file:
                    file = open("filters.dat", "w")
                    file.write("Energy Filter")


                    for energy, intensity_factor in zip(energies, intensity_factors):
                        file.write("\n" + str(energy) + " " + str(intensity_factor))

                    file.flush()
                    file.close()

                self.filter_plot.clear()
                self.filter_plot.addCurve(energies, intensity_factors, replace=True, legend="Intensity Factor")
                self.filter_plot.setGraphXLabel("Energy [eV]")
                self.filter_plot.setGraphYLabel("Intensity Factor")
                self.filter_plot.setGraphTitle("Filter on Flux")

                if self.autobinning==0:
                    if write_file: QMessageBox.information(self, "Info", "File filters.dat written on working directory, switch to Automatic binning to load it", QMessageBox.Ok)
                else:
                    if write_file: QMessageBox.information(self, "Info", "File filters.dat written on working directory", QMessageBox.Ok)

                if not self.spectrum_data is None:
                    calculated_data = DataExchangeObject(program_name="ShadowOui", widget_name="PowerLoopPoint")
                    calculated_data.add_content("spectrum_data", self.spectrum_data)

                    self.acceptEnergySpectrum(calculated_data)

            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e

    def acceptEnergySpectrum(self, exchange_data):
        if not exchange_data is None:
            try:
                write_file = True

                try:
                    data = exchange_data.get_content("spectrum_data")
                    write_file = False
                except:
                    try:
                        data = exchange_data.get_content("srw_data")
                    except:
                        data = exchange_data.get_content("xoppy_data")

                self.spectrum_data = data.copy()

                energies                              = data[:, 0]
                flux_through_finite_aperture          = data[:, 1]
                flux_through_finite_aperture_filtered = flux_through_finite_aperture.copy()

                if not self.filters is None:
                    flux_through_finite_aperture_filtered *= numpy.interp(energies, self.filters[:, 0], self.filters[:, 1])

                if write_file:
                    file = open("autobinning.dat", "w")
                    file.write("Energy Flux")

                    for energy, flux in zip(energies, flux_through_finite_aperture):
                        file.write("\n" + str(energy) + " " + str(flux))

                    file.flush()
                    file.close()

                if self.autobinning==0:
                    if write_file: QMessageBox.information(self, "Info", "File autobinning.dat written on working directory, switch to Automatic binning to load it", QMessageBox.Ok)
                else:
                    if write_file: QMessageBox.information(self, "Info", "File autobinning.dat written on working directory", QMessageBox.Ok)

                    congruence.checkStrictlyPositiveNumber(self.auto_n_step, "(Auto) % Number of Steps")
                    congruence.checkStrictlyPositiveNumber(self.auto_perc_total_power, "(Auto) % Total Power")

                    energy_step = energies[1] - energies[0]

                    # last energy do not contribute to the total (the approximated integral of the power is out of the range)

                    power           = flux_through_finite_aperture * (1e3 * energy_step * codata.e)
                    cumulated_power = numpy.cumsum(power)
                    total_power     = cumulated_power[-1]

                    if not self.filters is None:
                        power_filtered           = flux_through_finite_aperture_filtered * (1e3 * energy_step * codata.e)
                        cumulated_power_filtered = numpy.cumsum(power_filtered)
                        total_power_filtered     = cumulated_power_filtered[-1]

                    self.text_area.clear()

                    self.cumulated_power_plot.clear()
                    self.spectral_flux_plot.clear()

                    good = numpy.where(cumulated_power <= self.auto_perc_total_power*0.01*total_power)

                    energies                     = energies[good]
                    cumulated_power              = cumulated_power[good]
                    flux_through_finite_aperture = flux_through_finite_aperture[good]

                    if not self.filters is None:
                        cumulated_power_filtered = cumulated_power_filtered[good]
                        flux_through_finite_aperture_filtered = flux_through_finite_aperture_filtered[good]

                    if self.autobinning==1: # constant power
                        interpolated_cumulated_power = numpy.linspace(start=numpy.min(cumulated_power), stop=numpy.max(cumulated_power), num=self.auto_n_step+1)
                        interpolated_energies        = numpy.interp(interpolated_cumulated_power, cumulated_power, energies)
                        energy_steps = numpy.ediff1d(interpolated_energies)

                        interpolated_energies        = interpolated_energies[:-1]
                        interpolated_cumulated_power = interpolated_cumulated_power[:-1]

                        power_steps  = numpy.ones(self.auto_n_step)*cumulated_power[-1]/self.auto_n_step

                    elif self.autobinning==2: # constant energy
                        minimum_energy = energies[0]
                        maximum_energy = energies[-1]
                        energy_step = (maximum_energy-minimum_energy)/self.auto_n_step

                        interpolated_energies        = numpy.arange(minimum_energy, maximum_energy, energy_step)
                        interpolated_cumulated_power = numpy.interp(interpolated_energies, energies, cumulated_power)

                        energy_steps = numpy.ones(self.auto_n_step)*energy_step
                        power_steps  = numpy.ediff1d(numpy.append(numpy.zeros(1), interpolated_cumulated_power))

                    flux_steps = numpy.interp(interpolated_energies, energies, flux_through_finite_aperture)

                    self.energy_binnings = []
                    self.total_new_objects = 0

                    self.cumulated_power_plot.addCurve(energies, cumulated_power, replace=True, legend="Cumulated Power")
                    if not self.filters is None:  self.cumulated_power_plot.addCurve(energies, cumulated_power_filtered, replace=False, legend="Cumulated Power Filters",
                                                                                     linestyle="--", color="#006400")
                    self.cumulated_power_plot.setGraphXLabel("Energy [eV]")
                    self.cumulated_power_plot.setGraphYLabel("Cumulated " + ("" if self.filters is None else " (Filtered)") + " Power" )
                    if self.filters is None: self.cumulated_power_plot.setGraphTitle("Total Power: " + str(round(power_steps.sum(), 2)) + " W")
                    else:self.cumulated_power_plot.setGraphTitle("Total (Filtered) Power: " + str(round(power_steps.sum(), 2)) + "  (" + str(round(total_power_filtered, 2)) +  ") W")

                    self.spectral_flux_plot.addCurve(energies, flux_through_finite_aperture, replace=True, legend="Spectral Flux")
                    if not self.filters is None: self.spectral_flux_plot.addCurve(energies, flux_through_finite_aperture_filtered, replace=False, legend="Spectral Flux Filters",
                                                                                  linestyle="--", color="#006400")
                    self.spectral_flux_plot.setGraphXLabel("Energy [eV]")
                    self.spectral_flux_plot.setGraphYLabel("Flux [ph/s/.1%bw]")
                    self.spectral_flux_plot.setGraphTitle("Spectral Flux" + ("" if self.filters is None else " (Filtered)"))


                    self.cumulated_power_plot.addCurve(interpolated_energies, interpolated_cumulated_power, replace=False, legend="Energy Binning",
                                                       color="red", linestyle=" ", symbol="+")

                    self.spectral_flux_plot.addCurve(interpolated_energies, flux_steps, replace=False, legend="Energy Binning",
                                                       color="red", linestyle=" ", symbol="+")

                    text = ""

                    for energy_value, energy_step, power_step in zip(interpolated_energies, energy_steps, power_steps):
                        energy_binning = EnergyBinning(energy_value=round(energy_value, 3),
                                                       energy_step=round(energy_step, 3),
                                                       power_step=round(power_step, 4))

                        text += str(round(energy_value, 3)) + ", " + \
                                str(round(energy_step, 3))  + ", " + \
                                str(round(power_step, 4)) + "\n"

                        self.energy_binnings.append(energy_binning)
                        self.total_new_objects += 1

                    self.text_area.setText(text)

                    self.external_binning = True
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e
        else:
            self.energy_binnings = None
            self.total_new_objects = 0
            self.external_binning = False
            self.text_area.setText("")

    def calculate_energy_binnings(self):
        if not self.external_binning:
            self.total_new_objects = 0

            rows = self.energies.split("\n")
            for row in rows:
                data = row.split(",")
                if len(data) == 3:
                    if self.energy_binnings is None: self.energy_binnings = []

                    energy_from = float(data[0].strip())
                    energy_to   = float(data[1].strip())
                    energy_step = float(data[2].strip())

                    energy_binning = EnergyBinning(energy_value=energy_from,
                                                   energy_value_to=energy_to,
                                                   energy_step=energy_step)
                    self.energy_binnings.append(energy_binning)

                    self.total_new_objects += int((energy_to - energy_from) / energy_step)

    def calculate_number_of_new_objects(self):
        if len(self.energy_binnings) > 0:
            if self.external_binning:
                self.number_of_new_objects = 1
            else:
                energy_binning = self.energy_binnings[self.current_energy_binning]

                self.number_of_new_objects = int((energy_binning.energy_value_to - energy_binning.energy_value) / energy_binning.energy_step)
        else:
            self.number_of_new_objects = 0

    def reset_values(self):
        self.current_new_object = 0
        self.total_current_new_object = 0
        self.current_energy_value = None
        self.current_energy_step = None
        self.current_energy_binning = -1
        self.current_power_step = None

        if not self.external_binning: self.energy_binnings = None

    def startLoop(self):
        try:
            self.calculate_energy_binnings()

            self.current_new_object = 1
            self.total_current_new_object = 1
            self.current_energy_binning = 0
            self.current_energy_value             = round(self.energy_binnings[0].energy_value, 8)
            self.current_energy_step              = round(self.energy_binnings[0].energy_step, 8)
            self.current_power_step               = None if self.energy_binnings[0].power_step is None else (None if self.send_power_step==0 else round(self.energy_binnings[0].power_step, 8))
            self.calculate_number_of_new_objects()

            self.start_button.setEnabled(False)
            self.text_area.setEnabled(False)
            self.setStatusMessage("Running " + self.get_object_name() + " " + str(self.total_current_new_object) + " of " + str(self.total_new_objects))
            self.send("Trigger", TriggerOut(new_object=True,
                                            additional_parameters={"energy_value"   : self.current_energy_value,
                                                                   "energy_step"    : self.current_energy_step,
                                                                   "power_step"     : -1 if self.current_power_step is None else self.current_power_step,
                                                                   "seed_increment" : self.seed_increment,
                                                                   "start_event"    : True}))
        except Exception as e:
            if self.IS_DEVELOP : raise e
            else: pass

    def stopLoop(self):
        try:
            if ConfirmDialog.confirmed(parent=self, message="Confirm Interruption of the Loop?"):
                self.run_loop = False
                self.reset_values()
                self.setStatusMessage("Interrupted by user")
        except Exception as e:
            if self.IS_DEVELOP : raise e
            else: pass

    def suspendLoop(self):
        try:
            if ConfirmDialog.confirmed(parent=self, message="Confirm Suspension of the Loop?"):
                self.run_loop = False
                self.suspend_loop = True
                self.stop_button.setEnabled(False)
                self.re_start_button.setEnabled(True)
                self.setStatusMessage("Suspended by user")
        except Exception as e:
            if self.IS_DEVELOP : raise e
            else: pass


    def restartLoop(self):
        try:
            self.run_loop = True
            self.suspend_loop = False
            self.stop_button.setEnabled(True)
            self.re_start_button.setEnabled(False)
            self.passTrigger(TriggerIn(new_object=True))
        except Exception as e:
            if self.IS_DEVELOP : raise e
            else: pass

    def get_object_name(self):
        return "Beam"

    def passTrigger(self, trigger):
        if self.run_loop:
            if trigger:
                if trigger.interrupt:
                    self.reset_values()
                    self.start_button.setEnabled(True)
                    self.text_area.setEnabled(True)
                    self.setStatusMessage("")
                    self.send("Trigger", TriggerOut(new_object=False))
                elif trigger.new_object:
                    if self.energy_binnings is None: self.calculate_energy_binnings()

                    if self.current_energy_binning == -1:
                        QMessageBox.critical(self, "Error", "Power Loop has to be started properly: press the button Start", QMessageBox.Ok)
                        return

                    if self.current_energy_binning < len(self.energy_binnings):
                        energy_binning = self.energy_binnings[self.current_energy_binning]

                        self.total_current_new_object += 1

                        if self.current_new_object < self.number_of_new_objects:
                            if self.current_energy_value is None:
                                self.current_new_object = 1
                                self.calculate_number_of_new_objects()
                                self.current_energy_value = round(energy_binning.energy_value, 8)
                            else:
                                self.current_new_object += 1
                                self.current_energy_value = round(self.current_energy_value + energy_binning.energy_step, 8)

                            self.current_power_step = None if energy_binning.power_step is None else (None if self.send_power_step==0 else round(energy_binning.power_step, 8))

                            self.setStatusMessage("Running " + self.get_object_name() + " " + str(self.total_current_new_object) + " of " + str(self.total_new_objects))
                            self.start_button.setEnabled(False)
                            self.text_area.setEnabled(False)
                            self.send("Trigger", TriggerOut(new_object=True,
                                                            additional_parameters={"energy_value"   : self.current_energy_value,
                                                                                   "energy_step"    : energy_binning.energy_step,
                                                                                   "power_step"     : -1 if self.current_power_step is None else self.current_power_step,
                                                                                   "seed_increment" : self.seed_increment,
                                                                                   "start_event"    : False}))
                        else:
                            self.current_energy_binning += 1

                            if self.current_energy_binning < len(self.energy_binnings):
                                energy_binning = self.energy_binnings[self.current_energy_binning]

                                self.current_new_object = 1
                                self.calculate_number_of_new_objects()
                                self.current_energy_value = round(energy_binning.energy_value, 8)
                                self.current_power_step = None if energy_binning.power_step is None else (None if self.send_power_step==0 else round(energy_binning.power_step, 8))

                                self.setStatusMessage("Running " + self.get_object_name() + " " + str(self.total_current_new_object) + " of " + str(self.total_new_objects))
                                self.start_button.setEnabled(False)
                                self.text_area.setEnabled(False)
                                self.send("Trigger", TriggerOut(new_object=True,
                                                                additional_parameters={"energy_value"   : self.current_energy_value,
                                                                                       "energy_step"    : energy_binning.energy_step,
                                                                                       "power_step"     : -1 if self.current_power_step is None else self.current_power_step,
                                                                                       "seed_increment" : self.seed_increment,
                                                                                       "start_event"    : False}))
                            else:
                                self.reset_values()
                                self.start_button.setEnabled(True)
                                self.text_area.setEnabled(True)
                                self.setStatusMessage("")
                                self.send("Trigger", TriggerOut(new_object=False))
                    else:
                        self.reset_values()
                        self.start_button.setEnabled(True)
                        self.text_area.setEnabled(True)
                        self.setStatusMessage("")
                        self.send("Trigger", TriggerOut(new_object=False))
        else:
            if not self.suspend_loop:
                self.reset_values()
                self.start_button.setEnabled(True)
                self.text_area.setEnabled(True)

            self.send("Trigger", TriggerOut(new_object=False))
            self.setStatusMessage("")
            self.suspend_loop = False
            self.run_loop = True

if __name__ == "__main__":
    a = QApplication(sys.argv)
    ow = PowerLoopPoint()
    ow.show()
    a.exec_()
    ow.saveSettings()


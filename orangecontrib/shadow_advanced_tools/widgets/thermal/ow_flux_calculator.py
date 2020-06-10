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

from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QLabel, QSizePolicy
from PyQt5.QtGui import QPixmap

import orangecanvas.resources as resources

from orangewidget import gui
from orangewidget.widget import OWAction

from oasys.widgets.exchange import DataExchangeObject
from oasys.widgets import gui as oasysgui

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowCongruence
from orangecontrib.shadow.widgets.gui.ow_automatic_element import AutomaticElement

class FluxCalculator(AutomaticElement):

    name = "Flux Calculator"
    description = "Tools: Flux Calculator"
    icon = "icons/flux.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 10
    category = "User Defined"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Shadow Beam", ShadowBeam, "setBeam"),
              ("Spectrum Data", DataExchangeObject, "setSpectrumData")]

    outputs = [{"name":"Beam",
                "type":ShadowBeam,
                "doc":"Shadow Beam",
                "id":"beam"}]

    want_main_area = 0
    want_control_area = 1

    input_beam     = None
    input_spectrum = None
    flux_index = -1

    usage_path = os.path.join(resources.package_dirname("orangecontrib.shadow_advanced_tools.widgets.thermal"), "misc", "flux_calculator.png")

    def __init__(self):
        super(FluxCalculator, self).__init__()

        self.runaction = OWAction("Calculate Flux", self)
        self.runaction.triggered.connect(self.calculate_flux)
        self.addAction(self.runaction)

        self.setMaximumWidth(self.CONTROL_AREA_WIDTH+10)
        self.setMaximumHeight(580)

        box0 = gui.widgetBox(self.controlArea, "", orientation="horizontal")
        gui.button(box0, self, "Calculate Flux", callback=self.calculate_flux, height=45)

        tabs_setting = oasysgui.tabWidget(self.controlArea)
        tabs_setting.setFixedHeight(440)
        tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-8)

        tab_out = oasysgui.createTabPage(tabs_setting, "Flux Calculation Results")
        tab_usa = oasysgui.createTabPage(tabs_setting, "Use of the Widget")
        tab_usa.setStyleSheet("background-color: white;")

        self.text = oasysgui.textArea(width=self.CONTROL_AREA_WIDTH-22, height=400)

        tab_out.layout().addWidget(self.text)

        usage_box = oasysgui.widgetBox(tab_usa, "", addSpace=True, orientation="horizontal")

        label = QLabel("")
        label.setAlignment(Qt.AlignCenter)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label.setPixmap(QPixmap(self.usage_path))

        usage_box.layout().addWidget(label)

        gui.rubber(self.controlArea)

    def setBeam(self, beam):
        try:
            if ShadowCongruence.checkEmptyBeam(beam):
                if ShadowCongruence.checkGoodBeam(beam):
                    self.input_beam = beam

                    if self.is_automatic_run: self.calculate_flux()
        except Exception as exception:
            QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def setSpectrumData(self, data):
        if not data is None:
            try:
                if data.get_program_name() == "XOPPY":
                    if data.get_widget_name() == "UNDULATOR_FLUX" or data.get_widget_name() == "XWIGGLER" or data.get_widget_name() == "WS":
                        self.flux_index = 1
                    elif data.get_widget_name() == "BM":
                        self.flux_index = 5
                    else:
                        raise Exception("Connect to one of the following XOPPY widgets: Undulator Spectrum, BM, XWIGGLER, WS")

                    self.input_spectrum = data.get_content('xoppy_data')
                elif data.get_program_name() == "SRW":
                    if data.get_widget_name() == "UNDULATOR_SPECTRUM":
                        self.flux_index = 1
                    else:
                        raise Exception("Connect to one of the following SRW widgets: Undulator Spectrum")

                    self.input_spectrum = data.get_content('srw_data')
                else:
                    raise ValueError("Widget accept data from the following Add-ons: XOPPY, SRW")

                if self.is_automatic_run: self.calculate_flux()
            except Exception as exception:
                QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

                if self.IS_DEVELOP: raise exception

    def calculate_flux(self):
        if not self.input_beam is None and not self.input_spectrum is None:
            try:
                flux_factor, resolving_power, energy, ttext = calculate_flux_factor_and_resolving_power(self.input_beam)

                total_text = ttext

                flux_at_sample, ttext = calculate_flux_at_sample(self.input_spectrum, self.flux_index, flux_factor, energy)

                ticket = self.input_beam._beam.histo2(1, 3, nbins=100, nolost=1, ref=23)

                dx = ticket['fwhm_v'] * self.workspace_units_to_m*1000
                dy = ticket['fwhm_h'] * self.workspace_units_to_m*1000

                total_text += "\n" + ttext

                total_text += "\n\n ---> Integrated Flux : %g"%flux_at_sample + " ph/s"
                total_text += "\n ---> <Flux Density>  : %g"%(flux_at_sample/(dx*dy)) + " ph/s/mm^2"
                total_text += "\n ---> Resolving Power : %g"%resolving_power

                self.text.clear()
                self.text.setText(total_text)

                self.send("Beam", self.input_beam)
            except Exception as exception:
                QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

                if self.IS_DEVELOP: raise exception

def calculate_flux_factor_and_resolving_power(beam):
    ticket = beam._beam.histo1(11, nbins=2, nolost=1)

    energy_min = ticket['xrange'][0]
    energy_max = ticket['xrange'][-1]

    Denergy_source = numpy.abs(energy_max - energy_min)
    energy = numpy.average([energy_min, energy_max])

    if Denergy_source == 0.0:
        raise ValueError("This calculation is not possibile for a single energy value")

    ticket = beam._beam.histo1(11, nbins=200, nolost=1, ref=23)

    initial_intensity = len(beam._beam.rays)
    final_intensity = ticket['intensity']
    efficiency = final_intensity/initial_intensity
    bandwidth = ticket['fwhm']

    if bandwidth == 0.0:
        raise ValueError("Bandwidth is 0.0: calculation not possible")

    resolving_power = energy/bandwidth

    if Denergy_source < 4*bandwidth:
        raise ValueError("Source \u0394E (" + str(round(Denergy_source, 2)) + " eV) should be at least 4 times bigger than the bandwidth (" + str(round(bandwidth, 3)) + " eV)")

    text = "\n# SOURCE ---------\n"
    text += "\n Source Central Energy: %g"%round(energy, 2) + " eV"
    text += "\n Source Energy Range  : %g - %g"%(round(energy_min, 2), round(energy_max, 2)) + " eV"
    text += "\n Source \u0394E: %g"%round(Denergy_source, 2) + " eV"

    text += "\n\n# BEAMLINE ---------\n"
    text += "\n Shadow Intensity (Initial): %g"%initial_intensity
    text += "\n Shadow Intensity (Final)  : %g"%final_intensity
    text += "\n"
    text += "\n Efficiency: %g"%round(100*efficiency, 3) + "%"
    text += "\n Bandwidth (at the Image Plane): %g"%round(bandwidth, 3) + " eV"

    beamline_bandwidth = Denergy_source * efficiency

    flux_factor = beamline_bandwidth / (1e-3*energy)

    return flux_factor, resolving_power, energy, text

def calculate_flux_at_sample(spectrum, flux_index, flux_factor, energy):
    if energy < spectrum[0, 0] or energy > spectrum[-1, 0]: raise ValueError("Spectrum does not contained central energy")
    interpolated_flux = numpy.interp([energy],
                                     spectrum[:, 0],
                                     spectrum[:, flux_index],
                                     left=spectrum[:, flux_index][0],
                                     right=spectrum[:, flux_index][-1])[0]

    text = "\n# FLUX INTERPOLATION ---------\n"
    text += "\n Initial Flux from Source: %g"%interpolated_flux + " ph/s/0.1%bw"

    return interpolated_flux*flux_factor, text


if __name__ == "__main__":
    a = QtGui.QApplication(sys.argv)
    ow = FluxCalculator()
    ow.show()
    a.exec_()
    ow.saveSettings()



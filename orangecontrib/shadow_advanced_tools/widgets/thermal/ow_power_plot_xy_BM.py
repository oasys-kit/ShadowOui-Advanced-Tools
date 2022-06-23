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


import scipy.constants as codata

from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.widgets.exchange import DataExchangeObject

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowCongruence
from orangecontrib.shadow_advanced_tools.util.gui import PowerPlotXYWidget

from orangecontrib.shadow_advanced_tools.widgets.thermal.gui.power_plot_xy import AbstractPowerPlotXY

class PowerPlotXYBM(AbstractPowerPlotXY):

    name = "Power Plot XY - BM"
    description = "Display Data Tools: Power Plot XY - BM"
    icon = "icons/bm_plot_xy_power.png"
    priority = 5.101

    inputs = [("Input Beam", ShadowBeam, "setBeam"),
              ("Input Spectrum", DataExchangeObject, "setFlux")]


    nbins_interpolation = Setting(500)

    initial_flux = None
    initial_energy = None

    def __init__(self):
        super().__init__()

    def _set_additional_boxes(self, tab_gen):
        interpolation_box = oasysgui.widgetBox(tab_gen, "Interpolation", addSpace=True, orientation="vertical", height=65)

        oasysgui.lineEdit(interpolation_box, self, "nbins_interpolation", "Number of Bins for energy interpolation", labelWidth=250, valueType=int, orientation="horizontal")

    def replace_fig(self, shadow_beam, var_x, var_y, xrange, yrange, nbins_h, nbins_v, nolost):
        if self.plot_canvas is None:
            self.plot_canvas = PowerPlotXYWidget()
            self.image_box.layout().addWidget(self.plot_canvas)
        else:
            self.plot_canvas.clear()

        try:
            ticket = self.plot_canvas.plot_power_density_BM(shadow_beam, self.initial_energy, self.initial_flux, self.nbins_interpolation,
                                                            var_x, var_y, nbins_h, nbins_v, xrange, yrange, nolost,
                                                            show_image=self.view_type==1, to_mm=self.workspace_units_to_mm)

            self.plotted_ticket = ticket
            self.plotted_ticket_original = self.plotted_ticket.copy()

        except Exception as e:
            if not self.IS_DEVELOP:
                raise Exception("Data not plottable: " + str(e))
            else:
                raise e

    def _check_other_fields(self):
        self.nbins_interpolation = congruence.checkStrictlyPositiveNumber(self.nbins_interpolation, "Number of Bins for energy interpolation")

    #########################################################
    # I/O

    def _analyze_input_beam(self, input_beam):
        self.input_beam = input_beam.duplicate()

        if self.input_beam.scanned_variable_data and self.input_beam.scanned_variable_data.has_additional_parameter("is_footprint"):
            if self.input_beam.scanned_variable_data.get_additional_parameter("is_footprint"):
                self.cb_rays.setEnabled(False)
                self.rays = 0  # transmitted, absorbed doesn't make sense since is precalculated by footprint object
            else:
                self.cb_rays.setEnabled(True)

        return True

    def _can_be_plotted(self, input_beam):
        if super(PowerPlotXYBM, self)._can_be_plotted(input_beam): return not self.initial_flux is None
        else: return False

    def setFlux(self, exchange_data):
        if not exchange_data is None:
            if exchange_data.get_program_name() == "XOPPY" and exchange_data.get_widget_name() == "BM":
                    if exchange_data.get_content("is_log_plot") == 1:
                        raise Exception("Logarithmic X scale of Xoppy Energy distribution not supported")
                    elif exchange_data.get_content("calculation_type") == 0 and (exchange_data.get_content("psi") == 0 or exchange_data.get_content("psi") == 2):
                        index_flux = 5
                    else:
                        raise Exception("Xoppy result is not an Flux vs Energy distribution integrated in a rectangular space")
            else:
                raise Exception("Exchange data are not from a XOPPY BM widget")

            spectrum = exchange_data.get_content("xoppy_data")
            self.initial_flux = spectrum[:, index_flux]
            self.initial_energy = spectrum[:, 0]

            initial_energy_step = self.initial_energy[1] - self.initial_energy[0]

            self.total_initial_power = self.initial_flux.sum() * 1e3 * codata.e * initial_energy_step

            print("Total Initial Power from XOPPY", self.total_initial_power)

            if not self.input_beam is None:
                if ShadowCongruence.checkEmptyBeam(self.input_beam):
                    if ShadowCongruence.checkGoodBeam(self.input_beam):
                        self.plot_results()

        else:
            self.initial_flux = None
            self.initial_energy = None

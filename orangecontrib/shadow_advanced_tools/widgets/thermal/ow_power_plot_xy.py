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

import sys
import time

from PyQt5.QtWidgets import QMessageBox

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.widgets.gui import ConfirmDialog

from oasys.util.oasys_util import EmittingStream

from orangecontrib.shadow.util.shadow_util import ShadowCongruence, ShadowPlot
from orangecontrib.shadow_advanced_tools.util.gui import PowerPlotXYWidget

import scipy.constants as codata

from orangecontrib.shadow_advanced_tools.widgets.thermal.gui.power_plot_xy import AbstractPowerPlotXY

class PowerPlotXY(AbstractPowerPlotXY):
    name = "Power Plot XY - Undulator"
    description = "Display Data Tools: Power Plot XY - Undulator"
    icon = "icons/plot_xy_power.png"
    priority = 5.1

    keep_result=Setting(1)
    autosave_partial_results = Setting(0)

    autosave = Setting(0)
    autosave_file_name = Setting("autosave_power_density.hdf5")

    autosave_file = None

    def __init__(self):
        super().__init__()

    def _set_additional_boxes(self, tab_gen):
        autosave_box = oasysgui.widgetBox(tab_gen, "Autosave", addSpace=True, orientation="vertical", height=85)

        gui.comboBox(autosave_box, self, "autosave", label="Save automatically plot into file", labelWidth=250,
                                         items=["No", "Yes"],
                                         sendSelectedValue=False, orientation="horizontal", callback=self.set_autosave)

        self.autosave_box_1 = oasysgui.widgetBox(autosave_box, "", addSpace=False, orientation="horizontal", height=25)
        self.autosave_box_2 = oasysgui.widgetBox(autosave_box, "", addSpace=False, orientation="horizontal", height=25)

        self.le_autosave_file_name = oasysgui.lineEdit(self.autosave_box_1, self, "autosave_file_name", "File Name", labelWidth=100,  valueType=str, orientation="horizontal")

        gui.button(self.autosave_box_1, self, "...", callback=self.select_autosave_file)

        incremental_box = oasysgui.widgetBox(tab_gen, "Incremental Result", addSpace=True, orientation="vertical", height=120)

        gui.comboBox(incremental_box, self, "keep_result", label="Keep Result", labelWidth=250,
                     items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal", callback=self.set_autosave)

        self.cb_autosave_partial_results = gui.comboBox(incremental_box, self, "autosave_partial_results", label="Save partial plots into file", labelWidth=250,
                                                        items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal")

        gui.button(incremental_box, self, "Clear", callback=self.clear_results)

        self.set_autosave()

    def clear_results(self, interactive=True):
        if not interactive: proceed = True
        else: proceed = ConfirmDialog.confirmed(parent=self)

        if proceed:
            self.input_beam = None
            self.cumulated_ticket = None
            self.plotted_ticket = None
            self.energy_min = None
            self.energy_max = None
            self.energy_step = None
            self.total_power = None
            self.cumulated_total_power = None

            if not self.autosave_file is None:
                self.autosave_file.close()
                self.autosave_file = None

            if not self.plot_canvas is None:
                self.plot_canvas.clear()

    def set_autosave(self):
        self.autosave_box_1.setVisible(self.autosave==1)
        self.autosave_box_2.setVisible(self.autosave==0)

        self.cb_autosave_partial_results.setEnabled(self.autosave==1 and self.keep_result==1)

    def select_autosave_file(self):
        file_name = oasysgui.selectSaveFileFromDialog(self, "Select File", default_file_name="", file_extension_filter="HDF5 Files (*.hdf5 *.h5 *.hdf)")
        self.le_autosave_file_name.setText("" if file_name is None else file_name)

    #########################################################
    # I/O

    def _analyze_input_beam(self, input_beam):
        if not input_beam.scanned_variable_data is None and input_beam.scanned_variable_data.has_additional_parameter("total_power"):
            self.input_beam = input_beam.duplicate()

            self.current_step = self.input_beam.scanned_variable_data.get_additional_parameter("current_step")
            self.total_steps = self.input_beam.scanned_variable_data.get_additional_parameter("total_steps")
            self.energy_step = self.input_beam.scanned_variable_data.get_additional_parameter("photon_energy_step")

            self.total_power = self.input_beam.scanned_variable_data.get_additional_parameter("total_power")

            if self.cumulated_quantity == 1:  # Intensity
                self.total_power /= (1e3 * self.energy_step * codata.e)  # to ph/s

            self.energy_max = self.input_beam.scanned_variable_data.get_scanned_variable_value()

            if self.energy_min is None:
                self.energy_min = self.input_beam.scanned_variable_data.get_scanned_variable_value()
                self.cumulated_total_power = self.total_power
            else:
                self.cumulated_total_power += self.total_power

            if self.input_beam.scanned_variable_data.has_additional_parameter("is_footprint"):
                if self.input_beam.scanned_variable_data.get_additional_parameter("is_footprint"):
                    self.cb_rays.setEnabled(False)
                    self.rays = 0  # transmitted, absorbed doesn't make sense since is precalculated by footprint object
                else:
                    self.cb_rays.setEnabled(True)

            return True
        else:
            return False

    #########################################################
    # PLOTTING

    def replace_fig(self, shadow_beam, var_x, var_y, xrange, yrange, nbins_h, nbins_v, nolost):
        if self.plot_canvas is None:
            self.plot_canvas = PowerPlotXYWidget()
            self.image_box.layout().addWidget(self.plot_canvas)

        try:
            if self.autosave == 1:
                if self.autosave_file is None:
                    self.autosave_file = ShadowPlot.PlotXYHdf5File(congruence.checkDir(self.autosave_file_name))
                elif self.autosave_file.filename != congruence.checkFileName(self.autosave_file_name):
                    self.autosave_file.close()
                    self.autosave_file = ShadowPlot.PlotXYHdf5File(congruence.checkDir(self.autosave_file_name))

                self.autosave_file.add_attribute("current_step", self.current_step, dataset_name="additional_data")
                self.autosave_file.add_attribute("total_steps", self.total_steps, dataset_name="additional_data")
                self.autosave_file.add_attribute("last_energy_value", self.energy_max, dataset_name="additional_data")
                self.autosave_file.add_attribute("last_power_value", self.total_power, dataset_name="additional_data")

            if self.keep_result == 1:
                self.cumulated_ticket, last_ticket = self.plot_canvas.plot_power_density(shadow_beam, var_x, var_y,
                                                                                         self.total_power, self.cumulated_total_power,
                                                                                         self.energy_min, self.energy_max, self.energy_step,
                                                                                         nbins_h=nbins_h, nbins_v=nbins_v, xrange=xrange, yrange=yrange, nolost=nolost,
                                                                                         ticket_to_add=self.cumulated_ticket,
                                                                                         to_mm=self.workspace_units_to_mm,
                                                                                         show_image=self.view_type==1,
                                                                                         kind_of_calculation=self.kind_of_calculation,
                                                                                         replace_poor_statistic=self.replace_poor_statistic,
                                                                                         good_rays_limit=self.good_rays_limit,
                                                                                         center_x=self.center_x,
                                                                                         center_y=self.center_y,
                                                                                         sigma_x=self.sigma_x,
                                                                                         sigma_y=self.sigma_y,
                                                                                         gamma=self.gamma,
                                                                                         cumulated_quantity=self.cumulated_quantity)

                if self.autosave == 1:
                    self.autosave_file.add_attribute("last_plotted_power",  self.cumulated_ticket['plotted_power'],  dataset_name="additional_data")
                    self.autosave_file.add_attribute("last_incident_power", self.cumulated_ticket['incident_power'], dataset_name="additional_data")
                    self.autosave_file.add_attribute("last_total_power",    self.cumulated_ticket['total_power'],    dataset_name="additional_data")
                    self.autosave_file.add_attribute("last_energy_min",     self.cumulated_ticket['energy_min'],     dataset_name="additional_data")
                    self.autosave_file.add_attribute("last_energy_max",     self.cumulated_ticket['energy_max'],     dataset_name="additional_data")
                    self.autosave_file.add_attribute("last_energy_step",    self.cumulated_ticket['energy_step'],    dataset_name="additional_data")

                self.plotted_ticket          = self.cumulated_ticket
                self.plotted_ticket_original = self.plotted_ticket.copy()

                if self.autosave == 1:
                    self.autosave_file.write_coordinates(self.cumulated_ticket)
                    dataset_name = "power_density"

                    self.autosave_file.add_plot_xy(self.cumulated_ticket, dataset_name=dataset_name)

                    if self.autosave_partial_results == 1:
                        if last_ticket is None:
                            self.autosave_file.add_plot_xy(self.cumulated_ticket,
                                                           plot_name="Energy Range: " + str(round(self.energy_max-self.energy_step, 2)) + "-" + str(round(self.energy_max, 2)),
                                                           dataset_name=dataset_name)
                        else:
                            self.autosave_file.add_plot_xy(last_ticket,
                                                           plot_name="Energy Range: " + str(round(self.energy_max-self.energy_step, 2)) + "-" + str(round(self.energy_max, 2)),
                                                           dataset_name=dataset_name)

                    self.autosave_file.flush()
            else:
                ticket, _ = self.plot_canvas.plot_power_density(shadow_beam, var_x, var_y,
                                                                self.total_power, self.cumulated_total_power,
                                                                self.energy_min, self.energy_max, self.energy_step,
                                                                nbins_h=nbins_h, nbins_v=nbins_v, xrange=xrange, yrange=yrange, nolost=nolost,
                                                                to_mm=self.workspace_units_to_mm,
                                                                show_image=self.view_type==1,
                                                                kind_of_calculation=self.kind_of_calculation,
                                                                replace_poor_statistic=self.replace_poor_statistic,
                                                                good_rays_limit=self.good_rays_limit,
                                                                center_x=self.center_x,
                                                                center_y=self.center_y,
                                                                sigma_x=self.sigma_x,
                                                                sigma_y=self.sigma_y,
                                                                gamma=self.gamma,
                                                                cumulated_quantity=self.cumulated_quantity)

                self.cumulated_ticket = None
                self.plotted_ticket = ticket
                self.plotted_ticket_original = self.plotted_ticket.copy()

                if self.autosave == 1:
                    self.autosave_file.write_coordinates(ticket)
                    self.autosave_file.add_plot_xy(ticket, dataset_name="power_density")
                    self.autosave_file.flush()

        except Exception as e:
            if not self.IS_DEVELOP:
                raise Exception("Data not plottable: " + str(e))
            else:
                raise e

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

import os, numpy

from PyQt5 import QtGui, QtWidgets
from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui, congruence
from oasys.widgets import widget as oasyswidget

from orangecontrib.shadow.util.shadow_util import ShadowCongruence
from orangecontrib.shadow.util.shadow_objects import ShadowBeam, ShadowOpticalElement, ShadowOEHistoryItem


class FootprintFileReader(oasyswidget.OWWidget):
    name = "Footprint Reader"
    description = "Utility: Footprint Reader"
    icon = "icons/footprint_reader.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 5.2
    category = "Utility"
    keywords = ["data", "file", "load", "read"]

    want_main_area = 0

    beam_file_name = None
    input_beam = None

    inputs = [("Footprint", list, "setBeam")]

    outputs = [{"name": "Beam",
                "type": ShadowBeam,
                "doc": "Shadow Beam",
                "id": "beam"}, ]

    kind_of_power = Setting(0)

    def __init__(self):
        super().__init__()

        self.setFixedWidth(590)
        self.setFixedHeight(150)

        left_box_1 = oasysgui.widgetBox(self.controlArea, "Footprint Settings", addSpace=True, orientation="vertical",
                                         width=570, height=120)

        self.le_beam_file_name = oasysgui.lineEdit(left_box_1, self, "beam_file_name", "Shadow File Name", labelWidth=120, valueType=str, orientation="horizontal")
        self.le_beam_file_name.setReadOnly(True)
        font = QtGui.QFont(self.le_beam_file_name.font())
        font.setBold(True)
        self.le_beam_file_name.setFont(font)
        palette = QtGui.QPalette(self.le_beam_file_name.palette()) # make a copy of the palette
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor('dark blue'))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(243, 240, 160))
        self.le_beam_file_name.setPalette(palette)

        gui.comboBox(left_box_1, self, "kind_of_power", label="Kind Of Power",
                     items=["Incident", "Absorbed", "Transmitted"], labelWidth=260, sendSelectedValue=False, orientation="horizontal")


        gui.rubber(self.controlArea)

    def setBeam(self, beam):
        if ShadowCongruence.checkEmptyBeam(beam[0]) and ShadowCongruence.checkGoodBeam(beam[0]):
            if beam[0].scanned_variable_data and beam[0].scanned_variable_data.has_additional_parameter("total_power"):
                self.input_beam     = beam[0]
                self.footprint_beam = beam[1]

                self.calculate_footprint()

    def calculate_footprint(self):
        self.setStatusMessage("")

        try:
            beam_out = self.footprint_beam.duplicate()
            beam_out.history.append(ShadowOEHistoryItem()) # fake Source
            beam_out._oe_number = 0

            # just to create a safe history for possible re-tracing
            beam_out.traceFromOE(beam_out, self.create_dummy_oe(), history=True)

            total_power = self.input_beam.scanned_variable_data.get_additional_parameter("total_power")

            additional_parameters = {}
            additional_parameters["total_power"]        = total_power
            additional_parameters["photon_energy_step"] = self.input_beam.scanned_variable_data.get_additional_parameter("photon_energy_step")
            additional_parameters["is_footprint"] = True

            n_rays = len(beam_out._beam.rays[:, 0]) # lost and good!

            incident_beam = self.input_beam.getOEHistory(self.input_beam._oe_number)._input_beam

            ticket = incident_beam._beam.histo2(1, 3, nbins=100, xrange=None, yrange=None, nolost=1, ref=23)
            ticket['histogram'] *= (total_power/n_rays) # power

            additional_parameters["incident_power"] = ticket['histogram'].sum()

            if self.kind_of_power == 0: # incident
                beam_out._beam.rays[:, 6]  = incident_beam._beam.rays[:, 6]
                beam_out._beam.rays[:, 7]  = incident_beam._beam.rays[:, 7]
                beam_out._beam.rays[:, 8]  = incident_beam._beam.rays[:, 8]
                beam_out._beam.rays[:, 15] = incident_beam._beam.rays[:, 15]
                beam_out._beam.rays[:, 16] = incident_beam._beam.rays[:, 16]
                beam_out._beam.rays[:, 17] = incident_beam._beam.rays[:, 17]
            elif self.kind_of_power == 1: # absorbed
                # need a trick: put the whole intensity of one single component

                incident_intensity = incident_beam._beam.rays[:, 6]**2 + incident_beam._beam.rays[:, 7]**2 + incident_beam._beam.rays[:, 8]**2 +\
                                     incident_beam._beam.rays[:, 15]**2 + incident_beam._beam.rays[:, 16]**2 + incident_beam._beam.rays[:, 17]**2
                transmitted_intensity = beam_out._beam.rays[:, 6]**2 + beam_out._beam.rays[:, 7]**2 + beam_out._beam.rays[:, 8]**2 +\
                                        beam_out._beam.rays[:, 15]**2 + beam_out._beam.rays[:, 16]**2 + beam_out._beam.rays[:, 17]**2

                electric_field = numpy.sqrt(incident_intensity - transmitted_intensity)
                electric_field[numpy.where(electric_field == numpy.nan)] = 0.0

                beam_out._beam.rays[:, 6]  = electric_field
                beam_out._beam.rays[:, 7]  = 0.0
                beam_out._beam.rays[:, 8]  = 0.0
                beam_out._beam.rays[:, 15] = 0.0
                beam_out._beam.rays[:, 16] = 0.0
                beam_out._beam.rays[:, 17] = 0.0

            beam_out.setScanningData(ShadowBeam.ScanningData(self.input_beam.scanned_variable_data.get_scanned_variable_name(),
                                                             self.input_beam.scanned_variable_data.get_scanned_variable_value(),
                                                             self.input_beam.scanned_variable_data.get_scanned_variable_display_name(),
                                                             self.input_beam.scanned_variable_data.get_scanned_variable_um(),
                                                             additional_parameters))
            self.send("Beam", beam_out)
        except Exception as exception:
            QtWidgets.QMessageBox.critical(self, "Error",
                                       str(exception), QtWidgets.QMessageBox.Ok)


    def create_dummy_oe(self):
        empty_element = ShadowOpticalElement.create_empty_oe()

        empty_element._oe.DUMMY = self.workspace_units_to_cm

        empty_element._oe.T_SOURCE     = 0.0
        empty_element._oe.T_IMAGE = 0.0
        empty_element._oe.T_INCIDENCE  = 0.0
        empty_element._oe.T_REFLECTION = 180.0
        empty_element._oe.ALPHA        = 0.0

        empty_element._oe.FWRITE = 3
        empty_element._oe.F_ANGLE = 0

        return empty_element

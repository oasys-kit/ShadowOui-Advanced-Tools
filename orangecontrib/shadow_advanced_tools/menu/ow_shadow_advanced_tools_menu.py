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

from PyQt5 import QtWidgets
from oasys.menus.menu import OMenu

from orangecontrib.shadow_advanced_tools.widgets.thermal.ow_power_plot_xy import PowerPlotXY

class ShadowAdvancedToolsMenu(OMenu):
    def __init__(self):
        super().__init__(name="Shadow Advanced Tools")

        self.openContainer()
        self.addContainer("Cumulative Plotting")
        self.addSubMenu("Enable all the Power Plot XY widgets")
        self.addSubMenu("Disable all the Power Plot XY widgets")
        self.addSeparator()
        self.addSubMenu("Select Plotting \"Yes\" in all the Power Plot XY widgets")
        self.addSubMenu("Select Plotting \"No\" in all the Power Plot XY widgets")
        self.addSeparator()
        self.addSubMenu("Clear all the cumulated plots in Power Plot XY widgets")
        self.addSubMenu("Reload all the cumulated plots in Power Plot XY widgets (from work. dir.)")
        self.closeContainer()

    def executeAction_1(self, action):
        try:
            for link in self.canvas_main_window.current_document().scheme().links:
                if not link.enabled:
                    widget = self.canvas_main_window.current_document().scheme().widget_for_node(link.sink_node)

                    if isinstance(widget, PowerPlotXY): link.set_enabled(True)
        except Exception as exception:
            QtWidgets.QMessageBox.critical(None, "Error",
                exception.args[0],
                QtWidgets.QMessageBox.Ok)

    def executeAction_2(self, action):
        try:
            for link in self.canvas_main_window.current_document().scheme().links:
                if link.enabled:
                    widget = self.canvas_main_window.current_document().scheme().widget_for_node(link.sink_node)

                    if isinstance(widget, PowerPlotXY): link.set_enabled(False)
        except Exception as exception:
            QtWidgets.QMessageBox.critical(None, "Error",
                exception.args[0],
                QtWidgets.QMessageBox.Ok)

    def executeAction_3(self, action):
        try:
            for node in self.canvas_main_window.current_document().scheme().nodes:
                widget = self.canvas_main_window.current_document().scheme().widget_for_node(node)

                if isinstance(widget, PowerPlotXY): widget.view_type = 1
        except Exception as exception:
            QtWidgets.QMessageBox.critical(None, "Error",
                exception.args[0],
                QtWidgets.QMessageBox.Ok)

    def executeAction_4(self, action):
        try:
            for node in self.canvas_main_window.current_document().scheme().nodes:
                widget = self.canvas_main_window.current_document().scheme().widget_for_node(node)

                if isinstance(widget, PowerPlotXY): widget.view_type = 0
        except Exception as exception:
            QtWidgets.QMessageBox.critical(None, "Error",
                exception.args[0],
                QtWidgets.QMessageBox.Ok)


    def executeAction_5(self, action):
        try:
            for node in self.canvas_main_window.current_document().scheme().nodes:
                widget = self.canvas_main_window.current_document().scheme().widget_for_node(node)

                if isinstance(widget, PowerPlotXY): widget.clearResults(interactive=False)
        except Exception as exception:
            QtWidgets.QMessageBox.critical(None, "Error",
                exception.args[0],
                QtWidgets.QMessageBox.Ok)

    def executeAction_6(self, action):
        try:
            for node in self.canvas_main_window.current_document().scheme().nodes:
                widget = self.canvas_main_window.current_document().scheme().widget_for_node(node)

                if isinstance(widget, PowerPlotXY): widget.load_partial_results()
        except Exception as exception:
            QtWidgets.QMessageBox.critical(None, "Error",
                exception.args[0],
                QtWidgets.QMessageBox.Ok)

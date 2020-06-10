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

import os, sys
import time
import numpy
import scipy.ndimage.filters as filters
import scipy.ndimage.interpolation as interpolation
import scipy.ndimage.fourier as fourier

from PyQt5.QtWidgets import QMessageBox, QFileDialog, QInputDialog
from PyQt5.QtGui import QTextCursor

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.widgets.gui import ConfirmDialog

from oasys.util.oasys_util import EmittingStream

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowCongruence, ShadowPlot
from orangecontrib.shadow.widgets.gui.ow_automatic_element import AutomaticElement
from orangecontrib.shadow_advanced_tools.util.gui import PowerPlotXYWidget

class PowerPlotXY(AutomaticElement):

    name = "Power Plot XY"
    description = "Display Data Tools: Power Plot XY"
    icon = "icons/plot_xy_power.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 5.1
    category = "Display Data Tools"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Input Beam", ShadowBeam, "setBeam")]

    IMAGE_WIDTH = 878
    IMAGE_HEIGHT = 570

    want_main_area=1
    plot_canvas=None
    input_beam=None

    image_plane=Setting(0)
    image_plane_new_position=Setting(10.0)
    image_plane_rel_abs_position=Setting(0)

    x_column_index=Setting(0)
    y_column_index=Setting(2)

    x_range=Setting(0)
    x_range_min=Setting(0.0)
    x_range_max=Setting(0.0)

    y_range=Setting(0)
    y_range_min=Setting(0.0)
    y_range_max=Setting(0.0)

    rays=Setting(1)
    number_of_bins=Setting(100)

    title=Setting("X,Z")

    keep_result=Setting(1)
    autosave_partial_results = Setting(0)

    autosave = Setting(0)
    autosave_file_name = Setting("autosave_power_density.hdf5")

    kind_of_calculation = Setting(0)
    replace_poor_statistic = Setting(0)
    good_rays_limit = Setting(100)
    center_x = Setting(0.0)
    center_y = Setting(0.0)
    sigma_x = Setting(0.0)
    sigma_y = Setting(0.0)
    gamma = Setting(0.0)


    loaded_plot_file_name = "<load hdf5 file>"

    new_nbins_h = Setting(25)
    new_nbins_v = Setting(25)

    filter = Setting(3)
    filter_sigma_h = Setting(1.0)
    filter_sigma_v = Setting(1.0)
    filter_mode = Setting(0)
    filter_cval = Setting(0.0)
    filter_spline_order = Setting(2)
    masking_level = Setting(1e-3)

    cumulated_ticket=None
    plotted_ticket   = None
    energy_min = None
    energy_max = None
    energy_step = None
    total_power = None
    cumulated_total_power = None

    plotted_ticket_original = None

    view_type=Setting(1)

    autosave_file = None

    def __init__(self):
        super().__init__(show_automatic_box=False)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        gui.button(button_box, self, "Plot Data", callback=self.plot_cumulated_data, height=45)
        gui.button(button_box, self, "Save Plot", callback=self.save_cumulated_data, height=45)

        gui.separator(self.controlArea, 10)

        self.tabs_setting = oasysgui.tabWidget(self.controlArea)
        self.tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)

        # graph tab
        tab_set = oasysgui.createTabPage(self.tabs_setting, "Plot Settings")
        tab_gen = oasysgui.createTabPage(self.tabs_setting, "Histogram Settings")
        tab_post = oasysgui.createTabPage(self.tabs_setting, "Post Processing")

        screen_box = oasysgui.widgetBox(tab_set, "Screen Position Settings", addSpace=True, orientation="vertical", height=120)

        self.image_plane_combo = gui.comboBox(screen_box, self, "image_plane", label="Position of the Image",
                                            items=["On Image Plane", "Retraced"], labelWidth=260,
                                            callback=self.set_ImagePlane, sendSelectedValue=False, orientation="horizontal")

        self.image_plane_box = oasysgui.widgetBox(screen_box, "", addSpace=False, orientation="vertical", height=50)
        self.image_plane_box_empty = oasysgui.widgetBox(screen_box, "", addSpace=False, orientation="vertical", height=50)

        oasysgui.lineEdit(self.image_plane_box, self, "image_plane_new_position", "Image Plane new Position", labelWidth=220, valueType=float, orientation="horizontal")

        gui.comboBox(self.image_plane_box, self, "image_plane_rel_abs_position", label="Position Type", labelWidth=250,
                     items=["Absolute", "Relative"], sendSelectedValue=False, orientation="horizontal")

        self.set_ImagePlane()

        general_box = oasysgui.widgetBox(tab_set, "Variables Settings", addSpace=True, orientation="vertical", height=350)

        self.x_column = gui.comboBox(general_box, self, "x_column_index", label="X Column",labelWidth=70,
                                     items=["1: X",
                                            "2: Y",
                                            "3: Z",
                                     ],
                                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(general_box, self, "x_range", label="X Range", labelWidth=250,
                                     items=["<Default>",
                                            "Set.."],
                                     callback=self.set_XRange, sendSelectedValue=False, orientation="horizontal")

        self.xrange_box = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=100)
        self.xrange_box_empty = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=100)

        oasysgui.lineEdit(self.xrange_box, self, "x_range_min", "X min", labelWidth=220, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.xrange_box, self, "x_range_max", "X max", labelWidth=220, valueType=float, orientation="horizontal")

        self.set_XRange()

        self.y_column = gui.comboBox(general_box, self, "y_column_index", label="Y Column",labelWidth=70,
                                     items=["1: X",
                                            "2: Y",
                                            "3: Z",
                                     ],

                                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(general_box, self, "y_range", label="Y Range",labelWidth=250,
                                     items=["<Default>",
                                            "Set.."],
                                     callback=self.set_YRange, sendSelectedValue=False, orientation="horizontal")

        self.yrange_box = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=100)
        self.yrange_box_empty = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=100)

        oasysgui.lineEdit(self.yrange_box, self, "y_range_min", "Y min", labelWidth=220, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.yrange_box, self, "y_range_max", "Y max", labelWidth=220, valueType=float, orientation="horizontal")

        self.set_YRange()

        self.cb_rays = gui.comboBox(general_box, self, "rays", label="Power", labelWidth=250,
                                    items=["Transmitted", "Absorbed (Lost)", "Absorbed (Still Good)"],
                                    sendSelectedValue=False, orientation="horizontal")

        autosave_box = oasysgui.widgetBox(tab_gen, "Autosave", addSpace=True, orientation="vertical", height=85)

        gui.comboBox(autosave_box, self, "autosave", label="Save automatically plot into file", labelWidth=250,
                                         items=["No", "Yes"],
                                         sendSelectedValue=False, orientation="horizontal", callback=self.set_autosave)

        self.autosave_box_1 = oasysgui.widgetBox(autosave_box, "", addSpace=False, orientation="horizontal", height=25)
        self.autosave_box_2 = oasysgui.widgetBox(autosave_box, "", addSpace=False, orientation="horizontal", height=25)

        self.le_autosave_file_name = oasysgui.lineEdit(self.autosave_box_1, self, "autosave_file_name", "File Name", labelWidth=100,  valueType=str, orientation="horizontal")

        gui.button(self.autosave_box_1, self, "...", callback=self.selectAutosaveFile)

        incremental_box = oasysgui.widgetBox(tab_gen, "Incremental Result", addSpace=True, orientation="vertical", height=120)

        gui.comboBox(incremental_box, self, "keep_result", label="Keep Result", labelWidth=250,
                     items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal", callback=self.set_autosave)

        self.cb_autosave_partial_results = gui.comboBox(incremental_box, self, "autosave_partial_results", label="Save partial plots into file", labelWidth=250,
                                                        items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal")

        gui.button(incremental_box, self, "Clear", callback=self.clearResults)

        self.set_autosave()

        histograms_box = oasysgui.widgetBox(tab_gen, "Histograms settings", addSpace=True, orientation="vertical", height=270)

        oasysgui.lineEdit(histograms_box, self, "number_of_bins", "Number of Bins", labelWidth=250, valueType=int, orientation="horizontal")

        gui.separator(histograms_box)

        gui.comboBox(histograms_box, self, "kind_of_calculation", label="Kind of Calculation", labelWidth=200,
                     items=["From Rays", "Flat Distribution", "Gaussian Distribution", "Lorentzian Distribution"], sendSelectedValue=False, orientation="horizontal", callback=self.set_kind_of_calculation)

        self.poor_statics_cb = gui.comboBox(histograms_box, self, "replace_poor_statistic", label="Activate on Poor Statistics", labelWidth=250,
                                            items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal", callback=self.set_manage_poor_statistics)

        self.poor_statistics_box_1 = oasysgui.widgetBox(histograms_box, "", addSpace=False, orientation="vertical", height=30)
        self.poor_statistics_box_2 = oasysgui.widgetBox(histograms_box, "", addSpace=False, orientation="vertical", height=30)

        self.le_autosave_file_name = oasysgui.lineEdit(self.poor_statistics_box_1, self, "good_rays_limit", "Good Rays Limit", labelWidth=100,  valueType=int, orientation="horizontal")

        self.kind_of_calculation_box_1 = oasysgui.widgetBox(histograms_box, "", addSpace=False, orientation="vertical", height=110)
        self.kind_of_calculation_box_2 = oasysgui.widgetBox(histograms_box, "", addSpace=False, orientation="vertical", height=110)
        self.kind_of_calculation_box_3 = oasysgui.widgetBox(histograms_box, "", addSpace=False, orientation="vertical", height=110)

        self.le_g_sigma_x = oasysgui.lineEdit(self.kind_of_calculation_box_2, self, "sigma_x", "Sigma H", labelWidth=100,  valueType=float, orientation="horizontal")
        self.le_g_sigma_y = oasysgui.lineEdit(self.kind_of_calculation_box_2, self, "sigma_y", "Sigma V", labelWidth=100,  valueType=float, orientation="horizontal")
        self.le_g_center_x = oasysgui.lineEdit(self.kind_of_calculation_box_2, self, "center_x", "Center H", labelWidth=100,  valueType=float, orientation="horizontal")
        self.le_g_center_y = oasysgui.lineEdit(self.kind_of_calculation_box_2, self, "center_y", "Center V", labelWidth=100,  valueType=float, orientation="horizontal")

        self.le_l_gamma = oasysgui.lineEdit(self.kind_of_calculation_box_3, self, "gamma", "Gamma", labelWidth=100,  valueType=float, orientation="horizontal")
        self.le_l_center_x = oasysgui.lineEdit(self.kind_of_calculation_box_3, self, "center_x", "Center H", labelWidth=100,  valueType=float, orientation="horizontal")
        self.le_l_center_y = oasysgui.lineEdit(self.kind_of_calculation_box_3, self, "center_y", "Center V", labelWidth=100,  valueType=float, orientation="horizontal")

        self.set_kind_of_calculation()

        # post porcessing

        post_box = oasysgui.widgetBox(tab_post, "Post Processing Setting", addSpace=False, orientation="vertical", height=500)

        post_box_1 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="horizontal", height=25)
        self.le_loaded_plot_file_name = oasysgui.lineEdit(post_box_1, self, "loaded_plot_file_name", "Loaded File", labelWidth=100,  valueType=str, orientation="horizontal")
        gui.button(post_box_1, self, "...", callback=self.selectPlotFile)

        gui.separator(post_box)

        button_box = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="vertical")
        gui.button(button_box, self, "Reset", callback=self.reloadPlot, height=35)
        gui.separator(button_box)
        gui.button(button_box, self, "Invert", callback=self.invertPlot, height=35)

        gui.separator(post_box)

        button_box = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="horizontal")
        gui.button(button_box, self, "Rebin Plot", callback=self.rebinPlot, height=35)

        post_box_0 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="vertical", height=60)
        oasysgui.lineEdit(post_box_0, self, "new_nbins_h", "Nr. Bins H", labelWidth=200,  valueType=int, orientation="horizontal")
        oasysgui.lineEdit(post_box_0, self, "new_nbins_v", "Nr. Bins V", labelWidth=200,  valueType=int, orientation="horizontal")

        button_box = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="horizontal")
        gui.button(button_box, self, "Smooth Plot", callback=self.smoothPlot, height=35)

        gui.separator(post_box)

        gui.comboBox(post_box, self, "filter", label="Filter", labelWidth=200,
                     items=["Gaussian",
                            "Spline",
                            "Uniform",
                            "Fourier-Gaussian",
                            "Fourier-Ellipsoid",
                            "Fourier-Uniform",
                            "Fill Holes"
                            ], sendSelectedValue=False, orientation="horizontal", callback=self.set_Filter)

        self.post_box_1 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="vertical", height=110)
        self.post_box_2 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="vertical", height=110)
        self.post_box_3 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="vertical", height=110)
        self.post_box_4 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="vertical", height=110)

        oasysgui.lineEdit(self.post_box_1, self, "filter_sigma_h", "Sigma/Size H", labelWidth=200,  valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.post_box_1, self, "filter_sigma_v", "Sigma/Size V", labelWidth=200,  valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.post_box_2, self, "filter_sigma_h", "Sigma/Size H", labelWidth=200,  valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.post_box_2, self, "filter_sigma_v", "Sigma/Size V", labelWidth=200,  valueType=float, orientation="horizontal")

        self.cb_filter_mode = gui.comboBox(self.post_box_2, self, "filter_mode", label="Mode", labelWidth=200,
                                           items=["reflect", "constant", "nearest", "mirror", "wrap"],
                                           sendSelectedValue=False, orientation="horizontal", callback=self.set_FilterMode)

        self.le_filter_cval = oasysgui.lineEdit(self.post_box_2, self, "filter_cval", "Constant Value", labelWidth=250,  valueType=float, orientation="horizontal")

        oasysgui.lineEdit(self.post_box_3, self, "filter_spline_order", "Spline Order", labelWidth=250,  valueType=int, orientation="horizontal")

        gui.separator(post_box)

        oasysgui.lineEdit(post_box, self, "masking_level", "Mask if < factor of max value", labelWidth=250,  valueType=float, orientation="horizontal")

        self.set_Filter()

        self.main_tabs = oasysgui.tabWidget(self.mainArea)
        plot_tab = oasysgui.createTabPage(self.main_tabs, "Plots")
        out_tab = oasysgui.createTabPage(self.main_tabs, "Output")

        view_box = oasysgui.widgetBox(plot_tab, "Plotting", addSpace=False, orientation="vertical", width=self.IMAGE_WIDTH)
        view_box_1 = oasysgui.widgetBox(view_box, "", addSpace=False, orientation="vertical", width=350)

        gui.comboBox(view_box_1, self, "view_type", label="Plot Accumulated Results", labelWidth=320,
                     items=["No", "Yes"],  sendSelectedValue=False, orientation="horizontal")

        self.image_box = gui.widgetBox(plot_tab, "Plot Result", addSpace=True, orientation="vertical")
        self.image_box.setFixedHeight(self.IMAGE_HEIGHT)
        self.image_box.setFixedWidth(self.IMAGE_WIDTH)

        self.shadow_output = oasysgui.textArea(height=580, width=800)

        out_box = gui.widgetBox(out_tab, "System Output", addSpace=True, orientation="horizontal")
        out_box.layout().addWidget(self.shadow_output)

    def clearResults(self, interactive=True):
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

    def set_kind_of_calculation(self):
        self.kind_of_calculation_box_1.setVisible(self.kind_of_calculation<=1)
        self.kind_of_calculation_box_2.setVisible(self.kind_of_calculation==2)
        self.kind_of_calculation_box_3.setVisible(self.kind_of_calculation==3)

        if self.kind_of_calculation > 0:
            self.poor_statics_cb.setEnabled(True)
        else:
            self.poor_statics_cb.setEnabled(False)
            self.replace_poor_statistic = 0

        self.set_manage_poor_statistics()

    def set_manage_poor_statistics(self):
        self.poor_statistics_box_1.setVisible(self.replace_poor_statistic==1)
        self.poor_statistics_box_2.setVisible(self.replace_poor_statistic==0)

    def set_autosave(self):
        self.autosave_box_1.setVisible(self.autosave==1)
        self.autosave_box_2.setVisible(self.autosave==0)

        self.cb_autosave_partial_results.setEnabled(self.autosave==1 and self.keep_result==1)

    def set_ImagePlane(self):
        self.image_plane_box.setVisible(self.image_plane==1)
        self.image_plane_box_empty.setVisible(self.image_plane==0)

    def set_XRange(self):
        self.xrange_box.setVisible(self.x_range == 1)
        self.xrange_box_empty.setVisible(self.x_range == 0)

    def set_YRange(self):
        self.yrange_box.setVisible(self.y_range == 1)
        self.yrange_box_empty.setVisible(self.y_range == 0)

    def set_Filter(self):
        self.post_box_1.setVisible(3<=self.filter<=5)
        self.post_box_2.setVisible(self.filter==0 or self.filter==2)
        self.post_box_3.setVisible(self.filter==1 )
        self.post_box_4.setVisible(self.filter==6)

        if self.filter==0 or self.filter==2: self.set_FilterMode()

    def set_FilterMode(self):
        self.le_filter_cval.setEnabled(self.filter_mode==1)

    def selectAutosaveFile(self):
        self.le_autosave_file_name.setText(oasysgui.selectFileFromDialog(self, self.autosave_file_name, "Select File", file_extension_filter="HDF5 Files (*.hdf5 *.h5 *.hdf)"))

    def selectPlotFile(self):
        file_name = oasysgui.selectFileFromDialog(self, None, "Select File", file_extension_filter="HDF5 Files (*.hdf5 *.h5 *.hdf)")

        if not file_name is None:
            self.le_loaded_plot_file_name.setText(os.path.basename(os.path.normpath(file_name)))

            plot_file = ShadowPlot.PlotXYHdf5File(congruence.checkDir(file_name), mode="r")

            ticket = {}

            ticket["histogram"], ticket["histogram_h"], ticket["histogram_v"], attributes = plot_file.get_last_plot(dataset_name="power_density")
            ticket["bin_h_center"], ticket["bin_v_center"], ticket["h_label"], ticket["v_label"] = plot_file.get_coordinates()
            ticket["intensity"] = attributes["intensity"]
            ticket["nrays"]     = attributes["total_rays"]
            ticket["good_rays"] = attributes["good_rays"]

            if self.plot_canvas is None:
                self.plot_canvas = PowerPlotXYWidget()
                self.image_box.layout().addWidget(self.plot_canvas)
            else:
                if not self.plotted_ticket is None:
                    if QMessageBox.question(self, "Load Plot", "Merge with current Plot?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
                        if ticket["histogram"].shape == self.plotted_ticket["histogram"].shape and \
                           ticket["bin_h_center"].shape == self.plotted_ticket["bin_h_center"].shape and \
                           ticket["bin_v_center"].shape == self.plotted_ticket["bin_v_center"].shape and \
                           ticket["bin_h_center"][0] == self.plotted_ticket["bin_h_center"][0] and \
                           ticket["bin_h_center"][-1] == self.plotted_ticket["bin_h_center"][-1] and \
                           ticket["bin_v_center"][0] == self.plotted_ticket["bin_v_center"][0] and \
                           ticket["bin_v_center"][-1] == self.plotted_ticket["bin_v_center"][-1]:
                            ticket["histogram"] += self.plotted_ticket["histogram"]

                            if  QMessageBox.question(self, "Load Plot", "Average with current Plot?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
                                ticket["histogram"] *= 0.5
                        else:
                            raise ValueError("The plots cannot be merged: the should have same dimensions and ranges")

            cumulated_power_plot = numpy.sum(ticket["histogram"])*(ticket["bin_h_center"][1]-ticket["bin_h_center"][0])*(ticket["bin_v_center"][1]-ticket["bin_v_center"][0])

            try:
                energy_min=0.0
                energy_max=0.0
                energy_step=0.0

                self.plot_canvas.cumulated_power_plot = cumulated_power_plot
                self.plot_canvas.plot_power_density_ticket(ticket,
                                                           ticket["h_label"],
                                                           ticket["v_label"],
                                                           cumulated_total_power=0.0,
                                                           energy_min=energy_min,
                                                           energy_max=energy_max,
                                                           energy_step=energy_step)

                self.cumulated_ticket = None
                self.plotted_ticket = ticket
                self.plotted_ticket_original = ticket.copy()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e

    def reloadPlot(self):
        if not self.plotted_ticket_original is None:
            ticket = self.plotted_ticket_original.copy()

            if self.plot_canvas is None:
                self.plot_canvas = PowerPlotXYWidget()
                self.image_box.layout().addWidget(self.plot_canvas)

            cumulated_power_plot = numpy.sum(ticket["histogram"])*(ticket["bin_h_center"][1]-ticket["bin_h_center"][0])*(ticket["bin_v_center"][1]-ticket["bin_v_center"][0])

            try:
                energy_min=0.0
                energy_max=0.0
                energy_step=0.0

                self.plot_canvas.cumulated_power_plot = cumulated_power_plot
                self.plot_canvas.plot_power_density_ticket(ticket,
                                                           ticket["h_label"],
                                                           ticket["v_label"],
                                                           cumulated_total_power=0.0,
                                                           energy_min=energy_min,
                                                           energy_max=energy_max,
                                                           energy_step=energy_step)


                self.plotted_ticket = ticket
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e

    def invertPlot(self):
        if not self.plotted_ticket is None:
            try:
                ticket = self.plotted_ticket.copy()

                histogram = ticket["histogram"]
                h_coord = ticket["bin_h_center"]
                v_coord = ticket["bin_v_center"]

                h_coord, v_coord, histogram = self.invert(h_coord, v_coord, histogram)

                ticket["histogram"] = histogram
                ticket["bin_h_center"] = h_coord
                ticket["bin_v_center"] = v_coord

                pixel_area = (h_coord[1]-h_coord[0])*(v_coord[1]-v_coord[0])

                if self.plot_canvas is None:
                    self.plot_canvas = PowerPlotXYWidget()
                    self.image_box.layout().addWidget(self.plot_canvas)

                cumulated_power_plot = numpy.sum(histogram)*pixel_area

                energy_min = 0.0
                energy_max = 0.0
                energy_step = 0.0

                self.plot_canvas.cumulated_power_plot = cumulated_power_plot
                self.plot_canvas.plot_power_density_ticket(ticket,
                                                           ticket["v_label"],
                                                           ticket["h_label"],
                                                           cumulated_total_power=0.0,
                                                           energy_min=energy_min,
                                                           energy_max=energy_max,
                                                           energy_step=energy_step)

                self.plotted_ticket = ticket
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e

    def rebinPlot(self):
        if not self.plotted_ticket is None:
            try:
                congruence.checkStrictlyPositiveNumber(self.new_nbins_h, "Nr. Bins H")
                congruence.checkStrictlyPositiveNumber(self.new_nbins_v, "Nr. Bins V")

                ticket = self.plotted_ticket.copy()

                histogram = ticket["histogram"]
                h_coord = ticket["bin_h_center"]
                v_coord = ticket["bin_v_center"]

                h_coord, v_coord, histogram = self.rebin(h_coord, v_coord, histogram, (int(self.new_nbins_h), int(self.new_nbins_v)))

                ticket["histogram"] = histogram
                ticket["bin_h_center"] = h_coord
                ticket["bin_v_center"] = v_coord

                pixel_area = (h_coord[1]-h_coord[0])*(v_coord[1]-v_coord[0])

                if self.plot_canvas is None:
                    self.plot_canvas = PowerPlotXYWidget()
                    self.image_box.layout().addWidget(self.plot_canvas)

                cumulated_power_plot = numpy.sum(histogram)*pixel_area

                energy_min = 0.0
                energy_max = 0.0
                energy_step = 0.0

                self.plot_canvas.cumulated_power_plot = cumulated_power_plot
                self.plot_canvas.plot_power_density_ticket(ticket,
                                                           ticket["h_label"],
                                                           ticket["v_label"],
                                                           cumulated_total_power=0.0,
                                                           energy_min=energy_min,
                                                           energy_max=energy_max,
                                                           energy_step=energy_step)

                self.plotted_ticket = ticket
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e

    def smoothPlot(self):
        if not self.plotted_ticket is None:
            try:
                if self.filter==0 or 2<=self.filter<=5:
                    congruence.checkStrictlyPositiveNumber(self.filter_sigma_h, "Sigma/Size H")
                    congruence.checkStrictlyPositiveNumber(self.filter_sigma_v, "Sigma/Size V")

                if self.filter == 1: congruence.checkStrictlyPositiveNumber(self.filter_spline_order, "Spline Order")

                ticket = self.plotted_ticket.copy()

                mask = numpy.where(self.plotted_ticket["histogram"] <= self.plotted_ticket["histogram"].max()*self.masking_level)

                histogram = ticket["histogram"]
                h_coord = ticket["bin_h_center"]
                v_coord = ticket["bin_v_center"]

                norm = histogram.sum()

                pixel_area = (h_coord[1]-h_coord[0])*(v_coord[1]-v_coord[0])

                filter_mode = self.cb_filter_mode.currentText()

                if self.filter == 0:
                    histogram = filters.gaussian_filter(histogram, sigma=(self.filter_sigma_h, self.filter_sigma_v), mode=filter_mode, cval=self.filter_cval)
                elif self.filter == 1:
                    histogram = interpolation.spline_filter(histogram, order=int(self.filter_spline_order))
                elif self.filter == 2:
                    histogram = filters.uniform_filter(histogram, size=(int(self.filter_sigma_h), int(self.filter_sigma_v)), mode=filter_mode, cval=self.filter_cval)
                elif self.filter == 3:
                    histogram = numpy.real(numpy.fft.ifft2(fourier.fourier_gaussian(numpy.fft.fft2(histogram), sigma=(self.filter_sigma_h, self.filter_sigma_v))))
                elif self.filter == 4:
                    histogram = numpy.real(numpy.fft.ifft2(fourier.fourier_ellipsoid(numpy.fft.fft2(histogram), size=(self.filter_sigma_h, self.filter_sigma_v))))
                elif self.filter == 5:
                    histogram = numpy.real(numpy.fft.ifft2(fourier.fourier_uniform(numpy.fft.fft2(histogram), size=(self.filter_sigma_h, self.filter_sigma_v))))
                elif self.filter == 6:
                    histogram = self.apply_fill_holes(histogram)

                histogram[mask] = 0.0

                norm /= histogram.sum()

                ticket["histogram"] = histogram*norm
                
                if self.plot_canvas is None:
                    self.plot_canvas = PowerPlotXYWidget()
                    self.image_box.layout().addWidget(self.plot_canvas)

                cumulated_power_plot = numpy.sum(histogram)*pixel_area

                energy_min=0.0
                energy_max=0.0
                energy_step=0.0

                self.plot_canvas.cumulated_power_plot = cumulated_power_plot
                self.plot_canvas.plot_power_density_ticket(ticket,
                                                           ticket["h_label"],
                                                           ticket["v_label"],
                                                           cumulated_total_power=0.0,
                                                           energy_min=energy_min,
                                                           energy_max=energy_max,
                                                           energy_step=energy_step)

                self.plotted_ticket = ticket
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e

    def rebin(self, x, y, z, new_shape):
        shape = (new_shape[0], z.shape[0] // new_shape[0], new_shape[1], z.shape[1] // new_shape[1])

        return numpy.linspace(x[0], x[-1], new_shape[0]), \
               numpy.linspace(y[0], y[-1], new_shape[1]),  \
               z.reshape(shape).mean(-1).mean(1)

    def invert(self, x, y, data):
        return y, x, data.T

    def apply_fill_holes(self, histogram):
        from skimage.morphology import reconstruction

        seed = numpy.copy(histogram)
        seed[1:-1, 1:-1] = histogram.max()

        filled = reconstruction(seed=seed, mask=histogram, method='erosion')

        return filled*(histogram.sum()/filled.sum())

    def save_cumulated_data(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Current Plot", filter="HDF5 Files (*.hdf5 *.h5 *.hdf);;Text Files (*.dat *.txt)")

        if not file_name is None and not file_name.strip()=="":
            items = ("Hdf5 only", "Text only", "Hdf5 and Text")

            item, ok = QInputDialog.getItem(self, "Select Output Format", "Formats: ", items, 2, False)

            if ok and item:
                if item == "Hdf5 only" or item == "Hdf5 and Text":
                    self.save_cumulated_data_hdf5(file_name)
                if item == "Text only" or item == "Hdf5 and Text":
                    self.save_cumulated_data_txt(file_name)

    def save_cumulated_data_hdf5(self, file_name):
        if not self.plotted_ticket is None:
            try:
                save_file = ShadowPlot.PlotXYHdf5File(congruence.checkDir(os.path.splitext(file_name)[0] + ".hdf5"))

                save_file.write_coordinates(self.plotted_ticket)
                save_file.add_plot_xy(self.plotted_ticket, dataset_name="power_density")

                save_file.close()
            except Exception as exception:
                QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

                if self.IS_DEVELOP: raise exception

    def save_cumulated_data_txt(self, file_name):
        if not self.plotted_ticket is None:
            try:
                save_file = open(os.path.splitext(file_name)[0] + ".dat", "w")

                x_values = self.plotted_ticket["bin_h_center"]
                y_values = self.plotted_ticket["bin_v_center"]
                z_values = self.plotted_ticket["histogram"]

                for i in range(len(x_values)):
                    for j in range(len(y_values)):
                        row = str(x_values[i]) + " " + str(y_values[j]) + " " + str(z_values[i, j])

                        if i+j > 0: row = "\n" + row

                        save_file.write(row)

                save_file.flush()
                save_file.close()
            except Exception as exception:
                QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

                if self.IS_DEVELOP: raise exception

    def replace_fig(self, shadow_beam, var_x, var_y, xrange, yrange, nbins, nolost):
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

            if self.keep_result == 1:
                self.cumulated_ticket, last_ticket = self.plot_canvas.plot_power_density(shadow_beam, var_x, var_y,
                                                                                         self.total_power, self.cumulated_total_power,
                                                                                         self.energy_min, self.energy_max, self.energy_step,
                                                                                         nbins=nbins, xrange=xrange, yrange=yrange, nolost=nolost,
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
                                                                                         gamma=self.gamma)
                self.plotted_ticket = self.cumulated_ticket
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
                                                                nbins=nbins, xrange=xrange, yrange=yrange, nolost=nolost,
                                                                to_mm=self.workspace_units_to_mm,
                                                                show_image=self.view_type==1,
                                                                kind_of_calculation=self.kind_of_calculation,
                                                                replace_poor_statistic=self.replace_poor_statistic,
                                                                good_rays_limit=self.good_rays_limit,
                                                                center_x=self.center_x,
                                                                center_y=self.center_y,
                                                                sigma_x=self.sigma_x,
                                                                sigma_y=self.sigma_y,
                                                                gamma=self.gamma)

                self.cumulated_ticket = None
                self.plotted_ticket = ticket
                self.plotted_ticket_original = self.plotted_ticket.copy()

                if self.autosave == 1:
                    self.autosave_file.write_coordinates(ticket)
                    self.autosave_file.add_plot_xy(ticket, dataset_name="power_density")
                    self.autosave_file.flush()

        except Exception as e:
            if not self.IS_DEVELOP:
                raise Exception("Data not plottable: No good rays or bad content")
            else:
                raise e

    def plot_xy(self, var_x, var_y):
        beam_to_plot = self.input_beam

        if self.image_plane == 1:
            new_shadow_beam = self.input_beam.duplicate(history=False)

            if self.image_plane_rel_abs_position == 1:  # relative
                dist = self.image_plane_new_position
            else:  # absolute
                if self.input_beam.historySize() == 0:
                    historyItem = None
                else:
                    historyItem = self.input_beam.getOEHistory(oe_number=self.input_beam._oe_number)

                if historyItem is None: image_plane = 0.0
                elif self.input_beam._oe_number == 0: image_plane = 0.0
                else: image_plane = historyItem._shadow_oe_end._oe.T_IMAGE

                dist = self.image_plane_new_position - image_plane

            self.retrace_beam(new_shadow_beam, dist)

            beam_to_plot = new_shadow_beam

        xrange, yrange = self.get_ranges()

        self.replace_fig(beam_to_plot, var_x, var_y, xrange=xrange, yrange=yrange, nbins=int(self.number_of_bins), nolost=self.rays+1)

    def get_ranges(self):
        xrange = None
        yrange = None
        factor1 = self.workspace_units_to_mm
        factor2 = self.workspace_units_to_mm

        if self.x_range == 1:
            congruence.checkLessThan(self.x_range_min, self.x_range_max, "X range min", "X range max")

            xrange = [self.x_range_min / factor1, self.x_range_max / factor1]

        if self.y_range == 1:
            congruence.checkLessThan(self.y_range_min, self.y_range_max, "Y range min", "Y range max")

            yrange = [self.y_range_min / factor2, self.y_range_max / factor2]

        return xrange, yrange

    def plot_cumulated_data(self):
        if not self.cumulated_ticket is None:
            self.plot_canvas.plot_power_density_ticket(ticket=self.cumulated_ticket,
                                                       var_x=self.x_column_index+1,
                                                       var_y=self.y_column_index+1,
                                                       cumulated_total_power=self.cumulated_total_power,
                                                       energy_min=self.energy_min,
                                                       energy_max=self.energy_max,
                                                       energy_step=self.energy_step,
                                                       show_image=self.view_type==1)

            self.plotted_ticket_original = self.cumulated_ticket.copy()

    def plot_results(self):
        try:
            sys.stdout = EmittingStream(textWritten=self.writeStdOut)

            if ShadowCongruence.checkEmptyBeam(self.input_beam):
                self.number_of_bins = congruence.checkStrictlyPositiveNumber(self.number_of_bins, "Number of Bins")

                self.plot_xy(self.x_column_index+1, self.y_column_index+1)

            time.sleep(0.1)  # prevents a misterious dead lock in the Orange cycle when refreshing the histogram
        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                       str(exception),
                                       QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def setBeam(self, input_beam):
        self.cb_rays.setEnabled(True)

        if not input_beam is None:
            if not input_beam.scanned_variable_data is None and input_beam.scanned_variable_data.has_additional_parameter("total_power"):
                self.input_beam = input_beam

                self.total_power = self.input_beam.scanned_variable_data.get_additional_parameter("total_power")

                if self.energy_min is None:
                    self.energy_min  = self.input_beam.scanned_variable_data.get_scanned_variable_value()
                    self.cumulated_total_power = self.total_power
                else:
                    self.cumulated_total_power += self.total_power

                self.energy_step = self.input_beam.scanned_variable_data.get_additional_parameter("photon_energy_step")
                self.energy_max  = self.input_beam.scanned_variable_data.get_scanned_variable_value()

                if self.input_beam.scanned_variable_data.has_additional_parameter("is_footprint"):
                    if self.input_beam.scanned_variable_data.get_additional_parameter("is_footprint"):
                        self.cb_rays.setEnabled(False)
                        self.rays = 0 # transmitted, absorbed doesn't make sense since is precalculated by footprint object
                    else:
                        self.cb_rays.setEnabled(True)

                if ShadowCongruence.checkEmptyBeam(input_beam):
                    if ShadowCongruence.checkGoodBeam(input_beam):
                        self.plot_results()

    def writeStdOut(self, text):
        cursor = self.shadow_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.shadow_output.setTextCursor(cursor)
        self.shadow_output.ensureCursorVisible()

    def retrace_beam(self, new_shadow_beam, dist):
            new_shadow_beam._beam.retrace(dist)

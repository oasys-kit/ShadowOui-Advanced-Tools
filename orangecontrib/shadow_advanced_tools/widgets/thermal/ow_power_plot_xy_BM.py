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

import os, sys
import time
import numpy
import scipy.ndimage.filters as filters
import scipy.ndimage.interpolation as interpolation
import scipy.ndimage.fourier as fourier
import scipy.constants as codata

from PyQt5.QtWidgets import QMessageBox, QFileDialog, QInputDialog
from PyQt5.QtGui import QTextCursor

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.widgets.gui import ConfirmDialog
from oasys.widgets.exchange import DataExchangeObject

from oasys.util.oasys_util import EmittingStream

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowCongruence, ShadowPlot, ShadowPhysics
from orangecontrib.shadow.widgets.gui.ow_automatic_element import AutomaticElement
from orangecontrib.shadow_advanced_tools.util.gui import PowerPlotXYWidget

class PowerPlotXYBM(AutomaticElement):

    name = "Power Plot XY - BM"
    description = "Display Data Tools: Power Plot XY - BM"
    icon = "icons/bm_plot_xy_power.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 5.101
    category = "Display Data Tools"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Input Beam", ShadowBeam, "setBeam"),
              ("Input Spectrum", DataExchangeObject, "setFlux")]

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

    rays=Setting(0)
    number_of_bins=Setting(100) # for retrocompatibility: I don't change the name
    number_of_bins_v=Setting(100)

    title=Setting("X,Z")

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

    nbins_interpolation = Setting(500)

    initial_flux = None
    initial_energy = None

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

        general_box = oasysgui.widgetBox(tab_set, "Histogram Settings", addSpace=True, orientation="vertical", height=380)

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

        self.xrange_box = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=60)
        self.xrange_box_empty = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=60)

        oasysgui.lineEdit(self.xrange_box, self, "x_range_min", "X min", labelWidth=220, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.xrange_box, self, "x_range_max", "X max", labelWidth=220, valueType=float, orientation="horizontal")

        self.set_XRange()

        self.y_column = gui.comboBox(general_box, self, "y_column_index", label="Y Column", labelWidth=70,
                                     items=["1: X",
                                            "2: Y",
                                            "3: Z",
                                     ],

                                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(general_box, self, "y_range", label="Y Range",labelWidth=250,
                                     items=["<Default>",
                                            "Set.."],
                                     callback=self.set_YRange, sendSelectedValue=False, orientation="horizontal")

        self.yrange_box = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=60)
        self.yrange_box_empty = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=60)

        oasysgui.lineEdit(self.yrange_box, self, "y_range_min", "Y min", labelWidth=220, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.yrange_box, self, "y_range_max", "Y max", labelWidth=220, valueType=float, orientation="horizontal")

        self.set_YRange()


        oasysgui.lineEdit(general_box, self, "number_of_bins", "Number of Bins H", labelWidth=250, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(general_box, self, "number_of_bins_v", "Number of Bins V", labelWidth=250, valueType=int, orientation="horizontal")

        gui.separator(general_box)

        self.cb_rays = gui.comboBox(general_box, self, "rays", label="Power", labelWidth=250,
                                    items=["Transmitted", "Absorbed (Lost)", "Absorbed (Still Good)"],
                                    sendSelectedValue=False, orientation="horizontal")

        oasysgui.lineEdit(general_box, self, "nbins_interpolation", "Number of Bins for energy interpolation", labelWidth=250, valueType=int, orientation="horizontal")

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

        gui.comboBox(view_box_1, self, "view_type", label="Plot Results", labelWidth=320,
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

            if not self.plot_canvas is None:
                self.plot_canvas.clear()

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

                cumulated_power_plot = numpy.sum(ticket["histogram"])*pixel_area

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
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Current Plot", filter="HDF5 Files (*.hdf5 *.h5 *.hdf);;Text Files (*.dat *.txt);;Ansys Files (*.csv)")

        if not file_name is None and not file_name.strip()=="":
            format, ok = QInputDialog.getItem(self, "Select Output Format", "Formats: ", ("Hdf5", "Text", "Ansys", "All"), 3, False)

            if ok and format:
                if format == "Hdf5" or format == "All":  self.save_cumulated_data_hdf5(file_name)
                if format == "Text" or format == "All":  self.save_cumulated_data_txt(file_name)
                if format == "Ansys" or format == "All": self.save_cumulated_data_ansys(file_name)

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

    def save_cumulated_data_ansys(self, file_name):
        if not self.plotted_ticket is None:
            try:
                column, ok = QInputDialog.getItem(self, "Ansys File", "Empty column in Ansys axes system", ("x", "y", "z"), 2, False)

                if ok and column:
                    save_file = open(os.path.splitext(file_name)[0] + ".csv", "w")

                    x_values = self.plotted_ticket["bin_h_center"]
                    y_values = self.plotted_ticket["bin_v_center"]
                    z_values = self.plotted_ticket["histogram"]

                    for i in range(x_values.shape[0]):
                        for j in range(y_values.shape[0]):
                            if column == "x":   row = "0.0,"                              + str(x_values[i]) + ","  + str(y_values[j]) + "," + str(z_values[i, j])
                            elif column == "y": row = str(x_values[i])                    + ",0.0,"                 + str(y_values[j]) + "," + str(z_values[i, j])
                            elif column == "z": row = str(x_values[i]) + ","              + str(y_values[j])        + ",0.0,"                + str(z_values[i, j])

                            if i+j > 0: row = "\n" + row

                            save_file.write(row)

                    save_file.flush()
                    save_file.close()
            except Exception as exception:
                QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

                if self.IS_DEVELOP: raise exception

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

    def plot_xy(self, var_x, var_y):
        beam_to_plot = self.input_beam.duplicate()

        if ShadowCongruence.checkGoodBeam(beam_to_plot):
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
        else:
            # no good rays in the region of interest: creates a 0 power step with 1 good ray
            beam_to_plot._beam.rays[0, 9] = 1 # convert to good rays

            beam_to_plot._beam.rays[:, 6] = 0.0
            beam_to_plot._beam.rays[:, 7] = 0.0
            beam_to_plot._beam.rays[:, 8] = 0.0
            beam_to_plot._beam.rays[:, 15] = 0.0
            beam_to_plot._beam.rays[:, 16] = 0.0
            beam_to_plot._beam.rays[:, 17] = 0.0

        xrange, yrange = self.get_ranges()

        self.replace_fig(beam_to_plot, var_x, var_y,
                         xrange=xrange,
                         yrange=yrange,
                         nbins_h=int(self.number_of_bins),
                         nbins_v=int(self.number_of_bins_v),
                         nolost=self.rays+1)

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
        if not self.plotted_ticket is None:
            self.plot_results()

    def plot_results(self):
        try:
            sys.stdout = EmittingStream(textWritten=self.writeStdOut)

            if ShadowCongruence.checkEmptyBeam(self.input_beam):
                self.number_of_bins = congruence.checkStrictlyPositiveNumber(self.number_of_bins, "Number of Bins H")
                self.number_of_bins_v = congruence.checkStrictlyPositiveNumber(self.number_of_bins_v, "Number of Bins V")
                self.nbins_interpolation = congruence.checkStrictlyPositiveNumber(self.nbins_interpolation, "Number of Bins for energy interpolation")

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
            self.input_beam = input_beam.duplicate()

            if self.input_beam.scanned_variable_data and self.input_beam.scanned_variable_data.has_additional_parameter("is_footprint"):
                if self.input_beam.scanned_variable_data.get_additional_parameter("is_footprint"):
                    self.cb_rays.setEnabled(False)
                    self.rays = 0 # transmitted, absorbed doesn't make sense since is precalculated by footprint object
                else:
                    self.cb_rays.setEnabled(True)

            if ShadowCongruence.checkEmptyBeam(self.input_beam):
                if ShadowCongruence.checkGoodBeam(self.input_beam):
                    if not self.initial_flux is None:
                        self.plot_results()

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

    def writeStdOut(self, text):
        cursor = self.shadow_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.shadow_output.setTextCursor(cursor)
        self.shadow_output.ensureCursorVisible()

    def retrace_beam(self, new_shadow_beam, dist):
            new_shadow_beam._beam.retrace(dist)

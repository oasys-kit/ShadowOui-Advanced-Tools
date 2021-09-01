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

import os, sys, copy
import time
import numpy
import scipy.ndimage.filters as filters
import scipy.ndimage.interpolation as interpolation
import scipy.ndimage.fourier as fourier
from scipy.optimize import least_squares
from numpy.polynomial.polynomial import polyval2d

from PyQt5.QtWidgets import QMessageBox, QFileDialog, QInputDialog, QDialog, \
    QLabel, QVBoxLayout, QDialogButtonBox, QSizePolicy
from PyQt5.QtGui import QTextCursor, QPixmap, QFont, QColor, QPalette
from PyQt5.QtCore import Qt

import orangecanvas.resources as resources

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

import scipy.constants as codata

from matplotlib.colors import LinearSegmentedColormap, Normalize

cdict_temperature = {'red': ((0.0, 0.0, 0.0),
                             (0.5, 0.0, 0.0),
                             (0.75, 1.0, 1.0),
                             (1.0, 1.0, 1.0)),
                     'green': ((0.0, 0.0, 0.0),
                               (0.25, 1.0, 1.0),
                               (0.75, 1.0, 1.0),
                               (1.0, 0.0, 0.0)),
                     'blue': ((0.0, 1.0, 1.0),
                              (0.25, 1.0, 1.0),
                              (0.5, 0.0, 0.0),
                              (1.0, 0.0, 0.0))}

cmap_temperature = LinearSegmentedColormap('temperature', cdict_temperature, 256)

class PowerPlotXY(AutomaticElement):

    name = "Power Plot XY - Undulator"
    description = "Display Data Tools: Power Plot XY - Undulator"
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
    number_of_bins=Setting(100) # for retrocompatibility: I don't change the name
    number_of_bins_v=Setting(100)

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

    new_range_h_from = Setting(0.0)
    new_range_h_to   = Setting(0.0)
    new_range_v_from = Setting(0.0)
    new_range_v_to   = Setting(0.0)

    filter = Setting(3)
    filter_sigma_h = Setting(1.0)
    filter_sigma_v = Setting(1.0)
    filter_mode = Setting(0)
    filter_cval = Setting(0.0)
    filter_spline_order = Setting(2)
    scaling_factor = Setting(1.0)

    masking = Setting(0)
    masking_type = Setting(0)
    masking_level = Setting(1e-3)
    masking_width = Setting(0.0)
    masking_height = Setting(0.0)
    masking_diameter = Setting(0.0)

    fit_algorithm = Setting(0)
    show_fit_plot = Setting(1)

    gauss_c = 0.0
    gauss_A = 0.0
    gauss_x0 = 0.0
    gauss_y0 = 0.0
    gauss_fx = 0.0
    gauss_fy = 0.0
    gauss_chisquare = 0.0

    pv_c = 0.0
    pv_A = 0.0
    pv_x0 = 0.0
    pv_y0 = 0.0
    pv_fx = 0.0
    pv_fy = 0.0
    pv_mx = 0.0
    pv_my = 0.0
    pv_chisquare = 0.0

    poly_degree = Setting(4)
    poly_coefficients = []
    poly_chisquare = 0.0

    cumulated_ticket=None
    plotted_ticket   = None
    energy_min = None
    energy_max = None
    energy_step = None
    total_power = None
    current_step = None
    total_steps = None
    cumulated_total_power = None

    plotted_ticket_original = None

    view_type=Setting(1)

    cumulated_quantity = Setting(0)

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

        general_box = oasysgui.widgetBox(tab_set, "Variables Settings", addSpace=True, orientation="vertical", height=395)

        self.cb_cumulated_quantity = gui.comboBox(general_box, self, "cumulated_quantity", label="Cumulated Quantity", labelWidth=250,
                                    items=["Power Density [W/mm\u00b2]", "Intensity [ph/s/mm\u00b2]"],
                                    sendSelectedValue=False, orientation="horizontal")

        self.cb_rays = gui.comboBox(general_box, self, "rays", label="Rays", labelWidth=250,
                                    items=["Transmitted", "Absorbed (Lost)", "Absorbed (Still Good)"],
                                    sendSelectedValue=False, orientation="horizontal")

        gui.separator(general_box, height=10)

        self.x_column = gui.comboBox(general_box, self, "x_column_index", label="X Column", labelWidth=70,
                                     items=["1: X",
                                            "2: Y",
                                            "3: Z",
                                     ],
                                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(general_box, self, "x_range", label="X Range", labelWidth=250,
                                     items=["<Default>",
                                            "Set.."],
                                     callback=self.set_XRange, sendSelectedValue=False, orientation="horizontal")

        self.xrange_box = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=70)
        self.xrange_box_empty = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=70)

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

        self.yrange_box = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=70)
        self.yrange_box_empty = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=70)

        oasysgui.lineEdit(self.yrange_box, self, "y_range_min", "Y min", labelWidth=220, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.yrange_box, self, "y_range_max", "Y max", labelWidth=220, valueType=float, orientation="horizontal")

        self.set_YRange()

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

        histograms_box = oasysgui.widgetBox(tab_gen, "Histograms settings", addSpace=True, orientation="vertical", height=300)

        oasysgui.lineEdit(histograms_box, self, "number_of_bins", "Number of Bins H", labelWidth=250, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(histograms_box, self, "number_of_bins_v", "Number of Bins V", labelWidth=250, valueType=int, orientation="horizontal")

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

        # post processing

        gui.separator(tab_post)

        post_box_1 = oasysgui.widgetBox(tab_post, "", addSpace=False, orientation="horizontal", height=25)
        self.le_loaded_plot_file_name = oasysgui.lineEdit(post_box_1, self, "loaded_plot_file_name", "Loaded File", labelWidth=100,  valueType=str, orientation="horizontal")
        gui.button(post_box_1, self, "...", callback=self.selectPlotFile)

        tabs_post = oasysgui.tabWidget(tab_post)
        tabs_post.setFixedWidth(self.CONTROL_AREA_WIDTH-20)

        # graph tab
        tab_post_basic  = oasysgui.createTabPage(tabs_post, "Basic")
        tab_post_smooth = oasysgui.createTabPage(tabs_post, "Smoothing")
        tab_post_fit    = oasysgui.createTabPage(tabs_post, "Fit")

        post_box = oasysgui.widgetBox(tab_post_basic, "Basic Post Processing Setting", addSpace=False, orientation="vertical", height=460)

        button_box = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="vertical")
        button = gui.button(button_box, self, "Reset", callback=self.reloadPlot, height=25)

        font = QFont(button.font())
        font.setItalic(True)
        button.setFont(font)
        palette = QPalette(button.palette())
        palette.setColor(QPalette.ButtonText, QColor('dark red'))
        button.setPalette(palette)

        gui.separator(button_box, height=10)
        gui.button(button_box, self, "Invert", callback=self.invertPlot, height=25)
        gui.button(button_box, self, "Rescale Plot", callback=self.rescalePlot, height=25)

        oasysgui.lineEdit(post_box, self, "scaling_factor", "Scaling factor", labelWidth=250,  valueType=float, orientation="horizontal")

        button_box = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="horizontal")
        gui.button(button_box, self, "Rebin Plot", callback=self.rebinPlot, height=25)

        post_box_0 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="horizontal", height=25)
        oasysgui.lineEdit(post_box_0, self, "new_nbins_h", "Nr. Bins H x V", labelWidth=150,  valueType=int, orientation="horizontal")
        oasysgui.lineEdit(post_box_0, self, "new_nbins_v", "x", labelWidth=10,  valueType=int, orientation="horizontal")

        button_box = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="horizontal")
        gui.button(button_box, self, "Cut Plot", callback=self.cutPlot, height=25)
        post_box_0 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="horizontal", height=25)
        oasysgui.lineEdit(post_box_0, self, "new_range_h_from", "New Range H (from, to)", labelWidth=150,  valueType=float, orientation="horizontal")
        oasysgui.lineEdit(post_box_0, self, "new_range_h_to", "x", labelWidth=10,  valueType=float, orientation="horizontal")
        post_box_0 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="horizontal", height=25)
        oasysgui.lineEdit(post_box_0, self, "new_range_v_from", "New Range V (from, to)", labelWidth=150,  valueType=float, orientation="horizontal")
        oasysgui.lineEdit(post_box_0, self, "new_range_v_to", "x", labelWidth=10,  valueType=float, orientation="horizontal")

        gui.separator(post_box)

        button_box = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="horizontal")
        gui.button(button_box, self, "Mask", callback=self.maskPlot, height=25)

        gui.comboBox(post_box, self, "masking", label="Mask", labelWidth=200,
                     items=["Level", "Rectangular", "Circular"], sendSelectedValue=False, orientation="horizontal", callback=self.set_Masking)

        gui.comboBox(post_box, self, "masking_type", label="Mask Type", labelWidth=100,
                     items=["Aperture or < Level", "Obstruction or > Level"], sendSelectedValue=False, orientation="horizontal")

        self.mask_box_1 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="vertical", height=50)
        self.mask_box_2 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="vertical", height=50)
        self.mask_box_3 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="vertical", height=50)

        oasysgui.lineEdit(self.mask_box_1, self, "masking_level", "Mask Level (W/mm\u00B2)", labelWidth=250,  valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.mask_box_2, self, "masking_width", "Mask Width ", labelWidth=250,  valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.mask_box_2, self, "masking_height", "Mask Height", labelWidth=250,  valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.mask_box_3, self, "masking_diameter", "Mask Diameter ", labelWidth=250,  valueType=float, orientation="horizontal")

        self.set_Masking()

        post_box = oasysgui.widgetBox(tab_post_smooth, "Smoothing Setting", addSpace=False, orientation="vertical", height=220)

        button_box = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="horizontal")
        gui.button(button_box, self, "Smooth Plot", callback=self.smoothPlot, height=25)

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

        self.set_Filter()

        post_box = oasysgui.widgetBox(tab_post_fit, "Fit Setting", addSpace=False, orientation="vertical", height=460)

        gui.comboBox(post_box, self, "fit_algorithm", label="Fit Algorithm",
                     items=["Gaussian", "Pseudo-Voigt", "Polynomial"], labelWidth=200,
                     callback=self.set_FitAlgorithm, sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(post_box, self, "show_fit_plot", label="Show Fit Plot",
                     items=["No", "Yes"], labelWidth=260,
                     sendSelectedValue=False, orientation="horizontal")

        self.fit_box_1 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="vertical", height=340)
        self.fit_box_2 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="vertical", height=340)
        self.fit_box_3 = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="vertical", height=340)

        le_gauss_c  = oasysgui.lineEdit(self.fit_box_1, self, "gauss_c", "c [W/mm\u00b2]", labelWidth=200,  valueType=float, orientation="horizontal")
        le_gauss_A  = oasysgui.lineEdit(self.fit_box_1, self, "gauss_A", "A [W/mm\u00b2]", labelWidth=200,  valueType=float, orientation="horizontal")
        self.le_gauss_x0 = oasysgui.lineEdit(self.fit_box_1, self, "gauss_x0", "x0 ", labelWidth=200,  valueType=float, orientation="horizontal")
        self.le_gauss_y0 = oasysgui.lineEdit(self.fit_box_1, self, "gauss_y0", "y0 ", labelWidth=200,  valueType=float, orientation="horizontal")
        self.le_gauss_fx = oasysgui.lineEdit(self.fit_box_1, self, "gauss_fx", "fx ", labelWidth=200,  valueType=float, orientation="horizontal")
        self.le_gauss_fy = oasysgui.lineEdit(self.fit_box_1, self, "gauss_fy", "fy ", labelWidth=200,  valueType=float, orientation="horizontal")
        self.le_gauss_chisquare = oasysgui.lineEdit(self.fit_box_1, self, "gauss_chisquare", "\u03c7\u00b2 (RSS/\u03bd)", labelWidth=200,  valueType=float, orientation="horizontal")

        le_gauss_c.setReadOnly(True)
        le_gauss_A.setReadOnly(True)
        self.le_gauss_x0.setReadOnly(True)
        self.le_gauss_y0.setReadOnly(True)
        self.le_gauss_fx.setReadOnly(True)
        self.le_gauss_fy.setReadOnly(True)
        self.le_gauss_chisquare.setReadOnly(True)

        le_pv_c  = oasysgui.lineEdit(self.fit_box_2, self, "pv_c", "c [W/mm\u00b2]", labelWidth=200,  valueType=float, orientation="horizontal")
        le_pv_A  = oasysgui.lineEdit(self.fit_box_2, self, "pv_A", "A [W/mm\u00b2]", labelWidth=200,  valueType=float, orientation="horizontal")
        self.le_pv_x0 = oasysgui.lineEdit(self.fit_box_2, self, "pv_x0", "x0 ", labelWidth=200,  valueType=float, orientation="horizontal")
        self.le_pv_y0 = oasysgui.lineEdit(self.fit_box_2, self, "pv_y0", "y0 ", labelWidth=200,  valueType=float, orientation="horizontal")
        self.le_pv_fx = oasysgui.lineEdit(self.fit_box_2, self, "pv_fx", "fx ", labelWidth=200,  valueType=float, orientation="horizontal")
        self.le_pv_fy = oasysgui.lineEdit(self.fit_box_2, self, "pv_fy", "fy ", labelWidth=200,  valueType=float, orientation="horizontal")
        le_pv_mx = oasysgui.lineEdit(self.fit_box_2, self, "pv_mx", "mx", labelWidth=200,  valueType=float, orientation="horizontal")
        le_pv_my = oasysgui.lineEdit(self.fit_box_2, self, "pv_my", "my", labelWidth=200,  valueType=float, orientation="horizontal")
        self.le_pv_chisquare = oasysgui.lineEdit(self.fit_box_2, self, "pv_chisquare", "\u03c7\u00b2 (RSS/\u03bd)", labelWidth=200,  valueType=float, orientation="horizontal")

        le_pv_c.setReadOnly(True)
        le_pv_A.setReadOnly(True)
        self.le_pv_x0.setReadOnly(True)
        self.le_pv_y0.setReadOnly(True)
        self.le_pv_fx.setReadOnly(True)
        self.le_pv_fy.setReadOnly(True)
        le_pv_mx.setReadOnly(True)
        le_pv_my.setReadOnly(True)
        self.le_pv_chisquare.setReadOnly(True)

        oasysgui.lineEdit(self.fit_box_3, self, "poly_degree", "Degree", labelWidth=260, valueType=int, orientation="horizontal")
        oasysgui.widgetLabel(self.fit_box_3, "Polynomial Coefficients")

        text_box = oasysgui.widgetBox(self.fit_box_3, "", addSpace=False, orientation="vertical", height=205)

        self.poly_coefficients_text = oasysgui.textArea(205, 350, readOnly=True)
        text_box.layout().addWidget(self.poly_coefficients_text)
        self.le_poly_chisquare = oasysgui.lineEdit(self.fit_box_3, self, "poly_chisquare", "\u03c7\u00b2 (RSS/\u03bd)", labelWidth=200,  valueType=float, orientation="horizontal")

        self.le_poly_chisquare.setReadOnly(True)

        button_box = oasysgui.widgetBox(post_box, "", addSpace=False, orientation="horizontal")
        gui.button(button_box, self, "Do Fit", callback=self.doFit, height=25)
        button = gui.button(button_box, self, "Show Fit Formulas", callback=self.showFitFormulas, height=25)

        font = QFont(button.font())
        font.setItalic(True)
        button.setFont(font)
        palette = QPalette(button.palette())
        palette.setColor(QPalette.ButtonText, QColor('dark blue'))
        button.setPalette(palette)

        self.set_FitAlgorithm()

        #######################################################
        # MAIN TAB

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

    def set_Masking(self):
        self.mask_box_1.setVisible(self.masking==0)
        self.mask_box_2.setVisible(self.masking==1)
        self.mask_box_3.setVisible(self.masking==2)

    def set_FilterMode(self):
        self.le_filter_cval.setEnabled(self.filter_mode==1)

    def set_FitAlgorithm(self):
        self.fit_box_1.setVisible(self.fit_algorithm==0)
        self.fit_box_2.setVisible(self.fit_algorithm==1)
        self.fit_box_3.setVisible(self.fit_algorithm==2)

    def selectAutosaveFile(self):
        file_name = oasysgui.selectSaveFileFromDialog(self, "Select File", default_file_name="", file_extension_filter="HDF5 Files (*.hdf5 *.h5 *.hdf)")
        self.le_autosave_file_name.setText("" if file_name is None else file_name)

    def after_change_workspace_units(self):
        label = self.le_gauss_x0.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_gauss_y0.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_gauss_fx.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_gauss_fy.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_pv_x0.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_pv_y0.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_pv_fx.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_pv_fy.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")

    #########################################################
    # I/O

    def setBeam(self, input_beam):
        self.cb_rays.setEnabled(True)

        if not input_beam is None:
            if not input_beam.scanned_variable_data is None and input_beam.scanned_variable_data.has_additional_parameter("total_power"):
                self.input_beam = input_beam

                self.current_step = self.input_beam.scanned_variable_data.get_additional_parameter("current_step")
                self.total_steps = self.input_beam.scanned_variable_data.get_additional_parameter("total_steps")
                self.energy_step = self.input_beam.scanned_variable_data.get_additional_parameter("photon_energy_step")

                self.total_power = self.input_beam.scanned_variable_data.get_additional_parameter("total_power")

                if self.cumulated_quantity == 1: # Intensity
                    self.total_power /= (1e3 * self.energy_step * codata.e) # to ph/s

                self.energy_max  = self.input_beam.scanned_variable_data.get_scanned_variable_value()

                if self.energy_min is None:
                    self.energy_min  = self.input_beam.scanned_variable_data.get_scanned_variable_value()
                    self.cumulated_total_power = self.total_power
                else:
                    self.cumulated_total_power += self.total_power

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

    def plot_xy(self, var_x, var_y):
        beam_to_plot = self.input_beam

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

                new_shadow_beam._beam.retrace(dist)

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
        if not self.cumulated_ticket is None:
            self.plot_canvas.plot_power_density_ticket(ticket=self.cumulated_ticket,
                                                       var_x=self.x_column_index+1,
                                                       var_y=self.y_column_index+1,
                                                       cumulated_total_power=self.cumulated_total_power,
                                                       energy_min=self.energy_min,
                                                       energy_max=self.energy_max,
                                                       energy_step=self.energy_step,
                                                       show_image=self.view_type==1,
                                                       cumulated_quantity=self.cumulated_quantity)

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

    ##################################################
    # SAVE

    def save_cumulated_data(self):
        file_name = oasysgui.selectSaveFileFromDialog(self, "Save Current Plot", default_file_name=("" if self.autosave==0 else self.autosave_file_name),
                                                      file_extension_filter="HDF5 Files (*.hdf5 *.h5 *.hdf);;Text Files (*.dat *.txt);;Ansys Files (*.csv)")

        if not file_name is None and not file_name.strip()=="":
            format, ok = QInputDialog.getItem(self, "Select Output Format", "Formats: ", ("Hdf5", "Text", "Ansys", "Image", "Hdf5 & Image", "All"), 4, False)

            if ok and format:
                if format == "Hdf5" or format == "All":  self.save_cumulated_data_hdf5(file_name)
                if format == "Text" or format == "All":  self.save_cumulated_data_txt(file_name)
                if format == "Ansys" or format == "All": self.save_cumulated_data_ansys(file_name)
                if format == "Image" or format == "All": self.save_cumulated_data_image(file_name)
                if format == "Hdf5 & Image":
                    self.save_cumulated_data_hdf5(file_name)
                    self.save_cumulated_data_image(file_name)

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

    def save_cumulated_data_image(self, file_name):
        if not self.plotted_ticket is None:
            try:
                def duplicate(obj):
                    import io, pickle
                    buf = io.BytesIO()
                    pickle.dump(obj, buf)
                    buf.seek(0)
                    return pickle.load(buf)

                fig = duplicate(self.plot_canvas.plot_canvas._backend.fig)

                vmin = numpy.min(self.plotted_ticket["histogram"])
                vmax = numpy.max(self.plotted_ticket["histogram"])

                cbar = fig.colorbar(cm.ScalarMappable(norm=Normalize(vmin=vmin, vmax=vmax), cmap=cmap_temperature), ax=fig.gca())
                cbar.ax.set_ylabel('Power Density [W/mm\u00b2]')
                ticks = cbar.get_ticks()
                cbar.set_ticks([vmax] + list(ticks))

                def format_number(number):
                    order_of_magnitude = (1 if number >= 1 else -1) * int(numpy.floor(numpy.log10(numpy.abs(number))))

                    if order_of_magnitude > 3:
                        return round(number, 1)
                    elif order_of_magnitude >= 0:
                        return round(number, 4 - order_of_magnitude)
                    else:
                        return round(number, 3 + abs(order_of_magnitude))

                cbar.set_ticklabels([str(format_number(vmax))] + ["{:.1e}".format(t) for t in ticks])

                fig.savefig(os.path.splitext(file_name)[0] + ".png")

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

    ##################################################
    # POST EDITING

    def selectPlotFile(self):
        file_name = oasysgui.selectFileFromDialog(self, None, "Select File", file_extension_filter="HDF5 Files (*.hdf5 *.h5 *.hdf)")

        if not file_name is None:
            self.le_loaded_plot_file_name.setText(os.path.basename(os.path.normpath(file_name)))

            plot_file = ShadowPlot.PlotXYHdf5File(congruence.checkDir(file_name), mode="r")

            ticket = {}

            ticket["histogram"], ticket["histogram_h"], ticket["histogram_v"], attributes = plot_file.get_last_plot(dataset_name="power_density")
            ticket["bin_h_center"], ticket["bin_v_center"], ticket["h_label"], ticket["v_label"] = plot_file.get_coordinates()
            ticket["intensity"] = attributes["intensity"]
            ticket["nrays"] = attributes["total_rays"]
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

                            if QMessageBox.question(self, "Load Plot", "Average with current Plot?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
                                ticket["histogram"] *= 0.5
                        else:
                            raise ValueError("The plots cannot be merged: the should have same dimensions and ranges")

            try:
                last_plotted_power = plot_file.get_attribute("last_plotted_power", dataset_name="additional_data")
                last_incident_power = plot_file.get_attribute("last_incident_power", dataset_name="additional_data")
                last_total_power = plot_file.get_attribute("last_total_power", dataset_name="additional_data")
                energy_min = plot_file.get_attribute("last_energy_min", dataset_name="additional_data")
                energy_max = plot_file.get_attribute("last_energy_max", dataset_name="additional_data")
                energy_step = plot_file.get_attribute("last_energy_step", dataset_name="additional_data")
            except:
                last_plotted_power = numpy.sum(ticket["histogram"]) * (ticket["bin_h_center"][1] - ticket["bin_h_center"][0]) * (ticket["bin_v_center"][1] - ticket["bin_v_center"][0])
                last_incident_power = 0.0
                last_total_power = 0.0
                energy_min = 0.0
                energy_max = 0.0
                energy_step = 0.0

            try:
                self.plot_canvas.cumulated_power_plot = last_plotted_power
                self.plot_canvas.cumulated_previous_power_plot = last_incident_power
                self.plot_canvas.plot_power_density_ticket(ticket,
                                                           ticket["h_label"],
                                                           ticket["v_label"],
                                                           cumulated_total_power=last_total_power,
                                                           energy_min=energy_min,
                                                           energy_max=energy_max,
                                                           energy_step=energy_step,
                                                           cumulated_quantity=self.cumulated_quantity)

                self.cumulated_ticket = ticket
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

            cumulated_power_plot = numpy.sum(ticket["histogram"]) * (ticket["bin_h_center"][1] - ticket["bin_h_center"][0]) * (ticket["bin_v_center"][1] - ticket["bin_v_center"][0])

            try:
                try:
                    energy_min = ticket["energy_min"]
                    energy_max = ticket["energy_max"]
                    energy_step = ticket["energy_step"]
                except:
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
                                                           energy_step=energy_step,
                                                           cumulated_quantity=self.cumulated_quantity)

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

                h_coord, v_coord, histogram = invert(h_coord, v_coord, histogram)

                ticket["histogram"] = histogram
                ticket["bin_h_center"] = h_coord
                ticket["bin_v_center"] = v_coord

                pixel_area = (h_coord[1] - h_coord[0]) * (v_coord[1] - v_coord[0])

                if self.plot_canvas is None:
                    self.plot_canvas = PowerPlotXYWidget()
                    self.image_box.layout().addWidget(self.plot_canvas)

                cumulated_power_plot = numpy.sum(histogram) * pixel_area

                try:
                    energy_min = ticket["energy_min"]
                    energy_max = ticket["energy_max"]
                    energy_step = ticket["energy_step"]
                except:
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
                                                           energy_step=energy_step,
                                                           cumulated_quantity=self.cumulated_quantity)

                self.plotted_ticket = ticket
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e

    def rescalePlot(self):
        if not self.plotted_ticket is None:
            try:
                congruence.checkStrictlyPositiveNumber(self.scaling_factor, "Scaling Factor")

                ticket = self.plotted_ticket.copy()

                histogram = ticket["histogram"] * self.scaling_factor
                h_coord = ticket["bin_h_center"]
                v_coord = ticket["bin_v_center"]

                pixel_area = (h_coord[1] - h_coord[0]) * (v_coord[1] - v_coord[0])

                ticket["histogram"] = histogram

                if self.plot_canvas is None:
                    self.plot_canvas = PowerPlotXYWidget()
                    self.image_box.layout().addWidget(self.plot_canvas)

                cumulated_power_plot = numpy.sum(histogram) * pixel_area

                try:
                    energy_min = ticket["energy_min"]
                    energy_max = ticket["energy_max"]
                    energy_step = ticket["energy_step"]
                except:
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
                                                           energy_step=energy_step,
                                                           cumulated_quantity=self.cumulated_quantity)

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

                pixel_area_original = (h_coord[1] - h_coord[0]) * (v_coord[1] - v_coord[0])
                integral_original   = numpy.sum(histogram)

                h_coord, v_coord, histogram = rebin(h_coord, v_coord, histogram, (int(self.new_nbins_h), int(self.new_nbins_v)))

                pixel_area_rebin = (h_coord[1] - h_coord[0]) * (v_coord[1] - v_coord[0])

                if self.plot_canvas is None:
                    self.plot_canvas = PowerPlotXYWidget()
                    self.image_box.layout().addWidget(self.plot_canvas)

                integral_rebin = numpy.sum(histogram)

                histogram *= (integral_original * pixel_area_original) / (integral_rebin * pixel_area_rebin) # rinormalization

                cumulated_power_plot = numpy.sum(histogram) * pixel_area_rebin

                ticket["histogram"] = histogram
                ticket["bin_h_center"] = h_coord
                ticket["bin_v_center"] = v_coord

                try:
                    energy_min = ticket["energy_min"]
                    energy_max = ticket["energy_max"]
                    energy_step = ticket["energy_step"]
                except:
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
                                                           energy_step=energy_step,
                                                           cumulated_quantity=self.cumulated_quantity)

                self.plotted_ticket = ticket
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e

    def cutPlot(self):
        if not self.plotted_ticket is None:
            try:
                congruence.checkLessThan(self.new_range_h_from, self.new_range_h_to, "New Range H from", "New Range H to")
                congruence.checkLessThan(self.new_range_v_from, self.new_range_v_to, "New Range V from", "New Range V to")

                ticket = self.plotted_ticket.copy()

                histogram = ticket["histogram"]
                h_coord = ticket["bin_h_center"]
                v_coord = ticket["bin_v_center"]

                congruence.checkGreaterOrEqualThan(self.new_range_h_from, h_coord[0], "New Range H from", "Original Min(H)")
                congruence.checkLessOrEqualThan(self.new_range_h_to, h_coord[-1], "New Range H to", "Original Max(H)")
                congruence.checkGreaterOrEqualThan(self.new_range_v_from, v_coord[0], "New Range V from", "Original Min(V)")
                congruence.checkLessOrEqualThan(self.new_range_v_to, v_coord[-1], "New Range V to", "Original Max(V)")

                h_coord, v_coord, histogram = cut(h_coord, v_coord, histogram,
                                                  range_x=[self.new_range_h_from, self.new_range_h_to],
                                                  range_y=[self.new_range_v_from, self.new_range_v_to])

                ticket["histogram"] = histogram
                ticket["bin_h_center"] = h_coord
                ticket["bin_v_center"] = v_coord

                pixel_area = (h_coord[1] - h_coord[0]) * (v_coord[1] - v_coord[0])

                if self.plot_canvas is None:
                    self.plot_canvas = PowerPlotXYWidget()
                    self.image_box.layout().addWidget(self.plot_canvas)

                cumulated_power_plot = numpy.sum(histogram) * pixel_area

                try:
                    energy_min = ticket["energy_min"]
                    energy_max = ticket["energy_max"]
                    energy_step = ticket["energy_step"]
                except:
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
                                                           energy_step=energy_step,
                                                           cumulated_quantity=self.cumulated_quantity)

                self.plotted_ticket = ticket
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e

    def maskPlot(self):
        if not self.plotted_ticket is None:
            try:
                if self.masking == 0:
                    congruence.checkPositiveNumber(self.masking_level, "Masking Level")
                if self.masking == 1:
                    congruence.checkPositiveNumber(self.masking_width, "Masking Width")
                    congruence.checkPositiveNumber(self.masking_height, "Masking height")
                if self.masking == 2:
                    congruence.checkPositiveNumber(self.masking_diameter, "Masking Radius")

                ticket = copy.deepcopy(self.plotted_ticket)

                histogram = ticket["histogram"]
                h_coord = ticket["bin_h_center"]
                v_coord = ticket["bin_v_center"]

                if self.masking == 0:
                    if self.masking_type == 0:
                        mask = numpy.where(histogram <= self.masking_level)
                    else:
                        mask = numpy.where(histogram >= self.masking_level)
                    histogram[mask] = 0.0
                elif self.masking == 1:
                    if self.masking_type == 0:
                        mask_h = numpy.where(numpy.logical_or(h_coord < -self.masking_width / 2, h_coord > self.masking_width / 2))
                        mask_v = numpy.where(numpy.logical_or(v_coord < -self.masking_height / 2, v_coord > self.masking_height / 2))

                        histogram[mask_h, :] = 0.0
                        histogram[:, mask_v] = 0.0
                    else:
                        mask_h = numpy.where(numpy.logical_and(h_coord >= -self.masking_width / 2, h_coord <= self.masking_width / 2))
                        mask_v = numpy.where(numpy.logical_and(v_coord >= -self.masking_height / 2, v_coord <= self.masking_height / 2))

                        histogram[numpy.meshgrid(mask_h, mask_v)] = 0.0
                elif self.masking == 2:
                    h, v = numpy.meshgrid(h_coord, v_coord)
                    r = numpy.sqrt(h ** 2 + v ** 2)

                    if self.masking_type == 0:
                        mask = r > self.masking_diameter * 0.5
                    else:
                        mask = r <= self.masking_diameter * 0.5

                    histogram[mask] = 0.0

                pixel_area = (h_coord[1] - h_coord[0]) * (v_coord[1] - v_coord[0])

                ticket["histogram"] = histogram

                if self.plot_canvas is None:
                    self.plot_canvas = PowerPlotXYWidget()
                    self.image_box.layout().addWidget(self.plot_canvas)

                cumulated_power_plot = numpy.sum(ticket["histogram"]) * pixel_area

                try:
                    energy_min = ticket["energy_min"]
                    energy_max = ticket["energy_max"]
                    energy_step = ticket["energy_step"]
                except:
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
                                                           energy_step=energy_step,
                                                           cumulated_quantity=self.cumulated_quantity)

                self.plotted_ticket = ticket
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e

    def smoothPlot(self):
        if not self.plotted_ticket is None:
            try:
                if self.filter == 0 or 2 <= self.filter <= 5:
                    congruence.checkStrictlyPositiveNumber(self.filter_sigma_h, "Sigma/Size H")
                    congruence.checkStrictlyPositiveNumber(self.filter_sigma_v, "Sigma/Size V")

                if self.filter == 1: congruence.checkStrictlyPositiveNumber(self.filter_spline_order, "Spline Order")

                ticket = self.plotted_ticket.copy()

                histogram = ticket["histogram"]
                h_coord = ticket["bin_h_center"]
                v_coord = ticket["bin_v_center"]

                norm = histogram.sum()

                pixel_area = (h_coord[1] - h_coord[0]) * (v_coord[1] - v_coord[0])

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

                norm /= histogram.sum()

                ticket["histogram"] = histogram * norm

                if self.plot_canvas is None:
                    self.plot_canvas = PowerPlotXYWidget()
                    self.image_box.layout().addWidget(self.plot_canvas)

                cumulated_power_plot = numpy.sum(ticket["histogram"]) * pixel_area

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
                                                           energy_step=energy_step,
                                                           cumulated_quantity=self.cumulated_quantity)

                self.plotted_ticket = ticket
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e

    def showFitFormulas(self):
        dialog = ShowFitFormulasDialog(parent=self)
        dialog.show()

    def doFit(self):
        if not self.plotted_ticket is None:
            try:
                ticket = self.plotted_ticket.copy()

                # NB, matplotlib inverts....
                histogram = ticket["histogram"].T
                h_coord = ticket["bin_h_center"]
                v_coord = ticket["bin_v_center"]

                def chisquare(pd, pd_fit, n):
                    N = pd.shape[0]*pd.shape[1]
                    squared_deviations = (pd-pd_fit)**2

                    return squared_deviations.sum()/(N-n)

                show = self.show_fit_plot == 1

                if self.fit_algorithm == 0:
                    pd_fit_g, params_g = get_fitted_data_gaussian(h_coord, v_coord, histogram)

                    self.gauss_c =  round(params_g[0], 4)
                    self.gauss_A =  round(params_g[1], 4)
                    self.gauss_x0 = round(params_g[2], 4)
                    self.gauss_y0 = round(params_g[3], 4)
                    self.gauss_fx = round(params_g[4], 6)
                    self.gauss_fy = round(params_g[5], 6)
                    self.gauss_chisquare = round(chisquare(histogram, pd_fit_g, 6), 4)

                    params_string = '\n'.join((
                        r'$c=%.4f$' %   (self.gauss_c,),
                        r'$A=%.4f$' %   (self.gauss_A,),
                        r'$x_0=%.4f$' % (self.gauss_x0,),
                        r'$y_0=%.4f$' % (self.gauss_y0,),
                        r'$f_x=%.6f$' % (self.gauss_fx,),
                        r'$f_y=%.6f$' % (self.gauss_fy,),
                    ))

                    if show: self.plot_fit(h_coord, v_coord, histogram, pd_fit_g, "Gaussian", self.gauss_chisquare, params_string)

                elif self.fit_algorithm == 1:
                    pd_fit_pv, params_pv = get_fitted_data_pv(h_coord, v_coord, histogram)

                    self.pv_c =  round(params_pv[0], 4)
                    self.pv_A =  round(params_pv[1], 4)
                    self.pv_x0 = round(params_pv[2], 4)
                    self.pv_y0 = round(params_pv[3], 4)
                    self.pv_fx = round(params_pv[4], 6)
                    self.pv_fy = round(params_pv[5], 6)
                    self.pv_mx = round(params_pv[6], 4)
                    self.pv_my = round(params_pv[7], 4)
                    self.pv_chisquare = round(chisquare(histogram, pd_fit_pv, 8), 4)

                    params_string = '\n'.join((
                        r'$c=%.4f$' %   (self.pv_c,),
                        r'$A=%.4f$' %   (self.pv_A,),
                        r'$x_0=%.4f$' % (self.pv_x0,),
                        r'$y_0=%.4f$' % (self.pv_y0,),
                        r'$f_x=%.6f$' % (self.pv_fx,),
                        r'$f_y=%.6f$' % (self.pv_fy,),
                        r'$m_x=%.4f$' % (self.pv_mx,),
                        r'$m_y=%.4f$' % (self.pv_my,),
                    ))

                    if show: self.plot_fit(h_coord, v_coord, histogram, pd_fit_pv, "Pseudo-Voigt", self.pv_chisquare, params_string)

                elif self.fit_algorithm == 2:
                    congruence.checkStrictlyPositiveNumber(self.poly_degree, "Degree")

                    pd_fit_poly, params_poly = get_fitted_data_poly(h_coord, v_coord, histogram, self.poly_degree)

                    params_poly = numpy.reshape(params_poly, (self.poly_degree + 1, self.poly_degree + 1))
                    params_string     = []
                    params_string_mpl = []
                    for i in range(params_poly.shape[0]):
                        for j in range(params_poly.shape[1]):
                            param = params_poly[i, j]
                            params_string.append(r'c%d,%d=%.4f$' %   (i, j, param,))
                            params_string_mpl.append(r'$c_{%d,%d}=%.4f$' %   (i, j, param,))

                    params_string = '\n'.join(params_string)
                    params_string_mpl = '\n'.join(params_string_mpl)

                    self.poly_coefficients_text.setText(params_string)
                    self.poly_chisquare = round(chisquare(histogram, pd_fit_poly, len(params_poly)), 4)

                    if show: self.plot_fit(h_coord, v_coord, histogram, pd_fit_poly, "Polynomial", self.poly_chisquare, params_string_mpl, fontsize=10)

            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e

    def plot_fit(self, xx, yy, pd, pd_fit, algorithm, chisquare, params, fontsize=14):
        dialog = ShowFitResultDialog(xx, yy, pd, pd_fit, algorithm, chisquare, params,
                                     file_name=None if self.autosave==0 else self.autosave_file_name,
                                     fontsize=fontsize,
                                     parent=self)
        dialog.show()

    def load_partial_results(self):
        file_name = None if self.autosave==0 else self.autosave_file_name

        if not file_name is None:
            plot_file = ShadowPlot.PlotXYHdf5File(congruence.checkDir(file_name), mode="r")

            ticket = {}

            ticket["histogram"], ticket["histogram_h"], ticket["histogram_v"], attributes = plot_file.get_last_plot(dataset_name="power_density")
            ticket["bin_h_center"], ticket["bin_v_center"], ticket["h_label"], ticket["v_label"] = plot_file.get_coordinates()
            ticket["intensity"] = attributes["intensity"]
            ticket["nrays"] = attributes["total_rays"]
            ticket["good_rays"] = attributes["good_rays"]

            if self.plot_canvas is None:
                self.plot_canvas = PowerPlotXYWidget()
                self.image_box.layout().addWidget(self.plot_canvas)

            try:
                last_plotted_power = plot_file.get_attribute("last_plotted_power", dataset_name="additional_data")
                last_incident_power = plot_file.get_attribute("last_incident_power", dataset_name="additional_data")
                last_total_power = plot_file.get_attribute("last_total_power", dataset_name="additional_data")
                energy_min = plot_file.get_attribute("last_energy_min", dataset_name="additional_data")
                energy_max = plot_file.get_attribute("last_energy_max", dataset_name="additional_data")
                energy_step = plot_file.get_attribute("last_energy_step", dataset_name="additional_data")
            except:
                last_plotted_power = numpy.sum(ticket["histogram"]) * (ticket["bin_h_center"][1] - ticket["bin_h_center"][0]) * (ticket["bin_v_center"][1] - ticket["bin_v_center"][0])
                last_incident_power = 0.0
                last_total_power = 0.0
                energy_min = 0.0
                energy_max = 0.0
                energy_step = 0.0

            try:
                self.plot_canvas.cumulated_power_plot = last_plotted_power
                self.plot_canvas.cumulated_previous_power_plot = last_incident_power
                self.plot_canvas.plot_power_density_ticket(ticket,
                                                           ticket["h_label"],
                                                           ticket["v_label"],
                                                           cumulated_total_power=last_total_power,
                                                           energy_min=energy_min,
                                                           energy_max=energy_max,
                                                           energy_step=energy_step,
                                                           cumulated_quantity=self.cumulated_quantity)

                self.cumulated_ticket = ticket
                self.plotted_ticket = ticket
                self.plotted_ticket_original = ticket.copy()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e


#################################################
# UTILITIES

def rebin(x, y, z, new_shape):
    shape = (new_shape[0], z.shape[0] // new_shape[0], new_shape[1], z.shape[1] // new_shape[1])

    return numpy.linspace(x[0], x[-1], new_shape[0]), \
           numpy.linspace(y[0], y[-1], new_shape[1]), \
           z.reshape(shape).mean(-1).mean(1)

def invert(x, y, data):
    return y, x, data.T

def cut(x, y, data, range_x, range_y):
    zoom_x = numpy.where(numpy.logical_and(x >= range_x[0], x <= range_x[1]))
    zoom_y = numpy.where(numpy.logical_and(y >= range_y[0], y <= range_y[1]))

    return x[zoom_x], y[zoom_y], data[numpy.meshgrid(zoom_x, zoom_y)].T

def apply_fill_holes(histogram):
    from skimage.morphology import reconstruction

    seed = numpy.copy(histogram)
    seed[1:-1, 1:-1] = histogram.max()

    filled = reconstruction(seed=seed, mask=histogram, method='erosion')

    return filled * (histogram.sum() / filled.sum())

####################################################
# FIT FUNCTIONS

def gaussian(c, height, center_x, center_y, fwhm_x, fwhm_y):
    sigma_x = float(fwhm_x/2.355)
    sigma_y = float(fwhm_y/2.355)

    return lambda x, y: c + height * numpy.exp(-((0.5*((x-center_x)/sigma_x)**2) + (0.5*((y-center_y)/sigma_y)**2)))

def pseudovoigt(c, height, center_x, center_y, fwhm_x, fwhm_y, mixing_x, mixing_y):
    sigma_x = fwhm_x/2.355
    gamma_x = fwhm_x/2
    sigma_y = fwhm_y/2.355
    gamma_y = fwhm_y/2

    def pv(x, center, sigma, gamma, mixing):
        return mixing*numpy.exp(-0.5*(x-center)**2/(sigma**2)) + (1-mixing)*((gamma**2)/((x-center)**2 + gamma**2))

    return lambda x, y: c + height*pv(x, center_x, sigma_x, gamma_x, mixing_x)*pv(y, center_y, sigma_y, gamma_y, mixing_y)

def polynomial(coefficients):
    size = int(numpy.sqrt(len(coefficients)))
    coefficients = numpy.array(coefficients).reshape((size,size))

    return lambda x, y: polyval2d(x, y, coefficients)

from oasys.util.oasys_util import get_sigma, get_average

# Returns (x, y, width_x, width_y) the gaussian parameters of a 2D distribution by calculating its moments
def guess_params_gaussian(xx, yy, data):
    h_histo = data.sum(axis=0)
    v_histo = data.sum(axis=1)
    center_x = get_average(h_histo, xx)
    center_y = get_average(v_histo, yy)
    sigma_x = get_sigma(h_histo, xx)
    sigma_y = get_sigma(v_histo, yy)

    return 0.001, data.max(), center_x, center_y, sigma_x*2.355, sigma_y*2.355

def guess_params_pv(xx, yy, data):
    c, height, center_x, center_y, fwhm_x, fwhm_y = guess_params_gaussian(xx, yy, data)

    return c, height, center_x, center_y, fwhm_x, fwhm_y, 0.5, 0.5

def guess_params_poly(degree):
    return numpy.ones(int(degree + 1)**2).tolist()

def fit_gaussian(xx, yy, pd, guess_params=None):
    error_function = lambda p: numpy.ravel(gaussian(*p)(*numpy.meshgrid(xx, yy)) - pd)

    bounds = [[0,          0,         -numpy.inf, -numpy.inf, 0,         0],
              [numpy.inf,  numpy.inf,  numpy.inf,  numpy.inf, numpy.inf, numpy.inf]]

    optimized_result = least_squares(fun=error_function,
                                     x0=guess_params_gaussian(xx, yy, pd) if guess_params is None else guess_params,
                                     bounds=bounds)

    return optimized_result.x

def fit_pseudovoigt(xx, yy, pd, guess_params=None):
    error_function = lambda p: numpy.ravel(pseudovoigt(*p)(*numpy.meshgrid(xx, yy)) - pd)

    bounds = [[0,         0,        -numpy.inf, -numpy.inf, 0,         0,         0, 0],
              [numpy.inf, numpy.inf, numpy.inf,  numpy.inf, numpy.inf, numpy.inf, 1, 1]]

    optimized_result = least_squares(fun=error_function,
                                     x0=guess_params_pv(xx, yy, pd) if guess_params is None else guess_params,
                                     bounds=bounds)

    return optimized_result.x

def fit_polynomial(xx, yy, pd, degree=4, guess_params=None):
    error_function = lambda p: numpy.ravel(polynomial(p)(*numpy.meshgrid(xx, yy)) - pd)

    bounds = [numpy.full(int(degree + 1)**2, -numpy.inf).tolist(),
              numpy.full(int(degree + 1)**2, numpy.inf).tolist()]
    bounds[0][0] = 0.0

    optimized_result = least_squares(fun=error_function,
                                     x0=guess_params_poly(degree) if guess_params is None else guess_params,
                                     bounds=bounds)

    return optimized_result.x

def get_fitted_data_gaussian(xx, yy, pd, guess_params=None):
    params = fit_gaussian(xx, yy, pd, guess_params)
    fit = gaussian(*params)

    return fit(*numpy.meshgrid(xx, yy)), params

def get_fitted_data_pv(xx, yy, pd, guess_params=None):
    params = fit_pseudovoigt(xx, yy, pd, guess_params)
    fit = pseudovoigt(*params)

    return fit(*numpy.meshgrid(xx, yy)), params

def get_fitted_data_poly(xx, yy, pd, degree=4, guess_params=None):
    params = fit_polynomial(xx, yy, pd, degree, guess_params)
    fit = polynomial(params)

    return fit(*numpy.meshgrid(xx, yy)), params


class ShowFitFormulasDialog(QDialog):

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle('Fit Formulas')
        layout = QVBoxLayout(self)

        formulas_path = os.path.join(resources.package_dirname("orangecontrib.shadow_advanced_tools.widgets.thermal"), "misc", "fit_formulas.png")

        label = QLabel("")
        label.setAlignment(Qt.AlignCenter)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label.setPixmap(QPixmap(formulas_path))

        bbox = QDialogButtonBox(QDialogButtonBox.Ok)

        bbox.accepted.connect(self.accept)
        layout.addWidget(label)
        layout.addWidget(bbox)

from matplotlib import cm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from matplotlib import gridspec


class ShowFitResultDialog(QDialog):

    def __init__(self, xx, yy, pd, pd_fit, algorithm, chisquare, params_string, file_name=None, fontsize=14, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle('Fit Result')
        layout = QVBoxLayout(self)

        self.file_name = None if file_name is None else congruence.checkDir(os.path.splitext(file_name)[0] + "_fit.png")

        figure = Figure(figsize=(4, 8))
        figure.patch.set_facecolor('white')

        gs = gridspec.GridSpec(1, 2, width_ratios=[1, 3])
        ax = [None, None]
        ax[0] = figure.add_subplot(gs[0])
        ax[1] = figure.add_subplot(gs[1], projection='3d')

        ax[0].axis('off')
        ax[0].set_title("Fit Parameters")
        ax[0].text(-0.2, 0.95, params_string,
                   transform=ax[0].transAxes,
                   fontsize=fontsize,
                   verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        x_to_plot, y_to_plot = numpy.meshgrid(xx, yy)

        ax[1].plot_surface(x_to_plot, y_to_plot, pd,
                        rstride=1, cstride=1, cmap=cm.coolwarm, linewidth=0.5, antialiased=True, alpha=0.25)

        ax[1].plot_surface(x_to_plot, y_to_plot, pd_fit,
                        rstride=1, cstride=1, cmap=cm.Blues, linewidth=0.5, antialiased=True, alpha=0.75)

        ax[1].set_title(algorithm + " Fit\n\u03c7\u00b2 (RSS/\u03bd): " + str(chisquare))
        ax[1].set_xlabel("H [mm]")
        ax[1].set_ylabel("V [mm]")
        ax[1].set_zlabel("Power Density [W/mm\u00b2]")
        ax[1].axes.mouse_init()

        figure_canvas = FigureCanvasQTAgg(figure)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.rejected.connect(self.reject)

        layout.addWidget(figure_canvas)
        layout.addWidget(self.buttonBox)

        self.figure = figure

    def save(self):
        file_name = oasysgui.selectSaveFileFromDialog(self, "Select File", default_file_name=("" if self.file_name is None else self.file_name), file_extension_filter="PNG Files (*.png)")

        if not file_name is None and not file_name.strip() == "":
            try:
                self.figure.savefig(file_name)
                QMessageBox.information(self, "Save", "Fit plot saved on file " + file_name, QMessageBox.Ok)
            except Exception as e: QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)


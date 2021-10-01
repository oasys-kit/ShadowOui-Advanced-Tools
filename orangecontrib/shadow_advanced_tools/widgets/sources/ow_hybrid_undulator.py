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
import numpy

from silx.gui.plot import Plot2D

from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from PyQt5.QtGui import QPixmap, QPalette, QColor, QFont
from PyQt5.QtCore import QSettings

import orangecanvas.resources as resources
from orangewidget import gui
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from orangewidget import widget
from oasys.util.oasys_util import TriggerOut, EmittingStream

from syned.beamline.beamline import Beamline
from syned.beamline.optical_elements.absorbers.slit import Slit
from syned.storage_ring.light_source import LightSource
from syned.widget.widget_decorator import WidgetDecorator
from syned.beamline.shape import Rectangle

from orangecontrib.shadow.util.shadow_objects import ShadowBeam

from orangecontrib.shadow.widgets.gui.ow_generic_element import GenericElement
from orangecontrib.shadow_advanced_tools.widgets.sources.attributes.hybrid_undulator_attributes import HybridUndulatorAttributes

import scipy.constants as codata

m2ev = codata.c * codata.h / codata.e

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from orangecontrib.shadow_advanced_tools.widgets.sources.bl import hybrid_undulator_bl as BL

VERTICAL = 1
HORIZONTAL = 2
BOTH = 3

class Distribution:
    POSITION = 0
    DIVERGENCE = 1

class HybridUndulator(GenericElement, HybridUndulatorAttributes):

    TABS_AREA_HEIGHT = 620

    name = "Shadow/SRW Undulator"
    description = "Shadow Source: Hybrid Shadow/SRW Undulator"
    icon = "icons/undulator.png"
    priority = 1
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    category = "Sources"
    keywords = ["data", "file", "load", "read"]

    inputs = WidgetDecorator.syned_input_data()
    inputs.append(("SynedData#2", Beamline, "receive_syned_data"))
    inputs.append(("Trigger", TriggerOut, "sendNewBeam"))

    outputs = [{"name":"Beam",
                "type":ShadowBeam,
                "doc":"Shadow Beam",
                "id":"beam"}]

    def __init__(self, show_automatic_box=False):
        super().__init__(show_automatic_box=show_automatic_box)

        self.runaction = widget.OWAction("Run Shadow/Source", self)
        self.runaction.triggered.connect(self.runShadowSource)
        self.addAction(self.runaction)

        self.general_options_box.setVisible(False)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Run Shadow/Source", callback=self.runShadowSource)
        font = QFont(button.font())
        font.setBold(True)
        button.setFont(font)
        palette = QPalette(button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('Dark Blue'))
        button.setPalette(palette) # assign new palette
        button.setFixedHeight(45)

        button = gui.button(button_box, self, "Reset Fields", callback=self.callResetSettings)
        font = QFont(button.font())
        font.setItalic(True)
        button.setFont(font)
        palette = QPalette(button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('Dark Red'))
        button.setPalette(palette) # assign new palette
        button.setFixedHeight(45)
        button.setFixedWidth(150)

        gui.separator(self.controlArea)

        ######################################

        self.controlArea.setFixedWidth(self.CONTROL_AREA_WIDTH)

        tabs_setting = oasysgui.tabWidget(self.controlArea)
        tabs_setting.setFixedHeight(self.TABS_AREA_HEIGHT)
        tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)

        tab_shadow = oasysgui.createTabPage(tabs_setting, "Shadow Setting")
        tab_spdiv = oasysgui.createTabPage(tabs_setting, "Position/Divergence Setting")
        tab_util = oasysgui.createTabPage(tabs_setting, "Utility")

        gui.comboBox(tab_spdiv, self, "distribution_source", label="Distribution Source", labelWidth=310,
                     items=["SRW Calculation", "SRW Files", "ASCII Files"], orientation="horizontal", callback=self.set_DistributionSource)

        self.srw_box = oasysgui.widgetBox(tab_spdiv, "", addSpace=False, orientation="vertical", height=550)
        self.srw_files_box = oasysgui.widgetBox(tab_spdiv, "", addSpace=False, orientation="vertical", height=550)
        self.ascii_box = oasysgui.widgetBox(tab_spdiv, "", addSpace=False, orientation="vertical", height=550)

        ####################################################################################
        # SHADOW

        left_box_1 = oasysgui.widgetBox(tab_shadow, "Monte Carlo and Energy Spectrum", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_1, self, "number_of_rays", "Number of Rays", tooltip="Number of Rays", labelWidth=250, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "seed", "Seed", tooltip="Seed (0=clock)", labelWidth=250, valueType=int, orientation="horizontal")

        gui.comboBox(left_box_1, self, "use_harmonic", label="Photon Energy Setting",
                     items=["Harmonic", "Other", "Range"], labelWidth=260,
                     callback=self.set_WFUseHarmonic, sendSelectedValue=False, orientation="horizontal")

        self.use_harmonic_box_1 = oasysgui.widgetBox(left_box_1, "", addSpace=False, orientation="vertical", height=80)
        oasysgui.lineEdit(self.use_harmonic_box_1, self, "harmonic_number", "Harmonic #", labelWidth=260, valueType=int, orientation="horizontal", callback=self.set_harmonic_energy)
        le_he = oasysgui.lineEdit(self.use_harmonic_box_1, self, "harmonic_energy", "Harmonic Energy", labelWidth=260, valueType=float, orientation="horizontal")
        le_he.setReadOnly(True)
        font = QFont(le_he.font())
        font.setBold(True)
        le_he.setFont(font)
        palette = QPalette(le_he.palette())
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        le_he.setPalette(palette)

        self.use_harmonic_box_2 = oasysgui.widgetBox(left_box_1, "", addSpace=False, orientation="vertical", height=80)
        oasysgui.lineEdit(self.use_harmonic_box_2, self, "energy", "Photon Energy [eV]", labelWidth=260, valueType=float, orientation="horizontal")

        self.use_harmonic_box_3 = oasysgui.widgetBox(left_box_1, "", addSpace=False, orientation="vertical", height=80)
        oasysgui.lineEdit(self.use_harmonic_box_3, self, "energy", "Photon Energy from [eV]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.use_harmonic_box_3, self, "energy_to", "Photon Energy to [eV]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.use_harmonic_box_3, self, "energy_points", "Nr. of Energy values", labelWidth=260, valueType=int, orientation="horizontal")

        self.set_WFUseHarmonic()

        polarization_box = oasysgui.widgetBox(tab_shadow, "Polarization", addSpace=False, orientation="vertical", height=140)

        gui.comboBox(polarization_box, self, "polarization", label="Polarization", labelWidth=310,
                     items=["No", "Yes"], orientation="horizontal", callback=self.set_Polarization)

        self.ewp_box_8 = oasysgui.widgetBox(polarization_box, "", addSpace=False, orientation="vertical")

        gui.comboBox(self.ewp_box_8, self, "coherent_beam", label="Coherent Beam", labelWidth=310,
                     items=["No", "Yes"], orientation="horizontal")

        oasysgui.lineEdit(self.ewp_box_8, self, "phase_diff", "Phase Difference [deg,0=linear,+90=ell/right]", labelWidth=310, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.ewp_box_8, self, "polarization_degree", "Polarization Degree [cos_s/(cos_s+sin_s)]", labelWidth=310, valueType=float, orientation="horizontal")

        self.set_Polarization()

        ##############################

        left_box_4 = oasysgui.widgetBox(tab_shadow, "Reject Rays", addSpace=False, orientation="vertical", height=140)

        gui.comboBox(left_box_4, self, "optimize_source", label="Optimize Source", items=["No", "Using file with phase/space volume)", "Using file with slit/acceptance"],
                     labelWidth=120, callback=self.set_OptimizeSource, orientation="horizontal")
        self.optimize_file_name_box       = oasysgui.widgetBox(left_box_4, "", addSpace=False, orientation="vertical", height=80)

        file_box = oasysgui.widgetBox(self.optimize_file_name_box, "", addSpace=True, orientation="horizontal", height=25)

        self.le_optimize_file_name = oasysgui.lineEdit(file_box, self, "optimize_file_name", "File Name", labelWidth=100,  valueType=str, orientation="horizontal")

        gui.button(file_box, self, "...", callback=self.selectOptimizeFile)

        oasysgui.lineEdit(self.optimize_file_name_box, self, "max_number_of_rejected_rays", "Max number of rejected rays (set 0 for infinity)", labelWidth=280,  valueType=int, orientation="horizontal")

        self.set_OptimizeSource()

        adv_other_box = oasysgui.widgetBox(tab_shadow, "Optional file output", addSpace=False, orientation="vertical")

        gui.comboBox(adv_other_box, self, "file_to_write_out", label="Files to write out", labelWidth=120,
                     items=["None", "Begin.dat", "Debug (begin.dat + start.xx/end.xx)"],
                     sendSelectedValue=False, orientation="horizontal")

        ####################################################################################
        # SRW

        tabs_srw = oasysgui.tabWidget(self.srw_box)

        if self.IS_DEVELOP:
            gui.comboBox(self.srw_box, self, "kind_of_sampler", label="Random Generator", labelWidth=250,
                         items=["Simple", "Accurate", "Accurate (SRIO)", ], orientation="horizontal")
        else:
            gui.comboBox(self.srw_box, self, "kind_of_sampler", label="Random Generator", labelWidth=250,
                         items=["Simple", "Accurate"], orientation="horizontal")

        gui.comboBox(self.srw_box, self, "save_srw_result", label="Save SRW results", labelWidth=310,
                     items=["No", "Yes"], orientation="horizontal", callback=self.set_SaveFileSRW)

        self.save_file_box = oasysgui.widgetBox(self.srw_box, "", addSpace=False, orientation="vertical")
        self.save_file_box_empty = oasysgui.widgetBox(self.srw_box, "", addSpace=False, orientation="vertical", height=55)

        file_box = oasysgui.widgetBox(self.save_file_box, "", addSpace=False, orientation="horizontal", height=25)

        self.le_source_dimension_srw_file = oasysgui.lineEdit(file_box, self, "source_dimension_srw_file", "Source Dimension File", labelWidth=140,  valueType=str, orientation="horizontal")

        gui.button(file_box, self, "...", callback=self.selectSourceDimensionFile)

        file_box = oasysgui.widgetBox(self.save_file_box, "", addSpace=False, orientation="horizontal", height=25)

        self.le_angular_distribution_srw_file = oasysgui.lineEdit(file_box, self, "angular_distribution_srw_file", "Angular Distribution File", labelWidth=140,  valueType=str, orientation="horizontal")

        gui.button(file_box, self, "...", callback=self.selectAngularDistributionFile)

        self.set_SaveFileSRW()

        tab_ls = oasysgui.createTabPage(tabs_srw, "Undulator Setting")
        tab_wf = oasysgui.createTabPage(tabs_srw, "Wavefront Setting")

        ####################################

        tab_und = oasysgui.tabWidget(tab_ls)

        tab_mach = oasysgui.createTabPage(tab_und, "Machine Parameters")
        tab_id   = oasysgui.createTabPage(tab_und, "ID Parameters")
        tab_traj = oasysgui.createTabPage(tab_und, "Trajectory")

        self.tab_pos = oasysgui.tabWidget(tab_id)

        tab_dim   = oasysgui.createTabPage(self.tab_pos, "ID")

        oasysgui.lineEdit(tab_dim, self, "undulator_period", "Period Length [m]", labelWidth=260, valueType=float, orientation="horizontal", callback=self.set_harmonic_energy)
        oasysgui.lineEdit(tab_dim, self, "number_of_periods", "Number of Periods", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(tab_dim, self, "horizontal_central_position", "Horizontal Central Position [m]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(tab_dim, self, "vertical_central_position", "Vertical Central Position [m]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(tab_dim, self, "longitudinal_central_position", "Longitudinal Central Position [m]", labelWidth=260, valueType=float, orientation="horizontal", callback=self.manageWaistPosition)

        self.warning_label = oasysgui.widgetLabel(tab_dim, "  Warning: The source will be positioned at the center\n" +
                                                  "  of the ID: the relative distance of the first optical\n" +
                                                  "  element has to be longitudinally shifted accordingly")
        self.warning_label.setStyleSheet("color: red; font: bold")

        gui.comboBox(tab_dim, self, "magnetic_field_from", label="Magnetic Field", labelWidth=350,
                     items=["From K", "From B"],
                     callback=self.set_MagneticField,
                     sendSelectedValue=False, orientation="horizontal")

        container = oasysgui.widgetBox(tab_dim, "", addSpace=False, orientation="horizontal")

        horizontal_box = oasysgui.widgetBox(container, "", addSpace=False, orientation="vertical", width=195)
        vertical_box = oasysgui.widgetBox(container,  "", addSpace=False, orientation="vertical", width=155)

        gui.label(horizontal_box, self, "                     Horizontal")
        gui.label(vertical_box, self, "  Vertical")

        self.magnetic_field_box_1_h = oasysgui.widgetBox(horizontal_box, "", addSpace=False, orientation="vertical")
        self.magnetic_field_box_2_h = oasysgui.widgetBox(horizontal_box, "", addSpace=False, orientation="vertical")
        self.magnetic_field_box_1_v = oasysgui.widgetBox(vertical_box, "", addSpace=False, orientation="vertical")
        self.magnetic_field_box_2_v = oasysgui.widgetBox(vertical_box, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.magnetic_field_box_1_h, self, "Kh", "K", labelWidth=70, valueType=float, orientation="horizontal", callback=self.set_harmonic_energy)
        oasysgui.lineEdit(self.magnetic_field_box_1_v, self, "Kv", " ", labelWidth=2, valueType=float, orientation="horizontal", callback=self.set_harmonic_energy)
        oasysgui.lineEdit(self.magnetic_field_box_2_h, self, "Bh", "B [T]", labelWidth=70, valueType=float, orientation="horizontal", callback=self.set_harmonic_energy)
        oasysgui.lineEdit(self.magnetic_field_box_2_v, self, "Bv", " ", labelWidth=2, valueType=float, orientation="horizontal", callback=self.set_harmonic_energy)

        self.set_MagneticField()

        oasysgui.lineEdit(horizontal_box, self, "initial_phase_horizontal", "\u03c6\u2080 [rad]", labelWidth=70, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(vertical_box, self, "initial_phase_vertical", " ", labelWidth=2, valueType=float, orientation="horizontal")

        gui.comboBox(horizontal_box, self, "symmetry_vs_longitudinal_position_horizontal", label="Symmetry", labelWidth=70,
                     items=["Symmetrical", "Anti-Symmetrical"],
                     sendSelectedValue=False, orientation="horizontal")

        symmetry_v_box =  oasysgui.widgetBox(vertical_box, "", addSpace=False, orientation="horizontal")
        gui.comboBox(symmetry_v_box, self, "symmetry_vs_longitudinal_position_vertical", label=" ", labelWidth=2,
                     items=["Symmetrical", "Anti-Symmetrical"],
                     sendSelectedValue=False, orientation="horizontal")
        gui.button(symmetry_v_box, self, "?", callback=self.open_help, width=12)

        oasysgui.lineEdit(tab_mach, self, "electron_energy_in_GeV", "Energy [GeV]", labelWidth=260, valueType=float, orientation="horizontal", callback=self.set_harmonic_energy)
        oasysgui.lineEdit(tab_mach, self, "electron_energy_spread", "Energy Spread", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(tab_mach, self, "ring_current", "Ring Current [A]", labelWidth=260, valueType=float, orientation="horizontal")
        
        gui.separator(tab_mach)

        oasysgui.lineEdit(tab_mach, self, "electron_beam_size_h",       "Horizontal Beam Size [m]", labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(tab_mach, self, "electron_beam_size_v",       "Vertical Beam Size [m]",  labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(tab_mach, self, "electron_beam_divergence_h", "Horizontal Beam Divergence [rad]", labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(tab_mach, self, "electron_beam_divergence_v", "Vertical Beam Divergence [rad]", labelWidth=230, valueType=float, orientation="horizontal")

        gui.comboBox(tab_traj, self, "type_of_initialization", label="Trajectory Initialization", labelWidth=140,
                     items=["Automatic", "At Fixed Position", "Sampled from Phase Space"],
                     callback=self.set_TypeOfInitialization,
                     sendSelectedValue=False, orientation="horizontal")

        self.left_box_3_1 = oasysgui.widgetBox(tab_traj, "", addSpace=False, orientation="vertical", height=160)
        self.left_box_3_2 = oasysgui.widgetBox(tab_traj, "", addSpace=False, orientation="vertical", height=160)

        oasysgui.lineEdit(self.left_box_3_1, self, "moment_x", "x\u2080 [m]", labelWidth=200, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_3_1, self, "moment_y", "y\u2080 [m]", labelWidth=200, valueType=float, orientation="horizontal")

        box = oasysgui.widgetBox(self.left_box_3_1, "", addSpace=False, orientation="horizontal")

        oasysgui.lineEdit(box, self, "moment_z", "z\u2080 [m]", labelWidth=160, valueType=float, orientation="horizontal")
        gui.button(box, self, "Auto", width=35, callback=self.set_z0Default)

        oasysgui.lineEdit(self.left_box_3_1, self, "moment_xp", "x'\u2080 [rad]", labelWidth=200, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_3_1, self, "moment_yp", "y'\u2080 [rad]", labelWidth=200, valueType=float, orientation="horizontal")

        self.set_TypeOfInitialization()

        left_box_3 = oasysgui.widgetBox(tab_wf, "Divergence Distribution Propagation Parameters", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_3, self, "source_dimension_wf_h_slit_gap", "H Slit Gap [m]", labelWidth=250, valueType=float, orientation="horizontal", callback=self.setDataX)
        oasysgui.lineEdit(left_box_3, self, "source_dimension_wf_v_slit_gap", "V Slit Gap [m]", labelWidth=250, valueType=float, orientation="horizontal", callback=self.setDataY)
        oasysgui.lineEdit(left_box_3, self, "source_dimension_wf_h_slit_points", "H Slit Points", labelWidth=250, valueType=int, orientation="horizontal", callback=self.setDataX)
        oasysgui.lineEdit(left_box_3, self, "source_dimension_wf_v_slit_points", "V Slit Points", labelWidth=250, valueType=int, orientation="horizontal", callback=self.setDataY)
        oasysgui.lineEdit(left_box_3, self, "source_dimension_wf_distance", "Propagation Distance [m]\n(relative to the center of the ID)", labelWidth=250, valueType=float, orientation="horizontal")

        left_box_4 = oasysgui.widgetBox(tab_wf, "Size Distribution (Back) Propagation Parameters", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_4, self, "horizontal_range_modification_factor_at_resizing", "H range modification factor at resizing", labelWidth=290, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_4, self, "horizontal_resolution_modification_factor_at_resizing", "H resolution modification factor at resizing", labelWidth=290, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_4, self, "vertical_range_modification_factor_at_resizing", "V range modification factor at resizing", labelWidth=290, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_4, self, "vertical_resolution_modification_factor_at_resizing", "V resolution modification factor at resizing", labelWidth=290, valueType=float, orientation="horizontal")

        gui.comboBox(tab_wf, self, "auto_expand", label="Auto Expand Slit to Compensate Random Generator", labelWidth=310,
                     items=["No", "Yes"], orientation="horizontal", callback=self.set_auto_expand)

        self.cb_auto_expand_rays = gui.comboBox(tab_wf, self, "auto_expand_rays", label="Auto Increase Number of Rays", labelWidth=310,
                                                items=["No", "Yes"], orientation="horizontal")

        self.set_auto_expand()

        ####################################################################################
        # SRW FILES

        gui.separator(self.srw_files_box)

        file_box = oasysgui.widgetBox(self.srw_files_box, "", addSpace=True, orientation="horizontal", height=45)

        self.le_source_dimension_srw_file = oasysgui.lineEdit(file_box, self, "source_dimension_srw_file", "Source Dimension File", labelWidth=180,  valueType=str, orientation="vertical")

        gui.button(file_box, self, "...", height=45, callback=self.selectSourceDimensionFile)

        file_box = oasysgui.widgetBox(self.srw_files_box, "", addSpace=True, orientation="horizontal", height=45)

        self.le_angular_distribution_srw_file = oasysgui.lineEdit(file_box, self, "angular_distribution_srw_file", "Angular Distribution File", labelWidth=180,  valueType=str, orientation="vertical")

        gui.button(file_box, self, "...", height=45, callback=self.selectAngularDistributionFile)


        ####################################################################################
        # ASCII FILES

        gui.separator(self.ascii_box)

        file_box = oasysgui.widgetBox(self.ascii_box, "", addSpace=True, orientation="horizontal", height=45)

        self.le_x_positions_file = oasysgui.lineEdit(file_box, self, "x_positions_file", "X Positions File", labelWidth=180,  valueType=str, orientation="vertical")

        gui.button(file_box, self, "...", height=45, callback=self.selectXPositionsFile)

        file_box = oasysgui.widgetBox(self.ascii_box, "", addSpace=True, orientation="horizontal", height=45)

        self.le_z_positions_file = oasysgui.lineEdit(file_box, self, "z_positions_file", "Z Positions File", labelWidth=180,  valueType=str, orientation="vertical")

        gui.button(file_box, self, "...", height=45, callback=self.selectZPositionsFile)

        file_box = oasysgui.widgetBox(self.ascii_box, "", addSpace=True, orientation="horizontal", height=45)

        self.le_x_divergences_file = oasysgui.lineEdit(file_box, self, "x_divergences_file", "X Divergences File", labelWidth=180,  valueType=str, orientation="vertical")

        gui.button(file_box, self, "...", height=45, callback=self.selectXDivergencesFile)

        file_box = oasysgui.widgetBox(self.ascii_box, "", addSpace=True, orientation="horizontal", height=45)

        self.le_z_divergences_file = oasysgui.lineEdit(file_box, self, "z_divergences_file", "Z Divergences File", labelWidth=180,  valueType=str, orientation="vertical")

        gui.button(file_box, self, "...", height=45, callback=self.selectZDivergencesFile)

        gui.separator(self.ascii_box)

        oasysgui.lineEdit(self.ascii_box, self, "x_positions_factor",   "X Positions UM to Workspace UM", labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.ascii_box, self, "z_positions_factor",   "Z Positions UM to Workspace UM",  labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.ascii_box, self, "x_divergences_factor", "X Divergences UM to rad", labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.ascii_box, self, "z_divergences_factor", "X Divergences UM to rad", labelWidth=230, valueType=float, orientation="horizontal")

        gui.separator(self.ascii_box)

        gui.comboBox(self.ascii_box, self, "combine_strategy", label="2D Distribution Creation Strategy", labelWidth=310,
                     items=["Sqrt(Product)", "Sqrt(Quadratic Sum)", "Convolution", "Average"], orientation="horizontal", callback=self.set_SaveFileSRW)

        ####################################################################################
        # Utility

        left_box_1 = oasysgui.widgetBox(tab_util, "Auto Setting of Undulator", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_1, self, "auto_energy", "Set Undulator at Energy [eV]", labelWidth=250, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "auto_harmonic_number", "As Harmonic #",  labelWidth=250, valueType=int, orientation="horizontal")

        button_box = oasysgui.widgetBox(left_box_1, "", addSpace=False, orientation="horizontal")

        gui.button(button_box, self, "Set Kv value", callback=self.auto_set_undulator_V)
        gui.button(button_box, self, "Set Kh value", callback=self.auto_set_undulator_H)
        gui.button(button_box, self, "Set Both K values", callback=self.auto_set_undulator_B)

        gui.rubber(self.controlArea)

        cumulated_plot_tab = oasysgui.createTabPage(self.main_tabs, "Cumulated Plots")

        view_box = oasysgui.widgetBox(cumulated_plot_tab, "Plotting Style", addSpace=False, orientation="horizontal")
        view_box_1 = oasysgui.widgetBox(view_box, "", addSpace=False, orientation="vertical", width=350)

        self.cumulated_view_type_combo = gui.comboBox(view_box_1, self, "cumulated_view_type", label="Show Plots",
                                            labelWidth=220,
                                            items=["No", "Yes"],
                                            callback=self.set_CumulatedPlotQuality, sendSelectedValue=False, orientation="horizontal")


        self.cumulated_tabs = oasysgui.tabWidget(cumulated_plot_tab)

        self.initializeCumulatedTabs()

        self.set_DistributionSource()

        gui.rubber(self.mainArea)

    def initializeCumulatedTabs(self):
        current_tab = self.cumulated_tabs.currentIndex()

        self.cumulated_tabs.removeTab(2)
        self.cumulated_tabs.removeTab(1)
        self.cumulated_tabs.removeTab(0)

        self.cumulated_plot_canvas = [None]*3
        self.cumulated_tab = []
        self.cumulated_tab.append(oasysgui.createTabPage(self.cumulated_tabs, "Spectral Flux"))
        self.cumulated_tab.append(oasysgui.createTabPage(self.cumulated_tabs, "Cumulated Power"))
        self.cumulated_tab.append(oasysgui.createTabPage(self.cumulated_tabs, "Power Density"))

        for tab in self.cumulated_tab:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)

        self.cumulated_tabs.setCurrentIndex(current_tab)

    def manageWaistPosition(self):
        is_canted = BL.is_canted_undulator(self)

        self.warning_label.setVisible(is_canted)
        self.initializeWaistPositionTab(show=is_canted)
        self.initializeWaistPositionPlotTab(show=(is_canted and self.waist_position_calculation==1))

    def initializeWaistPositionTab(self, show=True):
        if show and self.tab_pos.count() == 1:
            tab_waist   = oasysgui.createTabPage(self.tab_pos, "Waist Position")

            gui.comboBox(tab_waist, self, "waist_position_calculation", label="Waist Position Calculation", labelWidth=310,
                         items=["None", "Automatic", "User Defined"], orientation="horizontal", callback=self.set_WaistPositionCalculation)

            self.box_none     = oasysgui.widgetBox(tab_waist, "", addSpace=False, orientation="vertical", height=350)
            self.box_auto     = oasysgui.widgetBox(tab_waist, "", addSpace=False, orientation="vertical", height=350)

            gui.comboBox(self.box_auto, self, "waist_back_propagation_parameters", label="Propagation Parameters", labelWidth=250,
                         items=["Same as Source", "Different"], orientation="horizontal", callback=self.set_WaistBackPropagationParameters)

            self.waist_param_box_1 = oasysgui.widgetBox(self.box_auto, "", addSpace=False, orientation="vertical", height=110)
            self.waist_param_box_2 = oasysgui.widgetBox(self.box_auto, "", addSpace=False, orientation="vertical", height=110)

            gui.separator(self.box_auto, height=5)

            oasysgui.lineEdit(self.waist_param_box_2, self, "waist_horizontal_range_modification_factor_at_resizing", "H range modification factor at resizing", labelWidth=290, valueType=float, orientation="horizontal")
            oasysgui.lineEdit(self.waist_param_box_2, self, "waist_horizontal_resolution_modification_factor_at_resizing", "H resolution modification factor at resizing", labelWidth=290, valueType=float, orientation="horizontal")
            oasysgui.lineEdit(self.waist_param_box_2, self, "waist_vertical_range_modification_factor_at_resizing", "V range modification factor at resizing", labelWidth=290, valueType=float, orientation="horizontal")
            oasysgui.lineEdit(self.waist_param_box_2, self, "waist_vertical_resolution_modification_factor_at_resizing", "V resolution modification factor at resizing", labelWidth=290, valueType=float, orientation="horizontal")

            oasysgui.lineEdit(self.box_auto, self, "number_of_waist_fit_points", "Number of Fit Points", labelWidth=290, valueType=int, orientation="horizontal")
            oasysgui.lineEdit(self.box_auto, self, "degree_of_waist_fit", "Degree of Polynomial Fit", labelWidth=290, valueType=int, orientation="horizontal")

            gui.comboBox(self.box_auto, self, "use_sigma_or_fwhm", label="Gaussian size from", labelWidth=250,
                         items=["Sigma", "FWHM"], orientation="horizontal")

            gui.comboBox(self.box_auto, self, "which_waist", label="Use Direction", labelWidth=150,
                         items=["Horizontal", "Vertical", "Both (middle point)"], orientation="horizontal",
                         callback=self.set_which_waist)

            self.set_WaistBackPropagationParameters()

            le = oasysgui.lineEdit(self.box_auto, self, "waist_position_auto", "Waist Position (relative to ID center) [m]", labelWidth=265, valueType=float, orientation="horizontal")
            le.setReadOnly(True)
            font = QFont(le.font())
            font.setBold(True)
            le.setFont(font)
            palette = QPalette(le.palette())
            palette.setColor(QPalette.Text, QColor('dark blue'))
            palette.setColor(QPalette.Base, QColor(243, 240, 160))
            le.setPalette(palette)

            self.box_user_def = oasysgui.widgetBox(tab_waist, "", addSpace=False, orientation="vertical", height=250)

            oasysgui.lineEdit(self.box_user_def, self, "waist_position_user_defined", "Waist Position (relative to ID center) [m]", labelWidth=265, valueType=float, orientation="horizontal")

            self.set_WaistPositionCalculation()

        elif not show and self.tab_pos.count() == 2:
            self.tab_pos.removeTab(1)

    def initializeWaistPositionPlotTab(self, show=True):
        if show and self.main_tabs.count() == 3:
            waist_tab = oasysgui.createTabPage(self.main_tabs, "Waist Position for Canted Undulator")

            figure = Figure(figsize=(700, 500))

            self.waist_axes = figure.subplots(1, 2)
            self.waist_axes[0].set_title("Horizontal Direction", fontdict={'horizontalalignment': 'right'})
            self.waist_axes[1].set_title("Vertical Direction", fontdict={'horizontalalignment': 'right'})
            self.waist_axes[0].set_xlabel("Position relative to ID center [mm]")
            self.waist_axes[0].set_ylabel("Sigma [um]")
            self.waist_axes[1].set_xlabel("Position relative to ID center [mm]")
            self.waist_axes[1].set_ylabel("Sigma [um]")

            self.waist_figure = FigureCanvas(figure)

            waist_tab.layout().addWidget(self.waist_figure)

        elif not show and self.main_tabs.count() == 4:
            self.main_tabs.removeTab(3)
            self.waist_axes = None

    def set_WaistPositionCalculation(self):
        self.box_none.setVisible(self.waist_position_calculation==0)
        self.box_auto.setVisible(self.waist_position_calculation==1)
        self.box_user_def.setVisible(self.waist_position_calculation==2)

        self.initializeWaistPositionPlotTab(show=(self.waist_position_calculation==1))

    def set_WaistBackPropagationParameters(self):
        self.waist_param_box_1.setVisible(self.waist_back_propagation_parameters==0)
        self.waist_param_box_2.setVisible(self.waist_back_propagation_parameters==1)

    def set_CumulatedPlotQuality(self):
        if not self.cumulated_power is None:
            self.initializeCumulatedTabs()

            self.plot_cumulated_results(True)

    def set_auto_expand(self):
        self.cb_auto_expand_rays.setEnabled(self.auto_expand==1)

        self.setDataXY()

    def setDataXY(self):
        self.setDataX()
        self.setDataY()

    def setDataX(self):
        source_dimension_wf_h_slit_points, \
        source_dimension_wf_h_slit_gap = BL.get_source_slit_data(self, direction="h")

        x2 = 0.5 * source_dimension_wf_h_slit_gap
        x1 = -x2

        self.dataX = 1e3 * numpy.linspace(x1, x2, source_dimension_wf_h_slit_points)

    def setDataY(self):
        source_dimension_wf_v_slit_points, \
        source_dimension_wf_v_slit_gap = BL.get_source_slit_data(self, direction="v")

        y2 = 0.5 * source_dimension_wf_v_slit_gap
        y1 = -y2

        self.dataY = 1e3*numpy.linspace(y1, y2, source_dimension_wf_v_slit_points)

    def onReceivingInput(self):
        super(HybridUndulator, self).onReceivingInput()

        self.initializeCumulatedTabs()
        self.manageWaistPosition()

    ####################################################################################
    # GRAPHICS
    ####################################################################################

    def after_change_workspace_units(self):
        pass

    def set_TypeOfInitialization(self):
        self.left_box_3_1.setVisible(self.type_of_initialization==1)
        self.left_box_3_2.setVisible(self.type_of_initialization!=1)

    def set_z0Default(self):
        self.moment_z = BL.get_default_initial_z(self)

    def auto_set_undulator_V(self):
        self.auto_set_undulator(VERTICAL)

    def auto_set_undulator_H(self):
        self.auto_set_undulator(HORIZONTAL)

    def auto_set_undulator_B(self):
        self.auto_set_undulator(BOTH)

    def auto_set_undulator(self, which=VERTICAL):
        if not self.distribution_source == 0: raise Exception("This calculation can be performed only for explicit SRW Calculation")
        congruence.checkStrictlyPositiveNumber(self.auto_energy, "Set Undulator at Energy")
        congruence.checkStrictlyPositiveNumber(self.auto_harmonic_number, "As Harmonic #")
        congruence.checkStrictlyPositiveNumber(self.electron_energy_in_GeV, "Energy")
        congruence.checkStrictlyPositiveNumber(self.undulator_period, "Period Length")

        wavelength = self.auto_harmonic_number*m2ev/self.auto_energy
        K = round(numpy.sqrt(2*(((wavelength*2*BL.gamma(self)**2)/self.undulator_period)-1)), 6)

        if which == VERTICAL:
            self.Kv = K
            self.Kh = 0.0

        if which == BOTH:
            Kboth = round(K / numpy.sqrt(2), 6)
            self.Kv = Kboth
            self.Kh = Kboth

        if which == HORIZONTAL:
            self.Kh = K
            self.Kv = 0.0

        self.set_WFUseHarmonic()

    class ShowHelpDialog(QDialog):

        def __init__(self, parent=None):
            QDialog.__init__(self, parent)
            self.setWindowTitle('Symmetry vs Longitudinal Position')
            layout = QVBoxLayout(self)
            label = QLabel("")

            file = os.path.join(resources.package_dirname("orangecontrib.shadow_advanced_tools.widgets.sources"), "misc", "symmetry.png")

            label.setPixmap(QPixmap(file))

            bbox = QDialogButtonBox(QDialogButtonBox.Ok)

            bbox.accepted.connect(self.accept)
            layout.addWidget(label)
            layout.addWidget(bbox)

    def open_help(self):
        dialog = HybridUndulator.ShowHelpDialog(parent=self)
        dialog.show()

    def set_MagneticField(self):
        self.magnetic_field_box_1_h.setVisible(self.magnetic_field_from==0)
        self.magnetic_field_box_2_h.setVisible(self.magnetic_field_from==1)
        self.magnetic_field_box_1_v.setVisible(self.magnetic_field_from==0)
        self.magnetic_field_box_2_v.setVisible(self.magnetic_field_from==1)

        self.set_harmonic_energy()

    def set_harmonic_energy(self):
        if self.distribution_source==0 and self.use_harmonic==0:
            self.harmonic_energy = round(BL.resonance_energy(self, harmonic=self.harmonic_number), 2)
        else:
            self.harmonic_energy = numpy.nan

    def set_WFUseHarmonic(self):
        self.use_harmonic_box_1.setVisible(self.use_harmonic==0)
        self.use_harmonic_box_2.setVisible(self.use_harmonic==1)
        self.use_harmonic_box_3.setVisible(self.use_harmonic==2)

        self.set_harmonic_energy()

    def set_DistributionSource(self):
        self.srw_box.setVisible(self.distribution_source == 0)
        self.srw_files_box.setVisible(self.distribution_source == 1)
        self.ascii_box.setVisible(self.distribution_source == 2)

        self.set_harmonic_energy()

        if self.distribution_source == 0:
            self.manageWaistPosition()
        else:
            self.initializeWaistPositionPlotTab(show=False)

    def set_Polarization(self):
        self.ewp_box_8.setVisible(self.polarization==1)

    def set_OptimizeSource(self):
        self.optimize_file_name_box.setVisible(self.optimize_source != 0)

    def set_SaveFileSRW(self):
        self.save_file_box.setVisible(self.save_srw_result == 1)
        self.save_file_box_empty.setVisible(self.save_srw_result == 0)

    def selectOptimizeFile(self):
        self.le_optimize_file_name.setText(oasysgui.selectFileFromDialog(self, self.optimize_file_name, "Open Optimize Source Parameters File"))

    def selectSourceDimensionFile(self):
        self.le_source_dimension_srw_file.setText(oasysgui.selectFileFromDialog(self, self.source_dimension_srw_file, "Open Source Dimension File"))

    def selectAngularDistributionFile(self):
        self.le_angular_distribution_srw_file.setText(oasysgui.selectFileFromDialog(self, self.angular_distribution_srw_file, "Open Angular Distribution File"))

    def selectXPositionsFile(self):
        self.le_x_positions_file.setText(oasysgui.selectFileFromDialog(self, self.x_positions_file, "Open X Positions File", file_extension_filter="*.dat, *.txt"))

    def selectZPositionsFile(self):
        self.le_z_positions_file.setText(oasysgui.selectFileFromDialog(self, self.z_positions_file, "Open Z Positions File", file_extension_filter="*.dat, *.txt"))

    def selectXDivergencesFile(self):
        self.le_x_divergences_file.setText(oasysgui.selectFileFromDialog(self, self.x_divergences_file, "Open X Divergences File", file_extension_filter="*.dat, *.txt"))

    def selectZDivergencesFile(self):
        self.le_z_divergences_file.setText(oasysgui.selectFileFromDialog(self, self.z_divergences_file, "Open Z Divergences File", file_extension_filter="*.dat, *.txt"))

    def set_which_waist(self):
        BL.set_which_waist(self)

    ####################################################################################
    # SYNED
    ####################################################################################

    def receive_syned_data(self, data):
        if not data is None:
            try:
                if data.get_beamline_elements_number() > 0:
                    slit_element = data.get_beamline_element_at(0)
                    slit = slit_element.get_optical_element()
                    coordinates = slit_element.get_coordinates()

                    if isinstance(slit, Slit) and isinstance(slit.get_boundary_shape(), Rectangle):
                        rectangle = slit.get_boundary_shape()

                        self.source_dimension_wf_h_slit_gap = rectangle._x_right - rectangle._x_left
                        self.source_dimension_wf_v_slit_gap = rectangle._y_top - rectangle._y_bottom
                        self.source_dimension_wf_distance = coordinates.p()
                elif not data._light_source is None and isinstance(data._light_source, LightSource):
                    light_source = data._light_source

                    self.electron_energy_in_GeV = light_source._electron_beam._energy_in_GeV
                    self.electron_energy_spread = light_source._electron_beam._energy_spread
                    self.ring_current = light_source._electron_beam._current

                    x, xp, y, yp = light_source._electron_beam.get_sigmas_all()

                    self.electron_beam_size_h = round(x, 9)
                    self.electron_beam_size_v = round(y, 9)
                    self.electron_beam_divergence_h = round(xp, 10)
                    self.electron_beam_divergence_v = round(yp, 10)

                    self.Kh = light_source._magnetic_structure._K_horizontal
                    self.Kv = light_source._magnetic_structure._K_vertical
                    self.undulator_period = light_source._magnetic_structure._period_length
                    self.number_of_periods = light_source._magnetic_structure._number_of_periods

                    self.set_harmonic_energy()
                else:
                    raise ValueError("Syned data not correct")
            except Exception as exception:
                QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

    def receive_specific_syned_data(self, data):
        raise NotImplementedError()

    ####################################################################################
    # PROCEDURES
    ####################################################################################

    def runShadowSource(self, do_cumulated_calculations=False):
        self.setStatusMessage("")
        self.progressBarInit()

        sys.stdout = EmittingStream(textWritten=self.writeStdOut)

        try:
            beam_out, total_power = BL.run_hybrid_undulator_simulation(self, do_cumulated_calculations)

            self.setStatusMessage("Plotting Results")

            self.progressBarSet(80)

            self.plot_results(beam_out)
            self.plot_cumulated_results(do_cumulated_calculations)

            self.setStatusMessage("")

            if self.compute_power and self.energy_step and total_power:
                additional_parameters = {}

                additional_parameters["total_power"]        = total_power
                additional_parameters["photon_energy_step"] = self.energy_step
                additional_parameters["current_step"]       = self.current_step
                additional_parameters["total_steps"]        = self.total_steps

                beam_out.setScanningData(ShadowBeam.ScanningData("photon_energy", self.energy, "Energy for Power Calculation", "eV", additional_parameters))

            if self.file_to_write_out > 0: beam_out._beam.write("begin.dat")

            self.send("Beam", beam_out)
        except Exception as exception:
            QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

        self.progressBarFinished()

    def initializeTabs(self):
        current_tab = self.tabs.currentIndex()

        size = len(self.tab)
        indexes = range(0, size)
        for index in indexes:
            self.tabs.removeTab(size - 1 - index)

        show_effective_source_size = QSettings().value("output/show-effective-source-size", 0, int) == 1

        titles = self.getTitles()

        if show_effective_source_size:
            self.tab = [oasysgui.createTabPage(self.tabs, titles[0]),
                        oasysgui.createTabPage(self.tabs, titles[1]),
                        oasysgui.createTabPage(self.tabs, titles[2]),
                        oasysgui.createTabPage(self.tabs, titles[3]),
                        oasysgui.createTabPage(self.tabs, titles[4]),
                        oasysgui.createTabPage(self.tabs, titles[5]),
                        ]

            self.plot_canvas = [None, None, None, None, None, None]
        else:
            self.tab = [oasysgui.createTabPage(self.tabs, titles[0]),
                        oasysgui.createTabPage(self.tabs, titles[1]),
                        oasysgui.createTabPage(self.tabs, titles[2]),
                        oasysgui.createTabPage(self.tabs, titles[3]),
                        oasysgui.createTabPage(self.tabs, titles[4]),
                        ]

            self.plot_canvas = [None, None, None, None, None]

        for tab in self.tab:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)

        self.tabs.setCurrentIndex(min(current_tab, len(self.tab) - 1))

    def isFootprintEnabled(self):
        return False

    def enableFootprint(self, enabled=False):
        pass

    def plot_results(self, beam_out, footprint_beam=None, progressBarValue=80):
        show_effective_source_size = QSettings().value("output/show-effective-source-size", 0, int) == 1

        if show_effective_source_size:
            if len(self.tab)==5: self.initializeTabs()
        else:
            if len(self.tab)==6: self.initializeTabs()

        super().plot_results(beam_out, footprint_beam, progressBarValue)

        if show_effective_source_size and not self.view_type == 2:
            effective_source_size_beam = beam_out.duplicate(history=False)
            effective_source_size_beam._beam.retrace(0)

            variables = self.getVariablestoPlot()
            titles = self.getTitles()
            xtitles = self.getXTitles()
            ytitles = self.getYTitles()
            xums = self.getXUM()
            yums = self.getYUM()

            if self.view_type == 1:
                self.plot_xy_fast(effective_source_size_beam, 100,  variables[0][0], variables[0][1], plot_canvas_index=5, title=titles[0], xtitle=xtitles[0], ytitle=ytitles[0])
            elif self.view_type == 0:
                self.plot_xy(effective_source_size_beam, 100,  variables[0][0], variables[0][1], plot_canvas_index=5, title=titles[0], xtitle=xtitles[0], ytitle=ytitles[0], xum=xums[0], yum=yums[0])

    def getTitles(self):
        return ["X,Z", "X',Z'", "X,X'", "Z,Z'", "Energy", "Effective Source Size"]

    def sendNewBeam(self, trigger):
        self.compute_power = False
        self.energy_step = None

        if trigger and trigger.new_object == True:
            do_cumulated_calculations = False

            if trigger.has_additional_parameter("seed_increment"):
                self.seed += trigger.get_additional_parameter("seed_increment")

            if not trigger.has_additional_parameter("start_event"):
                self.cumulated_energies = None
                self.cumulated_integrated_flux = None
                self.cumulated_power_density = None
                self.cumulated_power = None

            if trigger.has_additional_parameter("energy_value") and trigger.has_additional_parameter("energy_step"):
                self.compute_power = True
                self.use_harmonic = 1
                self.distribution_source = 0
                self.save_srw_result = 0
                do_cumulated_calculations = True

                if trigger.has_additional_parameter("start_event") and trigger.get_additional_parameter("start_event") == True:
                    self.cumulated_energies = None
                    self.cumulated_integrated_flux = None
                    self.cumulated_power_density = None
                    self.cumulated_power = None

                self.energy = trigger.get_additional_parameter("energy_value")
                self.energy_step = trigger.get_additional_parameter("energy_step")
                self.power_step = trigger.get_additional_parameter("power_step")
                self.current_step = trigger.get_additional_parameter("current_step")
                self.total_steps  = trigger.get_additional_parameter("total_steps")
                self.start_event = trigger.get_additional_parameter("start_event")

                self.set_WFUseHarmonic()
                self.set_DistributionSource()
                self.set_SaveFileSRW()

            self.runShadowSource(do_cumulated_calculations)

    def cumulated_plot_data1D(self, dataX, dataY, plot_canvas_index, title="", xtitle="", ytitle=""):
        if self.cumulated_plot_canvas[plot_canvas_index] is None:
            self.cumulated_plot_canvas[plot_canvas_index] = oasysgui.plotWindow()
            self.cumulated_tab[plot_canvas_index].layout().addWidget(self.cumulated_plot_canvas[plot_canvas_index])

        self.cumulated_plot_canvas[plot_canvas_index].addCurve(dataX, dataY,)

        self.cumulated_plot_canvas[plot_canvas_index].resetZoom()
        self.cumulated_plot_canvas[plot_canvas_index].setXAxisAutoScale(True)
        self.cumulated_plot_canvas[plot_canvas_index].setYAxisAutoScale(True)
        self.cumulated_plot_canvas[plot_canvas_index].setGraphGrid(False)

        self.cumulated_plot_canvas[plot_canvas_index].setXAxisLogarithmic(False)
        self.cumulated_plot_canvas[plot_canvas_index].setYAxisLogarithmic(False)
        self.cumulated_plot_canvas[plot_canvas_index].setGraphXLabel(xtitle)
        self.cumulated_plot_canvas[plot_canvas_index].setGraphYLabel(ytitle)
        self.cumulated_plot_canvas[plot_canvas_index].setGraphTitle(title)

    def cumulated_plot_data2D(self, data2D, dataX, dataY, plot_canvas_index, title="", xtitle="", ytitle=""):

        if self.cumulated_plot_canvas[plot_canvas_index] is None:
            self.cumulated_plot_canvas[plot_canvas_index] = Plot2D()
            self.cumulated_tab[plot_canvas_index].layout().addWidget(self.cumulated_plot_canvas[plot_canvas_index])

        origin = (dataX[0],dataY[0])
        scale = (dataX[1]-dataX[0], dataY[1]-dataY[0])

        data_to_plot = data2D.T

        colormap = {"name":"temperature", "normalization":"linear", "autoscale":True, "vmin":0, "vmax":0, "colors":256}

        self.cumulated_plot_canvas[plot_canvas_index].resetZoom()
        self.cumulated_plot_canvas[plot_canvas_index].setXAxisAutoScale(True)
        self.cumulated_plot_canvas[plot_canvas_index].setYAxisAutoScale(True)
        self.cumulated_plot_canvas[plot_canvas_index].setGraphGrid(False)
        self.cumulated_plot_canvas[plot_canvas_index].setKeepDataAspectRatio(True)
        self.cumulated_plot_canvas[plot_canvas_index].yAxisInvertedAction.setVisible(False)

        self.cumulated_plot_canvas[plot_canvas_index].setXAxisLogarithmic(False)
        self.cumulated_plot_canvas[plot_canvas_index].setYAxisLogarithmic(False)
        self.cumulated_plot_canvas[plot_canvas_index].getMaskAction().setVisible(False)
        self.cumulated_plot_canvas[plot_canvas_index].getRoiAction().setVisible(False)
        self.cumulated_plot_canvas[plot_canvas_index].getColormapAction().setVisible(False)
        self.cumulated_plot_canvas[plot_canvas_index].setKeepDataAspectRatio(False)



        self.cumulated_plot_canvas[plot_canvas_index].addImage(numpy.array(data_to_plot),
                                                     legend="zio billy",
                                                     scale=scale,
                                                     origin=origin,
                                                     colormap=colormap,
                                                     replace=True)

        self.cumulated_plot_canvas[plot_canvas_index].setActiveImage("zio billy")

        self.cumulated_plot_canvas[plot_canvas_index].setGraphXLabel(xtitle)
        self.cumulated_plot_canvas[plot_canvas_index].setGraphYLabel(ytitle)
        self.cumulated_plot_canvas[plot_canvas_index].setGraphTitle(title)

    def plot_cumulated_results(self, do_cumulated_calculations):
        if not self.cumulated_view_type == 0 and do_cumulated_calculations==True:
            try:
                self.cumulated_view_type_combo.setEnabled(False)

                total_power = str(round(self.cumulated_power[-1], 2))

                self.cumulated_plot_data1D(self.cumulated_energies, self.cumulated_integrated_flux, 0, "Spectral Flux", "Energy [eV]", "Flux [ph/s/0.1%BW]")
                self.cumulated_plot_data1D(self.cumulated_energies, self.cumulated_power, 1,
                                           "Cumulated Power (Total = " + total_power + " W)", "Energy [eV]", "Power [W]")
                self.cumulated_plot_data2D(self.cumulated_power_density, self.dataX, self.dataY, 2,
                                           "Power Density [W/mm^2] (Total Power = " + total_power + " W)", "X [mm]", "Y [mm]")

                self.cumulated_view_type_combo.setEnabled(True)
            except Exception as e:
                self.cumulated_view_type_combo.setEnabled(True)

                raise Exception("Data not plottable: exception: " + str(e))


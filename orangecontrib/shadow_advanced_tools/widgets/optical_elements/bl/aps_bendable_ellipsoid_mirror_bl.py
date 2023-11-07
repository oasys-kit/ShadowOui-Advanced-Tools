#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------- #
# Copyright (c) 2021, UChicago Argonne, LLC. All rights reserved.         #
#                                                                         #
# Copyright 2021. UChicago Argonne, LLC. This software was produced       #
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
# ----------------------------------------------------------------------- #

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowPreProcessor

from Shadow import ShadowTools as ST

from syned.tools.benders.aps_bendable_ellipsoid_mirror import *

def apply_bender_surface(widget, input_beam, shadow_oe):
    shadow_oe_temp  = shadow_oe.duplicate()
    input_beam_temp = input_beam.duplicate(history=False)

    widget.manage_acceptance_slits(shadow_oe_temp)

    ShadowBeam.traceFromOE(input_beam_temp,
                           shadow_oe_temp,
                           write_start_file=0,
                           write_end_file=0,
                           widget_class_name=type(widget).__name__)

    input_parameters = ApsBenderParameters()
    input_parameters.dim_x_minus           = widget.dim_x_minus
    input_parameters.dim_x_plus            = widget.dim_x_plus
    input_parameters.bender_bin_x          = widget.bender_bin_x
    input_parameters.dim_y_minus           = widget.dim_y_minus
    input_parameters.dim_y_plus            = widget.dim_y_plus
    input_parameters.bender_bin_y          = widget.bender_bin_y
    input_parameters.conic_coefficients    = shadow_oe_temp._oe.CCC
    if widget.which_length == 1: input_parameters.optimized_length = widget.optimized_length
    input_parameters.n_fit_steps           = widget.n_fit_steps
    input_parameters.E                     = widget.E
    input_parameters.h                     = widget.h
    input_parameters.shape                 = widget.shape
    input_parameters.kind_of_bender        = widget.kind_of_bender
    input_parameters.M1                    = widget.M1
    input_parameters.M1_min                = widget.M1_min
    input_parameters.M1_max                = widget.M1_max
    input_parameters.M1_fixed              = widget.M1_fixed
    input_parameters.e                     = widget.e
    input_parameters.e_min                 = widget.e_min
    input_parameters.e_max                 = widget.e_max
    input_parameters.e_fixed               = widget.e_fixed
    input_parameters.ratio                 = widget.ratio
    input_parameters.ratio_min             = widget.ratio_min
    input_parameters.ratio_max             = widget.ratio_max
    input_parameters.ratio_fixed           = widget.ratio_fixed
    input_parameters.workspace_units_to_m  = widget.workspace_units_to_m
    if widget.modified_surface == 1 and widget.ms_type_of_defect == 2: input_parameters.figure_error = ShadowPreProcessor.read_surface_error_file(widget.ms_defect_file_name)

    bender_parameter, bender_data_to_plot = calculate_bender_correction(input_parameters)

    widget.M1_out = round(bender_parameter[0], int(6 * widget.workspace_units_to_mm))
    if widget.shape == TRAPEZIUM:
        widget.e_out = round(bender_parameter[1], 5)
        if widget.kind_of_bender == DOUBLE_MOMENTUM: widget.ratio_out = round(bender_parameter[2], 5)
    elif widget.shape == RECTANGLE:
        if widget.kind_of_bender == DOUBLE_MOMENTUM: widget.ratio_out = round(bender_parameter[1], 5)

    ST.write_shadow_surface(bender_data_to_plot.z_bender_correction.T, numpy.round(x, 6), numpy.round(y, 6), widget.output_file_name_full)

    # Add new surface as figure error
    shadow_oe._oe.F_RIPPLE = 1
    shadow_oe._oe.F_G_S = 2
    shadow_oe._oe.FILE_RIP = bytes(widget.output_file_name_full, 'utf-8')

    return shadow_oe, bender_data_to_plot
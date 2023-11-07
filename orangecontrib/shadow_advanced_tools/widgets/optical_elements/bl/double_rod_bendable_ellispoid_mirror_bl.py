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

import numpy

from orangecontrib.shadow.util.shadow_util import ShadowPreProcessor

from Shadow import ShadowTools as ST

from syned.tools.benders.double_rod_bendable_ellispoid_mirror import DoubleRodBenderParameters, calculate_bender_correction

def apply_bender_surface(widget, shadow_oe):
    x = numpy.linspace(-widget.dim_x_minus, widget.dim_x_plus, widget.bender_bin_x + 1)
    y = numpy.linspace(-widget.dim_y_minus, widget.dim_y_plus, widget.bender_bin_y + 1)

    input_parameters = DoubleRodBenderParameters()
    input_parameters.x                     = x
    input_parameters.y                     = y
    input_parameters.W1                    = widget.dim_x_plus + widget.dim_x_minus
    input_parameters.L                     = widget.dim_y_plus + widget.dim_y_minus  # add optimization length
    input_parameters.p                     = widget.object_side_focal_distance
    input_parameters.q                     = widget.image_side_focal_distance
    input_parameters.grazing_angle         = numpy.radians(90 - widget.incidence_angle_respect_to_normal)
    if widget.which_length == 1: input_parameters.optimized_length = widget.optimized_length
    input_parameters.E                     = widget.E
    input_parameters.h                     = widget.h
    input_parameters.r                     = widget.r
    input_parameters.l                     = widget.l
    input_parameters.R0                    = widget.R0
    input_parameters.R0_max                = widget.R0_max
    input_parameters.R0_min                = widget.R0_min
    input_parameters.R0_fixed              = widget.R0_fixed
    input_parameters.eta                   = widget.eta
    input_parameters.eta_max               = widget.eta_max
    input_parameters.eta_min               = widget.eta_min
    input_parameters.eta_fixed             = widget.eta_fixed
    input_parameters.W2                    = widget.W2
    input_parameters.W2_max                = widget.W2_max
    input_parameters.W2_min                = widget.W2_min
    input_parameters.W2_fixed              = widget.W2_fixed
    input_parameters.n_fit_steps           = widget.n_fit_steps
    input_parameters.workspace_units_to_m  = widget.workspace_units_to_m
    input_parameters.workspace_units_to_mm = widget.workspace_units_to_mm
    if widget.modified_surface == 1 and widget.ms_type_of_defect == 2:
        input_parameters.figure_error = ShadowPreProcessor.read_surface_error_file(widget.ms_defect_file_name)

    bender_parameter, bender_data_to_plot = calculate_bender_correction(input_parameters)

    widget.R0_out  = round(bender_parameter[0], 5)
    widget.eta_out = bender_parameter[1]
    widget.W2_out  = round(bender_parameter[2], 3)

    widget.alpha           = bender_parameter[3]
    widget.W0              = bender_parameter[4]
    widget.F_upstream      = bender_parameter[5]
    widget.F_downstream    = bender_parameter[6]

    ST.write_shadow_surface(bender_data_to_plot.z_bender_correction.T, numpy.round(x, 6), numpy.round(y, 6), widget.output_file_name_full)

    # Add new surface as figure error
    shadow_oe._oe.F_RIPPLE = 1
    shadow_oe._oe.F_G_S = 2
    shadow_oe._oe.FILE_RIP = bytes(widget.output_file_name_full, 'utf-8')

    return bender_data_to_plot



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
from Shadow import ShadowTools as ST
from orangecontrib.shadow.util.shadow_util import ShadowPreProcessor

from syned.tools.benders.aps_bendable_ellipsoid_mirror import ApsBenderParameters, calculate_bender_correction, TRAPEZIUM, DOUBLE_MOMENTUM

def apply_bender_surface(widget, shadow_oe):
    input_parameters = ApsBenderParameters(dim_x_minus           = widget.dim_x_minus,
                                           dim_x_plus            = widget.dim_x_plus,
                                           bender_bin_x          = widget.bender_bin_x,
                                           dim_y_minus           = widget.dim_y_minus,
                                           dim_y_plus            = widget.dim_y_plus,
                                           bender_bin_y          = widget.bender_bin_y,
                                           optimized_length      = widget.optimized_length if widget.which_length==1 else None,
                                           p                     = widget.object_side_focal_distance,
                                           q                     = widget.image_side_focal_distance,
                                           grazing_angle         = numpy.radians(90 - widget.incidence_angle_respect_to_normal),
                                           E                     = widget.E,
                                           h                     = widget.h,
                                           figure_error_mesh     = ShadowPreProcessor.read_surface_error_file(widget.ms_defect_file_name) if (widget.modified_surface==1 and widget.ms_type_of_defect==2) else None,
                                           n_fit_steps           = widget.n_fit_steps,
                                           workspace_units_to_m  = widget.workspace_units_to_m,
                                           workspace_units_to_mm = widget.workspace_units_to_mm,
                                           shape                 = widget.shape,
                                           kind_of_bender        = widget.kind_of_bender,
                                           M1                    = widget.M1,
                                           M1_min                = widget.M1_min,
                                           M1_max                = widget.M1_max,
                                           M1_fixed              = widget.M1_fixed,
                                           e                     = widget.e,
                                           e_min                 = widget.e_min,
                                           e_max                 = widget.e_max,
                                           e_fixed               = widget.e_fixed,
                                           ratio                 = widget.ratio,
                                           ratio_min             = widget.ratio_min,
                                           ratio_max             = widget.ratio_max,
                                           ratio_fixed           = widget.ratio_fixed)

    bender_data = calculate_bender_correction(input_parameters)

    widget.M1_out = bender_data.M1_out
    if widget.shape == TRAPEZIUM:                widget.e_out     = bender_data.e_out
    if widget.kind_of_bender == DOUBLE_MOMENTUM: widget.ratio_out = bender_data.ratio_out

    ST.write_shadow_surface(bender_data.z_bender_correction.T, numpy.round(bender_data.x, 6), numpy.round(bender_data.y, 6), widget.output_file_name_full)

    # Add new surface as figure error
    shadow_oe._oe.F_RIPPLE = 1
    shadow_oe._oe.F_G_S = 2
    shadow_oe._oe.FILE_RIP = bytes(widget.output_file_name_full, 'utf-8')

    return bender_data
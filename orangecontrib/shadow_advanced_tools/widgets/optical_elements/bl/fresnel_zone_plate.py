#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------- #
# Copyright (c) 2024, UChicago Argonne, LLC. All rights reserved.         #
#                                                                         #
# Copyright 2024. UChicago Argonne, LLC. This software was produced       #
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
import copy
from typing import Tuple

from hybrid_methods.fresnel_zone_plate.hybrid_fresnel_zone_plate import HybridFresnelZonePlate, FZPAttributes, FZPSimulatorOptions, FZPCalculationInputParameters, FZPCalculationResult

from orangecontrib.shadow.util.shadow_objects import ShadowOpticalElement, ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowPhysics
from srxraylib.util.inverse_method_sampler import Sampler2D

GOOD = 1

class ShadowFresnelZonePlate(HybridFresnelZonePlate):
    def __init__(self,
                 options: FZPSimulatorOptions,
                 attributes: FZPAttributes,
                 widget):
        super(ShadowFresnelZonePlate, self).__init__(options=options, attributes=attributes)
        self.__widget = widget

    def get_zp_focal_distance(self): return self._simulator.zp_focal_distance / self.__widget.workspace_units_to_m
    def get_zp_image_distance(self):    return self._simulator.zp_image_distance / self.__widget.workspace_units_to_m

    def _get_zone_plate_aperture_beam(self, attributes: FZPAttributes, **kwargs) -> Tuple[ShadowBeam, float]:
        empty_element = ShadowOpticalElement.create_empty_oe()

        empty_element._oe.DUMMY        = self.__widget.workspace_units_to_cm
        empty_element._oe.T_SOURCE     = self.__widget.source_plane_distance
        empty_element._oe.T_IMAGE      = 0.0
        empty_element._oe.T_INCIDENCE  = 0.0
        empty_element._oe.T_REFLECTION = 180.0
        empty_element._oe.ALPHA        = 0.0

        empty_element._oe.FWRITE  = 3
        empty_element._oe.F_ANGLE = 0

        n_screen = 1
        i_screen = numpy.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        i_abs = numpy.zeros(10)
        i_slit = numpy.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        i_stop = numpy.zeros(10)
        k_slit = numpy.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        thick = numpy.zeros(10)
        file_abs = numpy.array(['', '', '', '', '', '', '', '', '', ''])
        rx_slit = numpy.zeros(10)
        rz_slit = numpy.zeros(10)
        sl_dis = numpy.zeros(10)
        file_scr_ext = numpy.array(['', '', '', '', '', '', '', '', '', ''])
        cx_slit = numpy.zeros(10)
        cz_slit = numpy.zeros(10)

        sl_dis[0] = 0.0
        rx_slit[0] = attributes.diameter / self.__widget.workspace_units_to_m
        rz_slit[0] = attributes.diameter / self.__widget.workspace_units_to_m
        cx_slit[0] = 0.0
        cz_slit[0] = 0.0

        empty_element._oe.set_screens(n_screen,
                                      i_screen,
                                      i_abs,
                                      sl_dis,
                                      i_slit,
                                      i_stop,
                                      k_slit,
                                      thick,
                                      file_abs,
                                      rx_slit,
                                      rz_slit,
                                      cx_slit,
                                      cz_slit,
                                      file_scr_ext)

        output_beam = ShadowBeam.traceFromOE(self.__widget.input_beam, empty_element, history=True, widget_class_name=type(self.__widget).__name__)
        energy      = numpy.round(ShadowPhysics.getEnergyFromShadowK(numpy.average(output_beam._beam.rays[numpy.where(output_beam._beam.rays[:, 9] == GOOD), 10])), 2)

        return output_beam, 1e-3*energy

    def _get_ideal_lens_beam(self, zone_plate_beam: ShadowBeam, **kwargs) -> ShadowBeam:
        ideal_lens = ShadowOpticalElement.create_ideal_lens()

        focal_distance = self.get_zp_focal_distance()

        ideal_lens._oe.focal_x = focal_distance
        ideal_lens._oe.focal_z = focal_distance

        ideal_lens._oe.user_units_to_cm = self.__widget.workspace_units_to_cm
        ideal_lens._oe.T_SOURCE         = 0.0
        ideal_lens._oe.T_IMAGE          = 0.0 # hybrid screen!

        return ShadowBeam.traceIdealLensOE(zone_plate_beam, ideal_lens, history=True)

    def _apply_convolution_to_rays(self, output_beam: ShadowBeam, calculation_result: FZPCalculationResult, **kwargs):
        go = numpy.where(output_beam._beam.rays[:, 9] == GOOD)

        dx_ray = numpy.arctan(output_beam._beam.rays[go, 3] / output_beam._beam.rays[go, 4])  # calculate divergence from direction cosines from SHADOW file  dx = atan(v_x/v_y)
        dz_ray = numpy.arctan(output_beam._beam.rays[go, 5] / output_beam._beam.rays[go, 4])  # calculate divergence from direction cosines from SHADOW file  dz = atan(v_z/v_y)

        s2d = Sampler2D(calculation_result.dif_xpzp, calculation_result.xp, calculation_result.zp)

        pos_dif_x, pos_dif_z = s2d.get_n_sampled_points(dx_ray.shape[1])

        # new divergence distribution: convolution
        dx_conv = dx_ray + numpy.arctan(pos_dif_x)  # add the ray divergence kicks
        dz_conv = dz_ray + numpy.arctan(pos_dif_z)  # add the ray divergence kicks

        # correction to the position with the divergence kick from the waveoptics calculation
        # the correction is made on the positions at the hybrid screen (T_IMAGE = 0)
        if self._simulator.image_distance is None: image_distance = self.get_zp_image_distance()
        else:                                      image_distance = self._simulator.image_distance/self.__widget.workspace_units_to_m

        xx_image = output_beam._beam.rays[go, 0] + image_distance * numpy.tan(dx_conv) # ray tracing to the image plane
        zz_image = output_beam._beam.rays[go, 2] + image_distance * numpy.tan(dz_conv) # ray tracing to the image plane

        output_beam._oe_number = self.__widget.input_beam._oe_number + 1

        angle_num = numpy.sqrt(1 + (numpy.tan(dz_conv)) ** 2 + (numpy.tan(dx_conv)) ** 2)

        output_beam._beam.rays[go, 0] = copy.deepcopy(xx_image)
        output_beam._beam.rays[go, 2] = copy.deepcopy(zz_image)
        output_beam._beam.rays[go, 3] = numpy.tan(dx_conv) / angle_num
        output_beam._beam.rays[go, 4] = 1 / angle_num
        output_beam._beam.rays[go, 5] = numpy.tan(dz_conv) / angle_num
        #----------------------------------------------------------------------------------------

        efficiency_factor = numpy.sqrt(calculation_result.efficiency)

        output_beam._beam.rays[go, 6] *= efficiency_factor
        output_beam._beam.rays[go, 7] *= efficiency_factor
        output_beam._beam.rays[go, 8] *= efficiency_factor
        output_beam._beam.rays[go, 15] *= efficiency_factor
        output_beam._beam.rays[go, 16] *= efficiency_factor
        output_beam._beam.rays[go, 17] *= efficiency_factor


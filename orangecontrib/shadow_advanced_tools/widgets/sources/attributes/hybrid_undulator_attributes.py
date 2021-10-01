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
import sys

from settings import Setting

class HybridUndulatorAttributes():
    distribution_source = Setting(0)

    # SRW INPUT
    cumulated_view_type = Setting(0)

    number_of_periods = Setting(184)  # Number of ID Periods (without counting for terminations
    undulator_period = Setting(0.025)  # Period Length [m]
    Kv = Setting(0.857)
    Kh = Setting(0)
    Bh = Setting(0.0)
    Bv = Setting(1.5)

    magnetic_field_from = Setting(0)

    initial_phase_vertical = Setting(0.0)
    initial_phase_horizontal = Setting(0.0)

    symmetry_vs_longitudinal_position_vertical = Setting(1)
    symmetry_vs_longitudinal_position_horizontal = Setting(0)

    horizontal_central_position = Setting(0.0)
    vertical_central_position = Setting(0.0)
    longitudinal_central_position = Setting(0.0)

    electron_energy_in_GeV = Setting(6.0)
    electron_energy_spread = Setting(1.35e-3)
    ring_current = Setting(0.2)
    electron_beam_size_h = Setting(1.45e-05)
    electron_beam_size_v = Setting(2.8e-06)
    electron_beam_divergence_h = Setting(2.9e-06)
    electron_beam_divergence_v = Setting(1.5e-06)

    auto_expand = Setting(0)
    auto_expand_rays = Setting(0)

    type_of_initialization = Setting(0)

    moment_x = Setting(0.0)
    moment_y = Setting(0.0)
    moment_z = Setting(0.0)
    moment_xp = Setting(0.0)
    moment_yp = Setting(0.0)

    source_dimension_wf_h_slit_gap = Setting(0.0015)
    source_dimension_wf_v_slit_gap = Setting(0.0015)
    source_dimension_wf_h_slit_points = Setting(301)
    source_dimension_wf_v_slit_points = Setting(301)
    source_dimension_wf_distance = Setting(28.0)

    horizontal_range_modification_factor_at_resizing = Setting(0.5)
    horizontal_resolution_modification_factor_at_resizing = Setting(5.0)
    vertical_range_modification_factor_at_resizing = Setting(0.5)
    vertical_resolution_modification_factor_at_resizing = Setting(5.0)

    waist_position_calculation = Setting(0)
    waist_position = Setting(0.0)

    waist_position_auto = Setting(0)
    waist_position_auto_h = Setting(0.0)
    waist_position_auto_v = Setting(0.0)
    waist_back_propagation_parameters = Setting(1)
    waist_horizontal_range_modification_factor_at_resizing = Setting(0.5)
    waist_horizontal_resolution_modification_factor_at_resizing = Setting(5.0)
    waist_vertical_range_modification_factor_at_resizing = Setting(0.5)
    waist_vertical_resolution_modification_factor_at_resizing = Setting(5.0)
    which_waist = Setting(2)
    number_of_waist_fit_points = Setting(10)
    degree_of_waist_fit = Setting(3)
    use_sigma_or_fwhm = Setting(0)

    waist_position_user_defined = Setting(0.0)

    kind_of_sampler = Setting(1)
    save_srw_result = Setting(0)

    # SRW FILE INPUT

    source_dimension_srw_file = Setting("intensity_source_dimension.dat")
    angular_distribution_srw_file = Setting("intensity_angular_distribution.dat")

    # ASCII FILE INPUT

    x_positions_file = Setting("x_positions.txt")
    z_positions_file = Setting("z_positions.txt")
    x_positions_factor = Setting(0.01)
    z_positions_factor = Setting(0.01)
    x_divergences_file = Setting("x_divergences.txt")
    z_divergences_file = Setting("z_divergences.txt")
    x_divergences_factor = Setting(1.0)
    z_divergences_factor = Setting(1.0)

    combine_strategy = Setting(0)

    # SHADOW SETTINGS

    number_of_rays = Setting(5000)
    seed = Setting(6775431)

    use_harmonic = Setting(0)
    harmonic_number = Setting(1)
    harmonic_energy = 0.0
    energy = Setting(10000.0)
    energy_to = Setting(10100.0)
    energy_points = Setting(10)

    polarization = Setting(1)
    coherent_beam = Setting(0)
    phase_diff = Setting(0.0)
    polarization_degree = Setting(1.0)

    optimize_source = Setting(0)
    optimize_file_name = Setting("NONESPECIFIED")
    max_number_of_rejected_rays = Setting(10000000)

    file_to_write_out = Setting(0)

    auto_energy = Setting(0.0)
    auto_harmonic_number = Setting(1)

    energy_step = None
    power_step = None
    current_step = None
    total_steps = None
    start_event = True
    compute_power = False
    integrated_flux = None
    power_density = None

    cumulated_energies = None
    cumulated_integrated_flux = None
    cumulated_power_density = None
    cumulated_power = None

    def get_write_file_options(self):
        write_begin_file = 0
        write_start_file = 0
        write_end_file = 0

        if self.file_to_write_out == 1:
            write_begin_file = 1
        if self.file_to_write_out == 2:
            write_begin_file = 1

            if sys.platform == 'linux':
                print("Warning", "Debug Mode is not yet available for sources in Linux platforms")
            else:
                write_start_file = 1
                write_end_file = 1

        return write_begin_file, write_start_file, write_end_file

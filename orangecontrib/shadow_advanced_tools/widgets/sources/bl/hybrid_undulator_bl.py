#!/usr/bin/env python
# -*- coding: utf-8 -*-
# #########################################################################
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
# #########################################################################

import numpy
import time
from numpy.matlib import repmat
from scipy.signal import convolve2d

from oasys.widgets import congruence
from oasys.util.oasys_util import get_fwhm, get_sigma

from srxraylib.util.inverse_method_sampler import Sampler2D

from orangecontrib.shadow.util.shadow_objects import ShadowBeam, ShadowSource
from orangecontrib.shadow.util.shadow_util import ShadowPhysics

from oasys.util.random_distributions import Distribution2D, Grid2D, distribution_from_grid
from oasys.util.custom_distribution import CustomDistribution

import scipy.constants as codata

m2ev = codata.c * codata.h / codata.e

from oasys_srw.srwlib import *
from oasys_srw.srwlib import array as srw_array

class Distribution:
    POSITION = 0
    DIVERGENCE = 1

####################################################################################
# SIMULATION ALGORITHM
####################################################################################

def __check_fields(widget):
    widget.number_of_rays = congruence.checkPositiveNumber(widget.number_of_rays, "Number of rays")
    widget.seed = congruence.checkPositiveNumber(widget.seed, "Seed")

    if widget.use_harmonic == 0:
        if widget.distribution_source != 0: raise Exception("Harmonic Energy can be computed only for explicit SRW Calculation")

        widget.harmonic_number = congruence.checkStrictlyPositiveNumber(widget.harmonic_number, "Harmonic Number")
    elif widget.use_harmonic == 2:
        if widget.distribution_source != 0: raise Exception("Energy Range can be computed only for explicit SRW Calculation")

        widget.energy        = congruence.checkStrictlyPositiveNumber(widget.energy, "Photon Energy From")
        widget.energy_to     = congruence.checkStrictlyPositiveNumber(widget.energy_to, "Photon Energy To")
        widget.energy_points = congruence.checkStrictlyPositiveNumber(widget.energy_points, "Nr. Energy Values")
        congruence.checkGreaterThan(widget.energy_to, widget.energy, "Photon Energy To", "Photon Energy From")
    else:
        widget.energy = congruence.checkStrictlyPositiveNumber(widget.energy, "Photon Energy")

    if widget.optimize_source > 0:
        widget.max_number_of_rejected_rays = congruence.checkPositiveNumber(widget.max_number_of_rejected_rays,
                                                                         "Max number of rejected rays")
        congruence.checkFile(widget.optimize_file_name)

def __populate_fields(widget, shadow_src):
    shadow_src.src.NPOINT = widget.number_of_rays if widget.auto_expand==0 else (widget.number_of_rays if widget.auto_expand_rays==0 else int(numpy.ceil(widget.number_of_rays*1.1)))
    shadow_src.src.ISTAR1 = widget.seed
    shadow_src.src.F_OPD = 1
    shadow_src.src.F_SR_TYPE = 0

    shadow_src.src.FGRID = 0
    shadow_src.src.IDO_VX = 0
    shadow_src.src.IDO_VZ = 0
    shadow_src.src.IDO_X_S = 0
    shadow_src.src.IDO_Y_S = 0
    shadow_src.src.IDO_Z_S = 0

    shadow_src.src.FSOUR = 0 # spatial_type (point)
    shadow_src.src.FDISTR = 1 # angular_distribution (flat)

    shadow_src.src.HDIV1 = -1.0e-6
    shadow_src.src.HDIV2 = 1.0e-6
    shadow_src.src.VDIV1 = -1.0e-6
    shadow_src.src.VDIV2 = 1.0e-6

    shadow_src.src.FSOURCE_DEPTH = 1 # OFF

    shadow_src.src.F_COLOR = 1 # single value
    shadow_src.src.F_PHOT = 0 # eV , 1 Angstrom

    shadow_src.src.PH1 = widget.energy if widget.use_harmonic !=0 else resonance_energy(widget, harmonic=widget.harmonic_number)

    shadow_src.src.F_POLAR = widget.polarization

    if widget.polarization == 1:
        shadow_src.src.F_COHER = widget.coherent_beam
        shadow_src.src.POL_ANGLE = widget.phase_diff
        shadow_src.src.POL_DEG = widget.polarization_degree

    shadow_src.src.F_OPD = 1
    shadow_src.src.F_BOUND_SOUR = widget.optimize_source
    if widget.optimize_source > 0: shadow_src.src.FILE_BOUND = bytes(congruence.checkFileName(widget.optimize_file_name), 'utf-8')
    shadow_src.src.NTOTALPOINT = widget.max_number_of_rejected_rays

def __generate_initial_beam(widget):
    ###########################################
    # TODO: TO BE ADDED JUST IN CASE OF BROKEN
    #       ENVIRONMENT: MUST BE FOUND A PROPER WAY
    #       TO TEST SHADOW
    widget.fixWeirdShadowBug()
    ###########################################

    shadow_src = ShadowSource.create_src()

    __populate_fields(widget, shadow_src)
    
    widget.setStatusMessage("Running SHADOW")
    
    write_begin_file, write_start_file, write_end_file = widget.get_write_file_options()
   
    beam_out = ShadowBeam.traceFromSource(shadow_src,
                                          write_begin_file=write_begin_file,
                                          write_start_file=write_start_file,
                                          write_end_file=write_end_file)

    # WEIRD MEMORY INITIALIZATION BY FORTRAN. JUST A FIX.
    def fix_Intensity(widget, beam_out):
        if widget.polarization == 0:
            for index in range(0, len(beam_out._beam.rays)):
                beam_out._beam.rays[index, 15] = 0
                beam_out._beam.rays[index, 16] = 0
                beam_out._beam.rays[index, 17] = 0

    fix_Intensity(widget, beam_out)
   
    return beam_out

def __apply_undulator_distributions_calculation(widget, beam_out, do_cumulated_calculations):
    if widget.use_harmonic == 2:
        energy_points = int(widget.energy_points)
        x_array = numpy.full(energy_points, None)
        z_array = numpy.full(energy_points, None)
        intensity_source_dimension_array = numpy.full(energy_points, None)
        x_first_array = numpy.full(energy_points, None)
        z_first_array = numpy.full(energy_points, None)
        intensity_angular_distribution_array = numpy.full(energy_points, None)
        integrated_flux_array = numpy.zeros(energy_points)
        nr_rays_array = numpy.zeros(energy_points)
        energies = numpy.linspace(widget.energy, widget.energy_to, energy_points)
        prog_bars = numpy.linspace(20, 50, energy_points)
        total_power = None

        delta_e = energies[1] - energies[0]

        for energy, i in zip(energies, range(energy_points)):
            widget.setStatusMessage("Running SRW for energy: " + str(energy))

            x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution, integrated_flux, _ = __run_SRW_calculation(widget, energy, False)

            x_array[i] = x
            z_array[i] = z
            intensity_source_dimension_array[i] = intensity_source_dimension
            x_first_array[i] = x_first
            z_first_array[i] = z_first
            intensity_angular_distribution_array[i] = intensity_angular_distribution
            integrated_flux_array[i] = integrated_flux * delta_e / (0.001 * energy)  # switch to BW = energy step
            nr_rays_array[i] = widget.number_of_rays * integrated_flux_array[i]

            widget.progressBarSet(prog_bars[i])

        nr_rays_array /= numpy.sum(integrated_flux_array)

        first_index = 0
        prog_bars = numpy.linspace(50, 80, energy_points)
        current_seed = time.time() if widget.seed == 0 else widget.seed
        random.seed(current_seed)

        for energy, i in zip(energies, range(energy_points)):
            last_index = min(first_index + int(nr_rays_array[i]), len(beam_out._beam.rays))

            temp_beam = ShadowBeam()
            temp_beam._beam.rays = beam_out._beam.rays[first_index:last_index]

            temp_beam._beam.rays[:, 10] = ShadowPhysics.getShadowKFromEnergy(numpy.random.uniform(energy, energy + delta_e, size=len(temp_beam._beam.rays)))

            widget.setStatusMessage("Applying new Spatial/Angular Distribution for energy: " + str(energy))

            __generate_user_defined_distribution_from_srw(beam_out=temp_beam,
                                                          coord_x=x_array[i],
                                                          coord_z=z_array[i],
                                                          intensity=intensity_source_dimension_array[i],
                                                          distribution_type=Distribution.POSITION,
                                                          kind_of_sampler=widget.kind_of_sampler,
                                                          seed=current_seed + 1)

            __generate_user_defined_distribution_from_srw(beam_out=temp_beam,
                                                          coord_x=x_first_array[i],
                                                          coord_z=z_first_array[i],
                                                          intensity=intensity_angular_distribution_array[i],
                                                          distribution_type=Distribution.DIVERGENCE,
                                                          kind_of_sampler=widget.kind_of_sampler,
                                                          seed=current_seed + 2)

            widget.progressBarSet(prog_bars[i])

            current_seed += 2
            first_index = last_index

        if not last_index == len(beam_out._beam.rays):
            excluded_rays = beam_out._beam.rays[last_index:]
            excluded_rays[:, 9] = -999

        beam_out.set_initial_flux(None)
    else:
        integrated_flux = None

        energy = widget.energy if widget.use_harmonic == 1 else resonance_energy(widget, harmonic=widget.harmonic_number)

        if widget.distribution_source == 0:
            widget.setStatusMessage("Running SRW")

            x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution, integrated_flux, total_power = __run_SRW_calculation(widget, energy, do_cumulated_calculations)
        elif widget.distribution_source == 1:
            widget.setStatusMessage("Loading SRW files")

            x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution = __load_SRW_files(widget)
            total_power = None
        elif widget.distribution_source == 2:  # ASCII FILES
            widget.setStatusMessage("Loading Ascii files")

            x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution = __load_ASCII_files(widget)
            total_power = None

        beam_out.set_initial_flux(integrated_flux)

        widget.progressBarSet(50)

        widget.setStatusMessage("Applying new Spatial/Angular Distribution")

        widget.progressBarSet(60)

        __generate_user_defined_distribution_from_srw(beam_out=beam_out,
                                                      coord_x=x,
                                                      coord_z=z,
                                                      intensity=intensity_source_dimension,
                                                      distribution_type=Distribution.POSITION,
                                                      kind_of_sampler=widget.kind_of_sampler,
                                                      seed=time.time() if widget.seed == 0 else widget.seed + 1)

        widget.progressBarSet(70)

        __generate_user_defined_distribution_from_srw(beam_out=beam_out,
                                                      coord_x=x_first,
                                                      coord_z=z_first,
                                                      intensity=intensity_angular_distribution,
                                                      distribution_type=Distribution.DIVERGENCE,
                                                      kind_of_sampler=widget.kind_of_sampler,
                                                      seed=time.time() if widget.seed == 0 else widget.seed + 2)

    if widget.distribution_source == 0 and is_canted_undulator(widget) and widget.waist_position != 0.0:
        beam_out._beam.retrace(-widget.waist_position / widget.workspace_units_to_m)  # put the beam at the center of the ID

    return total_power

####################################################################################
# FACADE
####################################################################################

def run_hybrid_undulator_simulation(widget, do_cumulated_calculations=False):
    __check_fields(widget)

    widget.progressBarSet(10)

    beam_out = __generate_initial_beam(widget)

    widget.progressBarSet(20)

    total_power = __apply_undulator_distributions_calculation(widget, beam_out, do_cumulated_calculations)

    return beam_out, total_power

def get_source_slit_data(widget, direction="b"):
    if widget.auto_expand==1:
        source_dimension_wf_h_slit_points = int(numpy.ceil(0.55 *widget.source_dimension_wf_h_slit_points )*2)
        source_dimension_wf_v_slit_points = int(numpy.ceil(0.55 *widget.source_dimension_wf_v_slit_points )*2)
        source_dimension_wf_h_slit_gap = widget.source_dimension_wf_h_slit_gap*1.1
        source_dimension_wf_v_slit_gap = widget.source_dimension_wf_v_slit_gap*1.1
    else:
        source_dimension_wf_h_slit_points = widget.source_dimension_wf_h_slit_points
        source_dimension_wf_v_slit_points = widget.source_dimension_wf_v_slit_points
        source_dimension_wf_h_slit_gap = widget.source_dimension_wf_h_slit_gap
        source_dimension_wf_v_slit_gap = widget.source_dimension_wf_v_slit_gap

    if direction=="h":   return source_dimension_wf_h_slit_points, source_dimension_wf_h_slit_gap
    elif direction=="v": return source_dimension_wf_v_slit_points, source_dimension_wf_v_slit_gap
    else:                return source_dimension_wf_h_slit_points, source_dimension_wf_h_slit_gap, source_dimension_wf_v_slit_points, source_dimension_wf_v_slit_gap

def set_which_waist(widget):
    if widget.which_waist == 0:  # horizontal
        widget.waist_position_auto = round(widget.waist_position_auto_h, 4)
    elif widget.which_waist == 1:  # vertical
        widget.waist_position_auto = round(widget.waist_position_auto_v, 4)
    else:  # middle point
        widget.waist_position_auto = round(0.5 * (widget.waist_position_auto_h + widget.waist_position_auto_v), 4)

def gamma(widget):
    return 1e9*widget.electron_energy_in_GeV / (codata.m_e * codata.c**2 / codata.e)

def resonance_energy(widget, theta_x=0.0, theta_z=0.0, harmonic=1):
    g = gamma(widget)

    wavelength = ((widget.undulator_period / (2.0*g**2)) * \
                 (1 + widget.Kv**2 / 2.0 + widget.Kh**2 / 2.0 + \
                  g**2 * (theta_x**2 + theta_z**2))) / harmonic

    return m2ev/wavelength

def get_default_initial_z(widget):
    return widget.longitudinal_central_position-0.5*widget.undulator_period*(widget.number_of_periods + 8) # initial Longitudinal Coordinate (set before the ID)

def is_canted_undulator(widget):
    return widget.longitudinal_central_position != 0.0

####################################################################################
# SRW CALCULATION
####################################################################################

def __get_minimum_propagation_distance(widget):
    return round(__get_source_length(widget) * 1.01, 6)

def __get_source_length(widget):
    return widget.undulator_period *widget.number_of_periods

def __magnetic_field_from_K(widget):
    Bv = widget.Kv * 2 * pi * codata.m_e * codata.c / (codata.e * widget.undulator_period)
    Bh = widget.Kh * 2 * pi * codata.m_e * codata.c / (codata.e * widget.undulator_period)

    return Bv, Bh

def __create_undulator(widget, no_shift=False):
    # ***********Undulator
    if widget.magnetic_field_from == 0:
        By, Bx = __magnetic_field_from_K(widget)  # Peak Vertical field [T]
    else:
        By = widget.Bv
        Bx = widget.Bh

    symmetry_vs_longitudinal_position_horizontal = 1 if widget.symmetry_vs_longitudinal_position_horizontal == 0 else -1
    symmetry_vs_longitudinal_position_vertical = 1 if widget.symmetry_vs_longitudinal_position_vertical == 0 else -1

    und = SRWLMagFldU([SRWLMagFldH(1, 'h',
                                   _B=Bx,
                                   _ph=widget.initial_phase_horizontal,
                                   _s=symmetry_vs_longitudinal_position_horizontal,
                                   _a=1.0),
                       SRWLMagFldH(1, 'v',
                                   _B=By,
                                   _ph=widget.initial_phase_vertical,
                                   _s=symmetry_vs_longitudinal_position_vertical,
                                   _a=1)],
                      widget.undulator_period, widget.number_of_periods)  # Planar Undulator

    if no_shift:
        magFldCnt = SRWLMagFldC(_arMagFld=[und],
                                _arXc = array('d', [0.0]),
                                _arYc = array('d', [0.0]),
                                _arZc = array('d', [0.0]))  # Container of all Field Elements
    else:
        magFldCnt = SRWLMagFldC(_arMagFld=[und],
                                _arXc = array('d', [widget.horizontal_central_position]),
                                _arYc = array('d', [widget.vertical_central_position]),
                                _arZc = array('d', [widget.longitudinal_central_position])  )  # Container of all Field Elements

    return magFldCnt

def __create_electron_beam(widget, distribution_type=Distribution.DIVERGENCE, position=0.0, use_nominal=False):
    # ***********Electron Beam
    elecBeam = SRWLPartBeam()

    electron_beam_size_h = widget.electron_beam_size_h if use_nominal else \
        numpy.sqrt(widget.electron_beam_size_h ** 2 + (numpy.abs(widget.longitudinal_central_position + position) * numpy.tan(widget.electron_beam_divergence_h)) ** 2)
    electron_beam_size_v = widget.electron_beam_size_v if use_nominal else \
        numpy.sqrt(widget.electron_beam_size_v ** 2 + (numpy.abs(widget.longitudinal_central_position + position) * numpy.tan(widget.electron_beam_divergence_v)) ** 2)

    if widget.type_of_initialization == 0: # zero
        widget.moment_x = 0.0
        widget.moment_y = 0.0
        widget.moment_z = get_default_initial_z(widget)
        widget.moment_xp = 0.0
        widget.moment_yp = 0.0
    elif widget.type_of_initialization == 2: # sampled
        widget.moment_x = numpy.random.normal(0.0, electron_beam_size_h)
        widget.moment_y = numpy.random.normal(0.0, electron_beam_size_v)
        widget.moment_z = get_default_initial_z(widget)
        widget.moment_xp = numpy.random.normal(0.0, widget.electron_beam_divergence_h)
        widget.moment_yp = numpy.random.normal(0.0, widget.electron_beam_divergence_v)

    elecBeam.partStatMom1.x = widget.moment_x
    elecBeam.partStatMom1.y = widget.moment_y
    elecBeam.partStatMom1.z = widget.moment_z
    elecBeam.partStatMom1.xp = widget.moment_xp
    elecBeam.partStatMom1.yp = widget.moment_yp
    elecBeam.partStatMom1.gamma = gamma(widget)

    elecBeam.Iavg = widget.ring_current  # Average Current [A]

    # 2nd order statistical moments
    elecBeam.arStatMom2[0] = 0 if distribution_type==Distribution.DIVERGENCE else (electron_beam_size_h )**2  # <(x-x0)^2>
    elecBeam.arStatMom2[1] = 0
    elecBeam.arStatMom2[2] = (widget.electron_beam_divergence_h )**2  # <(x'-x'0)^2>
    elecBeam.arStatMom2[3] = 0 if distribution_type==Distribution.DIVERGENCE else (electron_beam_size_v )**2  # <(y-y0)^2>
    elecBeam.arStatMom2[4] = 0
    elecBeam.arStatMom2[5] = (widget.electron_beam_divergence_v )**2  # <(y'-y'0)^2>
    # energy spread
    elecBeam.arStatMom2[10] = (widget.electron_energy_spread )**2  # <(E-E0)^2>/E0^2

    return elecBeam

def __create_initial_wavefront_mesh(widget, elecBeam, energy):
    # ****************** Initial Wavefront
    wfr = SRWLWfr()  # For intensity distribution at fixed photon energy

    source_dimension_wf_h_slit_points, \
    source_dimension_wf_h_slit_gap, \
    source_dimension_wf_v_slit_points, \
    source_dimension_wf_v_slit_gap = get_source_slit_data(widget, direction="b")

    wfr.allocate(1, source_dimension_wf_h_slit_points, source_dimension_wf_v_slit_points)  # Numbers of points vs Photon Energy, Horizontal and Vertical Positions
    wfr.mesh.zStart = widget.source_dimension_wf_distance + widget.longitudinal_central_position  # Longitudinal Position [m] from Center of Straight Section at which SR has to be calculated
    wfr.mesh.eStart = energy  # Initial Photon Energy [eV]
    wfr.mesh.eFin = wfr.mesh.eStart  # Final Photon Energy [eV]

    wfr.mesh.xStart = -0.5 *source_dimension_wf_h_slit_gap  # Initial Horizontal Position [m]
    wfr.mesh.xFin = -1 * wfr.mesh.xStart  # 0.00015 #Final Horizontal Position [m]
    wfr.mesh.yStart = -0.5 *source_dimension_wf_v_slit_gap  # Initial Vertical Position [m]
    wfr.mesh.yFin = -1 * wfr.mesh.yStart  # 0.00015 #Final Vertical Position [m]

    wfr.partBeam = elecBeam

    return wfr

def __get_calculation_precision_settings():
    # ***********Precision Parameters for SR calculation
    meth = 1  # SR calculation method: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler"
    relPrec = 0.01  # relative precision
    zStartInteg = 0  # longitudinal position to start integration (effective if < zEndInteg)
    zEndInteg = 0  # longitudinal position to finish integration (effective if > zStartInteg)
    npTraj = 100000  # Number of points for trajectory calculation
    useTermin = 1  # Use "terminating terms" (i.e. asymptotic expansions at zStartInteg and zEndInteg) or not (1 or 0 respectively)
    # This is the convergence parameter. Higher is more accurate but slower!!
    sampFactNxNyForProp = 0.0  # 0.6 #sampling factor for adjusting nx, ny (effective if > 0)

    return [meth, relPrec, zStartInteg, zEndInteg, npTraj, useTermin, sampFactNxNyForProp]

def __calculate_automatic_waste_position(widget, energy, do_plot=True):
    magFldCnt = __create_undulator(widget, no_shift=True)
    arPrecParSpec = __get_calculation_precision_settings()

    undulator_length = widget.number_of_periods * widget.undulator_period
    wavelength       = (codata.h * codata.c / codata.e ) /energy

    gauss_sigma_ph  = numpy.sqrt( 2 *wavelength *undulator_length ) /( 2 *numpy.pi)
    gauss_sigmap_ph = numpy.sqrt(wavelength /( 2 *undulator_length))

    positions     = numpy.linspace(start=-0.5 *undulator_length, stop=0.5 *undulator_length, num=widget.number_of_waist_fit_points)
    sizes_e_x     = numpy.zeros(widget.number_of_waist_fit_points)
    sizes_e_y     = numpy.zeros(widget.number_of_waist_fit_points)
    sizes_ph_x    = numpy.zeros(widget.number_of_waist_fit_points)
    sizes_ph_y    = numpy.zeros(widget.number_of_waist_fit_points)
    sizes_ph_an_x = numpy.zeros(widget.number_of_waist_fit_points)
    sizes_ph_an_y = numpy.zeros(widget.number_of_waist_fit_points)
    sizes_tot_x   = numpy.zeros(widget.number_of_waist_fit_points)
    sizes_tot_y   = numpy.zeros(widget.number_of_waist_fit_points)


    for i in range(widget.number_of_waist_fit_points):
        position = positions[i]

        elecBeam    = __create_electron_beam(widget, distribution_type=Distribution.POSITION, position=position, use_nominal=False)
        elecBeam_Ph = __create_electron_beam(widget, distribution_type=Distribution.POSITION, use_nominal=True)
        wfr         = __create_initial_wavefront_mesh(widget, elecBeam_Ph, energy)
        optBLSouDim = __create_beamline_source_dimension(widget,
                                                         back_position=(widget.source_dimension_wf_distance + widget.longitudinal_central_position - position),
                                                         waist_calculation=widget.waist_back_propagation_parameters==1)

        srwl.CalcElecFieldSR(wfr, 0, magFldCnt, arPrecParSpec)
        srwl.PropagElecField(wfr, optBLSouDim)

        arI = array('f', [0] * wfr.mesh.nx * wfr.mesh.ny)  # "flat" 2D array to take intensity data
        srwl.CalcIntFromElecField(arI, wfr, 6, 0, 3, wfr.mesh.eStart, 0, 0) # SINGLE ELECTRON!

        x, y, intensity_distribution = __transform_srw_array(arI, wfr.mesh)

        def get_size(position, coord, intensity_distribution, projection_axis, ebeam_index):
            sigma_e  = numpy.sqrt(elecBeam.arStatMom2[ebeam_index])
            histo    = numpy.sum(intensity_distribution, axis=projection_axis)
            sigma    = get_sigma(histo, coord) if widget.use_sigma_or_fwhm==0 else get_fwhm(histo, coord)[0 ] /2.355
            sigma_an = numpy.sqrt(gauss_sigma_ph**2 + (position *numpy.tan(gauss_sigmap_ph) )**2)

            if numpy.isnan(sigma): sigma = 0.0

            return sigma_e, sigma, sigma_an, numpy.sqrt(sigma**2 + sigma_e**2)

        sizes_e_x[i], sizes_ph_x[i], sizes_ph_an_x[i], sizes_tot_x[i] = get_size(position, x, intensity_distribution, 1, 0)
        sizes_e_y[i], sizes_ph_y[i], sizes_ph_an_y[i], sizes_tot_y[i] = get_size(position, y, intensity_distribution, 0, 3)

    def plot(widget, direction, positions, sizes_e, sizes_ph, size_ph_an, sizes_tot, waist_position, waist_size):
        widget.waist_axes[direction].clear()
        widget.waist_axes[direction].set_title(("Horizontal" if direction == 0 else "Vertical") + " Direction\n" +
                                             "Source size: " + str(round(waist_size * 1e6, 2)) + " " + r'$\mu$' + "m \n" +
                                             "at " + str(round(waist_position * 1e3, 1)) + " mm from the ID center")

        widget.waist_axes[direction].plot(positions*1e3, sizes_e *1e6,   label='electron', color='g')
        widget.waist_axes[direction].plot(positions*1e3, sizes_ph *1e6,  label='photon', color='b')
        widget.waist_axes[direction].plot(positions*1e3, size_ph_an *1e6,  '--', label='photon (analytical)', color='b')
        widget.waist_axes[direction].plot(positions*1e3, sizes_tot *1e6, label='total', color='r')
        widget.waist_axes[direction].plot([waist_position *1e3], [waist_size *1e6], 'bo', label="waist")
        widget.waist_axes[direction].set_xlabel("Position relative to ID center [mm]")
        widget.waist_axes[direction].set_ylabel("Sigma [um]")
        widget.waist_axes[direction].legend()

    def get_minimum(positions, sizes):
        coeffiecients = numpy.polyfit(positions, sizes, deg=widget.degree_of_waist_fit)
        p = numpy.poly1d(coeffiecients)
        bounds = [positions[0], positions[-1]]

        critical_points = numpy.array(bounds + [x for x in p.deriv().r if x.imag == 0 and bounds[0] < x.real < bounds[1]])
        critical_sizes = p(critical_points)

        minimum_value = numpy.inf
        minimum_position = numpy.nan

        for i in range(len(critical_points)):
            if critical_sizes[i] <= minimum_value:
                minimum_value = critical_sizes[i]
                minimum_position = critical_points[i]

        return minimum_position, minimum_value

    waist_position_x, waist_size_x = get_minimum(positions, sizes_tot_x)
    waist_position_y, waist_size_y = get_minimum(positions, sizes_tot_y)

    if do_plot:
        plot(widget, 0, positions, sizes_e_x, sizes_ph_x, sizes_ph_an_x, sizes_tot_x, waist_position_x, waist_size_x)
        plot(widget, 1, positions, sizes_e_y, sizes_ph_y, sizes_ph_an_y, sizes_tot_y, waist_position_y, waist_size_y)

        try:
            widget.waist_figure.draw()
        except ValueError as e:
            if "Image size of " in str(e): pass
            else: raise e

    return waist_position_x, waist_position_y

def __create_beamline_source_dimension(widget, back_position=0.0, waist_calculation=False):
    # ***************** Optical Elements and Propagation Parameters

    opDrift = SRWLOptD(-back_position) # back to waist position
    if not waist_calculation:
        ppDrift = [0, 0, 1., 1, 0,
                   widget.horizontal_range_modification_factor_at_resizing,
                   widget.horizontal_resolution_modification_factor_at_resizing,
                   widget.vertical_range_modification_factor_at_resizing,
                   widget.vertical_resolution_modification_factor_at_resizing,
                   0, 0, 0]
    else:
        ppDrift = [0, 0, 1., 1, 0,
                   widget.waist_horizontal_range_modification_factor_at_resizing,
                   widget.waist_horizontal_resolution_modification_factor_at_resizing,
                   widget.waist_vertical_range_modification_factor_at_resizing,
                   widget.waist_vertical_resolution_modification_factor_at_resizing,
                   0, 0, 0]

    return SRWLOptC([opDrift] ,[ppDrift])

def __transform_srw_array(output_array, mesh):
    h_array = numpy.linspace(mesh.xStart, mesh.xFin, mesh.nx)
    v_array = numpy.linspace(mesh.yStart, mesh.yFin, mesh.ny)

    intensity_array = numpy.zeros((h_array.size, v_array.size))

    tot_len = int(mesh.ny * mesh.nx)
    len_output_array = len(output_array)

    if len_output_array > tot_len:
        output_array = numpy.array(output_array[0:tot_len])
    elif len_output_array < tot_len:
        aux_array = srw_array('d', [0] * len_output_array)
        for i in range(len_output_array): aux_array[i] = output_array[i]
        output_array = numpy.array(srw_array(aux_array))
    else:
        output_array = numpy.array(output_array)

    output_array = output_array.reshape(mesh.ny, mesh.nx)

    for ix in range(mesh.nx):
        for iy in range(mesh.ny):
            intensity_array[ix, iy] = output_array[iy, ix]

    intensity_array[numpy.where(numpy.isnan(intensity_array)) ] =0.0

    return h_array, v_array, intensity_array

def __calculate_waist_position(widget, energy):
    if widget.distribution_source == 0: # SRW calculation
        if is_canted_undulator(widget):
            if widget.waist_position_calculation == 0:  # None
                widget.waist_position = 0.0
            elif widget.waist_position_calculation == 1:  # Automatic
                if widget.use_harmonic == 2: raise ValueError("Automatic calculation of the waist position for canted undulator is not allowed when Photon Energy Setting: Range")
                if widget.compute_power: raise ValueError("Automatic calculation of the waist position for canted undulator is not allowed while running a thermal load loop")

                widget.waist_position_auto_h, widget.waist_position_auto_v = __calculate_automatic_waste_position(widget, energy)

                set_which_waist(widget)

                widget.waist_position = widget.waist_position_auto

            elif widget.waist_position_calculation == 2:  # User Defined
                congruence.checkNumber(widget.waist_position_user_defined, "User Defined Waist Position")
                congruence.checkLessOrEqualThan(widget.waist_position_user_defined, widget.source_dimension_wf_distance, "Waist Position", "Propagation Distance")

                widget.waist_position = widget.waist_position_user_defined
        else:
            widget.waist_position = 0.0
    else:
        widget.waist_position = 0.0

def __check_SRW_fields(widget):
    congruence.checkPositiveNumber(widget.Kh, "Horizontal K")
    congruence.checkPositiveNumber(widget.Kv, "Vertical K")
    congruence.checkStrictlyPositiveNumber(widget.undulator_period, "Period Length")
    congruence.checkStrictlyPositiveNumber(widget.number_of_periods, "Number of Periods")

    congruence.checkStrictlyPositiveNumber(widget.electron_energy_in_GeV, "Energy")
    congruence.checkPositiveNumber(widget.electron_energy_spread, "Energy Spread")
    congruence.checkStrictlyPositiveNumber(widget.ring_current, "Ring Current")

    congruence.checkPositiveNumber(widget.electron_beam_size_h, "Horizontal Beam Size")
    congruence.checkPositiveNumber(widget.electron_beam_divergence_h, "Vertical Beam Size")
    congruence.checkPositiveNumber(widget.electron_beam_size_v, "Horizontal Beam Divergence")
    congruence.checkPositiveNumber(widget.electron_beam_divergence_v, "Vertical Beam Divergence")

    congruence.checkStrictlyPositiveNumber(widget.source_dimension_wf_h_slit_gap, "Wavefront Propagation H Slit Gap")
    congruence.checkStrictlyPositiveNumber(widget.source_dimension_wf_v_slit_gap, "Wavefront Propagation V Slit Gap")
    congruence.checkStrictlyPositiveNumber(widget.source_dimension_wf_h_slit_points, "Wavefront Propagation H Slit Points")
    congruence.checkStrictlyPositiveNumber(widget.source_dimension_wf_v_slit_points, "Wavefront Propagation V Slit Points")
    congruence.checkGreaterOrEqualThan(widget.source_dimension_wf_distance, __get_minimum_propagation_distance(widget),
                                       "Wavefront Propagation Distance", "Minimum Distance out of the Source: " + str(__get_minimum_propagation_distance(widget)))

    if widget.save_srw_result == 1:
        congruence.checkDir(widget.source_dimension_srw_file)
        congruence.checkDir(widget.angular_distribution_srw_file)

def __run_SRW_calculation(widget, energy, do_cumulated_calculations=False):
    __check_SRW_fields(widget)

    __calculate_waist_position(widget, energy)

    magFldCnt = __create_undulator(widget)
    elecBeam  = __create_electron_beam(widget, distribution_type=Distribution.DIVERGENCE, position=widget.waist_position)
    wfr       = __create_initial_wavefront_mesh(widget, elecBeam, energy)

    arPrecParSpec = __get_calculation_precision_settings()

    # 1 calculate intensity distribution ME convoluted for dimension size
    srwl.CalcElecFieldSR(wfr, 0, magFldCnt, arPrecParSpec)

    arI = array('f', [0 ] *wfr.mesh.nx *wfr.mesh.ny)  # "flat" 2D array to take intensity data
    srwl.CalcIntFromElecField(arI, wfr, 6, 1, 3, wfr.mesh.eStart, 0, 0)

    # from radiation at the slit we can calculate Angular Distribution and Power

    x, z, intensity_angular_distribution = __transform_srw_array(arI, wfr.mesh)

    dx = (x[1] - x[0]) * 1e3  # mm for power computations
    dy = (z[1] - z[0]) * 1e3

    integrated_flux = intensity_angular_distribution.sum( ) *dx *dy

    if widget.compute_power:
        total_power = widget.power_step if widget.power_step > 0 else integrated_flux * (1e3 * widget.energy_step * codata.e)
    else:
        total_power = None

    if widget.compute_power and do_cumulated_calculations:
        current_energy          = numpy.ones(1) * energy
        current_integrated_flux = numpy.ones(1) * integrated_flux
        current_power_density   = intensity_angular_distribution.copy() * (1e3 * widget.energy_step * codata.e)
        current_power           = total_power

        if widget.cumulated_energies is None:
            widget.cumulated_energies        = current_energy
            widget.cumulated_integrated_flux = current_integrated_flux
            widget.cumulated_power_density   = current_power_density
            widget.cumulated_power           = numpy.ones(1) * (current_power)
        else:
            widget.cumulated_energies        = numpy.append(widget.cumulated_energies,  current_energy)
            widget.cumulated_integrated_flux = numpy.append(widget.cumulated_integrated_flux,  current_integrated_flux)
            widget.cumulated_power_density  += current_power_density
            widget.cumulated_power           = numpy.append(widget.cumulated_power,  numpy.ones(1) * (widget.cumulated_power[-1] + current_power))

    distance = widget.source_dimension_wf_distance - widget.waist_position # relative to the center of the undulator

    x_first = numpy.arctan(x/distance)
    z_first = numpy.arctan(z/distance)

    wfrAngDist = __create_initial_wavefront_mesh(widget, elecBeam, energy)
    wfrAngDist.mesh.xStart = numpy.arctan(wfr.mesh.xStart/distance)
    wfrAngDist.mesh.xFin   = numpy.arctan(wfr.mesh.xFin/distance)
    wfrAngDist.mesh.yStart = numpy.arctan(wfr.mesh.yStart/distance)
    wfrAngDist.mesh.yFin   = numpy.arctan(wfr.mesh.yFin/distance)

    if widget.save_srw_result == 1: srwl_uti_save_intens_ascii(arI, wfrAngDist.mesh, widget.angular_distribution_srw_file)

    # for source dimension, back propagation to the source position
    elecBeam    = __create_electron_beam(widget, distribution_type=Distribution.POSITION, position=widget.waist_position)
    wfr         = __create_initial_wavefront_mesh(widget, elecBeam, energy)
    optBLSouDim = __create_beamline_source_dimension(widget, back_position=(widget.source_dimension_wf_distance - widget.waist_position))

    srwl.CalcElecFieldSR(wfr, 0, magFldCnt, arPrecParSpec)
    srwl.PropagElecField(wfr, optBLSouDim)

    arI = array('f', [0 ]*wfr.mesh.nx*wfr.mesh.ny)  # "flat" 2D array to take intensity data
    srwl.CalcIntFromElecField(arI, wfr, 6, 1, 3, wfr.mesh.eStart, 0, 0)

    if widget.save_srw_result == 1: srwl_uti_save_intens_ascii(arI, wfr.mesh, widget.source_dimension_srw_file)

    x, z, intensity_source_dimension = __transform_srw_array(arI, wfr.mesh)

    # SWITCH FROM SRW METERS TO SHADOWOUI U.M.
    x /= widget.workspace_units_to_m
    z /= widget.workspace_units_to_m

    return x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution, integrated_flux, total_power

def __generate_user_defined_distribution_from_srw(beam_out,
                                                  coord_x,
                                                  coord_z,
                                                  intensity,
                                                  distribution_type=Distribution.POSITION,
                                                  kind_of_sampler=1,
                                                  seed=0):
    if kind_of_sampler == 2:
        s2d = Sampler2D(intensity, coord_x, coord_z)

        samples_x, samples_z = s2d.get_n_sampled_points(len(beam_out._beam.rays))

        if distribution_type == Distribution.POSITION:
            beam_out._beam.rays[:, 0] = samples_x
            beam_out._beam.rays[:, 2] = samples_z

        elif distribution_type == Distribution.DIVERGENCE:
            alpha_x = samples_x
            alpha_z = samples_z

            beam_out._beam.rays[:, 3] =  numpy.cos(alpha_z ) *numpy.sin(alpha_x)
            beam_out._beam.rays[:, 4] =  numpy.cos(alpha_z ) *numpy.cos(alpha_x)
            beam_out._beam.rays[:, 5] =  numpy.sin(alpha_z)
    elif kind_of_sampler == 0:
        pdf = numpy.abs(intensity /numpy.max(intensity))
        pdf /= pdf.sum()

        distribution = CustomDistribution(pdf, seed=seed)

        sampled = distribution(len(beam_out._beam.rays))

        min_value_x = numpy.min(coord_x)
        step_x = numpy.abs(coord_x[1 ] -coord_x[0])
        min_value_z = numpy.min(coord_z)
        step_z = numpy.abs(coord_z[1 ] -coord_z[0])

        if distribution_type == Distribution.POSITION:
            beam_out._beam.rays[:, 0] = min_value_x + sampled[0, : ] *step_x
            beam_out._beam.rays[:, 2] = min_value_z + sampled[1, : ] *step_z

        elif distribution_type == Distribution.DIVERGENCE:
            alpha_x = min_value_x + sampled[0, : ] *step_x
            alpha_z = min_value_z + sampled[1, : ] *step_z

            beam_out._beam.rays[:, 3] =  numpy.cos(alpha_z ) *numpy.sin(alpha_x)
            beam_out._beam.rays[:, 4] =  numpy.cos(alpha_z ) *numpy.cos(alpha_x)
            beam_out._beam.rays[:, 5] =  numpy.sin(alpha_z)
    elif kind_of_sampler == 1:
        min_x = numpy.min(coord_x)
        max_x = numpy.max(coord_x)
        delta_x = max_x - min_x

        min_z = numpy.min(coord_z)
        max_z = numpy.max(coord_z)
        delta_z = max_z - min_z

        dim_x = len(coord_x)
        dim_z = len(coord_z)

        grid = Grid2D((dim_x, dim_z))
        grid[..., ...] = intensity.tolist()

        d = Distribution2D(distribution_from_grid(grid, dim_x, dim_z), (0, 0), (dim_x, dim_z))

        samples = d.get_samples(len(beam_out._beam.rays), seed)

        if distribution_type == Distribution.POSITION:
            beam_out._beam.rays[:, 0] = min_x + samples[:, 0] * delta_x
            beam_out._beam.rays[:, 2] = min_z + samples[:, 1] * delta_z

        elif distribution_type == Distribution.DIVERGENCE:
            alpha_x = min_x + samples[:, 0] * delta_x
            alpha_z = min_z + samples[:, 1] * delta_z

            beam_out._beam.rays[:, 3] = numpy.cos(alpha_z) * numpy.sin(alpha_x)
            beam_out._beam.rays[:, 4] = numpy.cos(alpha_z) * numpy.cos(alpha_x)
            beam_out._beam.rays[:, 5] = numpy.sin(alpha_z)

    else:
        raise ValueError("Sampler not recognized")


####################################################################################
# SRW FILES
####################################################################################

def __load_SRW_files(widget):
    congruence.checkFile(widget.source_dimension_srw_file)
    congruence.checkFile(widget.angular_distribution_srw_file)

    x, z, intensity_source_dimension = __load_numpy_format(widget.source_dimension_srw_file)
    x_first, z_first, intensity_angular_distribution = __load_numpy_format(widget.angular_distribution_srw_file)

    # SWITCH FROM SRW METERS TO SHADOWOUI U.M.
    x = x/widget.workspace_units_to_m
    z = z/widget.workspace_units_to_m

    return x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution

def __file_load(_fname, _read_labels=1): # FROM SRW
    nLinesHead = 11
    hlp = []

    with open(_fname,'r') as f:
        for i in range(nLinesHead):
            hlp.append(f.readline())

    ne, nx, ny = [int(hlp[i].replace('#','').split()[0]) for i in [3,6,9]]
    ns = 1
    testStr = hlp[nLinesHead - 1]
    if testStr[0] == '#':
        ns = int(testStr.replace('#','').split()[0])

    e0,e1,x0,x1,y0,y1 = [float(hlp[i].replace('#','').split()[0]) for i in [1,2,4,5,7,8]]

    data = numpy.squeeze(numpy.loadtxt(_fname, dtype=numpy.float64)) #get data from file (C-aligned flat)

    allrange = e0, e1, ne, x0, x1, nx, y0, y1, ny

    arLabels = ['Photon Energy', 'Horizontal Position', 'Vertical Position', 'Intensity']
    arUnits = ['eV', 'm', 'm', 'ph/s/.1%bw/mm^2']

    if _read_labels:
        arTokens = hlp[0].split(' [')
        arLabels[3] = arTokens[0].replace('#','')
        arUnits[3] = '';
        if len(arTokens) > 1:
            arUnits[3] = arTokens[1].split('] ')[0]

        for i in range(3):
            arTokens = hlp[i*3 + 1].split()
            nTokens = len(arTokens)
            nTokensLabel = nTokens - 3
            nTokensLabel_mi_1 = nTokensLabel - 1
            strLabel = ''
            for j in range(nTokensLabel):
                strLabel += arTokens[j + 2]
                if j < nTokensLabel_mi_1: strLabel += ' '
            arLabels[i] = strLabel
            arUnits[i] = arTokens[nTokens - 1].replace('[','').replace(']','')

    return data, None, allrange, arLabels, arUnits

def __load_numpy_format(filename):
    data, dump, allrange, arLabels, arUnits = __file_load(filename)

    dim_x = allrange[5]
    dim_y = allrange[8]
    np_array = data.reshape((dim_y, dim_x))
    np_array = np_array.transpose()
    x_coordinates = numpy.linspace(allrange[3], allrange[4], dim_x)
    y_coordinates = numpy.linspace(allrange[6], allrange[7], dim_y)

    return x_coordinates, y_coordinates, np_array

####################################################################################
# ASCII FILES
####################################################################################
def __load_ASCII_files(widget):
    __check_ASCII_files_fields(widget)

    x_positions = __extract_distribution_from_file(distribution_file_name=widget.x_positions_file)
    z_positions = __extract_distribution_from_file(distribution_file_name=widget.z_positions_file)

    x_positions[:, 0] *= widget.x_positions_factor
    z_positions[:, 0] *= widget.z_positions_factor

    x_divergences = __extract_distribution_from_file(distribution_file_name=widget.x_divergences_file)
    z_divergences = __extract_distribution_from_file(distribution_file_name=widget.z_divergences_file)

    x_divergences[:, 0] *= widget.x_divergences_factor
    z_divergences[:, 0] *= widget.z_divergences_factor

    x, z, intensity_source_dimension = __combine_distributions(widget, x_positions, z_positions)
    x_first, z_first, intensity_angular_distribution = __combine_distributions(widget, x_divergences, z_divergences)

    return x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution

def __check_ASCII_files_fields(widget):
    congruence.checkFile(widget.x_positions_file)
    congruence.checkFile(widget.z_positions_file)
    congruence.checkFile(widget.x_divergences_file)
    congruence.checkFile(widget.z_divergences_file)

    widget.x_positions_factor = float(widget.x_positions_factor)
    widget.z_positions_factor = float(widget.z_positions_factor)
    widget.x_divergences_factor = float(widget.x_divergences_factor)
    widget.z_divergences_factor = float(widget.z_divergences_factor)

    congruence.checkStrictlyPositiveNumber(widget.x_positions_factor, "X Position Units to Workspace Units")
    congruence.checkStrictlyPositiveNumber(widget.z_positions_factor, "Z Position Units to Workspace Units")
    congruence.checkStrictlyPositiveNumber(widget.x_divergences_factor, "X Divergence Units to rad")
    congruence.checkStrictlyPositiveNumber(widget.z_divergences_factor, "Z Divergence Units to rad")

def __extract_distribution_from_file(distribution_file_name):
    distribution = []

    try:
        distribution_file = open(distribution_file_name, "r")

        rows = distribution_file.readlines()

        for index in range(0, len(rows)):
            row = rows[index]

            if not row.strip() == "":
                values = row.split()

                if not len(values) == 2: raise Exception("Malformed file, must be: <value> <spaces> <frequency>")

                value = float(values[0].strip())
                frequency = float(values[1].strip())

                distribution.append([value, frequency])

    except Exception as err:
        raise Exception("Problems reading distribution file: {0}".format(err))
    except:
        raise Exception("Unexpected error reading distribution file: ", sys.exc_info()[0])

    return numpy.array(distribution)

def __combine_distributions(widget, distribution_x, distribution_y):
    coord_x = distribution_x[:, 0]
    coord_y = distribution_y[:, 0]

    intensity_x = repmat(distribution_x[:, 1], len(coord_y), 1).transpose()
    intensity_y = repmat(distribution_y[:, 1], len(coord_x), 1)

    if widget.combine_strategy == 0:
        convoluted_intensity = numpy.sqrt(intensity_x*intensity_y)
    elif widget.combine_strategy == 1:
        convoluted_intensity = numpy.sqrt(intensity_x**2 + intensity_y**2)
    elif widget.combine_strategy == 2:
        convoluted_intensity = convolve2d(intensity_x, intensity_y, boundary='fill', mode='same', fillvalue=0)
    elif widget.combine_strategy == 3:
        convoluted_intensity = 0.5*(intensity_x + intensity_y)

    return coord_x, coord_y, convoluted_intensity


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
from scipy.interpolate import interp2d
from scipy.optimize import curve_fit
from scipy import integrate

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowPreProcessor

from Shadow import ShadowTools as ST

from orangecontrib.shadow_advanced_tools.widgets.optical_elements.bl.bender_data_to_plot import BenderDataToPlot

def apply_bender_surface(widget, input_beam, shadow_oe):
    shadow_oe_temp  = shadow_oe.duplicate()
    input_beam_temp = input_beam.duplicate(history=False)

    widget.manage_acceptance_slits(shadow_oe_temp)

    ShadowBeam.traceFromOE(input_beam_temp,
                           shadow_oe_temp,
                           write_start_file=0,
                           write_end_file=0,
                           widget_class_name=type(widget).__name__)

    x, y, z = __calculate_ideal_surface(widget, shadow_oe_temp)

    bender_parameter, z_bender_correction, bender_data_to_plot = __calculate_bender_correction(widget, y, z)

    bender_data_to_plot.x = x

    widget.K0_out = bender_parameter[0]
    widget.eta_out = bender_parameter[1]
    widget.W2_out = bender_parameter[2] # round(bender_parameter[2], int(6 * widget.workspace_units_to_mm))

    if widget.modified_surface > 0:
        x_e, y_e, z_e = ShadowPreProcessor.read_surface_error_file(widget.ms_defect_file_name)

        if len(x) == len(x_e) and len(y) == len(y_e) and \
                x[0] == x_e[0] and x[-1] == x_e[-1] and \
                y[0] == y_e[0] and y[-1] == y_e[-1]:
            z_figure_error = z_e
        else:
            z_figure_error = interp2d(y_e, x_e, z_e, kind='cubic')(y, x)

        z_bender_correction += z_figure_error

        bender_data_to_plot.z_figure_error=z_figure_error
        bender_data_to_plot.z_bender_correction=z_bender_correction
    else:
        bender_data_to_plot.z_bender_correction = z_bender_correction

    ST.write_shadow_surface(z_bender_correction.T, numpy.round(x, 6), numpy.round(y, 6), widget.output_file_name_full)

    # Add new surface as figure error
    shadow_oe._oe.F_RIPPLE = 1
    shadow_oe._oe.F_G_S = 2
    shadow_oe._oe.FILE_RIP = bytes(widget.output_file_name_full, 'utf-8')

    return shadow_oe, bender_data_to_plot

def __calculate_ideal_surface(widget, shadow_oe, sign=-1):
    x = numpy.linspace(-widget.dim_x_minus, widget.dim_x_plus, widget.bender_bin_x + 1)
    y = numpy.linspace(-widget.dim_y_minus, widget.dim_y_plus, widget.bender_bin_y + 1)

    c1 = round(shadow_oe._oe.CCC[0], 10)
    c2 = round(shadow_oe._oe.CCC[1], 10)
    c3 = round(shadow_oe._oe.CCC[2], 10)
    c4 = round(shadow_oe._oe.CCC[3], 10)
    c5 = round(shadow_oe._oe.CCC[4], 10)
    c6 = round(shadow_oe._oe.CCC[5], 10)
    c7 = round(shadow_oe._oe.CCC[6], 10)
    c8 = round(shadow_oe._oe.CCC[7], 10)
    c9 = round(shadow_oe._oe.CCC[8], 10)
    c10 = round(shadow_oe._oe.CCC[9], 10)

    xx, yy = numpy.meshgrid(x, y)

    c = c1 * (xx ** 2) + c2 * (yy ** 2) + c4 * xx * yy + c7 * xx + c8 * yy + c10
    b = c5 * yy + c6 * xx + c9
    a = c3

    z = (-b + sign * numpy.sqrt(b ** 2 - 4 * a * c)) / (2 * a)
    z[b ** 2 - 4 * a * c < 0] = numpy.nan

    return x, y, z.T

def __calculate_bender_correction(widget, y, z):
    W1 = widget.dim_x_plus + widget.dim_x_minus
    L  = widget.dim_y_plus + widget.dim_y_minus  # add optimization length

    p = widget.object_side_focal_distance
    q = widget.image_side_focal_distance
    grazing_angle = numpy.radians(90 - widget.incidence_angle_respect_to_normal)

    # TO BE VERIFIED
    ideal_profile = z[0, :][::-1]  # one row is the profile of the cylinder, enough for the minimizer
    ideal_profile += -ideal_profile[0] + ((L / 2 + y) * (ideal_profile[0] - ideal_profile[-1])) / L  # Rotation

    if widget.which_length == 0:
        y_fit = y
        ideal_profile_fit = ideal_profile
    else:
        cursor = numpy.where(numpy.logical_and(y >= -widget.optimized_length / 2, y <= widget.optimized_length / 2))
        y_fit = y[cursor]
        ideal_profile_fit = ideal_profile[cursor]

    epsilon_minus = 1 - 1e-8
    epsilon_plus  = 1 + 1e-8

    initial_guess    = [widget.K0, widget.eta, widget.W2]
    constraints     =  [[widget.K0_min if widget.K0_fixed == False else (widget.K0 * epsilon_minus),
                         widget.eta_min if widget.eta_fixed == False else (widget.eta * epsilon_minus),
                         widget.W2_min if widget.W2_fixed == False else (widget.W2 * epsilon_minus)],
                        [widget.K0_max if widget.K0_fixed == False else (widget.K0 * epsilon_plus),
                         widget.eta_max if widget.eta_fixed == False else (widget.eta * epsilon_plus),
                         widget.W2_max if widget.W2_fixed == False else (widget.W2 * epsilon_plus)]
                       ]

    def bender_function(y, K0, eta, W2):
        return __bender_slope_error(y, p, q, grazing_angle,
                                    K0,
                                    eta,
                                    alpha=__calculate_taper_factor(W1, W2, L, p, q, grazing_angle))

    for i in range(widget.n_fit_steps):
        parameters, _ = curve_fit(f=bender_function,
                                  xdata=y_fit,
                                  ydata=ideal_profile_fit,
                                  p0=initial_guess,
                                  bounds=constraints,
                                  method='trf')
        initial_guess = parameters

    bender_profile = __bender_profile(y, p, q, grazing_angle,
                                      K0=parameters[0],
                                      eta=parameters[1],
                                      alpha = __calculate_taper_factor(W1, parameters[2], L, p, q, grazing_angle))

    # rotate back to Shadow system
    bender_profile = bender_profile[::-1]
    ideal_profile = ideal_profile[::-1]

    # from here it's Shadow Axis system
    correction_profile = ideal_profile - bender_profile
    if widget.which_length == 1: correction_profile_fit = correction_profile[cursor]

    # r-squared = 1 - residual sum of squares / total sum of squares
    r_squared = 1 - (numpy.sum(correction_profile ** 2) / numpy.sum((ideal_profile - numpy.mean(ideal_profile)) ** 2))
    rms = round(correction_profile.std() * 1e9 * widget.workspace_units_to_m, 6)
    if widget.which_length == 1: rms_opt = round(correction_profile_fit.std() * 1e9 * widget.workspace_units_to_m, 6)

    z_bender_correction = numpy.zeros(z.shape)

    for i in range(z_bender_correction.shape[0]): z_bender_correction[i, :] = numpy.copy(correction_profile)

    return parameters, z_bender_correction, BenderDataToPlot(y=y,
                                                             ideal_profile=ideal_profile,
                                                             bender_profile=bender_profile,
                                                             correction_profile=correction_profile,
                                                             titles=["Bender vs. Ideal Profiles" + "\n" + r'$R^2$ = ' + str(r_squared),
                                                                     "Correction Profile 1D, r.m.s. = " + str(rms) + " nm" + ("" if widget.which_length == 0 else (", " + str(rms_opt) + " nm (optimized)"))],
                                                             z_bender_correction_no_figure_error=z_bender_correction)


def __focal_distance(p, q):
    return p*q/(p+q)

def __demagnification_factor(p, q):
    return p/q

def __mu_nu(m):
    return (m - 1) / (m + 1), m/(m+1)**2

def __calculate_ideal_slope_variation(y, fprime, K0id, mu, nu):
    return 2*fprime*K0id*((2 * nu * (y / fprime) + mu) * numpy.sqrt(1 - mu * (y / fprime) - nu * (y / fprime) ** 2) - mu)

def __calculate_taper_factor(W1, W2, L, p, q, grazing_angle):
    f = p * q / (p + q)
    fprime = f / numpy.cos(grazing_angle)

    # W  = W0 (1 - alpha (x/f'))
    #
    # W1 = W0 (1 + alpha (L/2f') )
    # W2 = W0 (1 - alpha (L/2f') )
    #
    # W1 - W2 = alpha (L/f')
    #
    # -> alpha =  (W1 - W2) * (f'/L)

    return (W1 - W2) * (fprime / L)

def __calculate_bender_slope_variation(y, fprime, K0, eta, alpha):
    return -(K0*fprime/alpha**2)*(eta * alpha * (y / fprime) + (eta + alpha) * numpy.log(1 - (alpha * y / fprime)))

def __bender_slope_error(y, p, q, grazing_angle, K0, eta, alpha):
    mu, nu = __mu_nu(__demagnification_factor(p, q))
    fprime = __focal_distance(p, q)/numpy.cos(grazing_angle)
    K0id   = numpy.tan(grazing_angle)/(2*fprime)

    return __calculate_ideal_slope_variation(y, fprime, K0id, mu, nu) - __calculate_bender_slope_variation(y, fprime, K0, eta, alpha)

def __bender_profile(y, p, q, grazing_angle, K0, eta, alpha):
    profile = numpy.zeros(len(y))

    fprime = __focal_distance(p, q)/numpy.cos(grazing_angle)

    def integrand(x): return __calculate_bender_slope_variation(x, fprime, K0, eta, alpha)

    for i in range(len(y)):  profile[i] = integrate.quad(func=integrand, a=y[0], b=y[i])

    return profile

# -----------------------------------------------
# q = focus distance (from mirror center) (1/p + 1/q = 1/f lenses equation)
# eta = bender asymmetry factor (from slope minimization)
# K0 = 1/R (radius of curvature at the center)
# E0 = Young's modulus
# L = lenght of the mirror
# r = distance between inner ond outer rods
# ----------------------------------------------------------------
def __calculate_bender_forces(q, eta, K0, E0, L, r):
    M0 = K0*E0
    F1 = (M0/r) * (1 - (eta*(L + 2*r)/(2*q)))
    F2 = (M0/r) * (1 + (eta*(L + 2*r)/(2*q)))

    return F1, F2

# -----------------------------------------------
# F = bender pusher applied force
# k = elastic constant F = kh
# -----------------------------------------------
def calculate_bender_pusher_height(F, k):
    return F/k

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

import copy, numpy

from PyQt5.QtWidgets import QWidget, QVBoxLayout

try:
    from mpl_toolkits.mplot3d import Axes3D  # mandatory to load 3D plot
except:
    pass

from Shadow import Beam

from silx.gui.plot import Plot2D
import scipy.constants as codata
from orangecontrib.shadow.util.shadow_util import ShadowPhysics

class PowerPlotXYWidget(QWidget):
    
    def __init__(self, parent=None):
        pass
    
        super(QWidget, self).__init__(parent=parent)

        self.plot_canvas = None
        self.cumulated_power_plot = 0.0
        self.cumulated_previous_power_plot = 0.0

        self.setLayout(QVBoxLayout())

    def manage_empty_beam(self, ticket_to_add, nbins_h, nbins_v, xrange, yrange, var_x, var_y, cumulated_total_power, energy_min, energy_max, energy_step, show_image, to_mm, cumulated_quantity=0):
        if not ticket_to_add is None:
            ticket      = copy.deepcopy(ticket_to_add)
            last_ticket = copy.deepcopy(ticket_to_add)
        else:
            ticket = {}
            ticket["histogram"] = numpy.zeros((nbins_h, nbins_v))
            ticket['intensity'] = numpy.zeros((nbins_h, nbins_v))
            ticket['nrays']     = 0
            ticket['good_rays'] = 0

            if not xrange is None and not yrange is None:
                ticket['bin_h_center'] = numpy.arange(xrange[0], xrange[1], nbins_h)*to_mm
                ticket['bin_v_center'] = numpy.arange(yrange[0], yrange[1], nbins_v)*to_mm
            else:
                raise ValueError("Beam is empty and no range has been specified: Calculation is impossible")

        self.plot_power_density_ticket(ticket, var_x, var_y, cumulated_total_power, energy_min, energy_max, energy_step, show_image, cumulated_quantity)

        if not ticket_to_add is None:
            return ticket, last_ticket
        else:
            return ticket, None

    def plot_power_density_BM(self, shadow_beam, initial_energy, initial_flux, nbins_interpolation,
                              var_x, var_y, nbins_h=100, nbins_v=100, xrange=None, yrange=None, nolost=1, to_mm=1.0, show_image=True, cumulated_quantity=0):
        n_rays = len(shadow_beam._beam.rays[:, 0]) # lost and good!

        if n_rays == 0:
            ticket, _ = self.manage_empty_beam(None,
                                               nbins_h,
                                               nbins_v,
                                               xrange,
                                               yrange,
                                               var_x,
                                               var_y,
                                               0.0,
                                               0.0,
                                               0.0,
                                               0.0,
                                               show_image,
                                               to_mm)
            return ticket

        source_beam  = shadow_beam.getOEHistory(oe_number=1)._input_beam.duplicate(history=False)
        history_item = shadow_beam.getOEHistory(oe_number=shadow_beam._oe_number)

        if history_item is None or history_item._input_beam is None:
            previous_beam = shadow_beam
        else:
            previous_beam = history_item._input_beam.duplicate(history=False)

        rays_energy = ShadowPhysics.getEnergyFromShadowK(shadow_beam._beam.rays[:, 10])
        energy_range = [numpy.min(rays_energy), numpy.max(rays_energy)]

        ticket_initial = source_beam._beam.histo1(11, xrange=energy_range, nbins=nbins_interpolation, nolost=1, ref=23)

        energy_bins = ticket_initial["bin_center"]

        energy_min = energy_bins[0]
        energy_max = energy_bins[-1]
        energy_step = energy_bins[1] - energy_bins[0]

        initial_flux_shadow = numpy.interp(energy_bins, initial_energy, initial_flux, left=initial_flux[0], right=initial_flux[-1])
        initial_power_shadow = initial_flux_shadow * 1e3 * codata.e * energy_step

        total_initial_power_shadow = initial_power_shadow.sum()

        print("Total Initial Power from Shadow", total_initial_power_shadow)

        if nolost>1: # must be calculating only the rays the become lost in the last object
            current_beam = shadow_beam

            if history_item is None or history_item._input_beam is None:
                beam = shadow_beam._beam
            else:
                if nolost==2:
                    current_lost_rays_cursor = numpy.where(current_beam._beam.rays[:, 9] != 1)

                    current_lost_rays          = current_beam._beam.rays[current_lost_rays_cursor]
                    lost_rays_in_previous_beam = previous_beam._beam.rays[current_lost_rays_cursor]

                    lost_that_were_good_rays_cursor = numpy.where(lost_rays_in_previous_beam[:, 9] == 1)

                    beam = Beam()
                    beam.rays = current_lost_rays[lost_that_were_good_rays_cursor] # lost rays that were good after the previous OE

                    # in case of filters, Shadow computes the absorption for lost rays. This cause an imbalance on the total power.
                    # the lost rays that were good must have the same intensity they had before the optical element.

                    beam.rays[:, 6]  = lost_rays_in_previous_beam[lost_that_were_good_rays_cursor][:, 6]
                    beam.rays[:, 7]  = lost_rays_in_previous_beam[lost_that_were_good_rays_cursor][:, 7]
                    beam.rays[:, 8]  = lost_rays_in_previous_beam[lost_that_were_good_rays_cursor][:, 8]
                    beam.rays[:, 15] = lost_rays_in_previous_beam[lost_that_were_good_rays_cursor][:, 15]
                    beam.rays[:, 16] = lost_rays_in_previous_beam[lost_that_were_good_rays_cursor][:, 16]
                    beam.rays[:, 17] = lost_rays_in_previous_beam[lost_that_were_good_rays_cursor][:, 17]
                else:
                    incident_rays = previous_beam._beam.rays
                    transmitted_rays = current_beam._beam.rays

                    incident_intensity = incident_rays[:, 6]**2  + incident_rays[:, 7]**2  + incident_rays[:, 8]**2 +\
                                         incident_rays[:, 15]**2 + incident_rays[:, 16]**2 + incident_rays[:, 17]**2
                    transmitted_intensity = transmitted_rays[:, 6]**2  + transmitted_rays[:, 7]**2  + transmitted_rays[:, 8]**2 +\
                                            transmitted_rays[:, 15]**2 + transmitted_rays[:, 16]**2 + transmitted_rays[:, 17]**2

                    electric_field = numpy.sqrt(incident_intensity - transmitted_intensity)
                    electric_field[numpy.where(electric_field == numpy.nan)] = 0.0

                    beam = Beam()
                    beam.rays = copy.deepcopy(shadow_beam._beam.rays)

                    beam.rays[:, 6]  = electric_field
                    beam.rays[:, 7]  = 0.0
                    beam.rays[:, 8]  = 0.0
                    beam.rays[:, 15] = 0.0
                    beam.rays[:, 16] = 0.0
                    beam.rays[:, 17] = 0.0
        else:
            beam = shadow_beam._beam

        if len(beam.rays) == 0:
            ticket, _ = self.manage_empty_beam(None,
                                               nbins_h,
                                               nbins_v,
                                               xrange,
                                               yrange,
                                               var_x,
                                               var_y,
                                               0.0,
                                               energy_min,
                                               energy_max,
                                               energy_step,
                                               show_image,
                                               to_mm)
            return ticket

        ticket_incident = previous_beam._beam.histo1(11, xrange=energy_range, nbins=nbins_interpolation, nolost=1, ref=23) # intensity of good rays per bin incident
        ticket_final    = beam.histo1(11, xrange=energy_range, nbins=nbins_interpolation, nolost=1, ref=23) # intensity of good rays per bin

        good = numpy.where(ticket_initial["histogram"] > 0)

        efficiency_incident = numpy.zeros(len(ticket_incident["histogram"]))
        efficiency_incident[good]  = ticket_incident["histogram"][good] / ticket_initial["histogram"][good]

        incident_power_shadow = initial_power_shadow * efficiency_incident

        total_incident_power_shadow = incident_power_shadow.sum()
        print("Total Incident Power from Shadow", total_incident_power_shadow)

        efficiency_final = numpy.zeros(len(ticket_final["histogram"]))
        efficiency_final[good]  = ticket_final["histogram"][good] / ticket_initial["histogram"][good]

        final_power_shadow = initial_power_shadow * efficiency_final

        total_final_power_shadow = final_power_shadow.sum()
        print("Total Final Power from Shadow", total_final_power_shadow)

        # CALCULATE POWER DENSITY PER EACH RAY -------------------------------------------------------

        ticket = beam.histo1(11, xrange=energy_range, nbins=nbins_interpolation, nolost=1, ref=0) # number of rays per bin
        good = numpy.where(ticket["histogram"] > 0)

        final_power_per_ray = numpy.zeros(len(final_power_shadow))
        final_power_per_ray[good] = final_power_shadow[good] / ticket["histogram"][good]

        go = numpy.where(shadow_beam._beam.rays[:, 9] == 1)

        rays_energy = ShadowPhysics.getEnergyFromShadowK(shadow_beam._beam.rays[go, 10])

        ticket = beam.histo2(var_x, var_y, nbins_h=nbins_h, nbins_v=nbins_v, xrange=xrange, yrange=yrange, nolost=1, ref=0)

        ticket['bin_h_center'] *= to_mm
        ticket['bin_v_center'] *= to_mm
        pixel_area = (ticket['bin_h_center'][1] - ticket['bin_h_center'][0]) * (ticket['bin_v_center'][1] - ticket['bin_v_center'][0])

        power_density = numpy.interp(rays_energy, energy_bins, final_power_per_ray, left=0, right=0) / pixel_area

        final_beam = Beam()
        final_beam.rays = copy.deepcopy(beam.rays)

        final_beam.rays[go, 6] = numpy.sqrt(power_density)
        final_beam.rays[go, 7] = 0.0
        final_beam.rays[go, 8] = 0.0
        final_beam.rays[go, 15] = 0.0
        final_beam.rays[go, 16] = 0.0
        final_beam.rays[go, 17] = 0.0

        ticket = final_beam.histo2(var_x, var_y,
                                   nbins_h=nbins_h, nbins_v=nbins_v, xrange=xrange, yrange=yrange,
                                   nolost=1, ref=23)

        ticket['histogram'][numpy.where(ticket['histogram'] < 1e-7)] = 0.0

        self.cumulated_previous_power_plot = total_incident_power_shadow
        self.cumulated_power_plot = total_final_power_shadow

        self.plot_power_density_ticket(ticket, var_x, var_y, total_initial_power_shadow, energy_min, energy_max, energy_step, show_image, cumulated_quantity)

        return ticket

    def plot_power_density(self, shadow_beam, var_x, var_y, total_power, cumulated_total_power, energy_min, energy_max, energy_step,
                           nbins_h=100, nbins_v=100, xrange=None, yrange=None, nolost=1, ticket_to_add=None, to_mm=1.0, show_image=True,
                           kind_of_calculation=0,
                           replace_poor_statistic=0,
                           good_rays_limit=100,
                           center_x = 0.0,
                           center_y = 0.0,
                           sigma_x=1.0,
                           sigma_y=1.0,
                           gamma=1.0,
                           cumulated_quantity=0):

        n_rays = len(shadow_beam._beam.rays[:, 0]) # lost and good!

        if n_rays == 0:
            return self.manage_empty_beam(ticket_to_add,
                                          nbins_h,
                                          nbins_v,
                                          xrange,
                                          yrange,
                                          var_x,
                                          var_y,
                                          cumulated_total_power,
                                          energy_min,
                                          energy_max,
                                          energy_step,
                                          show_image,
                                          to_mm)

        history_item = shadow_beam.getOEHistory(oe_number=shadow_beam._oe_number)

        previous_beam = None

        if shadow_beam.scanned_variable_data and shadow_beam.scanned_variable_data.has_additional_parameter("incident_power"):
            self.cumulated_previous_power_plot += shadow_beam.scanned_variable_data.get_additional_parameter("incident_power")
        elif not history_item is None and not history_item._input_beam is None:
            previous_ticket = history_item._input_beam._beam.histo2(var_x, var_y, nbins_h=nbins_h, nbins_v=nbins_v, xrange=None, yrange=None, nolost=1, ref=23)
            previous_ticket['histogram'] *= (total_power/n_rays) # power

            self.cumulated_previous_power_plot += previous_ticket['histogram'].sum()

        if nolost>1: # must be calculating only the rays the become lost in the last object
            current_beam = shadow_beam

            if history_item is None or history_item._input_beam is None:
                beam = shadow_beam._beam
            else:
                previous_beam = previous_beam if previous_beam else history_item._input_beam.duplicate(history=False)

                if nolost==2:
                    current_lost_rays_cursor = numpy.where(current_beam._beam.rays[:, 9] != 1)

                    current_lost_rays          = current_beam._beam.rays[current_lost_rays_cursor]
                    lost_rays_in_previous_beam = previous_beam._beam.rays[current_lost_rays_cursor]

                    lost_that_were_good_rays_cursor = numpy.where(lost_rays_in_previous_beam[:, 9] == 1)

                    beam = Beam()
                    beam.rays = current_lost_rays[lost_that_were_good_rays_cursor] # lost rays that were good after the previous OE

                    # in case of filters, Shadow computes the absorption for lost rays. This cause an imbalance on the total power.
                    # the lost rays that were good must have the same intensity they had before the optical element.

                    beam.rays[:, 6]  = lost_rays_in_previous_beam[lost_that_were_good_rays_cursor][:, 6]
                    beam.rays[:, 7]  = lost_rays_in_previous_beam[lost_that_were_good_rays_cursor][:, 7]
                    beam.rays[:, 8]  = lost_rays_in_previous_beam[lost_that_were_good_rays_cursor][:, 8]
                    beam.rays[:, 15] = lost_rays_in_previous_beam[lost_that_were_good_rays_cursor][:, 15]
                    beam.rays[:, 16] = lost_rays_in_previous_beam[lost_that_were_good_rays_cursor][:, 16]
                    beam.rays[:, 17] = lost_rays_in_previous_beam[lost_that_were_good_rays_cursor][:, 17]
                else:
                    incident_rays = previous_beam._beam.rays
                    transmitted_rays = current_beam._beam.rays

                    incident_intensity = incident_rays[:, 6]**2  + incident_rays[:, 7]**2  + incident_rays[:, 8]**2 +\
                                         incident_rays[:, 15]**2 + incident_rays[:, 16]**2 + incident_rays[:, 17]**2
                    transmitted_intensity = transmitted_rays[:, 6]**2  + transmitted_rays[:, 7]**2  + transmitted_rays[:, 8]**2 +\
                                            transmitted_rays[:, 15]**2 + transmitted_rays[:, 16]**2 + transmitted_rays[:, 17]**2

                    electric_field = numpy.sqrt(incident_intensity - transmitted_intensity)
                    electric_field[numpy.where(electric_field == numpy.nan)] = 0.0

                    beam = Beam()
                    beam.rays = copy.deepcopy(shadow_beam._beam.rays)

                    beam.rays[:, 6]  = electric_field
                    beam.rays[:, 7]  = 0.0
                    beam.rays[:, 8]  = 0.0
                    beam.rays[:, 15] = 0.0
                    beam.rays[:, 16] = 0.0
                    beam.rays[:, 17] = 0.0
        else:
            beam = shadow_beam._beam

        if len(beam.rays) == 0:
            return self.manage_empty_beam(ticket_to_add,
                                          nbins_h,
                                          nbins_v,
                                          xrange,
                                          yrange,
                                          var_x,
                                          var_y,
                                          cumulated_total_power,
                                          energy_min,
                                          energy_max,
                                          energy_step,
                                          show_image,
                                          to_mm)

        ticket = beam.histo2(var_x, var_y, nbins_h=nbins_h, nbins_v=nbins_v, xrange=xrange, yrange=yrange, nolost=1 if nolost != 2 else 2, ref=23)

        ticket['bin_h_center'] *= to_mm
        ticket['bin_v_center'] *= to_mm

        bin_h_size = (ticket['bin_h_center'][1] - ticket['bin_h_center'][0])
        bin_v_size = (ticket['bin_v_center'][1] - ticket['bin_v_center'][0])

        if kind_of_calculation > 0:
            if replace_poor_statistic == 0 or (replace_poor_statistic==1 and ticket['good_rays'] < good_rays_limit):
                if kind_of_calculation == 1: # FLAT
                    PowerPlotXYWidget.get_flat_2d(ticket['histogram'], ticket['bin_h_center'], ticket['bin_v_center'])
                elif kind_of_calculation == 2: # GAUSSIAN
                    PowerPlotXYWidget.get_gaussian_2d(ticket['histogram'], ticket['bin_h_center'], ticket['bin_v_center'],
                                                       sigma_x, sigma_y, center_x, center_y)
                elif kind_of_calculation == 3: #LORENTZIAN
                    PowerPlotXYWidget.get_lorentzian_2d(ticket['histogram'], ticket['bin_h_center'], ticket['bin_v_center'],
                                                        gamma, center_x, center_y)
                # rinormalization
                ticket['histogram'] *= ticket['intensity']

        ticket['histogram'][numpy.where(ticket['histogram'] < 1e-9)] = 0.0
        ticket['histogram'] *= (total_power / n_rays)  # power

        if ticket_to_add == None:
            self.cumulated_power_plot = ticket['histogram'].sum()
        else:
            self.cumulated_power_plot += ticket['histogram'].sum()

        ticket['histogram'] /= (bin_h_size * bin_v_size)  # power density

        if not ticket_to_add is None:
            last_ticket = copy.deepcopy(ticket)

            ticket['histogram'] += ticket_to_add['histogram']
            ticket['intensity'] += ticket_to_add['intensity']
            ticket['nrays']     += ticket_to_add['nrays']
            ticket['good_rays'] += ticket_to_add['good_rays']

        ticket['h_label'] = var_x
        ticket['v_label'] = var_y

        # data for reload of the file
        ticket['energy_min'] = energy_min
        ticket['energy_max'] = energy_max
        ticket['energy_step'] = energy_step
        ticket['plotted_power'] = self.cumulated_power_plot
        ticket['incident_power'] = self.cumulated_previous_power_plot
        ticket['total_power'] = cumulated_total_power

        self.plot_power_density_ticket(ticket, var_x, var_y, cumulated_total_power, energy_min, energy_max, energy_step, show_image, cumulated_quantity)

        if not ticket_to_add is None:
            return ticket, last_ticket
        else:
            return ticket, None

    def plot_power_density_ticket(self, ticket, var_x, var_y, cumulated_total_power, energy_min, energy_max, energy_step, show_image=True, cumulated_quantity=0):
        if show_image:
            histogram = ticket['histogram']

            average_power_density = numpy.average(histogram[numpy.where(histogram > 0.0)])

            if cumulated_quantity == 0: # Power density
                title = "Power Density [W/mm\u00b2] from " + str(round(energy_min, 2)) + " to " + str(round(energy_max+energy_step, 2)) + " [eV], Current Step: " + str(round(energy_step, 2)) + "\n" + \
                        "Power [W]: Plot=" + str(round(self.cumulated_power_plot, 3)) + \
                        ", Incid.=" + str(round(self.cumulated_previous_power_plot, 3)) + \
                        ", Tot.=" + str(round(cumulated_total_power, 3)) + \
                        ", <PD>=" + str(round(average_power_density, 3)) + " W/mm\u00b2"
            elif cumulated_quantity == 1: # Intensity
                title = "Intensity [ph/s/mm\u00b2] from " + str(round(energy_min, 2)) + " to " + str(round(energy_max+energy_step, 2)) + " [eV], Current Step: " + str(round(energy_step, 2)) + "\n" + \
                        "Flux [ph/s]: Plot=" + "{:.1e}".format(self.cumulated_power_plot) + \
                        ", Incid.=" + "{:.1e}".format(self.cumulated_previous_power_plot) + \
                        ", Tot.=" + "{:.1e}".format(cumulated_total_power) + \
                        ", <I>=" + "{:.2e}".format(average_power_density) + " ph/s/mm\u00b2"

            xx = ticket['bin_h_center']
            yy = ticket['bin_v_center']

            if not isinstance(var_x, str): var_x = self.get_label(var_x)
            if not isinstance(var_y, str): var_y = self.get_label(var_y)

            self.plot_data2D(histogram, xx, yy, title, var_x, var_y)

    def get_label(self, var):
        if var == 1: return "X [mm]"
        elif var == 2: return "Y [mm]"
        elif var == 3: return "Z [mm]"

    def plot_data2D(self, data2D, dataX, dataY, title="", xtitle="", ytitle=""):
        if self.plot_canvas is None:
            self.plot_canvas = Plot2D()

            self.plot_canvas.resetZoom()
            self.plot_canvas.setXAxisAutoScale(True)
            self.plot_canvas.setYAxisAutoScale(True)
            self.plot_canvas.setGraphGrid(False)
            self.plot_canvas.setKeepDataAspectRatio(False)
            self.plot_canvas.yAxisInvertedAction.setVisible(False)

            self.plot_canvas.setXAxisLogarithmic(False)
            self.plot_canvas.setYAxisLogarithmic(False)
            self.plot_canvas.getMaskAction().setVisible(False)
            self.plot_canvas.getRoiAction().setVisible(False)
            self.plot_canvas.getColormapAction().setVisible(True)

        origin = (dataX[0], dataY[0])
        scale = (dataX[1]-dataX[0], dataY[1]-dataY[0])

        self.plot_canvas.addImage(numpy.array(data2D.T),
                                  legend="power",
                                  scale=scale,
                                  origin=origin,
                                  colormap={"name":"temperature", "normalization":"linear", "autoscale":True, "vmin":0, "vmax":0, "colors":256},
                                  replace=True)

        self.plot_canvas.setActiveImage("power")

        self.plot_canvas.setGraphXLabel(xtitle)
        self.plot_canvas.setGraphYLabel(ytitle)
        self.plot_canvas.setGraphTitle(title)

        self.plot_canvas.resetZoom()
        self.plot_canvas.setXAxisAutoScale(True)
        self.plot_canvas.setYAxisAutoScale(True)

        layout = self.layout()
        layout.addWidget(self.plot_canvas)
        self.setLayout(layout)

    def clear(self):
        if not self.plot_canvas is None:
            self.plot_canvas.clear()
            self.cumulated_power_plot = 0.0
            self.cumulated_previous_power_plot = 0.0

    @classmethod
    def get_flat_2d(cls, z, x, y):
        for i in range(len(x)):
            z[i, :] = 1

        norm = numpy.sum(z)
        z[:,:] /= norm

    @classmethod
    def get_gaussian_2d(cls, z, x, y, sigma_x, sigma_y, center_x=0.0, center_y=0.0):
        for i in range(len(x)):
            z[i, :] = numpy.exp(-1*(0.5*((x[i]-center_x)/sigma_x)**2 + 0.5*((y-center_y)/sigma_y)**2))

        norm = numpy.sum(z)
        z[:,:] /= norm

    @classmethod
    def get_lorentzian_2d(cls, z, x, y, gamma, center_x=0.0, center_y=0.0):
        for i in range(len(x)):
            z[i, :] = gamma/(((x[i]-center_x)**2 + (y-center_y)**2 + gamma**2))

        norm = numpy.sum(z)
        z[:,:] /= norm


if __name__=="__main__":

    x2 = numpy.linspace(-40e-6, 40e-6, 100)
    y2 = numpy.linspace(-40e-6, 40e-6, 100)

    x, y = numpy.meshgrid(x2, y2)
    z = numpy.ones((100, 100))

    #PowerPlotXYWidget.get_gaussian_2d(z, x2, y2, 1e-5, 2e-5)
    PowerPlotXYWidget.get_lorentzian_2d(z, x2, y2, 1.5e-6)
    #z = PowerPlotXYWidget.get_flat_2d(x2, y2)

    from matplotlib import pyplot as plt

    fig=plt.figure();
    ax=fig.add_subplot(111, projection='3d')
    surf=ax.plot_surface(x, y, z)

    plt.show()

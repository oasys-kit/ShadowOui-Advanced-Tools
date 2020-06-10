import os, sys, numpy
from scipy.interpolate import RectBivariateSpline, interp2d
from scipy.optimize import curve_fit

from matplotlib import cm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
try:
    from mpl_toolkits.mplot3d import Axes3D  # necessario per caricare i plot 3D
except:
    pass

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.util.oasys_util import TriggerIn

from orangecontrib.shadow.util.shadow_objects import ShadowOpticalElement, ShadowBeam, ShadowPreProcessorData
from orangecontrib.shadow.util.shadow_util import ShadowPreProcessor
from orangecontrib.shadow.widgets.gui import ow_ellipsoid_element, ow_optical_element

from Shadow import ShadowTools as ST

TRAPEZIUM = 0
RECTANGLE = 1

SINGLE_MOMENTUM = 0
DOUBLE_MOMENTUM = 1

class BendableEllipsoidMirror(ow_ellipsoid_element.EllipsoidElement):
    name = "Bendable Ellipsoid Mirror"
    description = "Shadow OE: Bendable Ellipsoid Mirror"
    icon = "icons/bendable_ellipsoid_mirror.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 6
    category = "Optical Elements"
    keywords = ["data", "file", "load", "read"]

    send_footprint_beam = QSettings().value("output/send-footprint", 0, int) == 1

    if send_footprint_beam:
        outputs = [{"name":"Beam",
                    "type":ShadowBeam,
                    "doc":"Shadow Beam",
                    "id":"beam"},
                   {"name":"Footprint",
                    "type":list,
                    "doc":"Footprint",
                    "id":"beam"},
                   {"name":"Trigger",
                    "type": TriggerIn,
                    "doc":"Feedback signal to start a new beam simulation",
                    "id":"Trigger"},
                   {"name": "PreProcessor_Data",
                    "type": ShadowPreProcessorData,
                    "doc": "PreProcessor Data",
                    "id": "PreProcessor_Data"}
                   ]
    else:
        outputs = [{"name":"Beam",
                    "type":ShadowBeam,
                    "doc":"Shadow Beam",
                    "id":"beam"},
                   {"name":"Trigger",
                    "type": TriggerIn,
                    "doc":"Feedback signal to start a new beam simulation",
                    "id":"Trigger"},
                   {"name": "PreProcessor_Data",
                    "type": ShadowPreProcessorData,
                    "doc": "PreProcessor Data",
                    "id": "PreProcessor_Data"}
                   ]

    show_bender_plots = Setting(0)

    bender_bin_x = Setting(100)
    bender_bin_y = Setting(500)

    E = Setting(131000)
    h = Setting(10)

    kind_of_bender = Setting(1)
    shape = Setting(0)

    output_file_name = Setting("mirror_bender.dat")

    which_length = Setting(0)
    optimized_length = Setting(0.0)

    M1    = Setting(0.0)
    ratio = Setting(0.5)
    e     = Setting(0.3)

    M1_out    = 0.0
    ratio_out = 0.0
    e_out     = 0.0

    M1_fixed    = Setting(False)
    ratio_fixed = Setting(False)
    e_fixed     = Setting(False)

    M1_min    = Setting(0.0)
    ratio_min = Setting(0.0)
    e_min     = Setting(0.0)

    M1_max    = Setting(1000.0)
    ratio_max = Setting(10.0)
    e_max     = Setting(1.0)

    def __init__(self):
        graphical_Options=ow_optical_element.GraphicalOptions(is_mirror=True)

        super().__init__(graphical_Options)

        tabs = gui.tabWidget(oasysgui.createTabPage(self.tabs_basic_setting, "Bender"))

        tab_bender = oasysgui.createTabPage(tabs, "Bender Setting")

        surface_box = oasysgui.widgetBox(tab_bender, "Surface Setting", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(surface_box, self, "bender_bin_x", "bins Sagittal", labelWidth=260, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(surface_box, self, "bender_bin_y", "bins Transversal", labelWidth=260, valueType=int, orientation="horizontal")

        material_box = oasysgui.widgetBox(tab_bender, "Bender Setting", addSpace=False, orientation="vertical")

        self.le_E = oasysgui.lineEdit(material_box, self, "E", "Young's Modulus ", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_h = oasysgui.lineEdit(material_box, self, "h", "Thickness ", labelWidth=260, valueType=float, orientation="horizontal")

        gui.comboBox(material_box, self, "kind_of_bender", label="Kind Of Bender ", items=["Single Momentum", "Double Momentum"],
                     labelWidth=150, orientation="horizontal", callback=self.set_kind_of_bender)

        gui.comboBox(material_box, self, "shape", label="Shape ", items=["Trapezium", "Rectangle"],
                     labelWidth=150, orientation="horizontal", callback=self.set_shape)

        tab_fit = oasysgui.createTabPage(tabs, "Fit Setting")

        fit_box = oasysgui.widgetBox(tab_fit, "", addSpace=False, orientation="vertical")

        file_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="horizontal", height=25)
        self.le_output_file_name = oasysgui.lineEdit(file_box, self, "output_file_name", "Out File Name", labelWidth=100, valueType=str, orientation="horizontal")
        gui.button(file_box, self, "...", callback=self.select_output_file, width=20)

        length_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="horizontal")

        self.cb_optimized_length = gui.comboBox(length_box, self, "which_length", label="Optimized Length ", items=["Total", "Partial"],
                                                labelWidth=150, orientation="horizontal", callback=self.set_which_length)
        self.le_optimized_length = oasysgui.lineEdit(length_box, self, "optimized_length", " ", labelWidth=10, valueType=float, orientation="horizontal")
        self.set_which_length()

        gui.separator(fit_box)

        def add_parameter_box(container_box, variable, label):
            box = oasysgui.widgetBox(container_box, "", addSpace=False, orientation="horizontal")
            oasysgui.lineEdit(box, self, variable, label, labelWidth=50, valueType=float, orientation="horizontal")
            gui.label(box, self, " ", labelWidth=58)

            box = oasysgui.widgetBox(container_box, "", addSpace=False, orientation="horizontal")

            setattr(self, "le_" + variable + "_min", oasysgui.lineEdit(box, self, variable + "_min", "Min",
                                                                       labelWidth=50, valueType=float, orientation="horizontal"))
            setattr(self, "le_" + variable + "_max", oasysgui.lineEdit(box, self, variable + "_max", "Max",
                                                                        labelWidth=35, valueType=float, orientation="horizontal"))

            gui.checkBox(box, self, variable + "_fixed", "Fixed", callback=getattr(self, "set_" + variable))

            box = oasysgui.widgetBox(container_box, "", addSpace=False, orientation="horizontal")

            le = oasysgui.lineEdit(box, self, variable + "_out", "Fitted", labelWidth=50, valueType=float, orientation="horizontal")
            le.setEnabled(False)
            le.setStyleSheet("color: blue; background-color: rgb(254, 244, 205); font:bold")

            def set_variable_fit(): setattr(self, variable, getattr(self, variable + "_out"))
            gui.button(box, self, "<- Use", width=58, callback=set_variable_fit)

            getattr(self, "set_" + variable)()

        m1_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="vertical")
        gui.separator(fit_box, 10)
        self.ratio_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="vertical")
        gui.separator(fit_box, 10)
        self.e_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="vertical")
        gui.separator(fit_box, 10)

        add_parameter_box(m1_box, "M1", "M1")
        add_parameter_box(self.ratio_box, "ratio", "M1/M2")
        add_parameter_box(self.e_box, "e", "e")

        self.set_kind_of_bender()
        self.set_shape()

        #######################################################
        
        plot_tab = oasysgui.createTabPage(self.main_tabs, "Bender Plots")

        view_box = oasysgui.widgetBox(plot_tab, "Plotting Style", addSpace=False, orientation="vertical", width=350)

        self.view_type_combo = gui.comboBox(view_box, self, "show_bender_plots", label="Show Plots", labelWidth=220,
                                            items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal")

        bender_tabs = oasysgui.tabWidget(plot_tab)

        tabs = [oasysgui.createTabPage(bender_tabs, "Bender vs. Ideal (1D)"),
                oasysgui.createTabPage(bender_tabs, "Ideal - Bender (1D)"),
                oasysgui.createTabPage(bender_tabs, "Ideal - Bender (3D)"),
                oasysgui.createTabPage(bender_tabs, "Figure Error (3D)"),
                oasysgui.createTabPage(bender_tabs, "Ideal - Bender + Figure Error (3D)")]

        def create_figure_canvas(mode="3D"):
            figure = Figure(figsize=(100, 100))
            figure.patch.set_facecolor('white')
            if mode == "3D": figure.add_subplot(111, projection='3d')
            else: figure.add_subplot(111)

            figure_canvas = FigureCanvasQTAgg(figure)
            figure_canvas.setFixedWidth(self.IMAGE_WIDTH)
            figure_canvas.setFixedHeight(self.IMAGE_HEIGHT-10)

            return figure_canvas

        self.figure_canvas = [create_figure_canvas("1D"), create_figure_canvas("1D"),
                              create_figure_canvas(), create_figure_canvas(), create_figure_canvas()]

        for tab, figure_canvas in zip(tabs, self.figure_canvas): tab.layout().addWidget(figure_canvas)

        gui.rubber(self.controlArea)
        gui.rubber(self.mainArea)

    ################################################################
    #
    #  SHADOW MANAGEMENT
    #
    ################################################################

    def select_output_file(self):
        self.le_output_file_name.setText(oasysgui.selectFileFromDialog(self, self.output_file_name, "Select Output File", file_extension_filter="Data Files (*.dat)"))

    def set_kind_of_bender(self):
        self.ratio_box.setVisible(self.kind_of_bender==1)

    def set_shape(self):
        self.e_box.setVisible(self.shape==0)

    def set_which_length(self):
        self.le_optimized_length.setEnabled(self.which_length==1)
    
    def set_M1(self):
        self.le_M1_min.setEnabled(self.M1_fixed==False)
        self.le_M1_max.setEnabled(self.M1_fixed==False)

    def set_ratio(self):
        self.le_ratio_min.setEnabled(self.ratio_fixed==False)
        self.le_ratio_max.setEnabled(self.ratio_fixed==False)
        
    def set_e(self):
        self.le_e_min.setEnabled(self.e_fixed==False)
        self.le_e_max.setEnabled(self.e_fixed==False)

    def after_change_workspace_units(self):
        super().after_change_workspace_units()

        label = self.le_E.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [N/" + self.workspace_units_label + "^2]")
        label = self.le_h.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.cb_optimized_length.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")

    def checkFields(self):
        super().checkFields()

        if self.is_cylinder != 1: raise ValueError("Bender Ellipse must be a cylinder")
        if self.cylinder_orientation != 0: raise ValueError("Cylinder orientation must be 0")
        if self.is_infinite == 0: raise ValueError("This OE can't have infinite dimensions")
        if self.which_length==1:
            congruence.checkStrictlyPositiveNumber(self.optimized_length, "Optimized Length")
            congruence.checkLessOrEqualThan(self.optimized_length, self.dim_y_plus+self.dim_y_minus, "Optimized Length", "Total Length")

        if self.modified_surface > 0:
            if not (self.modified_surface == 1 and self.ms_type_of_defect == 2):
                raise ValueError("Only Preprocessor generated error profiles are admitted")

        congruence.checkStrictlyPositiveNumber(self.bender_bin_x, "Bins X")
        congruence.checkStrictlyPositiveNumber(self.bender_bin_y, "Bins Y")
        self.output_file_name_full = congruence.checkFileName(self.output_file_name)

    def completeOperations(self, shadow_oe):
        shadow_oe_temp  = shadow_oe.duplicate()
        input_beam_temp = self.input_beam.duplicate(history=False)

        self.manage_acceptance_slits(shadow_oe_temp)

        ShadowBeam.traceFromOE(input_beam_temp,
                               shadow_oe_temp,
                               write_start_file=0,
                               write_end_file=0,
                               widget_class_name=type(self).__name__)

        x, y, z = self.calculate_ideal_surface(shadow_oe_temp)

        bender_parameter, z_bender_correction = self.calculate_bender_correction(y, z, self.kind_of_bender, self.shape)

        self.M1_out = round(bender_parameter[0], int(6*self.workspace_units_to_mm))
        if self.shape == TRAPEZIUM:
            self.e_out = round(bender_parameter[1], 5)
            if self.kind_of_bender == DOUBLE_MOMENTUM: self.ratio_out = round(bender_parameter[2], 5)
        elif self.shape == RECTANGLE:
            if self.kind_of_bender == DOUBLE_MOMENTUM: self.ratio_out = round(bender_parameter[1], 5)

        self.plot3D(x, y, z_bender_correction, 2, "Ideal - Bender Surfaces")

        if self.modified_surface > 0:
            x_e, y_e, z_e = ShadowPreProcessor.read_surface_error_file(self.ms_defect_file_name)

            if len(x) == len(x_e) and len(y) == len(y_e) and \
                    x[0] == x_e[0] and x[-1] == x_e[-1] and \
                    y[0] == y_e[0] and y[-1] == y_e[-1]:
                z_figure_error = z_e
            else:
                z_figure_error = interp2d(y_e, x_e, z_e, kind='cubic')(y, x)

            z_bender_correction += z_figure_error

            self.plot3D(x, y, z_figure_error,      3, "Figure Error Surface")
            self.plot3D(x, y, z_bender_correction, 4, "Ideal - Bender + Figure Error Surfaces")

        ST.write_shadow_surface(z_bender_correction.T, numpy.round(x, 6), numpy.round(y, 6), self.output_file_name_full)

        # Add new surface as figure error
        shadow_oe._oe.F_RIPPLE  = 1
        shadow_oe._oe.F_G_S     = 2
        shadow_oe._oe.FILE_RIP  = bytes(self.output_file_name_full, 'utf-8')

        # Redo Raytracing with the new file
        super().completeOperations(shadow_oe)

        self.send("PreProcessor_Data", ShadowPreProcessorData(error_profile_data_file=self.output_file_name,
                                                              error_profile_x_dim=self.dim_x_plus+self.dim_x_minus,
                                                              error_profile_y_dim=self.dim_y_plus+self.dim_y_minus))

    def instantiateShadowOE(self):
        return ShadowOpticalElement.create_ellipsoid_mirror()


    def calculate_ideal_surface(self, shadow_oe, sign=-1):
        x = numpy.linspace(-self.dim_x_minus, self.dim_x_plus, self.bender_bin_x + 1)
        y = numpy.linspace(-self.dim_y_minus, self.dim_y_plus, self.bender_bin_y + 1)

        c1  = round(shadow_oe._oe.CCC[0], 10)
        c2  = round(shadow_oe._oe.CCC[1], 10)
        c3  = round(shadow_oe._oe.CCC[2], 10)
        c4  = round(shadow_oe._oe.CCC[3], 10)
        c5  = round(shadow_oe._oe.CCC[4], 10)
        c6  = round(shadow_oe._oe.CCC[5], 10)
        c7  = round(shadow_oe._oe.CCC[6], 10)
        c8  = round(shadow_oe._oe.CCC[7], 10)
        c9  = round(shadow_oe._oe.CCC[8], 10)
        c10 = round(shadow_oe._oe.CCC[9], 10)

        xx, yy = numpy.meshgrid(x, y)

        c = c1*(xx**2) + c2*(yy**2) + c4*xx*yy + c7*xx + c8*yy + c10
        b = c5*yy + c6*xx + c9
        a = c3

        z = (-b + sign*numpy.sqrt(b**2 - 4*a*c))/(2*a)
        z[b**2 - 4*a*c < 0] = numpy.nan

        return x, y, z.T

    def calculate_bender_correction(self, y, z, kind_of_bender, shape):
        b0 = self.dim_x_plus + self.dim_x_minus
        L  = self.dim_y_plus + self.dim_y_minus  # add optimization length

        # flip the coordinate system to be consistent with Mike's formulas
        ideal_profile = z[0, :][::-1]  # one row is the profile of the cylinder, enough for the minimizer
        ideal_profile += -ideal_profile[0] + ((L/2 + y)*(ideal_profile[0]-ideal_profile[-1]))/L # Rotation

        if self.which_length == 0:
            y_fit             = y
            ideal_profile_fit = ideal_profile
        else:
            cursor            = numpy.where(numpy.logical_and(y >= -self.optimized_length/2,
                                                              y <= self.optimized_length/2) )
            y_fit             = y[cursor]
            ideal_profile_fit = ideal_profile[cursor]

        epsilon_minus = 1 - 1e-8
        epsilon_plus = 1 + 1e-8

        Eh_3 = self.E * self.h ** 3

        initial_guess = None
        constraints = None
        bender_function = None

        if shape == TRAPEZIUM:
            def general_bender_function(Y, M1, e, ratio):
                M2 = M1 * ratio
                A = (M1 + M2) / 2
                B = (M1 - M2) / L
                C = Eh_3 * (2 * b0 + e * b0) / 24
                D = Eh_3 * e * b0 / (12 * L)
                H = (A * D + B * C) / D ** 2
                CDLP = C + D * L / 2
                CDLM = C - D * L / 2
                F = (H / L) * ((CDLM * numpy.log(CDLM) - CDLP * numpy.log(CDLP)) / D + L)
                G = (-H * ((CDLM * numpy.log(CDLM) + CDLP * numpy.log(CDLP))) + (B * L ** 2) / 4) / (2 * D)
                CDY = C + D * Y

                return H * ((CDY / D) * numpy.log(CDY) - Y) - (B * Y ** 2) / (2 * D) + F * Y + G

            def bender_function_2m(Y, M1, e, ratio): return general_bender_function(Y, M1, e, ratio)
            def bender_function_1m(Y, M1, e):        return general_bender_function(Y, M1, e, 1.0)

            if kind_of_bender == SINGLE_MOMENTUM:
                bender_function = bender_function_1m
                initial_guess = [self.M1, self.e]
                constraints = [[self.M1_min if self.M1_fixed == False else (self.M1 * epsilon_minus),
                                self.e_min  if self.e_fixed == False  else (self.e * epsilon_minus)],
                               [self.M1_max if self.M1_fixed == False else (self.M1 * epsilon_plus),
                                self.e_max  if self.e_fixed == False  else (self.e * epsilon_plus)]]
            elif kind_of_bender == DOUBLE_MOMENTUM:
                bender_function = bender_function_2m
                initial_guess = [self.M1, self.e, self.ratio]
                constraints = [[self.M1_min    if self.M1_fixed == False    else (self.M1*epsilon_minus),
                                self.e_min     if self.e_fixed == False     else (self.e*epsilon_minus),
                                self.ratio_min if self.ratio_fixed == False else (self.ratio*epsilon_minus)],
                               [self.M1_max    if self.M1_fixed == False    else (self.M1*epsilon_plus),
                                self.e_max     if self.e_fixed == False     else (self.e*epsilon_plus),
                                self.ratio_max if self.ratio_fixed == False else (self.ratio*epsilon_plus)]]
        elif shape == RECTANGLE:
            def general_bender_function(Y, M1, ratio):
                M2 = M1 * ratio
                A = (M1 + M2) / 2
                B = (M1 - M2) / L
                C = Eh_3 * b0 / 12
                F = (B * L**2) / (24 * C)
                G = -(A * L**2) / (8 * C)

                return -(B * Y**3) / (6 * C) + (A * Y**2) / (2 * C) + F * Y + G

            def bender_function_2m(Y, M1, ratio): return general_bender_function(Y, M1, ratio)
            def bender_function_1m(Y, M1):        return general_bender_function(Y, M1, 1.0)

            if kind_of_bender == SINGLE_MOMENTUM:
                bender_function = bender_function_1m
                initial_guess = [self.M1]
                constraints = [[self.M1_min if self.M1_fixed == False else (self.M1 * epsilon_minus)],
                               [self.M1_max if self.M1_fixed == False else (self.M1 * epsilon_plus)]]
            elif kind_of_bender == DOUBLE_MOMENTUM:
                bender_function = bender_function_2m
                initial_guess = [self.M1, self.ratio]
                constraints = [[self.M1_min    if self.M1_fixed == False    else (self.M1*epsilon_minus),
                                self.ratio_min if self.ratio_fixed == False else (self.ratio*epsilon_minus)],
                               [self.M1_max    if self.M1_fixed == False    else (self.M1*epsilon_plus),
                                self.ratio_max if self.ratio_fixed == False else (self.ratio*epsilon_plus)]]

        parameters, _ = curve_fit(f=bender_function,
                                  xdata=y_fit,
                                  ydata=ideal_profile_fit,
                                  p0=initial_guess,
                                  bounds=constraints,
                                  method='trf')

        if len(parameters)   == 1: bender_profile = bender_function(y, parameters[0])
        elif len(parameters) == 2: bender_profile = bender_function(y, parameters[0], parameters[1])
        else:                      bender_profile = bender_function(y, parameters[0], parameters[1], parameters[2])

        # rotate back to Shadow system
        bender_profile = bender_profile[::-1]
        ideal_profile  = ideal_profile[::-1]

        # from here it's Shadow Axis system
        correction_profile = ideal_profile - bender_profile
        if self.which_length == 1: correction_profile_fit = correction_profile[cursor]

        # r-squared = 1 - residual sum of squares / total sum of squares
        r_squared = 1 - (numpy.sum(correction_profile**2) / numpy.sum((ideal_profile - numpy.mean(ideal_profile))**2))
        rms       = round(correction_profile.std()*1e9*self.workspace_units_to_m, 6)
        if self.which_length == 1: rms_opt = round(correction_profile_fit.std()*1e9*self.workspace_units_to_m, 6)

        self.plot1D(y, bender_profile, y_values_2=ideal_profile, index=0, title = "Bender vs. Ideal Profiles" + "\n" + r'$R^2$ = ' + str(r_squared), um=1)
        self.plot1D(y, correction_profile, index=1, title="Correction Profile 1D, r.m.s. = " + str(rms) + " nm" +
                                                          ("" if self.which_length == 0 else (", " + str(rms_opt) + " nm (optimized)")))

        z_bender_correction = numpy.zeros(z.shape)
        for i in range(z_bender_correction.shape[0]): z_bender_correction[i, :] = numpy.copy(correction_profile)

        return parameters, z_bender_correction

    def plot1D(self, x_coords, y_values, y_values_2=None, index=0, title="", um=0):
        if self.show_bender_plots == 1:
            figure = self.figure_canvas[index].figure

            axis = figure.gca()
            axis.clear()

            axis.set_xlabel("Y [" + self.workspace_units_label + "]")
            axis.set_ylabel("Z [" + ("nm" if um==0 else "\u03bcm") + "]")
            axis.set_title(title)
            
            axis.plot(x_coords, (y_values * self.workspace_units_to_m * (1e9 if um==0 else 1e6)), color="blue", label="bender", linewidth=2)
            if not y_values_2 is None: axis.plot(x_coords, (y_values_2 * self.workspace_units_to_m * (1e9 if um==0 else 1e6)), "-.r", label="ideal")

            axis.legend(loc=0, fontsize='small')

            figure.canvas.draw()

    def plot3D(self, x_coords, y_coords, z_values, index, title=""):
        if self.show_bender_plots == 1:
            figure = self.figure_canvas[index].figure
            x_to_plot, y_to_plot = numpy.meshgrid(x_coords, y_coords)
            z_to_plot = z_values.T

            axis = figure.gca()
            axis.clear()

            axis.set_xlabel("X [" + self.workspace_units_label + "]")
            axis.set_ylabel("Y [" + self.workspace_units_label + "]")
            axis.set_zlabel("Z [nm]")
            axis.set_title(title)

            axis.plot_surface(x_to_plot, y_to_plot, (z_to_plot * self.workspace_units_to_m * 1e9),
                              rstride=1, cstride=1, cmap=cm.autumn, linewidth=0.5, antialiased=True)

            figure.canvas.draw()

            axis.mouse_init()

if __name__ == "__main__":
    a = QApplication(sys.argv)
    ow = BendableEllipsoidMirror()
    ow.show()
    a.exec_()
    ow.saveSettings()

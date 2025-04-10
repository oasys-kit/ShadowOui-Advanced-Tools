import sys
import numpy

from matplotlib import cm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from oasys.widgets.gui import FigureCanvas3D
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

from orangecontrib.shadow.util.shadow_objects import ShadowOpticalElement, ShadowPreProcessorData, ShadowBeam
from orangecontrib.shadow.widgets.gui import ow_ellipsoid_element, ow_optical_element

from orangecontrib.shadow_advanced_tools.widgets.optical_elements.bl.fixed_rods_bender_ellispoid_mirror_bl import apply_bender_surface

class DoubleRodBendableEllipsoidMirror(ow_ellipsoid_element.EllipsoidElement):
    name = "Double-Rod Bendable Ellipsoid Mirror"
    description = "Shadow OE: Double-Rod Bendable Ellipsoid Mirror"
    icon = "icons/double_rod_bendable_ellipsoid_mirror.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 7
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
    h = Setting(10.0)
    l = Setting(70.0)
    r = Setting(12.0)

    output_file_name = Setting("mirror_bender.dat")

    which_length = Setting(0)
    optimized_length = Setting(0.0)
    n_fit_steps = Setting(3)

    R0     = Setting(45)
    eta    = Setting(0.25)
    W2     = Setting(40.0)

    R0_out    = 0.0
    eta_out   = 0.0
    W2_out    = 0.0

    R0_fixed    = Setting(False)
    eta_fixed   = Setting(False)
    W2_fixed    = Setting(False)

    R0_min    = Setting(0.0)
    eta_min = Setting(0.0)
    W2_min     = Setting(0.0)

    R0_max    = Setting(1000.0)
    eta_max = Setting(10.0)
    W2_max     = Setting(1.0)

    alpha = 0.0
    W0    = 0.0
    F_upstream      = 0.0
    F_downstream    = 0.0

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
        self.le_l = oasysgui.lineEdit(material_box, self, "l", "Inner Rods distance ", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_r = oasysgui.lineEdit(material_box, self, "r", "Inner/Outer Rods distance ", labelWidth=260, valueType=float, orientation="horizontal")

        tab_fit = oasysgui.createTabPage(tabs, "Fit Setting")

        fit_box = oasysgui.widgetBox(tab_fit, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(fit_box, self, "n_fit_steps", "Nr. fit steps", labelWidth=250, valueType=int, orientation="horizontal")

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

        R0_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="vertical")
        gui.separator(fit_box, 10)
        eta_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="vertical")
        gui.separator(fit_box, 10)
        W2_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="vertical")
        gui.separator(fit_box, 10)

        add_parameter_box(R0_box, "R0",   "R0 [m]")
        add_parameter_box(eta_box, "eta", "\u03b7")
        add_parameter_box(W2_box, "W2",   "W2 [mm]")

        tab_fit_out = oasysgui.createTabPage(tabs, "Bender Out Parameters")

        fit_out_box = oasysgui.widgetBox(tab_fit_out, "", addSpace=False, orientation="vertical")

        le = oasysgui.lineEdit(fit_out_box, self, "alpha", "Momentum Asymmetry Factor (\u03b1)", labelWidth=250, valueType=float, orientation="horizontal")
        le.setReadOnly(True)
        le = oasysgui.lineEdit(fit_out_box, self, "W0", "Width at center [mm]", labelWidth=230, valueType=float, orientation="horizontal")
        le.setReadOnly(True)
        le = oasysgui.lineEdit(fit_out_box, self, "F_upstream", "Upstream Force", labelWidth=230, valueType=float, orientation="horizontal")
        le.setReadOnly(True)
        le = oasysgui.lineEdit(fit_out_box, self, "F_downstream", "Downstream Force", labelWidth=230, valueType=float, orientation="horizontal")
        le.setReadOnly(True)

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
            if mode == "3D":
                ax = figure.add_subplot(111, projection='3d')
                figure_canvas = FigureCanvas3D(ax=ax, fig=figure)
            else:
                figure.add_subplot(111)
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

    def set_which_length(self):
        self.le_optimized_length.setEnabled(self.which_length==1)
    
    def set_R0(self):
        self.le_R0_min.setEnabled(self.R0_fixed==False)
        self.le_R0_max.setEnabled(self.R0_fixed==False)

    def set_eta(self):
        self.le_eta_min.setEnabled(self.eta_fixed==False)
        self.le_eta_max.setEnabled(self.eta_fixed==False)
        
    def set_W2(self):
        self.le_W2_min.setEnabled(self.W2_fixed==False)
        self.le_W2_max.setEnabled(self.W2_fixed==False)

    def after_change_workspace_units(self):
        super().after_change_workspace_units()

        label = self.le_E.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [N/" + self.workspace_units_label + "^2]")
        label = self.le_h.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_r.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_l.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.cb_optimized_length.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")

    def checkFields(self):
        super().checkFields()

        if self.is_cylinder != 1: raise ValueError("Bender Ellipse must be a cylinder")
        if self.cylinder_orientation != 0: raise ValueError("Cylinder orientation must be 0")
        if self.is_infinite == 0: raise ValueError("This OE can't have infinite dimensions")
        congruence.checkStrictlyPositiveNumber(self.n_fit_steps, "Nr. Fit Steps")
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
        bender_data = apply_bender_surface(widget=self, shadow_oe=shadow_oe)

        self.plot1D(bender_data.y, bender_data.bender_profile, y_values_2=bender_data.ideal_profile,
                    index=0, title=bender_data.titles[0], um=1)
        self.plot1D(bender_data.y, bender_data.correction_profile,
                    index=1, title=bender_data.titles[1])

        self.plot3D(bender_data.x,
                    bender_data.y,
                    bender_data.z_bender_correction_no_figure_error,
                    index=2, title="Ideal - Bender Surfaces")

        if self.modified_surface > 0:
            self.plot3D(bender_data.x,
                        bender_data.y,
                        bender_data.z_figure_error,  index=3, title="Figure Error Surface")
            self.plot3D(bender_data.x,
                        bender_data.y,
                        bender_data.z_bender_correction, index=4, title="Ideal - Bender + Figure Error Surfaces")

        # Redo raytracing with the bender correction as error profile
        super().completeOperations(shadow_oe)

        self.send("PreProcessor_Data", ShadowPreProcessorData(error_profile_data_file=self.output_file_name,
                                                              error_profile_x_dim=self.dim_x_plus+self.dim_x_minus,
                                                              error_profile_y_dim=self.dim_y_plus+self.dim_y_minus))

    def instantiateShadowOE(self):
        return ShadowOpticalElement.create_ellipsoid_mirror()


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
    ow = DoubleRodBendableEllipsoidMirror()
    ow.show()
    a.exec_()
    ow.saveSettings()

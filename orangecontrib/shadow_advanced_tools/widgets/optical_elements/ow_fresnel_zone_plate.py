import sys, numpy, copy

from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QMessageBox

from orangewidget import gui, widget
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.util.oasys_util import EmittingStream, TTYGrabber, TriggerIn

from srxraylib.util.inverse_method_sampler import Sampler2D

from orangecontrib.shadow.util.shadow_objects import ShadowOpticalElement, ShadowCompoundOpticalElement, ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowCongruence, ShadowPhysics, ShadowMath
from orangecontrib.shadow_advanced_tools.util.zone_plates.fresnel_zone_plate_simulator import FZPAttributes, FZPSimulatorOptions, FresnelZonePlateSimulator

from orangecontrib.shadow.widgets.gui.ow_generic_element import GenericElement

GOOD = 1

COLLIMATED_SOURCE_LIMIT = 1e4 #m

class FresnelZonePlate(GenericElement):

    name = "Fresnel Zone Plate"
    description = "Shadow OE: Fresnel Zone Plate"
    icon = "icons/zone_plate.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 23
    category = "Optical Elements"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Input Beam", ShadowBeam, "setBeam")]

    outputs = [{"name":"Beam",
                "type":ShadowBeam,
                "doc":"Shadow Beam",
                "id":"beam"},
               {"name":"Trigger",
                "type": TriggerIn,
                "doc":"Feedback signal to start a new beam simulation",
                "id":"Trigger"}]

    input_beam = None
    output_beam = None

    NONE_SPECIFIED = "NONE SPECIFIED"

    ONE_ROW_HEIGHT = 65
    TWO_ROW_HEIGHT = 110
    THREE_ROW_HEIGHT = 170

    INNER_BOX_WIDTH_L3=322
    INNER_BOX_WIDTH_L2=335
    INNER_BOX_WIDTH_L1=358
    INNER_BOX_WIDTH_L0=375

    source_plane_distance = Setting(10.0)
    image_plane_distance = Setting(20.0)

    source_distance_flag = Setting(0)
    source_distance = Setting(0.0)

    ##################################################

    mirror_movement = Setting(0)

    mm_mirror_offset_x = Setting(0.0)
    mm_mirror_rotation_x = Setting(0.0)
    mm_mirror_offset_y = Setting(0.0)
    mm_mirror_rotation_y = Setting(0.0)
    mm_mirror_offset_z = Setting(0.0)
    mm_mirror_rotation_z = Setting(0.0)

    #####

    source_movement = Setting(0)
    sm_angle_of_incidence = Setting(0.0)
    sm_distance_from_mirror = Setting(0.0)
    sm_z_rotation = Setting(0.0)
    sm_offset_x_mirr_ref_frame = Setting(0.0)
    sm_offset_y_mirr_ref_frame = Setting(0.0)
    sm_offset_z_mirr_ref_frame = Setting(0.0)
    sm_offset_x_source_ref_frame = Setting(0.0)
    sm_offset_y_source_ref_frame = Setting(0.0)
    sm_offset_z_source_ref_frame = Setting(0.0)
    sm_rotation_around_x = Setting(0.0)
    sm_rotation_around_y = Setting(0.0)
    sm_rotation_around_z = Setting(0.0)

    #####

    file_to_write_out = Setting(3) # Mirror: users found difficoult to activate the "Footprint" option.
    write_out_inc_ref_angles = Setting(0)

    def __init__(self):
        super(FresnelZonePlate, self).__init__()

        self.runaction = widget.OWAction("Run Shadow/Trace", self)
        self.runaction.triggered.connect(self.traceOpticalElement)
        self.addAction(self.runaction)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Run Shadow/Trace", callback=self.traceOpticalElement)
        font = QFont(button.font())
        font.setBold(True)
        button.setFont(font)
        palette = QPalette(button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('Dark Blue'))
        button.setPalette(palette) # assign new palette
        button.setFixedHeight(45)

        button = gui.button(button_box, self, "Reset Fields", callback=self.callResetSettings)
        font = QFont(button.font())
        font.setItalic(True)
        button.setFont(font)
        palette = QPalette(button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('Dark Red'))
        button.setPalette(palette) # assign new palette
        button.setFixedHeight(45)
        button.setFixedWidth(150)

        gui.separator(self.controlArea)

        tabs_setting = oasysgui.tabWidget(self.controlArea)
        tabs_setting.setFixedHeight(self.TABS_AREA_HEIGHT)
        tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)

        tab_pos = oasysgui.createTabPage(tabs_setting, "Position")

        upper_box = oasysgui.widgetBox(tab_pos, "Optical Element Orientation", addSpace=True, orientation="vertical")

        self.le_source_plane_distance = oasysgui.lineEdit(upper_box, self, "source_plane_distance", "Source Plane Distance", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_image_plane_distance  = oasysgui.lineEdit(upper_box, self, "image_plane_distance", "Image Plane Distance", labelWidth=260, valueType=float, orientation="horizontal")

        tab_bas = oasysgui.createTabPage(tabs_setting, "Basic Setting")
        tab_adv = oasysgui.createTabPage(tabs_setting, "Advanced Setting")

        ##########################################
        ##########################################
        # BASIC SETTINGS
        ##########################################
        ##########################################

        tabs_basic_setting = oasysgui.tabWidget(tab_bas)
        tabs_setting.setFixedHeight(self.TABS_AREA_HEIGHT-5)
        tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)

        tab_zone_plate_1 = oasysgui.createTabPage(tabs_basic_setting, "Zone Plate Input Parameters")
        tab_zone_plate_2 = oasysgui.createTabPage(tabs_basic_setting, "Zone Plate Output Parameters")

        zp_box = oasysgui.widgetBox(tab_zone_plate_1, "Input Parameters", addSpace=False, orientation="vertical", height=290)



        gui.comboBox(zp_box, self, "source_distance_flag", label="Source Distance", labelWidth=350,
                     items=["Same as Source Plane", "Different"],
                     callback=self.set_SourceDistanceFlag, sendSelectedValue=False, orientation="horizontal")

        self.zp_box_1 = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical", height=30)
        self.zp_box_2 = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical", height=30)

        self.le_source_distance = oasysgui.lineEdit(self.zp_box_1, self, "source_distance", "Source Distance", labelWidth=260, valueType=float, orientation="horizontal")

        self.set_SourceDistanceFlag()


        '''
        oasysgui.lineEdit(zp_box, self, "delta_rn",  u"\u03B4" + "rn [nm]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(zp_box, self, "diameter", "Z.P. Diameter [" + u"\u03BC" + "m]", labelWidth=260, valueType=float, orientation="horizontal")

        gui.comboBox(zp_box, self, "source_distance_flag", label="Source Distance", labelWidth=350,
                     items=["Same as Source Plane", "Different"],
                     callback=self.set_SourceDistanceFlag, sendSelectedValue=False, orientation="horizontal")

        self.zp_box_1 = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical", height=30)
        self.zp_box_2 = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical", height=30)

        self.le_source_distance = oasysgui.lineEdit(self.zp_box_1, self, "source_distance", "Source Distance", labelWidth=260, valueType=float, orientation="horizontal")

        self.set_SourceDistanceFlag()

        gui.comboBox(zp_box, self, "type_of_zp", label="Type of Zone Plate", labelWidth=350,
                     items=["Amplitude", "Phase"],
                     callback=self.set_TypeOfZP, sendSelectedValue=False, orientation="horizontal")

        gui.separator(zp_box, height=5)

        self.zp_box_3 = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.zp_box_3, self, "zone_plate_material",  "Zone Plate Material", labelWidth=260, valueType=str, orientation="horizontal")
        oasysgui.lineEdit(self.zp_box_3, self, "zone_plate_thickness",  "Zone Plate Thickness [nm]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.zp_box_3, self, "substrate_material", "Substrate Material", labelWidth=260, valueType=str, orientation="horizontal")
        oasysgui.lineEdit(self.zp_box_3, self, "substrate_thickness",  "Substrate Thickness [nm]", labelWidth=260, valueType=float, orientation="horizontal")

        self.set_TypeOfZP()

        zp_out_box = oasysgui.widgetBox(tab_zone_plate_2, "Output Parameters", addSpace=False, orientation="vertical", height=270)

        self.le_avg_wavelength = oasysgui.lineEdit(zp_out_box, self, "avg_wavelength", "Average Wavelenght [nm]", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_avg_wavelength.setReadOnly(True)
        font = QFont(self.le_avg_wavelength.font())
        font.setBold(True)
        self.le_avg_wavelength.setFont(font)
        palette = QPalette(self.le_avg_wavelength.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_avg_wavelength.setPalette(palette)

        self.le_number_of_zones = oasysgui.lineEdit(zp_out_box, self, "number_of_zones", "Number of Zones", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_number_of_zones.setReadOnly(True)
        font = QFont(self.le_number_of_zones.font())
        font.setBold(True)
        self.le_number_of_zones.setFont(font)
        palette = QPalette(self.le_number_of_zones.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_number_of_zones.setPalette(palette)

        self.le_focal_distance = oasysgui.lineEdit(zp_out_box, self, "focal_distance", "Focal Distance", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_focal_distance.setReadOnly(True)
        font = QFont(self.le_focal_distance.font())
        font.setBold(True)
        self.le_focal_distance.setFont(font)
        palette = QPalette(self.le_focal_distance.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_focal_distance.setPalette(palette)

        self.le_image_position = oasysgui.lineEdit(zp_out_box, self, "image_position", "Image Position (Q)", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_image_position.setReadOnly(True)
        font = QFont(self.le_image_position.font())
        font.setBold(True)
        self.le_image_position.setFont(font)
        palette = QPalette(self.le_image_position.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_image_position.setPalette(palette)

        self.le_magnification = oasysgui.lineEdit(zp_out_box, self, "magnification", "Magnification", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_magnification.setReadOnly(True)
        font = QFont(self.le_magnification.font())
        font.setBold(True)
        self.le_magnification.setFont(font)
        palette = QPalette(self.le_magnification.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_magnification.setPalette(palette)

        self.le_efficiency = oasysgui.lineEdit(zp_out_box, self, "efficiency", "Efficiency % (Avg. Wavelength)", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_efficiency.setReadOnly(True)
        font = QFont(self.le_efficiency.font())
        font.setBold(True)
        self.le_efficiency.setFont(font)
        palette = QPalette(self.le_efficiency.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_efficiency.setPalette(palette)

        self.le_max_efficiency = oasysgui.lineEdit(zp_out_box, self, "max_efficiency", "Max Possible Efficiency %", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_max_efficiency.setReadOnly(True)
        font = QFont(self.le_max_efficiency.font())
        font.setBold(True)
        self.le_max_efficiency.setFont(font)
        palette = QPalette(self.le_max_efficiency.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_max_efficiency.setPalette(palette)

        self.le_thickness_max_efficiency = oasysgui.lineEdit(zp_out_box, self, "thickness_max_efficiency", "Max Efficiency Thickness [nm]", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_thickness_max_efficiency.setReadOnly(True)
        font = QFont(self.le_thickness_max_efficiency.font())
        font.setBold(True)
        self.le_thickness_max_efficiency.setFont(font)
        palette = QPalette(self.le_thickness_max_efficiency.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_thickness_max_efficiency.setPalette(palette)

        gui.comboBox(zp_out_box, self, "automatically_set_image_plane", label="Automatically set Image Plane Distance", labelWidth=350,
                     items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal")

        zp_out_box_2 = oasysgui.widgetBox(tab_zone_plate_2, "Efficiency Plot", addSpace=False, orientation="vertical", height=200)

        gui.comboBox(zp_out_box_2, self, "energy_plot", label="Plot Efficiency vs. Energy", labelWidth=350,
                     items=["No", "Yes"],
                     sendSelectedValue=False, orientation="horizontal", callback=self.set_EnergyPlot)

        self.zp_out_box_2_1 = oasysgui.widgetBox(zp_out_box_2, "", addSpace=False, orientation="vertical", height=50)
        self.zp_out_box_2_2 = oasysgui.widgetBox(zp_out_box_2, "", addSpace=False, orientation="vertical", height=50)

        oasysgui.lineEdit(self.zp_out_box_2_1, self, "energy_from",  "Energy From [eV]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.zp_out_box_2_1, self, "energy_to",  "Energy To [eV]", labelWidth=260, valueType=float, orientation="horizontal")

        gui.comboBox(zp_out_box_2, self, "thickness_plot", label="Plot Efficiency vs. Thickness", labelWidth=350,
                     items=["No", "Yes"],
                     sendSelectedValue=False, orientation="horizontal", callback=self.set_ThicknessPlot)

        self.zp_out_box_2_3 = oasysgui.widgetBox(zp_out_box_2, "", addSpace=False, orientation="vertical", height=50)
        self.zp_out_box_2_4 = oasysgui.widgetBox(zp_out_box_2, "", addSpace=False, orientation="vertical", height=50)

        oasysgui.lineEdit(self.zp_out_box_2_3, self, "thickness_from",  "Thickness From [nm]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.zp_out_box_2_3, self, "thickness_to",  "Thickness To [nm]", labelWidth=260, valueType=float, orientation="horizontal")

        self.set_EnergyPlot()
        self.set_ThicknessPlot()
        '''

        ##########################################
        ##########################################
        # ADVANCED SETTINGS
        ##########################################
        ##########################################

        tabs_advanced_setting = oasysgui.tabWidget(tab_adv)

        tab_adv_mir_mov = oasysgui.createTabPage(tabs_advanced_setting, "O.E. Movement")
        tab_adv_sou_mov = oasysgui.createTabPage(tabs_advanced_setting, "Source Movement")
        tab_adv_misc = oasysgui.createTabPage(tabs_advanced_setting, "Output Files")


        ##########################################
        #
        # TAB 2.2 - Mirror Movement
        #
        ##########################################

        mir_mov_box = oasysgui.widgetBox(tab_adv_mir_mov, "O.E. Movement Parameters", addSpace=False, orientation="vertical", height=230)

        gui.comboBox(mir_mov_box, self, "mirror_movement", label="O.E. Movement", labelWidth=350,
                     items=["No", "Yes"],
                     callback=self.set_MirrorMovement, sendSelectedValue=False, orientation="horizontal")

        gui.separator(mir_mov_box, height=10)

        self.mir_mov_box_1 = oasysgui.widgetBox(mir_mov_box, "", addSpace=False, orientation="vertical")

        self.le_mm_mirror_offset_x = oasysgui.lineEdit(self.mir_mov_box_1, self, "mm_mirror_offset_x", "O.E. Offset X", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.mir_mov_box_1, self, "mm_mirror_rotation_x", "O.E. Rotation X [CCW, deg]", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_mm_mirror_offset_y = oasysgui.lineEdit(self.mir_mov_box_1, self, "mm_mirror_offset_y", "O.E. Offset Y", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.mir_mov_box_1, self, "mm_mirror_rotation_y", "O.E. Rotation Y [CCW, deg]", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_mm_mirror_offset_z = oasysgui.lineEdit(self.mir_mov_box_1, self, "mm_mirror_offset_z", "O.E. Offset Z", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.mir_mov_box_1, self, "mm_mirror_rotation_z", "O.E. Rotation Z [CCW, deg]", labelWidth=260, valueType=float, orientation="horizontal")

        self.set_MirrorMovement()

       ##########################################
        #
        # TAB 2.3 - Source Movement
        #
        ##########################################

        sou_mov_box = oasysgui.widgetBox(tab_adv_sou_mov, "Source Movement Parameters", addSpace=False, orientation="vertical", height=400)

        gui.comboBox(sou_mov_box, self, "source_movement", label="Source Movement", labelWidth=350,
                     items=["No", "Yes"],
                     callback=self.set_SourceMovement, sendSelectedValue=False, orientation="horizontal")

        gui.separator(sou_mov_box, height=10)

        self.sou_mov_box_1 = oasysgui.widgetBox(sou_mov_box, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.sou_mov_box_1, self, "sm_angle_of_incidence", "Angle of Incidence [deg]", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_sm_distance_from_mirror = oasysgui.lineEdit(self.sou_mov_box_1, self, "sm_distance_from_mirror", "Distance from O.E.", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.sou_mov_box_1, self, "sm_z_rotation", "Z-rotation [deg]", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_sm_offset_x_mirr_ref_frame = oasysgui.lineEdit(self.sou_mov_box_1, self, "sm_offset_x_mirr_ref_frame", "--", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_sm_offset_y_mirr_ref_frame = oasysgui.lineEdit(self.sou_mov_box_1, self, "sm_offset_y_mirr_ref_frame", "--", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_sm_offset_z_mirr_ref_frame = oasysgui.lineEdit(self.sou_mov_box_1, self, "sm_offset_z_mirr_ref_frame", "--", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_sm_offset_x_source_ref_frame = oasysgui.lineEdit(self.sou_mov_box_1, self, "sm_offset_x_source_ref_frame", "--", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_sm_offset_y_source_ref_frame = oasysgui.lineEdit(self.sou_mov_box_1, self, "sm_offset_y_source_ref_frame", "--", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_sm_offset_z_source_ref_frame = oasysgui.lineEdit(self.sou_mov_box_1, self, "sm_offset_z_source_ref_frame", "--", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.sou_mov_box_1, self, "sm_rotation_around_x", "rotation [CCW, deg] around X", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.sou_mov_box_1, self, "sm_rotation_around_y", "rotation [CCW, deg] around Y", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.sou_mov_box_1, self, "sm_rotation_around_z", "rotation [CCW, deg] around Z", labelWidth=260, valueType=float, orientation="horizontal")

        self.set_SourceMovement()

        ##########################################
        #
        # TAB 2.4 - Other
        #
        ##########################################

        adv_other_box = oasysgui.widgetBox(tab_adv_misc, "Optional file output", addSpace=False, orientation="vertical")

        gui.comboBox(adv_other_box, self, "file_to_write_out", label="Files to write out", labelWidth=150,
                     items=["All", "Mirror", "Image", "None", "Debug (All + start.xx/end.xx)"],
                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(adv_other_box, self, "write_out_inc_ref_angles", label="Write out Incident/Reflected angles [angle.xx]", labelWidth=300,
                     items=["No", "Yes"],
                     sendSelectedValue=False, orientation="horizontal")


        gui.rubber(self.controlArea)
        gui.rubber(self.mainArea)


    def isFootprintEnabled(self):
        return False

    def enableFootprint(self, enabled=False):
        pass

    def traceOpticalElement(self):
        try:
            self.setStatusMessage("")
            self.progressBarInit()

            if ShadowCongruence.checkEmptyBeam(self.input_beam):
                if ShadowCongruence.checkGoodBeam(self.input_beam):
                    self.checkFields()

                    sys.stdout = EmittingStream(textWritten=self.writeStdOut)

                    if self.trace_shadow:
                        grabber = TTYGrabber()
                        grabber.start()

                    ###########################################
                    # TODO: TO BE ADDED JUST IN CASE OF BROKEN
                    #       ENVIRONMENT: MUST BE FOUND A PROPER WAY
                    #       TO TEST SHADOW
                    self.fixWeirdShadowBug()
                    ###########################################

                    self.progressBarSet(10)

                    if self.source_distance_flag == 0:
                        self.source_distance = self.source_plane_distance

                    options = FZPSimulatorOptions()
                    attributes = FZPAttributes()

                    zone_plate_beam = self.get_zone_plate_beam(attributes)

                    self.progressBarSet(30)

                    go = numpy.where(zone_plate_beam._beam.rays[:, 9] == GOOD)

                    fzp_simulator = FresnelZonePlateSimulator(attributes=attributes, options=options)
                    fzp_simulator.initialize(energy_in_KeV=ShadowPhysics.getEnergyFromShadowK(numpy.average(zone_plate_beam._beam.rays[go, 10]))/1000,
                                             n_points=5000)

                    beam_out = self.get_output_beam(zone_plate_beam, fzp_simulator)

                    self.progressBarSet(80)

                    if self.trace_shadow:
                        grabber.stop()

                        for row in grabber.ttyData:
                           self.writeStdOut(row)

                    self.setStatusMessage("Plotting Results")

                    self.plot_results(beam_out)

                    self.setStatusMessage("")

                    beam_out.setScanningData(self.input_beam.scanned_variable_data)

                    self.send("Beam", beam_out)
                    self.send("Trigger", TriggerIn(new_object=True))
                else:
                    raise Exception("Input Beam with no good rays")
            else:
                raise Exception("Empty Input Beam")

        except Exception as exception:
            QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

        self.progressBarFinished()



    def setBeam(self, beam):
        if ShadowCongruence.checkEmptyBeam(beam):
            self.input_beam = beam

            if self.is_automatic_run:
                self.traceOpticalElement()

    def checkFields(self):
        self.source_plane_distance = congruence.checkNumber(self.source_plane_distance, "Source plane distance")
        self.image_plane_distance = congruence.checkNumber(self.image_plane_distance, "Image plane distance")


    def after_change_workspace_units(self):
        label = self.le_source_plane_distance.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_image_plane_distance.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")

        label = self.le_source_distance.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")

        # ADVANCED SETTINGS
        # MIRROR MOVEMENTS
        label = self.le_mm_mirror_offset_x.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_mm_mirror_offset_y.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_mm_mirror_offset_z.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        # SOURCE MOVEMENTS
        label = self.le_sm_distance_from_mirror.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_sm_offset_x_mirr_ref_frame.parent().layout().itemAt(0).widget()
        label.setText("offset X [" + self.workspace_units_label + "] in O.E. reference frame")
        label = self.le_sm_offset_y_mirr_ref_frame.parent().layout().itemAt(0).widget()
        label.setText("offset Y [" + self.workspace_units_label + "] in O.E. reference frame")
        label = self.le_sm_offset_z_mirr_ref_frame.parent().layout().itemAt(0).widget()
        label.setText("offset Z [" + self.workspace_units_label + "] in O.E. reference frame")
        label = self.le_sm_offset_x_source_ref_frame.parent().layout().itemAt(0).widget()
        label.setText("offset X [" + self.workspace_units_label + "] in SOURCE reference frame")
        label = self.le_sm_offset_y_source_ref_frame.parent().layout().itemAt(0).widget()
        label.setText("offset Y [" + self.workspace_units_label + "] in SOURCE reference frame")
        label = self.le_sm_offset_z_source_ref_frame.parent().layout().itemAt(0).widget()
        label.setText("offset Z [" + self.workspace_units_label + "] in SOURCE reference frame")

    def callResetSettings(self):
        super().callResetSettings()
        self.setupUI()

    def set_SourceMovement(self):
        self.sou_mov_box_1.setVisible(self.source_movement == 1)

    def set_MirrorMovement(self):
        self.mir_mov_box_1.setVisible(self.mirror_movement == 1)

    def set_SourceDistanceFlag(self):
        self.zp_box_1.setVisible(self.source_distance_flag == 1)
        self.zp_box_2.setVisible(self.source_distance_flag == 0)


    ######################################################################
    # ZONE PLATE CALCULATION
    ######################################################################

    def get_zone_plate_beam(self, attributes):       # WS Units

        empty_element = ShadowOpticalElement.create_empty_oe()

        empty_element._oe.DUMMY        = self.workspace_units_to_cm
        empty_element._oe.T_SOURCE     = self.source_plane_distance
        empty_element._oe.T_IMAGE      = 0.0
        empty_element._oe.T_INCIDENCE  = 0.0
        empty_element._oe.T_REFLECTION = 180.0
        empty_element._oe.ALPHA        = 0.0

        empty_element._oe.FWRITE = 3
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
        rx_slit[0] = attributes.diameter/self.workspace_units_to_m
        rz_slit[0] = attributes.diameter/self.workspace_units_to_m
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

        output_beam = ShadowBeam.traceFromOE(self.input_beam, empty_element, history=True)

        go = numpy.where(output_beam._beam.rays[:, 9] == GOOD)
        lo = numpy.where(output_beam._beam.rays[:, 9] != GOOD)

        print("Zone Plate Beam: ", "GO", len(go[0]), "LO", len(lo[0]))

        return output_beam

    def get_output_beam(self, zone_plate_beam, fzp_simulator):
        ideal_lens = ShadowOpticalElement.create_ideal_lens()

        focal_distance = fzp_simulator.focal_distance/self.workspace_units_to_m
        focal_xz = 1 / ((1 / self.source_distance) + (1 / focal_distance))

        ideal_lens._oe.focal_x = focal_xz
        ideal_lens._oe.focal_z = focal_xz

        ideal_lens._oe.user_units_to_cm = self.workspace_units_to_cm
        ideal_lens._oe.T_SOURCE         = 0.0
        ideal_lens._oe.T_IMAGE          = focal_distance

        output_beam = ShadowBeam.traceIdealLensOE(zone_plate_beam, ideal_lens, history=True)

        intensity, amplitude, efficiency = fzp_simulator.simulate()

        #----------------------------------------------------------------------------------------
        # from Hybrid: the ideal focusing is corrected by using the image at focus as a divergence correction distribution
        X, Y, dif_xpzp = fzp_simulator.create_2D_profile(intensity[1, :], last_index=50)
        xp = X[0, :]/fzp_simulator.focal_distance
        zp = Y[:, 0]/fzp_simulator.focal_distance

        fzp_simulator.plot_2D(None, intensity[1, :], last_index=100, show=True)

        go = numpy.where(output_beam._beam.rays[:, 9] == GOOD)

        dx_ray = numpy.arctan(output_beam._beam.rays[go, 3] / output_beam._beam.rays[go, 4])  # calculate divergence from direction cosines from SHADOW file  dx = atan(v_x/v_y)
        dz_ray = numpy.arctan(output_beam._beam.rays[go, 5] / output_beam._beam.rays[go, 4])  # calculate divergence from direction cosines from SHADOW file  dz = atan(v_z/v_y)

        s2d = Sampler2D(dif_xpzp, xp, zp)

        pos_dif_x, pos_dif_z = s2d.get_n_sampled_points(dx_ray.shape[1])

        #correction to the position with the divergence kick from the waveoptics calculation
        xx_image = output_beam._beam.rays[go, 0] + focal_distance * pos_dif_x # ray tracing to the image plane
        zz_image = output_beam._beam.rays[go, 2] + focal_distance * pos_dif_z # ray tracing to the image plane

        output_beam._oe_number = self.input_beam._oe_number + 1

        # new divergence distribution: convolution
        dx_conv = numpy.arctan(pos_dif_x) + dx_ray  # add the ray divergence kicks
        dz_conv = numpy.arctan(pos_dif_z) + dz_ray  # add the ray divergence kicks

        angle_num = numpy.sqrt(1 + (numpy.tan(dz_conv)) ** 2 + (numpy.tan(dx_conv)) ** 2)

        output_beam._beam.rays[go, 0] = copy.deepcopy(xx_image)
        output_beam._beam.rays[go, 2] = copy.deepcopy(zz_image)
        output_beam._beam.rays[go, 3] = numpy.tan(dx_conv) / angle_num
        output_beam._beam.rays[go, 4] = 1 / angle_num
        output_beam._beam.rays[go, 5] = numpy.tan(dz_conv) / angle_num
        #----------------------------------------------------------------------------------------

        output_beam._beam.rays[go, 6] *= numpy.sqrt(efficiency)
        output_beam._beam.rays[go, 7] *= numpy.sqrt(efficiency)
        output_beam._beam.rays[go, 8] *= numpy.sqrt(efficiency)
        output_beam._beam.rays[go, 15] *= numpy.sqrt(efficiency)
        output_beam._beam.rays[go, 16] *= numpy.sqrt(efficiency)
        output_beam._beam.rays[go, 17] *= numpy.sqrt(efficiency)

        output_beam._beam.retrace(self.image_plane_distance - focal_distance)

        return output_beam

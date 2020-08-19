import sys, numpy, copy

from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QMessageBox

from matplotlib import cm, rcParams

from scipy.interpolate import RectBivariateSpline, interp1d

from silx.gui.plot import Plot2D

from orangewidget import gui, widget
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.util.oasys_util import EmittingStream, TTYGrabber, TriggerIn

from srxraylib.util.inverse_method_sampler import Sampler2D

from orangecontrib.shadow.util.shadow_objects import ShadowOpticalElement, ShadowCompoundOpticalElement, ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowCongruence, ShadowPhysics, ShadowMath
from orangecontrib.shadow_advanced_tools.util.fresnel_zone_plates.fresnel_zone_plate_simulator import FZPAttributes, FZPSimulatorOptions, FresnelZonePlateSimulator

from orangecontrib.shadow.widgets.gui.ow_generic_element import GenericElement

GOOD = 1

COLLIMATED_SOURCE_LIMIT = 1e4 #m

class FresnelZonePlate(GenericElement):

    name = "Fresnel Zone Plate (Beta)"
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

    height = Setting(400.0) # nm
    diameter = Setting(50.0) # um
    b_min = Setting(50.0) # nm
    zone_plate_material = Setting('Au')
    template_material = Setting('SiO2')

    zone_plate_type = Setting(0)
    width_coating = Setting(20) # nm
    height1_factor = Setting(0.33)
    height2_factor = Setting(0.67)

    with_central_stop = Setting(0)
    cs_diameter = Setting(10.0) # um

    with_order_sorting_aperture = Setting(0)

    osa_position = Setting(10.0) # user units
    osa_diameter =  Setting(30.0) # um

    source_distance_flag = Setting(0)
    source_distance = Setting(0.0)

    image_distance_flag = Setting(1)
    image_distance = Setting(0.0)

    with_multi_slicing = Setting(0)
    n_slices = Setting(100)

    increase_resolution = Setting(1)
    increase_points = Setting(200)

    n_points = Setting(5000)
    last_index = Setting(100)

    ##################################################

    avg_energy = 0.0
    number_of_zones = 0
    focal_distance = 0.0
    efficiency = 0.0

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

        tab_zone_plate_1 = oasysgui.createTabPage(tabs_basic_setting, "Input Parameters")
        tab_zone_plate_2 = oasysgui.createTabPage(tabs_basic_setting, "Propagation Parameters")
        tab_zone_plate_3 = oasysgui.createTabPage(tabs_basic_setting, "Output Parameters")

        zp_box = oasysgui.widgetBox(tab_zone_plate_1, "F.Z.P. Parameters", addSpace=False, orientation="vertical", height=475)

        oasysgui.lineEdit(zp_box, self, "b_min",  "Outermost Zone Width/Period [nm]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(zp_box, self, "diameter", "F.Z.P. Diameter [" + u"\u03BC" + "m]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(zp_box, self, "height",  "F.Z.P. Height [nm]", labelWidth=260, valueType=float, orientation="horizontal")

        gui.comboBox(zp_box, self, "zone_plate_type", label="Type of F.Z.P.", labelWidth=350,
                     items=["Ordinary", "Zone-Doubled", "Zone-Filled", "Two-Level"],
                     callback=self.set_FZPType, sendSelectedValue=False, orientation="horizontal")

        oasysgui.lineEdit(zp_box, self, "zone_plate_material",  "F.Z.P. Material", labelWidth=160, valueType=str, orientation="horizontal")

        self.ord_box = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical", height=60)

        self.zd_box = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical", height=60)
        oasysgui.lineEdit(self.zd_box, self, "template_material",  "Template Material", labelWidth=160, valueType=str, orientation="horizontal")
        oasysgui.lineEdit(self.zd_box, self, "width_coating",  "Coating Width [nm]", labelWidth=260, valueType=float, orientation="horizontal")

        self.zf_box = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical", height=60)
        oasysgui.lineEdit(self.zf_box, self, "template_material", "Template Material", labelWidth=160, valueType=str, orientation="horizontal")
        oasysgui.lineEdit(self.zf_box, self, "width_coating", "Coating Width [nm]", labelWidth=260, valueType=float, orientation="horizontal")

        self.tl_box = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical", height=60)
        oasysgui.lineEdit(self.tl_box, self, "height1_factor",  "Height 1 Factor", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.tl_box, self, "height2_factor",  "Height 2 Factor", labelWidth=260, valueType=float, orientation="horizontal")

        self.set_FZPType()

        gui.comboBox(zp_box, self, "with_central_stop", label="With Central Stop", labelWidth=350,
                     items=["No", "Yes"],
                     callback=self.set_WithCentralStop, sendSelectedValue=False, orientation="horizontal")

        self.cs_box_1 = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical", height=30)
        self.cs_box_2 = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical", height=30)

        oasysgui.lineEdit(self.cs_box_1, self, "cs_diameter", "C.S. Diameter [" + u"\u03BC" + "m]", labelWidth=260, valueType=float, orientation="horizontal")

        self.set_WithCentralStop()

        gui.comboBox(zp_box, self, "with_order_sorting_aperture", label="With Order Sorting Aperture", labelWidth=350,
                     items=["No", "Yes"],
                     callback=self.set_WithOrderSortingAperture, sendSelectedValue=False, orientation="horizontal")

        self.osa_box_1 = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical", height=60)
        self.osa_box_2 = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical", height=60)

        self.le_osa_position = oasysgui.lineEdit(self.osa_box_1, self, "osa_position", "O.S.A. position ", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.osa_box_1, self, "osa_diameter", "O.S.A. Diameter [" + u"\u03BC" + "m]", labelWidth=260, valueType=float, orientation="horizontal")

        self.set_WithOrderSortingAperture()

        gui.comboBox(zp_box, self, "source_distance_flag", label="Source Distance", labelWidth=350,
                     items=["Same as Source Plane", "Different"],
                     callback=self.set_SourceDistanceFlag, sendSelectedValue=False, orientation="horizontal")

        self.zp_box_1 = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical", height=30)
        self.zp_box_2 = oasysgui.widgetBox(zp_box, "", addSpace=False, orientation="vertical", height=30)

        self.le_source_distance = oasysgui.lineEdit(self.zp_box_1, self, "source_distance", "Source Distance", labelWidth=260, valueType=float, orientation="horizontal")

        self.set_SourceDistanceFlag()

        gui.comboBox(zp_box, self, "image_distance_flag", label="Image Distance", labelWidth=350,
                     items=["Image Plane Distance", "F.Z.P. Image Distance"],
                     callback=self.set_ImageDistanceFlag, sendSelectedValue=False, orientation="horizontal")

        self.set_ImageDistanceFlag()

        prop_box = oasysgui.widgetBox(tab_zone_plate_2, "Propagation Parameters", addSpace=False, orientation="vertical", height=270)

        '''
        gui.comboBox(prop_box, self, "with_multi_slicing", label="With Multi-Slicing", labelWidth=350,
                     items=["No", "Yes"],
                     callback=self.set_WithMultislicing, sendSelectedValue=False, orientation="horizontal")

        self.ms_box_1 = oasysgui.widgetBox(prop_box, "", addSpace=False, orientation="vertical", height=30)
        self.ms_box_2 = oasysgui.widgetBox(prop_box, "", addSpace=False, orientation="vertical", height=30)

        oasysgui.lineEdit(self.ms_box_1, self, "n_slices", "Nr. Slices", labelWidth=260, valueType=int, orientation="horizontal")

        self.set_WithMultislicing()
        '''

        oasysgui.lineEdit(prop_box, self, "n_points", "Nr. Sampling Points", labelWidth=260, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(prop_box, self, "last_index", "Last Index of Focal Image", labelWidth=260, valueType=int, orientation="horizontal")

        gui.separator(prop_box)

        gui.comboBox(prop_box, self, "increase_resolution", label="Increase Resolution in Focal Image", labelWidth=350,
                     items=["No", "Yes"],
                     callback=self.set_IncreaseResolution, sendSelectedValue=False, orientation="horizontal")

        self.res_box_1 = oasysgui.widgetBox(prop_box, "", addSpace=False, orientation="vertical", height=30)
        self.res_box_2 = oasysgui.widgetBox(prop_box, "", addSpace=False, orientation="vertical", height=30)

        oasysgui.lineEdit(self.res_box_1, self, "increase_points", "Nr. Points", labelWidth=260, valueType=int, orientation="horizontal")

        self.set_IncreaseResolution()

        zp_out_box = oasysgui.widgetBox(tab_zone_plate_3, "Output Parameters", addSpace=False, orientation="vertical", height=270)

        self.le_avg_wavelength = oasysgui.lineEdit(zp_out_box, self, "avg_energy", "Average Energy [eV]", labelWidth=260, valueType=float, orientation="horizontal")
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

        self.le_image_distance = oasysgui.lineEdit(zp_out_box, self, "image_distance", "Image Distance (Q)", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_image_distance.setReadOnly(True)
        font = QFont(self.le_image_distance.font())
        font.setBold(True)
        self.le_image_distance.setFont(font)
        palette = QPalette(self.le_image_distance.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_image_distance.setPalette(palette)

        self.le_efficiency = oasysgui.lineEdit(zp_out_box, self, "efficiency", "Efficiency % (Avg. Wavelength)", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_efficiency.setReadOnly(True)
        font = QFont(self.le_efficiency.font())
        font.setBold(True)
        self.le_efficiency.setFont(font)
        palette = QPalette(self.le_efficiency.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_efficiency.setPalette(palette)


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

        propagation_plot_tab = oasysgui.widgetBox(self.main_tabs, addToLayout=0, margin=4)

        self.main_tabs.insertTab(1, propagation_plot_tab, "TEMP")
        self.main_tabs.setTabText(0, "Shadow Plot")
        self.main_tabs.setTabText(1, "F.Z.P. Simulator Plot")

        self.prop_tabs = oasysgui.tabWidget(propagation_plot_tab)
        self.prop_tab = [oasysgui.createTabPage(self.prop_tabs, "Radial Intensity"),
                         oasysgui.createTabPage(self.prop_tabs, "Generated 2D distribution")]
        self.prop_plot_canvas = [None, None]

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

                    options = FZPSimulatorOptions(with_central_stop=self.with_central_stop==1,
                                                  cs_diameter=numpy.round(self.cs_diameter*1e-6, 7),
                                                  with_order_sorting_aperture=self.with_order_sorting_aperture==1,
                                                  osa_position=self.osa_position*self.workspace_units_to_m,
                                                  osa_diameter=numpy.round(self.osa_diameter*1e-6, 7),
                                                  zone_plate_type=self.zone_plate_type,
                                                  width_coating=numpy.round(self.width_coating*1e-9, 10),
                                                  height1_factor=self.height1_factor,
                                                  height2_factor=self.height2_factor,
                                                  with_range=False,
                                                  with_multi_slicing=self.with_multi_slicing==1,
                                                  n_slices=self.n_slices,
                                                  with_complex_amplitude=False,
                                                  store_partial_results=False)
                    attributes = FZPAttributes(height=numpy.round(self.height*1e-9, 7),
                                               diameter=numpy.round(self.diameter*1e-6, 7),
                                               b_min=numpy.round(self.b_min*1e-9, 10),
                                               zone_plate_material=self.zone_plate_material,
                                               template_material=self.template_material)

                    zone_plate_beam = self.get_zone_plate_beam(attributes)

                    self.progressBarSet(30)

                    self.avg_energy = numpy.round(ShadowPhysics.getEnergyFromShadowK(numpy.average(zone_plate_beam._beam.rays[numpy.where(zone_plate_beam._beam.rays[:, 9] == GOOD), 10])), 2)

                    fzp_simulator = FresnelZonePlateSimulator(attributes=attributes, options=options)
                    fzp_simulator.initialize(energy_in_KeV=self.avg_energy/1000, n_points=self.n_points)

                    self.number_of_zones = fzp_simulator.n_zones
                    self.focal_distance = numpy.round(fzp_simulator.focal_distance/self.workspace_units_to_m, 6)

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

        label = self.le_osa_position.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_source_distance.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_focal_distance.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_image_distance.parent().layout().itemAt(0).widget()
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

    def set_FZPType(self):
        self.ord_box.setVisible(self.zone_plate_type == 0)
        self.zd_box.setVisible(self.zone_plate_type == 1)
        self.zf_box.setVisible(self.zone_plate_type == 2)
        self.tl_box.setVisible(self.zone_plate_type == 3)

    def set_SourceDistanceFlag(self):
        self.zp_box_1.setVisible(self.source_distance_flag == 1)
        self.zp_box_2.setVisible(self.source_distance_flag == 0)

    def set_WithCentralStop(self):
        self.cs_box_1.setVisible(self.with_central_stop == 1)
        self.cs_box_2.setVisible(self.with_central_stop == 0)

    def set_WithOrderSortingAperture(self):
        self.osa_box_1.setVisible(self.with_order_sorting_aperture == 1)
        self.osa_box_2.setVisible(self.with_order_sorting_aperture == 0)

    def set_WithMultislicing(self):
        self.ms_box_1.setVisible(self.with_multi_slicing == 1)
        self.ms_box_2.setVisible(self.with_multi_slicing == 0)

    def set_IncreaseResolution(self):
        self.res_box_1.setVisible(self.increase_resolution == 1)
        self.res_box_2.setVisible(self.increase_resolution == 0)

    def set_ImageDistanceFlag(self):
        self.le_image_plane_distance.setEnabled(self.image_distance_flag==0)

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

        return output_beam

    def get_output_beam(self, zone_plate_beam, fzp_simulator):
        # ----------------------------------------------------------------------------------------
        # raytracing of an ideal lens to focal position
        ideal_lens = ShadowOpticalElement.create_ideal_lens()

        focal_distance      = fzp_simulator.focal_distance/self.workspace_units_to_m
        self.image_distance = numpy.round(1 / ((1 / focal_distance) - (1 / self.source_distance)), 6)

        ideal_lens._oe.focal_x = focal_distance
        ideal_lens._oe.focal_z = focal_distance

        ideal_lens._oe.user_units_to_cm = self.workspace_units_to_cm
        ideal_lens._oe.T_SOURCE         = 0.0
        ideal_lens._oe.T_IMAGE          = 0.0 # hybrid screen!

        output_beam = ShadowBeam.traceIdealLensOE(zone_plate_beam, ideal_lens, history=True)

        # ----------------------------------------------------------------------------------------

        intensity, _, efficiency = fzp_simulator.simulate()

        profile_1D = intensity[-1, :]
        self.efficiency = numpy.round(efficiency*100, 3)

        #----------------------------------------------------------------------------------------
        # from Hybrid: the ideal focusing is corrected by using the image at focus as a divergence correction distribution

        X, Y, dif_xpzp = fzp_simulator.create_2D_profile(profile_1D, self.last_index)
        
        x = X[0, :]
        z = Y[:, 0]

        xp = x/fzp_simulator.focal_distance
        zp = z/fzp_simulator.focal_distance

        data_1D = profile_1D[:self.last_index]
        radius  = numpy.arange(0, fzp_simulator.max_radius, fzp_simulator.step)[:self.last_index]

        if self.increase_resolution:
            interpolator = interp1d(radius, data_1D, bounds_error=False, fill_value=0.0, kind='quadratic')
            radius = numpy.linspace(radius[0], radius[-1], self.increase_points)
            
            data_1D = interpolator(radius)
            
            interpolator = RectBivariateSpline(xp, zp, dif_xpzp, bbox=[None, None, None, None], kx=2, ky=2, s=0)
            x  = numpy.linspace(x[0], x[-1], self.increase_points)
            z  = numpy.linspace(z[0], z[-1], self.increase_points)
            xp = numpy.linspace(xp[0], xp[-1], self.increase_points)
            zp = numpy.linspace(zp[0], zp[-1], self.increase_points)

            dif_xpzp = interpolator(xp, zp)

        go = numpy.where(output_beam._beam.rays[:, 9] == GOOD)

        dx_ray = numpy.arctan(output_beam._beam.rays[go, 3] / output_beam._beam.rays[go, 4])  # calculate divergence from direction cosines from SHADOW file  dx = atan(v_x/v_y)
        dz_ray = numpy.arctan(output_beam._beam.rays[go, 5] / output_beam._beam.rays[go, 4])  # calculate divergence from direction cosines from SHADOW file  dz = atan(v_z/v_y)

        s2d = Sampler2D(dif_xpzp, xp, zp)

        pos_dif_x, pos_dif_z = s2d.get_n_sampled_points(dx_ray.shape[1])

        # new divergence distribution: convolution
        dx_conv = dx_ray + numpy.arctan(pos_dif_x)  # add the ray divergence kicks
        dz_conv = dz_ray + numpy.arctan(pos_dif_z)  # add the ray divergence kicks

        # correction to the position with the divergence kick from the waveoptics calculation
        # the correction is made on the positions at the hybrid screen (T_IMAGE = 0)
        image_distance = (self.image_distance if self.image_distance_flag==1 else self.image_plane_distance)

        xx_image = output_beam._beam.rays[go, 0] + image_distance * numpy.tan(dx_conv) # ray tracing to the image plane
        zz_image = output_beam._beam.rays[go, 2] + image_distance * numpy.tan(dz_conv) # ray tracing to the image plane

        output_beam._oe_number = self.input_beam._oe_number + 1

        angle_num = numpy.sqrt(1 + (numpy.tan(dz_conv)) ** 2 + (numpy.tan(dx_conv)) ** 2)

        output_beam._beam.rays[go, 0] = copy.deepcopy(xx_image)
        output_beam._beam.rays[go, 2] = copy.deepcopy(zz_image)
        output_beam._beam.rays[go, 3] = numpy.tan(dx_conv) / angle_num
        output_beam._beam.rays[go, 4] = 1 / angle_num
        output_beam._beam.rays[go, 5] = numpy.tan(dz_conv) / angle_num
        #----------------------------------------------------------------------------------------

        efficiency_factor = numpy.sqrt(efficiency)
        output_beam._beam.rays[go, 6] *= efficiency_factor
        output_beam._beam.rays[go, 7] *= efficiency_factor
        output_beam._beam.rays[go, 8] *= efficiency_factor
        output_beam._beam.rays[go, 15] *= efficiency_factor
        output_beam._beam.rays[go, 16] *= efficiency_factor
        output_beam._beam.rays[go, 17] *= efficiency_factor

        self.plot_propagation_results(radius*1e6, data_1D, x*1e6, z*1e6, dif_xpzp)

        return output_beam

    def plot_propagation_results(self, radius, data_1D, x, z, data2D):
        self.plot_1D(0, radius, data_1D)
        self.plot_2D(1, x, z, data2D)

    def plot_1D(self, index, radius, profile_1D, replace=True, profile_name="z pos #1", control=False, color='blue'):
        if self.prop_plot_canvas[index] is None:
            self.prop_plot_canvas[index] = oasysgui.plotWindow(parent=None,
                                              backend=None,
                                              resetzoom=True,
                                              autoScale=True,
                                              logScale=True,
                                              grid=True,
                                              curveStyle=True,
                                              colormap=False,
                                              aspectRatio=False,
                                              yInverted=False,
                                              copy=True,
                                              save=True,
                                              print_=True,
                                              control=control,
                                              position=True,
                                              roi=False,
                                              mask=False,
                                              fit=True)

            self.prop_plot_canvas[index].setDefaultPlotLines(True)
            self.prop_plot_canvas[index].setActiveCurveColor(color="#00008B")
            self.prop_tab[index].layout().addWidget(self.prop_plot_canvas[index])

        title  = "Radial Intensity Profile"
        xtitle = "Radius [\u03bcm]"
        ytitle = "Intensity [A.U.]"

        self.prop_plot_canvas[index].setGraphTitle(title)
        self.prop_plot_canvas[index].setGraphXLabel(xtitle)
        self.prop_plot_canvas[index].setGraphYLabel(ytitle)

        rcParams['axes.formatter.useoffset']='False'

        self.prop_plot_canvas[index].addCurve(radius, profile_1D, profile_name, symbol='', color=color, xlabel=xtitle, ylabel=ytitle, replace=replace) #'+', '^', ','

        self.prop_plot_canvas[index].setInteractiveMode('zoom', color='orange')
        self.prop_plot_canvas[index].resetZoom()
        self.prop_plot_canvas[index].replot()

        self.prop_plot_canvas[index].setActiveCurve("Radial Intensity Profile")

    def plot_2D(self, index, dataX, dataY, data2D):
        origin = (dataX[0], dataY[0])
        scale = (dataX[1] - dataX[0], dataY[1] - dataY[0])

        colormap = {"name": "temperature", "normalization": "linear", "autoscale": True, "vmin": 0, "vmax": 0, "colors": 256}

        if self.prop_plot_canvas[index] is None:
            self.prop_plot_canvas[index] = Plot2D()

            self.prop_plot_canvas[index].resetZoom()
            self.prop_plot_canvas[index].setXAxisAutoScale(True)
            self.prop_plot_canvas[index].setYAxisAutoScale(True)
            self.prop_plot_canvas[index].setGraphGrid(False)
            self.prop_plot_canvas[index].setKeepDataAspectRatio(True)
            self.prop_plot_canvas[index].yAxisInvertedAction.setVisible(False)

            self.prop_plot_canvas[index].setXAxisLogarithmic(False)
            self.prop_plot_canvas[index].setYAxisLogarithmic(False)

            self.prop_plot_canvas[index].getMaskAction().setVisible(False)
            self.prop_plot_canvas[index].getRoiAction().setVisible(False)
            self.prop_plot_canvas[index].getColormapAction().setVisible(True)
            self.prop_plot_canvas[index].setKeepDataAspectRatio(False)

            self.prop_tab[index].layout().addWidget(self.prop_plot_canvas[index])
            
        self.prop_plot_canvas[index].clear()
        self.prop_plot_canvas[index].addImage(numpy.array(data2D),
                             legend="rotated",
                             scale=scale,
                             origin=origin,
                             colormap=colormap,
                             replace=True)

        self.prop_plot_canvas[index].setActiveImage("rotated")
        self.prop_plot_canvas[index].setGraphXLabel("X [\u03bcm]")
        self.prop_plot_canvas[index].setGraphYLabel("Z [\u03bcm]")
        self.prop_plot_canvas[index].setGraphTitle("2D Intensity Profile")



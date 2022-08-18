# -------------------------------------------------------------------------------
# Name:        CPP Tools
# Purpose:
#
# Author:      MMoore
#
# Created:     07/04/2020
# Copyright:   (c) MMoore 2020
# Licence:     <your licence>
# -------------------------------------------------------------------------------

# Import modules
import arcpy, time, datetime, sys, traceback
from getpass import getuser
from arcgis.features import FeatureLayer

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True
arcpy.env.workspace = "memory"

def parameter(displayName, name, datatype, defaultValue=None, parameterType='Required', direction='Input',
              multiValue=False, filterList=None):
    '''This function defines the parameter definitions for a tool. Using this
    function saves lines of code by prepopulating some of the values and also
    allows setting a default value.
    '''
    # create parameter with a few default properties
    param = arcpy.Parameter(
        displayName=displayName,
        name=name,
        datatype=datatype,
        parameterType=parameterType,
        direction=direction,
        multiValue=multiValue)
    # set new parameter to a default value
    param.value = defaultValue
    if filterList:
        param.filter.type = "ValueList"
        param.filter.list = filterList
    # return complete parameter object
    return param

def bufferFeatures(features, eoid, buff_dist):
    in_features = []
    query = "EO_ID = {}".format(eoid)
    # Create variables for naming feature layers and buffers
    for n, fc in enumerate(features):
        arcpy.MakeFeatureLayer_management(fc, "sf_lyr{}".format(n), query)
        out = arcpy.Buffer_analysis("sf_lyr{}".format(n), "memory\\sf_buff{}".format(n), buff_dist)
        # Append buffers to in_features list
        in_features.append(out)

    sf_buff_union = arcpy.Union_analysis(in_features, "memory\\sf_buff_union")
    sf_buff = arcpy.Dissolve_management(sf_buff_union, "memory\\sf_buff")

    with arcpy.da.SearchCursor(sf_buff, 'SHAPE@') as cursor:
        for row in cursor:
            geom = row[0]
    return geom

def calc_attr_core(eoid, eo_ptreps, specID=None, drawn_notes=None):
    query = "EO_ID = {}".format(eoid)
    with arcpy.da.SearchCursor(eo_ptreps, ["SNAME", "ELSUBID", "EXPT_DATE"], query) as cursor:
        for row in cursor:
            sname = row[0]
            elsubid = row[1]
            expt_date = row[2].strftime("%m/%d/%Y")
    date = datetime.datetime.today().strftime("%m/%d/%Y")
    user = getuser()
    if specID:
        SpecID = specID
    else:
        SpecID = None
    if drawn_notes:
        drawn_notes = drawn_notes
    else:
        drawn_notes = None
    values = [sname, eoid, user, date, drawn_notes, "r", SpecID, elsubid, expt_date]
    return values

def calc_attr_slp(core_lyr, specID=None, drawn_notes=None):
    with arcpy.da.SearchCursor(core_lyr,
                               ["SNAME", "EO_ID", "Project", "SpecID", "ELSUBID", "BioticsExportDate"]) as cursor:
        for row in cursor:
            sname = row[0]
            eoid = row[1]
            project = row[2]
            spec = row[3]
            elsubid = row[4]
            expt_date = row[5].strftime("%m/%d/%Y")
    date = datetime.datetime.today().strftime("%m/%d/%Y")
    user = getuser()
    if specID:
        specID = specID
    else:
        specID = spec
    if drawn_notes:
        drawn_notes = drawn_notes
    else:
        drawn_notes = None
    values = [sname, eoid, user, date, drawn_notes, project, "r", specID, elsubid, expt_date]
    return values

def localWatershed(input_poly, lidar_gdb, pa_county):
    arcpy.env.workspace = "memory"

    cnty_dict = {'Adams': 'Adams', 'Allegheny': 'Alleg', 'Armstrong': 'Armstrong', 'Beaver': 'Beave',
                 'Bedford': 'Bedfo', 'Berks': 'Berks', 'Blair': 'Blair', 'Bradford': 'Bradf', 'Bucks': 'Bucks',
                 'Butler': 'Butler', 'Cambria': 'Cambr', 'Cameron': 'Camer', 'Carbon': 'Carbo', 'Centre': 'Centr',
                 'Chester': 'Chest', 'Clarion': 'Clarion', 'Clearfield': 'Clear', 'Clinton': 'Clint',
                 'Columbia': 'Colum', 'Crawford': 'Erie_Cr', 'Cumberland': 'Cumbe', 'Dauphin': 'Dauph',
                 'Delaware': 'Delaw', 'Elk': 'Elk', 'Erie': 'Erie_Cr', 'Fayette': 'Fayet', 'Forest': 'Forest',
                 'Franklin': 'Frank', 'Fulton': 'Fulto', 'Greene': 'Green', 'Huntingdon': 'Hunti', 'Indiana': 'India',
                 'Jefferson': 'Jeffe', 'Juniata': 'Junia', 'Lackawanna': 'Lacka', 'Lancaster': 'Lanca',
                 'Lawrence': 'Lawrence', 'Lebanon': 'Leban', 'Lehigh': 'Leh_Nor', 'Luzerne': 'Luzerne', 'Lycoming':
                     'Lycom', 'Mckean': 'McKea', 'McKean': 'McKea', 'Mercer': 'Mercer', 'Mifflin': 'Miffl',
                 'Monroe': 'Monro',
                 'Montgomery': 'Montg', 'Montour': 'Monto', 'Northampton': 'Leh_Nor', 'Northumberland': 'Numb',
                 'Perry': 'Perry', 'Philadelphia': 'Phila', 'Pike': 'Pike', 'Potter': 'Potte', 'Schuylkill': 'Schuy',
                 'Snyder': 'Snyde', 'Somerset': 'Somer', 'Sullivan': 'Sulli', 'Susquehanna': 'Susqu', 'Tioga': 'Tioga',
                 'Union': 'Union', 'Venango': 'Venango', 'Warren': 'Warren', 'Washington': 'Washi', 'Wayne': 'Wayne',
                 'Westmoreland': 'Westm', 'Wyoming': 'Wyomi', 'York': 'York'}

    xy = [row[0] for row in arcpy.da.SearchCursor(input_poly, ["SHAPE@XY"])][0]
    spatial_ref = arcpy.Describe(input_poly).spatialReference
    centroid = arcpy.PointGeometry(arcpy.Point(xy[0], xy[1]), spatial_ref)
    cnty_lyr = arcpy.MakeFeatureLayer_management(pa_county, "cnty_lyr")
    arcpy.SelectLayerByLocation_management("cnty_lyr", "INTERSECT", centroid)

    ### ADD CHECK FOR NO SELECTION

    with arcpy.da.SearchCursor(cnty_lyr, "COUNTY_NAM") as cursor:
        county_name = sorted({row[0].title() for row in cursor})[0]
    county_abbr = cnty_dict[county_name]

    flow_acc = r"{0}\{1}_FlowAcc".format(lidar_gdb, county_abbr)
    flow_dir = r"{0}\{1}_FlowDir".format(lidar_gdb, county_abbr)

    spp = arcpy.sa.SnapPourPoint(input_poly, flow_acc, 0, "OBJECTID")
    watershed_raster = arcpy.sa.Watershed(flow_dir, spp, "VALUE")

    watershed_temp = arcpy.RasterToPolygon_conversion(watershed_raster, "memory\\watershed_temp")
    watershed_union = arcpy.Union_analysis([watershed_temp, input_poly], "memory\\watershed_union")
    watershed = arcpy.Dissolve_management(watershed_union, "memory\\watershed")

    with arcpy.da.SearchCursor(watershed, "SHAPE@") as cursor:
        for row in cursor:
            watershed_geom = row[0]

    return watershed_geom

def supportingWatershed(core, watershed_geom, slp_buff, slp_limit):
    watershed_limit = arcpy.Buffer_analysis(core, "memory\\watershed_limit", slp_limit)
    watershed_clip = arcpy.Clip_analysis(watershed_geom, watershed_limit, "memory\\watershed_clip")
    core_buff = arcpy.Buffer_analysis(core, "memory\\core_buff", slp_buff)

    slp_union = arcpy.Union_analysis([watershed_clip, core_buff], "memory\\slp_union")
    slp_shape = arcpy.Dissolve_management(slp_union, "memory\\slp_shape")

    with arcpy.da.SearchCursor(slp_shape, "SHAPE@") as cursor:
        for row in cursor:
            slp_geom = row[0]

    return slp_geom

def select_adjacent_features(initial_selection, search_distance = None):
    """This function selects additional features within the input feature layer that are adjacent to the already selected features. If a search distance is
    specified, features within a distance of the selected features will be selected. If no search distance is specified, only contiguous features will be selected."""

    # Get count of selected features in the initial selection
    count1 = (int(arcpy.GetCount_management(initial_selection).getOutput(0)))
    arcpy.AddMessage("Initial selection contains " + str(count1) + " features.")

    # If there is an initial selection, procede with script
    if count1 != 0:
        # Select additional features adjacent to the selected features
        arcpy.SelectLayerByLocation_management(initial_selection, "WITHIN_A_DISTANCE", initial_selection , search_distance, "ADD_TO_SELECTION")
        # Count number of selected features
        count2 = (int(arcpy.GetCount_management(initial_selection).getOutput(0)))

        # As long as the first count is less than the second count, continue selecting additional features
        while count1 < count2:
            # The second count becomes the first count
            count1 = count2
            # Select additional features adjacent to the selected features
            arcpy.SelectLayerByLocation_management(initial_selection, "WITHIN_A_DISTANCE", initial_selection, search_distance, "ADD_TO_SELECTION")
            # Count number of selected features
            count2 = (int(arcpy.GetCount_management(initial_selection).getOutput(0)))
        arcpy.AddMessage("Selection complete. There are {} adjacent features.".format(count2))

    # If there is no initial selection, add error message
    else:
        arcpy.AddError("Input layer {} has no features or there is no initial selection.".format(initial_selection))

######################################################################################################################################################
## Begin Toolbox
######################################################################################################################################################

class Toolbox(object):
    def __init__(self):
        self.label = "CPP Tools"
        self.alias = "CPP Tools"
        self.tools = [SetDefQuery, BufferSFs, BufferCore, PlantSupporting, BaldEagleCore, BaldEagleSupporting,
                      EasternRedbellyTurtleCore, EasternRedbellyTurtleSupporting, EasternSpadefootCore, EasternSpadefootSupporting,
                      SpottedTurtleCore, SpottedTurtleSupporting, NorthernLeopardFrogCore, NorthernLeopardFrogSupporting,
                      HellbenderMudpuppyCore, AlleghenyWoodratCore, AlleghenyWoodratSupporting, EasternHognoseSnakeCore,
                      EasternHognoseSnakeSupporting, QueensnakeCore, QueensnakeSupporting, ShortheadGarterSnakeCore,
                      ShortheadGarterSnakeSupporting, NorthernCoalSkinkSupporting, EasternRibbonSnakeSupporting,
                      GreenSalamanderSupporting, MountainChorusFrogCore, MountainChorusFrogSupporting, LepidopteraForestMosaicCore,
                      LepidopteraForestMosaicSupporting, LepidopteraWetlandCore, LepidopteraWetlandSupporting, NorthernCricketFrogCore,
                      NorthernCricketFrogSupporting,TimberRattlesnakeSupporting, BlueSpottedSalamanderCore, RoughGreenSnakeCore,
                      RoughGreenSnakeSupporting, GeneralWatershedSupportingTool]  # <<<<<< ADD TOOLS HERE >>>>>>>>

######################################################################################################################################################
## Set Definition Query
######################################################################################################################################################

class SetDefQuery(object):
    def __init__(self):
        self.label = "Set EO Definition Query"
        self.description = ""
        self.canRunInBackground = False
        self.category = "General CPP Tools"
        self.params = [
            parameter("EO ID that you wish to use for definitiona query on all Biotics and CPP layers:", "eoid",
                      "GPLong")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        m = aprx.listMaps("Map")[0]
        for lyr in m.listLayers("eo_*"):
            lyr.definitionQuery = "EO_ID = {}".format(eoid)
        for lyr in m.listLayers("CPP *"):
            lyr.definitionQuery = "EO_ID = {} OR EO_ID IS NULL".format(eoid)

######################################################################################################################################################
## Buffer SFs
######################################################################################################################################################

class BufferSFs(object):
    def __init__(self):
        self.label = "Create CPP Core from Buffered Source Features"
        self.description = ""
        self.canRunInBackground = False
        self.category = "General CPP Tools"
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Buffer Distance", "buff_dist", "GPLinearUnit"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("CPP Spec ID", "specID", "GPString", "", "Optional")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        buff_dist = params[1].valueAsText
        cpp_core = params[2].valueAsText
        specID = params[3].valueAsText

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        geom = bufferFeatures(srcfeatures, eoid, buff_dist)

        values = calc_attr_core(eoid, eo_ptreps, specID)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Buffer Core
######################################################################################################################################################

class BufferCore(object):
    def __init__(self):
        self.label = "Create CPP Supporting from Buffered Core"
        self.description = ""
        self.canRunInBackground = False
        self.category = "General CPP Tools"
        self.params = [
            parameter("Selected CPP Core Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("Buffer Distance", "buff_dist", "GPLinearUnit"),
            parameter("Supporting CPP Layer", "slp", "GPFeatureLayer", "CPPEdit\\CPP Supporting")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        cpp_core = params[0].valueAsText
        buff_dist = params[1].valueAsText
        cpp_supporting = params[2].valueAsText

        core_lyr = arcpy.MakeFeatureLayer_management(cpp_core, "core_lyr")
        buff = arcpy.Buffer_analysis(core_lyr, "memory\\core_buff", buff_dist)
        with arcpy.da.SearchCursor(buff, 'SHAPE@') as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_slp(cpp_core)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_supporting, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Plant Supporting
######################################################################################################################################################

class PlantSupporting(object):
    def __init__(self):
        # Override the label and description in the superclass
        self.label = "Plants Supporting"
        self.category = "Plants and Community"
        self.description = ""
        plantList = ["Plants_Aquatic_20121016", "Plants_Floodplain_20121016",
                     "Plants_Open_disturbed_upland_habitat_20121016",
                     "Plants_Outcrop_barren_20121212", "Plants_Palustrine_20120417", "Plants_Scour_20121016",
                     "Plants_Shoreline_20121016",
                     "Plants_Upland_forest_20121016", "Reptiles_Eastern_Ribbon_Snake_20121030"]
        self.params = [
            parameter("Which SpecID are you using?", "specID", "GPString", filterList=plantList),
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("LiDAR GDB", "lidar_gdb", "DEWorkspace"),
            parameter("PA County Layer", "pa_county", "GPFeatureLayer"),
            parameter("Supporting CPP Layer", "slp", "GPFeatureLayer", "CPPEdit\\CPP Supporting")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        specID = params[0].valueAsText
        core = params[1].valueAsText
        lidar_gdb = params[2].valueAsText
        pa_county = params[3].valueAsText
        slp = params[4].valueAsText

        if specID == "Plants_Aquatic_20121016":
            slp_buff = "120 Meters"
            slp_limit = "2000 Meters"
        elif specID == "Plants_Floodplain_20121016":
            slp_buff = "120 Meters"
            slp_limit = "300 Meters"
        elif specID == "Plants_Open_disturbed_upland_habitat_20121016":
            slp_buff = "120 Meters"
            slp_limit = "300 Meters"
        elif specID == "Plants_Outcrop_barren_20121212":
            slp_buff = "120 Meters"
            slp_limit = "300 Meters"
        elif specID == "Plants_Palustrine_20120417":
            slp_buff = "120 Meters"
            slp_limit = "2000 Meters"
        elif specID == "Plants_Scour_20121016":
            slp_buff = "120 Meters"
            slp_limit = "300 Meters"
        elif specID == "Plants_Shoreline_20121016":
            slp_buff = "120 Meters"
            slp_limit = "300 Meters"
        elif specID == "Plants_Upland_forest_20121016":
            slp_buff = "120 Meters"
            slp_limit = "300 Meters"
        elif specID == "Reptiles_Eastern_Ribbon_Snake_20121030":
            slp_buff = "120 Meters"
            slp_limit = "10000 Meters"
        else:
            arcpy.AddWarning("Oh no! No valid specID was returned and we don't know why.")

        watershed_geom = localWatershed(core, lidar_gdb, pa_county)
        slp_geom = supportingWatershed(core, watershed_geom, slp_buff, slp_limit)

        values = calc_attr_slp(core, drawn_notes="Used CPP watershed tool.")
        values.append(slp_geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(slp, fields) as cursor:
            cursor.insertRow(values)

        return

######################################################################################################################################################
## Bald Eagle Core
######################################################################################################################################################

class BaldEagleCore(object):
    def __init__(self):
        self.label = "Bald Eagle Core"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Birds"
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText

        buff_dist = 201
        specID = "Birds_Bald_eagle_20150317"
        notes = "PRELIMINARY - check line-of-sight exclusions and remove unsuitable habitat"

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        geom = bufferFeatures(srcfeatures, eoid, buff_dist)

        values = calc_attr_core(eoid, eo_ptreps, specID, notes)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Bald Eagle Supporting
######################################################################################################################################################

class BaldEagleSupporting(object):
    def __init__(self):
        self.label = "Bald Eagle Supporting"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Birds"
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("CPP Supporting Layer", "supporting", "GPFeatureLayer", "CPPEdit\\CPP Supporting"),
            parameter("NWI Layer", "NWI", "GPFeatureLayer"),
            parameter("Wengerrd Buffer Layer", "wengerrd", "GPFeatureLayer"),
            parameter("Connection Line", "connection", "GPFeatureLayer", "", "Optional")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        core = params[0].valueAsText
        supporting = params[1].valueAsText
        NWI = params[2].valueAsText
        wengerrd = params[3].valueAsText
        connection = params[4].valueAsText

        with arcpy.da.SearchCursor(core, "EO_ID") as cursor:
            for row in cursor:
                eoid = row[0]

        buff_dist = 599
        specID = "Birds_Bald_eagle_20150317"
        notes = "PRELIMINARY - review to ensure the main foraging habitat was not buffered and merge with Wengerrd feature"

        core_buff = arcpy.Buffer_analysis(core, "memory\\core_buff", buff_dist, "", "", "ALL")
        nwi = arcpy.MakeFeatureLayer_management(NWI, "nwi", "WETLAND_TYPE <> 'Riverine'")
        arcpy.SelectLayerByLocation_management(nwi, "INTERSECT", core_buff, "", "NEW_SELECTION")

        desc = arcpy.Describe(nwi)
        if desc.FIDSet == '':
            final_buff = core_buff
        else:
            nwi_buff = arcpy.Buffer_analysis(nwi, "memory\\nwi_buff", 300, "", "", "ALL")
            final_buff = arcpy.Merge_management([core_buff, nwi_buff], "memory\\final_buff")
            final_buff = arcpy.Dissolve_management(final_buff, "memory\\final_buff1")

        if connection:
            connection_buff = arcpy.Buffer_analysis(connection, "memory\\connection_buff", 50, "", "", "ALL")
            final_buff = arcpy.Merge_management([final_buff, connection_buff], "memory\\final_buff2")
            final_buff = arcpy.Dissolve_management(final_buff, "memory\\final_buff3")
        else:
            pass

        with arcpy.da.SearchCursor(final_buff, 'SHAPE@') as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_slp(core, specID, notes)
        values.append(geom)

        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(supporting, fields) as cursor:
            cursor.insertRow(values)

        wengerrd = arcpy.MakeFeatureLayer_management(wengerrd, "memory\\wengerrd")
        arcpy.SelectLayerByLocation_management(wengerrd, "INTERSECT", geom, "", "NEW_SELECTION")
        with arcpy.da.SearchCursor(wengerrd, "SHAPE@") as cursor:
            for row in cursor:
                geom1 = row[0]

        notes = "PRELIMINARY - remove wengerrd 1600 meters downstream of core."
        values = calc_attr_slp(core, specID, notes)
        values.append(geom1)

        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(supporting, fields) as cursor:
            cursor.insertRow(values)


######################################################################################################################################################
## Eastern Red Belly Turtle Core
######################################################################################################################################################

class EasternRedbellyTurtleCore(object):
    def __init__(self):
        self.label = "Eastern Redbelly Turtle Core"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Reptiles"
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("Habitat Delineation", "habitat", "GPFeatureLayer"),
            parameter("Buffered Habitat", "buffer", "GPFeatureLayer"),
            parameter("NWI Layer", "NWI", "GPFeatureLayer"),
            parameter("Ch93 streams", "ch93streams", "GPFeatureLayer"),
            parameter("NHD Flowline", "nhd_flowline", "GPFeatureLayer"),
            parameter("NHD Waterbodies", "waterbodies", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        habitat = params[2].valueAsText
        hab_buff = params[3].valueAsText
        NWI = params[4].valueAsText
        ch93streams = params[5].valueAsText
        nhd_flowline = params[6].valueAsText
        waterbodies = params[7].valueAsText

        eo_ptreps = "Biotics\\eo_ptreps"
        specID = "Reptiles_Eastern_Redbelly_Turtle_20140930"

        merge_features = []

        arcpy.AddMessage("create buffers")
        # hab_buff = arcpy.Buffer_analysis(habitat, "memory\\hab_buff", 250, "", "", "ALL")
        merge_features.append(hab_buff)
        clip_lyr = arcpy.Buffer_analysis(habitat, "memory\\clip_lyr", 1000, "", "", "ALL")

        arcpy.AddMessage("create layers")
        nwi = arcpy.MakeFeatureLayer_management(NWI, "nwi")
        ch93 = arcpy.MakeFeatureLayer_management(ch93streams, "ch93")
        nhd_lyr = arcpy.MakeFeatureLayer_management(nhd_flowline, "nhd_lyr", '"STREAMORDE" >= 3')
        waterbodies_lyr = arcpy.MakeFeatureLayer_management(waterbodies, "waterbodies_lyr")

        arcpy.AddMessage("select nwi and ch93")
        arcpy.SelectLayerByLocation_management(nwi, "INTERSECT", hab_buff, "", "NEW_SELECTION")
        arcpy.SelectLayerByLocation_management(ch93, "INTERSECT", hab_buff, "", "NEW_SELECTION")
        ch93_length = 0
        while ch93_length < 1000:
            arcpy.SelectLayerByLocation_management(ch93,"INTERSECT",ch93,"","ADD_TO_SELECTION")
            ch93_length = 0
            with arcpy.da.SearchCursor(ch93,"Shape_Length") as cursor:
                for row in cursor:
                    ch93_length = ch93_length + row[0]

        arcpy.AddMessage("select waterbodies")
        arcpy.SelectLayerByLocation_management(waterbodies_lyr, "INTERSECT", habitat, 1000, "NEW_SELECTION")
        arcpy.SelectLayerByLocation_management(waterbodies_lyr, "INTERSECT", nwi, "", "SUBSET_SELECTION")
        waterbodies_nwi_buff = arcpy.Buffer_analysis(waterbodies_lyr, "memory\\waterbodies_nwi_buff", 250, "", "", "ALL")
        merge_features.append(waterbodies_nwi_buff)

        arcpy.SelectLayerByLocation_management(waterbodies_lyr, "INTERSECT", habitat, 1000, "NEW_SELECTION")
        arcpy.SelectLayerByLocation_management(waterbodies_lyr, "INTERSECT", ch93, "", "SUBSET_SELECTION")
        waterbodies_ch93_buff = arcpy.Buffer_analysis(waterbodies_lyr, "memory\\waterbodies_ch93_buff", 250, "", "", "ALL")
        merge_features.append(waterbodies_ch93_buff)

        arcpy.AddMessage("select nhd")
        arcpy.SelectLayerByLocation_management(nhd_lyr, "INTERSECT", habitat, 1000, "NEW_SELECTION")
        nhd_clip = arcpy.Clip_analysis(nhd_lyr, clip_lyr, "memory\\nhd_clip")
        nhd_dissolve = arcpy.Dissolve_management(nhd_clip,"memory\\nhd_dissolve","","","",True)
        arcpy.SelectLayerByLocation_management(nhd_dissolve,"INTERSECT",hab_buff,"","NEW_SELECTION")
        nhd_buff = arcpy.Buffer_analysis(nhd_dissolve, "memory\\nhd_buff", 250, "", "", "ALL")
        merge_features.append(nhd_buff)

        arcpy.AddMessage("merge features")
        merge_lyr = arcpy.Merge_management(merge_features, "memory\\merge_lyr")
        dissolve_lyr = arcpy.Dissolve_management(merge_lyr, "memory\\dissolve_lyr")
        with arcpy.da.SearchCursor(dissolve_lyr, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_core(eoid, eo_ptreps, specID)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate",
                  "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Eastern Red Belly Turtle Supporting
######################################################################################################################################################

class EasternRedbellyTurtleSupporting(object):
    def __init__(self):
        self.label = "Eastern Redbelly Turtle Supporting"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Reptiles"
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("CPP Supporting Layer", "supporting", "GPFeatureLayer", "CPPEdit\\CPP Supporting"),
            parameter("HUC12 Watersheds", "HUC12", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        core = params[0].valueAsText
        supporting = params[1].valueAsText
        HUC12 = params[2].valueAsText

        arcpy.SelectLayerByLocation_management(HUC12, "INTERSECT", core, "", "NEW_SELECTION")
        huc_dissolve = arcpy.Dissolve_management(HUC12,"memory\\huc_dissolve")
        with arcpy.da.SearchCursor(huc_dissolve, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_slp(core)
        values.append(geom)

        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(supporting, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Eastern Spadefoot Core
######################################################################################################################################################

class EasternSpadefootCore(object):
    def __init__(self):
        self.label = "Eastern Spadefoot Core"
        self.category = "Amphibians"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("Unfiltered Core CPP Layer","unfiltered_cpp","GPFeatureLayer","no filter cpp"),
            parameter("NWI Layer", "NWI", "GPFeatureLayer"),
            parameter("Floodplain", "floodplain", "GPFeatureLayer"),
            parameter("Unmapped Wetland", "wetland", "GPFeatureLayer", "", "Optional")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        unfiltered_cpp = params[2].valueAsText
        NWI = params[3].valueAsText
        floodplain = params[4].valueAsText
        wetland = params[5].valueAsText

        specID = "Amphibians_Eastern_Spadefoot_20130816"

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        with arcpy.da.SearchCursor(eo_ptreps,"ELSUBID") as cursor:
            for row in cursor:
                elsubid = row[0]

        clip_geom = bufferFeatures(srcfeatures, eoid, 400)

        merge_features = []

        floodplain_clip = arcpy.Clip_analysis(floodplain,clip_geom,"memory\\floodplain_clip")
        floodplain_buff = arcpy.Buffer_analysis(floodplain_clip,"memory\\floodplain_buff",400)
        merge_features.append(floodplain_buff)

        NWI_lyr = arcpy.MakeFeatureLayer_management(NWI, "NWI_lyr", "WETLAND_TYPE <> 'Riverine' AND WETLAND_TYPE <> 'Lake'")
        arcpy.SelectLayerByLocation_management(NWI_lyr,"INTERSECT",clip_geom,"","NEW_SELECTION")
        NWI_buff = arcpy.Buffer_analysis(NWI_lyr,"memory\\NWI_buff",400)
        merge_features.append(NWI_buff)

        if wetland:
            wetland_lyr = arcpy.MakeFeatureLayer_management(wetland,"wetland_lyr")
            arcpy.SelectLayerByLocation_management(wetland_lyr,"INTERSECT",clip_geom,"","NEW_SELECTION")
            wetland_buff = arcpy.Buffer_analysis(wetland_lyr,"memory\\wetland_buff",400)
            merge_features.append(wetland_buff)

        merge_lyr = arcpy.Merge_management(merge_features, "memory\\merge_lyr")
        dissolve_lyr = arcpy.Dissolve_management(merge_lyr, "memory\\dissolve_lyr")
        with arcpy.da.SearchCursor(dissolve_lyr, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        cpp_lyr = arcpy.MakeFeatureLayer_management(unfiltered_cpp, "cpp_lyr", "ELSUBID = {} AND EO_ID <> {}".format(elsubid,eoid))
        arcpy.SelectLayerByLocation_management(cpp_lyr,"INTERSECT",geom,5000,"NEW_SELECTION")

        desc = arcpy.Describe(cpp_lyr)
        if desc.FIDSet == '':
            arcpy.AddMessage("No Eastern Spadefoot CPP cores are within 5km.")
            pass
        else:
            combine_eos = [str(f[0]) for f in arcpy.da.SearchCursor(cpp_lyr,"EO_ID")]
            notes = "Core is within 5km of the following EO IDs: "+", ".join(combine_eos)+". Combine this polygon with primary core if no major separation barriers."
            arcpy.AddMessage(str(len(combine_eos)) + " Eastern Spadefoot CPP cores were within 5km and will be combined with this core.")
            g = [f[0] for f in arcpy.da.SearchCursor(cpp_lyr,"SHAPE@")]
            g.append(geom)
            c = [f[0].convexHull() for f in arcpy.da.SearchCursor(arcpy.Dissolve_management(g,'memory\\dissolve'),"SHAPE@")]
            envelope = arcpy.management.CopyFeatures(c,"memory\\envelope")
            with arcpy.da.SearchCursor(envelope,"SHAPE@") as cursor:
                for row in cursor:
                    geom1 = row[0]
            values = calc_attr_core(eoid, eo_ptreps, specID, notes)
            values.append(geom1)
            fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
            with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
                cursor.insertRow(values)

        values = calc_attr_core(eoid, eo_ptreps, specID)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Eastern Spadefoot Supporting
######################################################################################################################################################

class EasternSpadefootSupporting(object):
    def __init__(self):
        self.label = "Eastern Spadefoot Supporting"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Amphibians"
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("CPP Supporting Layer", "supporting", "GPFeatureLayer", "CPPEdit\\CPP Supporting"),
            parameter("HUC12 Watersheds", "HUC12", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        core = params[0].valueAsText
        supporting = params[1].valueAsText
        HUC12 = params[2].valueAsText

        arcpy.SelectLayerByLocation_management(HUC12, "INTERSECT", core, "", "NEW_SELECTION")
        huc_dissolve = arcpy.Dissolve_management(HUC12,"memory\\huc_dissolve")
        with arcpy.da.SearchCursor(huc_dissolve, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_slp(core)
        values.append(geom)

        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(supporting, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Spotted Turtle Core
######################################################################################################################################################

class SpottedTurtleCore(object):
    def __init__(self):
        self.label = "Spotted Turtle Core"
        self.category = "Reptiles"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("NWI Layer", "NWI", "GPFeatureLayer"),
            parameter("Ch93 Streams", "streams", "GPFeatureLayer"),
            parameter("Unmapped Wetland", "wetland", "GPFeatureLayer", "", "Optional")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        NWI = params[2].valueAsText
        streams = params[3].valueAsText
        wetland = params[4].valueAsText

        specID = "Reptiles_Spotted_Turtle_20130430"

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        clip_geom = bufferFeatures(srcfeatures, eoid, 1000)

        merge_features = []

        NWI_lyr = arcpy.MakeFeatureLayer_management(NWI, "NWI_lyr", "WETLAND_TYPE <> 'Riverine'")
        arcpy.SelectLayerByLocation_management(NWI_lyr,"INTERSECT",clip_geom,"","NEW_SELECTION")

        if wetland:
            wetland_lyr = arcpy.MakeFeatureLayer_management(wetland,"wetland_lyr")
            arcpy.SelectLayerByLocation_management(wetland_lyr,"INTERSECT",clip_geom,"","NEW_SELECTION")
            wetland_buff = arcpy.Buffer_analysis(wetland_lyr,"memory\\wetland_buff",250)
            merge_features.append(wetland_buff)

        stream_lyr = arcpy.MakeFeatureLayer_management(streams,"stream_lyr")
        arcpy.SelectLayerByLocation_management(stream_lyr,"INTERSECT",NWI_lyr,5,"NEW_SELECTION")
        if wetland:
            arcpy.SelectLayerByLocation_management(stream_lyr, "INTERSECT", wetland_lyr,5, "ADD_TO_SELECTION")
        stream_clip = arcpy.Clip_analysis(stream_lyr,clip_geom,"memory\\stream_clip")
        stream_buff = arcpy.Buffer_analysis(stream_clip,"memory\\stream_buff",250)
        merge_features.append(stream_buff)

        NWI_buff = arcpy.Buffer_analysis(NWI_lyr,"memory\\NWI_buff",250)
        merge_features.append(NWI_buff)

        merge_lyr = arcpy.Merge_management(merge_features, "memory\\merge_lyr")
        dissolve_lyr = arcpy.Dissolve_management(merge_lyr, "memory\\dissolve_lyr")
        with arcpy.da.SearchCursor(dissolve_lyr, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_core(eoid, eo_ptreps, specID)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Spotted Turtle Supporting
######################################################################################################################################################

class SpottedTurtleSupporting(object):
    def __init__(self):
        self.label = "Spotted Turtle Supporting"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Reptiles"
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("CPP Supporting Layer", "supporting", "GPFeatureLayer", "CPPEdit\\CPP Supporting"),
            parameter("HUC12 Watersheds", "HUC12", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        core = params[0].valueAsText
        supporting = params[1].valueAsText
        HUC12 = params[2].valueAsText

        arcpy.SelectLayerByLocation_management(HUC12, "INTERSECT", core, "", "NEW_SELECTION")
        huc_dissolve = arcpy.Dissolve_management(HUC12,"memory\\huc_dissolve")
        core_buff = arcpy.Buffer_analysis(core,"memory\\core_buff",720)

        merge_feat = arcpy.Merge_management([huc_dissolve,core_buff],"memory\\merge_feat")
        merge_dissolve = arcpy.Dissolve_management(merge_feat,"memory\\merge_dissolve")

        with arcpy.da.SearchCursor(merge_dissolve, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_slp(core)
        values.append(geom)

        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(supporting, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Northern Leopard Frog Core
######################################################################################################################################################

class NorthernLeopardFrogCore(object):
    def __init__(self):
        self.label = "Northern Leopard Frog Core"
        self.category = "Amphibians"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("NWI Layer", "NWI", "GPFeatureLayer"),
            parameter("Ch93 Streams", "streams", "GPFeatureLayer"),
            parameter("Unmapped Wetland", "wetland", "GPFeatureLayer", "", "Optional")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        NWI = params[2].valueAsText
        streams = params[3].valueAsText
        wetland = params[4].valueAsText

        specID = "Amphibians_Northern_Leopard_Frog_20130225"

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        clip_geom = bufferFeatures(srcfeatures, eoid, 3000)

        merge_features = []

        NWI_clip = arcpy.Clip_analysis(NWI,clip_geom,"memory\\NWI_clip")
        NWI_buff = arcpy.Buffer_analysis(NWI_clip,"memory\\NWI_buff",500)
        merge_features.append(NWI_buff)

        stream_lyr = arcpy.MakeFeatureLayer_management(streams,"stream_lyr")
        stream_lyr = arcpy.SelectLayerByLocation_management(stream_lyr,"INTERSECT",clip_geom,"","NEW_SELECTION")
        stream_bank = arcpy.Buffer_analysis(stream_lyr,"memory\\stream_bank",7)
        stream_clip = arcpy.Clip_analysis(stream_bank,clip_geom,"memory\\stream_clip")
        stream_buff = arcpy.Buffer_analysis(stream_clip,"memory\\stream_buff",500)
        merge_features.append(stream_buff)

        if wetland:
            wetland_clip = arcpy.Clip_analysis(wetland,clip_geom,"memory\\wetland_clip")
            wetland_buff = arcpy.Buffer_analysis(wetland_clip,"memory\\wetland_buff",500)
            merge_features.append(wetland_buff)

        merge_lyr = arcpy.Merge_management(merge_features, "memory\\merge_lyr")
        dissolve_lyr = arcpy.Dissolve_management(merge_lyr, "memory\\dissolve_lyr")
        with arcpy.da.SearchCursor(dissolve_lyr, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_core(eoid, eo_ptreps, specID)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Northern Leopard Frog Supporting
######################################################################################################################################################

class NorthernLeopardFrogSupporting(object):
    def __init__(self):
        self.label = "Northern Leopard Frog Supporting"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Amphibians"
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("LiDAR GDB", "lidar_gdb", "DEWorkspace"),
            parameter("PA County Layer", "pa_county", "GPFeatureLayer"),
            parameter("Supporting CPP Layer", "slp", "GPFeatureLayer", "CPPEdit\\CPP Supporting")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        core = params[0].valueAsText
        lidar_gdb = params[1].valueAsText
        pa_county = params[2].valueAsText
        slp = params[3].valueAsText

        slp_buff = "120 Meters"
        slp_limit = "1000000 Meters"

        watershed_geom = localWatershed(core, lidar_gdb, pa_county)
        slp_geom = supportingWatershed(core, watershed_geom, slp_buff, slp_limit)

        values = calc_attr_slp(core, drawn_notes="Used CPP watershed tool.")
        values.append(slp_geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(slp, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Mudpuppy and Eastern Hellbender Core
######################################################################################################################################################

class HellbenderMudpuppyCore(object):
    def __init__(self):
        self.label = "Eastern Hellbender and Mudpuppy Core"
        self.category = "Amphibians"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("Wenger Buffer", "wenger", "GPFeatureLayer"),
            parameter("Which spec are you using?", "specID", "GPString", filterList=["Amphibians_Eastern_Hellbender_20130528","Amphibians_Mudpuppy_20130528"])]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        wenger = params[2].valueAsText
        specID = params[3].valueAsText

        if specID == "Amphibians_Eastern_Hellbender_20130528":
            notes = "PRELIMINARY - remove tributaries if < 4 Strahler class and/or downstream tributaries, connect disjointed CPPs along same stem"
        else:
            notes = "PRELIMINARY - remove tributaries if < 3 Strahler class and/or downstream tributaries, connect disjointed CPPs along same stem"

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        buff_feat = bufferFeatures(srcfeatures, eoid, 350)
        clip_feat = arcpy.Clip_analysis(buff_feat,wenger,os.path.join("memory","clip_feat"))

        with arcpy.da.SearchCursor(clip_feat, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_core(eoid, eo_ptreps, specID, notes)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Allegheny Woodrat Core
######################################################################################################################################################

class AlleghenyWoodratCore(object):
    def __init__(self):
        self.label = "Allegheny Woodrat Core"
        self.category = "Mammals"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("Butchkoski Active Woodrat Geology Layer", "woodrat_geo", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        woodrat_geo = params[2].valueAsText

        specID = "Mammals_Allegheny_woodrat_20100521"

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        merge_features = []
        buff_feat = bufferFeatures(srcfeatures, eoid, 200)
        merge_features.append(buff_feat)

        woodrat_lyr = arcpy.MakeFeatureLayer_management(woodrat_geo,"woodrat_lyr")
        woodrat_lyr = arcpy.SelectLayerByLocation_management(woodrat_lyr,"INTERSECT",buff_feat)

        with arcpy.da.SearchCursor(woodrat_lyr,"SHAPE@") as cursor:
            for row in cursor:
                merge_features.append(row[0])

        merge_lyr = arcpy.Merge_management(merge_features,os.path.join("memory","merge_lyr"))
        dissolve_lyr = arcpy.Dissolve_management(merge_lyr,os.path.join("memory","dissolve_lyr"))

        with arcpy.da.SearchCursor(dissolve_lyr, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_core(eoid, eo_ptreps, specID)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Allegheny Woodrat Supporting
######################################################################################################################################################

class AlleghenyWoodratSupporting(object):
    def __init__(self):
        self.label = "Allegheny Woodrat Supporting"
        self.category = "Mammals"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("CPP Supporting Layer", "supporting", "GPFeatureLayer", "CPPEdit\\CPP Supporting"),
            parameter("WPC 25ac Forest Blocks", "forest", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        core = params[0].valueAsText
        supporting = params[1].valueAsText
        forest = params[2].valueAsText

        arcpy.SelectLayerByLocation_management(forest, "INTERSECT", core, "", "NEW_SELECTION")
        dissolve_lyr = arcpy.Dissolve_management(forest,"memory\\dissolve_lyr")

        merge_feat = arcpy.Merge_management([dissolve_lyr,core],"memory\\merge_feat")
        merge_dissolve = arcpy.Dissolve_management(merge_feat,"memory\\merge_dissolve")

        with arcpy.da.SearchCursor(merge_dissolve, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_slp(core)
        values.append(geom)

        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(supporting, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Eastern Hognose Snake Core
######################################################################################################################################################

class EasternHognoseSnakeCore(object):
    def __init__(self):
        self.label = "Eastern Hognose Snake Core"
        self.category = "Reptiles"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("Unfiltered Core CPP Layer", "unfiltered_cpp", "GPFeatureLayer", "no filter cpp"),
            parameter("Floodplains", "floodplains", "GPFeatureLayer"),
            parameter("NWI Layer", "NWI", "GPFeatureLayer"),
            parameter("SSURGO Soil Layer", "soils", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        unfiltered_cpp = params[2].valueAsText
        floodplains = params[3].valueAsText
        NWI = params[4].valueAsText
        soils = params[5].valueAsText

        specID = "Reptiles_Eastern_Hognose_Snake_20121024"
        notes = "PRELIMINARY CORE - remove unsuitable habitat and connect cores along suitable habitat corrdors"

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        with arcpy.da.SearchCursor(eo_ptreps,"ELSUBID") as cursor:
            for row in cursor:
                elsubid = row[0]

        sf_buff = bufferFeatures(srcfeatures, eoid, 800)
        clip_buff = bufferFeatures(srcfeatures, eoid, 2000)

        clipped_features = []

        floodplain_clip = arcpy.Clip_analysis(floodplains,clip_buff,os.path.join("memory","floodplain_clip"))
        clipped_features.append(floodplain_clip)

        nwi_clip = arcpy.Clip_analysis(NWI,clip_buff,os.path.join("memory","nwi_clip"))
        clipped_features.append(nwi_clip)

        query = "muname LIKE '%sand%' Or muname LIKE '%gravel%'"
        soils_lyr = arcpy.MakeFeatureLayer_management(soils,"soils_lyr",query)
        soils_clip = arcpy.Clip_analysis(soils_lyr,clip_buff,os.path.join("memory","soils_clip"))
        clipped_features.append(soils_clip)

        merge = arcpy.Merge_management(clipped_features,os.path.join("memory","merge"))
        dissolve = arcpy.Dissolve_management(merge,os.path.join("memory","dissolve"),"","","SINGLE_PART")

        dissolve_lyr = arcpy.MakeFeatureLayer_management(dissolve,"dissolve_lyr")
        arcpy.SelectLayerByLocation_management(dissolve_lyr,"INTERSECT",sf_buff)
        core_features = arcpy.FeatureClassToFeatureClass_conversion(dissolve_lyr,"memory","core_features")

        core_merge = arcpy.Merge_management([core_features,sf_buff],os.path.join("memory","core_merge"))
        core_dissolve = arcpy.Dissolve_management(core_merge,os.path.join("memory","core_dissolve"))
        with arcpy.da.SearchCursor(core_dissolve,"SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        cpp_lyr = arcpy.MakeFeatureLayer_management(unfiltered_cpp, "cpp_lyr", "ELSUBID = {} AND EO_ID <> {}".format(elsubid,eoid))
        arcpy.SelectLayerByLocation_management(cpp_lyr,"INTERSECT",geom,5000,"NEW_SELECTION")

        desc = arcpy.Describe(cpp_lyr)
        if desc.FIDSet == '':
            arcpy.AddMessage("No Eastern Spadefoot CPP cores are within 5km.")
            pass
        else:
            combine_eos = [str(f[0]) for f in arcpy.da.SearchCursor(cpp_lyr,"EO_ID")]
            notes1 = "Core is within 5km of the following EO IDs: "+", ".join(combine_eos)+". Combine this polygon with primary core if suitable habitat is available for migration."
            arcpy.AddMessage(str(len(combine_eos)) + " Eastern Spadefoot CPP cores were within 5km and will be combined with this core.")
            g = [f[0] for f in arcpy.da.SearchCursor(cpp_lyr,"SHAPE@")]
            core_merge = arcpy.Merge_management(g,os.path.join("memory","core_merge"))
            core_dissolve = arcpy.Dissolve_management(core_merge,os.path.join("memory","core_dissolve"))
            with arcpy.da.SearchCursor(core_dissolve,"SHAPE@") as cursor:
                for row in cursor:
                    geom1 = row[0]
            values = calc_attr_core(eoid, eo_ptreps, specID, notes1)
            values.append(geom1)
            fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
            with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
                cursor.insertRow(values)

        values = calc_attr_core(eoid, eo_ptreps, specID, notes)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Eastern Hognose Snake Supporting
######################################################################################################################################################

class EasternHognoseSnakeSupporting(object):
    def __init__(self):
        self.label = "Eastern Hognose Snake Supporting"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Reptiles"
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("LiDAR GDB", "lidar_gdb", "DEWorkspace"),
            parameter("PA County Layer", "pa_county", "GPFeatureLayer"),
            parameter("HUC12 Watersheds", "HUC12", "GPFeatureLayer"),
            parameter("Supporting CPP Layer", "slp", "GPFeatureLayer", "CPPEdit\\CPP Supporting")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        core = params[0].valueAsText
        lidar_gdb = params[1].valueAsText
        pa_county = params[2].valueAsText
        huc12 = params[3].valueAsText
        slp = params[4].valueAsText

        slp_buff = "120 Meters"
        slp_limit = "1000000 Meters"

        watershed_geom = localWatershed(core, lidar_gdb, pa_county)
        slp_geom = supportingWatershed(core, watershed_geom, slp_buff, slp_limit)

        huc12_lyr = arcpy.MakeFeatureLayer_management(huc12,"huc12_lyr")
        arcpy.SelectLayerByLocation_management(huc12_lyr,"INTERSECT",core)
        watershed_clip = arcpy.Clip_analysis(slp_geom,huc12_lyr,os.path.join("memory","watershed_clip"))

        with arcpy.da.SearchCursor(watershed_clip,"SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        # slp_geom = supportingWatershed(core, watershed_geom, slp_buff, slp_limit)

        values = calc_attr_slp(core, drawn_notes="Used CPP watershed tool.")
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(slp, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Queensnake Core
######################################################################################################################################################

class QueensnakeCore(object):
    def __init__(self):
        self.label = "Queensnake Core"
        self.category = "Reptiles"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("Polygon representing the delineated stream 1730m upstream and downstream of occurrences", "stream_poly", "GPFeatureLayer"),
            parameter("NWI Layer", "NWI", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        stream_poly = params[2].valueAsText
        NWI = params[3].valueAsText

        specID = "Reptiles_Queen_Snake_20131031"
        notes = "PRELIMINARY CORE - remove unsuitable habitat and ensure the stream width adjacent to added wetlands is included"

        eo_ptreps = "Biotics\\eo_ptreps"

        merge_features = []

        nwi_lyr = arcpy.MakeFeatureLayer_management(NWI,"nwi_lyr")
        arcpy.SelectLayerByLocation_management(nwi_lyr,"INTERSECT",stream_poly)
        nwi_buff = arcpy.Buffer_analysis(nwi_lyr,os.path.join("memory","nwi_buff",),"100 Meters")

        with arcpy.da.SearchCursor(nwi_buff,"SHAPE@") as cursor:
            for row in cursor:
                merge_features.append(row[0])

        stream_buff = arcpy.Buffer_analysis(stream_poly,"INTERSECT","100 Meters")
        with arcpy.da.SearchCursor(stream_buff,"SHAPE@") as cursor:
            for row in cursor:
                merge_features.append(row[0])

        core_merge = arcpy.Merge_management(merge_features,os.path.join("memory","core_merge"))
        core_dissolve = arcpy.Dissolve_management(core_merge,os.path.join("memory","core_dissolve"))
        with arcpy.da.SearchCursor(core_dissolve,"SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_core(eoid, eo_ptreps, specID, notes)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Queensnake Supporting
######################################################################################################################################################

class QueensnakeSupporting(object):
    def __init__(self):
        self.label = "Queensnake Supporting"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Reptiles"
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("LiDAR GDB", "lidar_gdb", "DEWorkspace"),
            parameter("PA County Layer", "pa_county", "GPFeatureLayer"),
            parameter("HUC12 Watersheds", "HUC12", "GPFeatureLayer"),
            parameter("Supporting CPP Layer", "slp", "GPFeatureLayer", "CPPEdit\\CPP Supporting")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        core = params[0].valueAsText
        lidar_gdb = params[1].valueAsText
        pa_county = params[2].valueAsText
        huc12 = params[3].valueAsText
        slp = params[4].valueAsText

        slp_buff = "120 Meters"
        slp_limit = "1000000 Meters"

        watershed_geom = localWatershed(core, lidar_gdb, pa_county)
        slp_geom = supportingWatershed(core, watershed_geom, slp_buff, slp_limit)

        huc12_lyr = arcpy.MakeFeatureLayer_management(huc12,"huc12_lyr")
        arcpy.SelectLayerByLocation_management(huc12_lyr,"INTERSECT",core)
        watershed_clip = arcpy.Clip_analysis(slp_geom,huc12_lyr,os.path.join("memory","watershed_clip"))

        with arcpy.da.SearchCursor(watershed_clip,"SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        # slp_geom = supportingWatershed(core, watershed_geom, slp_buff, slp_limit)

        notes = "If SLP contains another queen snake SLP, use larger downstream SLP that contains both cores for both occurrences"

        values = calc_attr_slp(core,drawn_notes = notes)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(slp, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Shorthead Garter Snake Core
######################################################################################################################################################

class ShortheadGarterSnakeCore(object):
    def __init__(self):
        self.label = "Shorthead Garter Snake Core"
        self.category = "Reptiles"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("Unfiltered Core CPP Layer","unfiltered_cpp","GPFeatureLayer","no filter cpp"),
            parameter("NWI Layer", "NWI", "GPFeatureLayer"),
            parameter("Stream Layer", "streams", "GPFeatureLayer"),
            parameter("Delineated open habitat (meadows, old fields, wetlands, ag fields) within 500m of SFs", "open_land", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        unfiltered_cpp = params[2].valueAsText
        NWI = params[3].valueAsText
        streams = params[4].valueAsText
        open_land = params[5].valueAsText

        specID = "Reptiles_Shorthead_Garter_Snake_20130524"

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        with arcpy.da.SearchCursor(eo_ptreps,"ELSUBID") as cursor:
            for row in cursor:
                elsubid = row[0]

        clip_geom = bufferFeatures(srcfeatures, eoid, 500)

        merge_features = []

        NWI_lyr = arcpy.MakeFeatureLayer_management(NWI, "NWI_lyr", "ATTRIBUTE LIKE '%PEM%' OR ATTRIBUTE LIKE '%PFO%' OR ATTRIBUTE LIKE '%PSS%'")
        NWI_clip = arcpy.Clip_analysis(NWI_lyr,clip_geom,os.path.join("memory","NWI_clip"))
        merge_features.append(NWI_clip)

        streams_clip = arcpy.Clip_analysis(streams,clip_geom,"memory\\streams_clip")
        streams_buff = arcpy.Buffer_analysis(streams_clip,"memory\\streams_buff",1)
        merge_features.append(streams_buff)

        open_clip = arcpy.Clip_analysis(open_land,clip_geom,os.path.join("memory","open_clip"))
        merge_features.append(open_clip)

        merge_lyr = arcpy.Merge_management(merge_features, "memory\\merge_lyr")
        dissolve_lyr = arcpy.Dissolve_management(merge_lyr, "memory\\dissolve_lyr")
        envelope = arcpy.MinimumBoundingGeometry_management(dissolve_lyr,os.path.join("memory","envelope"),"CONVEX_HULL")
        envelope_buff = arcpy.Buffer_analysis(envelope,os.path.join("memory","envelope_buff"),50)
        with arcpy.da.SearchCursor(envelope_buff, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        cpp_lyr = arcpy.MakeFeatureLayer_management(unfiltered_cpp, "cpp_lyr", "ELSUBID = {} AND EO_ID <> {}".format(elsubid,eoid))
        arcpy.SelectLayerByLocation_management(cpp_lyr,"INTERSECT",geom,1000,"NEW_SELECTION")

        desc = arcpy.Describe(cpp_lyr)
        if desc.FIDSet == '':
            arcpy.AddMessage("No Shorthead Garter Snake CPP cores are within 1km.")
            pass
        else:
            combine_eos = [str(f[0]) for f in arcpy.da.SearchCursor(cpp_lyr,"EO_ID")]
            notes = "Core is within 1km of the following EO IDs: "+", ".join(combine_eos)+". If suitable habitat, connect this polygon with primary core using stream layer with a 200m buffer, or a straight line 400m wide polygon if no streams connect the occurrences."
            arcpy.AddMessage(str(len(combine_eos)) + " Shorthead Garter Snake CPP cores were within 5km and will be combined with this core.")
            g = [f[0] for f in arcpy.da.SearchCursor(cpp_lyr,"SHAPE@")]
            g.append(geom)
            merged = arcpy.Merge_management(g,os.path.join("memory","merged"))
            dissolved = arcpy.Dissolve_management(merged,os.path.join("memory","dissolved"))
            with arcpy.da.SearchCursor(dissolved,"SHAPE@") as cursor:
                for row in cursor:
                    geom1 = row[0]
            values = calc_attr_core(eoid, eo_ptreps, specID, notes)
            values.append(geom1)
            fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
            with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
                cursor.insertRow(values)

        values = calc_attr_core(eoid, eo_ptreps, specID)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Shorthead Garter Snake Supporting
######################################################################################################################################################

class ShortheadGarterSnakeSupporting(object):
    def __init__(self):
        self.label = "Shorthead Garter Supporting"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Reptiles"
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("LiDAR GDB", "lidar_gdb", "DEWorkspace"),
            parameter("PA County Layer", "pa_county", "GPFeatureLayer"),
            parameter("HUC12 Watersheds", "HUC12", "GPFeatureLayer"),
            parameter("Supporting CPP Layer", "slp", "GPFeatureLayer", "CPPEdit\\CPP Supporting")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        core = params[0].valueAsText
        lidar_gdb = params[1].valueAsText
        pa_county = params[2].valueAsText
        huc12 = params[3].valueAsText
        slp = params[4].valueAsText

        slp_buff = "120 Meters"
        slp_limit = "1000000 Meters"

        watershed_geom = localWatershed(core, lidar_gdb, pa_county)
        slp_geom = supportingWatershed(core, watershed_geom, slp_buff, slp_limit)

        huc12_lyr = arcpy.MakeFeatureLayer_management(huc12, "huc12_lyr")
        arcpy.SelectLayerByLocation_management(huc12_lyr, "INTERSECT", core)
        watershed_clip = arcpy.Clip_analysis(slp_geom, huc12_lyr, os.path.join("memory", "watershed_clip"))

        with arcpy.da.SearchCursor(watershed_clip, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        notes = "Used CPP tool to delineate local watershed"

        values = calc_attr_slp(core, drawn_notes=notes)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(slp, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Northern Coal Skink Supporting
######################################################################################################################################################

class NorthernCoalSkinkSupporting(object):
    def __init__(self):
        self.label = "Northern Coal Skink Supporting"
        self.category = "Reptiles"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("CPP Supporting Layer", "supporting", "GPFeatureLayer", "CPPEdit\\CPP Supporting"),
            parameter("WPC 25ac Forest Blocks", "forest", "GPFeatureLayer"),
            parameter("HUC12 Watersheds", "HUC12", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        core = params[0].valueAsText
        supporting = params[1].valueAsText
        forest = params[2].valueAsText
        huc12 = params[3].valueAsText

        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]
        with arcpy.da.SearchCursor(core,"EO_ID") as cursor:
            for row in cursor:
                eoid = row[0]

        core_lyr = arcpy.MakeFeatureLayer_management(core, "core_lyr")
        core_buff = arcpy.Buffer_analysis(core_lyr, "memory\\core_buff", 100)

        clip_dist = bufferFeatures(srcfeatures,eoid,5000)

        huc12_lyr = arcpy.MakeFeatureLayer_management(huc12,"huc12_lyr")
        arcpy.SelectLayerByLocation_management(huc12_lyr,"INTERSECT",core_lyr)
        forest_clip = arcpy.Clip_analysis(forest,huc12_lyr,"memory\\forest_clip")

        forest_clip_lyr = arcpy.MakeFeatureLayer_management(forest_clip,"forest_clip_lyr")
        arcpy.SelectLayerByLocation_management(forest_clip_lyr,"INTERSECT",core_lyr)
        select_adjacent_features(forest_clip_lyr,"100 Meters")

        merge = arcpy.Merge_management([core_buff,forest_clip_lyr],"memory\\merge")
        merge_buff = arcpy.Buffer_analysis(merge,"memory\\merge_buff",100)

        merge_buff_to_feature = arcpy.FeatureToPolygon_management(merge_buff,"memory\\merge_buff_to_poly")
        diss = arcpy.Dissolve_management(merge_buff_to_feature,"memory\\diss")

        diss_clip = arcpy.Clip_analysis(diss,clip_dist,"memory\\diss_clip")

        notes = "Remove unsuitable habitat, merge overlapping supportings"

        with arcpy.da.SearchCursor(diss_clip, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_slp(core,drawn_notes=notes)
        values.append(geom)

        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(supporting, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Eastern Ribbon Snake Supporting
######################################################################################################################################################

class EasternRibbonSnakeSupporting(object):
    def __init__(self):
        self.label = "Eastern Ribbon Snake Supporting"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Reptiles"
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("LiDAR GDB", "lidar_gdb", "DEWorkspace"),
            parameter("PA County Layer", "pa_county", "GPFeatureLayer"),
            parameter("Supporting CPP Layer", "slp", "GPFeatureLayer", "CPPEdit\\CPP Supporting")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        core = params[0].valueAsText
        lidar_gdb = params[1].valueAsText
        pa_county = params[2].valueAsText
        slp = params[3].valueAsText

        slp_buff = "120 Meters"
        slp_limit = "1000000 Meters"

        watershed_geom = localWatershed(core, lidar_gdb, pa_county)
        slp_geom = supportingWatershed(core, watershed_geom, slp_buff, slp_limit)

        values = calc_attr_slp(core, drawn_notes="Used CPP watershed tool.")
        values.append(slp_geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(slp, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Green Salamander Supporting
######################################################################################################################################################

class GreenSalamanderSupporting(object):
    def __init__(self):
        self.label = "Green Salamander Supporting"
        self.category = "Amphibians"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("CPP Supporting Layer", "supporting", "GPFeatureLayer", "CPPEdit\\CPP Supporting"),
            parameter("PA Bedrock Geology Layer (pagpoly)", "geology", "GPFeatureLayer"),
            parameter("HUC12 Watersheds", "HUC12", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        core = params[0].valueAsText
        supporting = params[1].valueAsText
        geology = params[2].valueAsText
        huc12 = params[3].valueAsText

        core_lyr = arcpy.MakeFeatureLayer_management(core, "core_lyr")
        core_buff = arcpy.Buffer_analysis(core_lyr, "memory\\core_buff", 200)

        huc12_lyr = arcpy.MakeFeatureLayer_management(huc12,"huc12_lyr")
        arcpy.SelectLayerByLocation_management(huc12_lyr,"INTERSECT",core_lyr)
        where_clause = "NAME = '{}' OR NAME = '{}'".format("Mauch Chunk Formation", "Pottsville Formation")
        geology_lyr = arcpy.MakeFeatureLayer_management(geology,"geology_lyr", where_clause)
        geology_clip = arcpy.Clip_analysis(geology_lyr,huc12_lyr)

        geology_buff = arcpy.Buffer_analysis(geology_clip,os.path.join("memory","geology_buff"),200)

        merge = arcpy.Merge_management([geology_buff,core_buff],"memory\\merge")
        merge_buff_to_feature = arcpy.FeatureToPolygon_management(merge,"memory\\merge_buff_to_poly")
        diss = arcpy.Dissolve_management(merge_buff_to_feature,"memory\\diss")

        notes = "Remove disjunct polygons."

        with arcpy.da.SearchCursor(diss, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_slp(core,drawn_notes=notes)
        values.append(geom)

        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(supporting, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Mountain Chorus Frog Core
######################################################################################################################################################

class MountainChorusFrogCore(object):
    def __init__(self):
        self.label = "Mountain Chorus Frog Core"
        self.category = "Amphibians"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("NWI Layer", "NWI", "GPFeatureLayer"),
            parameter("WPC 25ac Forest Blocks", "forest", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        NWI = params[2].valueAsText
        forest = params[3].valueAsText

        specID = "Amphibians_Mountain_Chorus_Frog_20130516"

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        merge_features = []

        clip_geom = bufferFeatures(srcfeatures, eoid, 1000)

        NWI_lyr = arcpy.MakeFeatureLayer_management(NWI, "NWI_lyr", "WETLAND_TYPE <> 'Riverine'")
        arcpy.SelectLayerByLocation_management(NWI_lyr,"INTERSECT",clip_geom,"","NEW_SELECTION")
        NWI_buff = arcpy.Buffer_analysis(NWI_lyr,"memory\\NWI_buff",100)
        merge_features.append(NWI_buff)

        forest_lyr = arcpy.MakeFeatureLayer_management(forest, "forest_lyr")
        arcpy.SelectLayerByLocation_management(forest_lyr,"INTERSECT",clip_geom,"","NEW_SELECTION")
        forest_buff = arcpy.Buffer_analysis(forest_lyr,"memory\\forest_buff",100)
        merge_features.append(forest_buff)

        merge_lyr = arcpy.Merge_management(merge_features, "memory\\merge_lyr")
        dissolve_lyr = arcpy.Dissolve_management(merge_lyr, "memory\\dissolve_lyr")
        merge_to_poly = arcpy.FeatureToPolygon_management(dissolve_lyr, "memory\\merge_to_poly")
        diss = arcpy.Dissolve_management(merge_to_poly, "memory\\diss")
        with arcpy.da.SearchCursor(diss, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_core(eoid, eo_ptreps, specID)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Mountain Chorus Frog Supporting
######################################################################################################################################################

class MountainChorusFrogSupporting(object):
    def __init__(self):
        self.label = "Mountain Chorus Frog Supporting"
        self.category = "Amphibians"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("CPP Supporting Layer", "supporting", "GPFeatureLayer", "CPPEdit\\CPP Supporting"),
            parameter("WPC 25ac Forest Blocks", "forest", "GPFeatureLayer"),
            parameter("HUC12 Watersheds", "HUC12", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        core = params[0].valueAsText
        supporting = params[1].valueAsText
        forest = params[2].valueAsText
        huc12 = params[3].valueAsText

        core_lyr = arcpy.MakeFeatureLayer_management(core, "core_lyr")
        core_buff = arcpy.Buffer_analysis(core_lyr, "memory\\core_buff", 100)

        huc12_lyr = arcpy.MakeFeatureLayer_management(huc12, "huc12_lyr")
        arcpy.SelectLayerByLocation_management(huc12_lyr, "INTERSECT", core_lyr)
        forest_clip = arcpy.Clip_analysis(forest, huc12_lyr, "memory\\forest_clip")

        forest_clip_lyr = arcpy.MakeFeatureLayer_management(forest_clip, "forest_clip_lyr")
        arcpy.SelectLayerByLocation_management(forest_clip_lyr, "INTERSECT", core_lyr)
        select_adjacent_features(forest_clip_lyr, "100 Meters")

        merge = arcpy.Merge_management([core_buff, forest_clip_lyr], "memory\\merge")
        merge_buff = arcpy.Buffer_analysis(merge, "memory\\merge_buff", 100)

        merge_to_poly = arcpy.FeatureToPolygon_management(merge_buff, "memory\\merge_to_poly")
        diss = arcpy.Dissolve_management(merge_to_poly, "memory\\diss")

        notes = "Merge overlapping SLPs of multiple occurrences."

        with arcpy.da.SearchCursor(diss, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_slp(core, drawn_notes=notes)
        values.append(geom)

        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(supporting, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Lepidoptera Forest Mosaic
######################################################################################################################################################

class LepidopteraForestMosaicCore(object):
    def __init__(self):
        self.label = "Lepidoptera Forest Mosaic Core"
        self.category = "Lepidoptera"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("Community Classification Layer", "communities", "GPFeatureLayer"),
            parameter("Core inferred extent radius", "inferred_extent_distance", "GPLinearUnit")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        communities = params[2].valueAsText
        inferred_extent_distance = params[3].valueAsText

        specID = "Lepidoptera_Forest_Mosaic_20150409"

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        merge_features = []

        inferred_extent = bufferFeatures(srcfeatures, eoid, inferred_extent_distance)
        merge_features.append(inferred_extent)

        # create query for selected barrens and herbaceous opening plant communities as follows
        # Pitch pine - heath woodland: CTWCPPH000
        # Pitch pine - scrub oak woodland: CTWCPPS000
        # Pitch pine - rhodora scrub oak woodland: CTWCPRS000
        # Pitch pine - mixed hardwood woodland: CTWMPPH000

        # Red-cedar - pine serpentine shrubland: CTSCRSE000
        # Low heath shrubland: CTSBLHE000
        # Scrub oak shrubland: CTSBSCO000
        # Rhodora - mixed heath - scrub oak shrubland: CTSBRHS000

        # Little bluestem - Pennsylvania sedge opening: CTHOLBS000
        # Side-oatsgramma calcareous grassland: CTHOSOG000
        # Calcareous opening/cliff: CTHOCOC000
        # Serpentine grassland: CTHOSGR000
        # Serpentine gravel forb community: CTHOSGF000
        # Great Lakes Region dry sandplain: CTHOGLS000
        # Great Lakes Region sparsely vegetated beach: th03

        included_communities = ['CTWCPPH000','CTWCPPS000','CTWCPRS000','CTWMPPH000',
                                'CTSCRSE000','CTSBLHE000','CTSBSCO000','CTSBRHS000',
                                'CTHOLBS000','CTHOSOG000','CTHOCOC000','CTHOSGR000','CTHOSGF000','CTHOGLS000','th03']

        query = "CommClass in {}".format(tuple(included_communities))

        communities_lyr = arcpy.MakeFeatureLayer_management(communities,"communities_lyr",query)
        communities_lyr = arcpy.SelectLayerByLocation_management(communities_lyr,"INTERSECT",inferred_extent,"","NEW_SELECTION")
        desc = arcpy.Describe(communities_lyr)
        if desc.FIDSet == '':
            pass
        else:
            comm_selection = arcpy.FeatureClassToFeatureClass_conversion(communities_lyr,"memory","comm_selection")
            merge_features.append(comm_selection)

        merge_lyr = arcpy.Merge_management(merge_features, "memory\\merge_lyr")
        dissolve_lyr = arcpy.Dissolve_management(merge_lyr, "memory\\dissolve_lyr")

        with arcpy.da.SearchCursor(dissolve_lyr, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        acres_10 = str(round(geom.getArea("GEODESIC","ACRES")*.1,1))
        notes = "Remove unsuitable habitat blocks greater than "+acres_10+" acres, but retain 50ft of adjacent unsuitable habitat to account for edge."

        values = calc_attr_core(eoid, eo_ptreps, specID, notes)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Lepidoptera Forest Mosaic Supporting
######################################################################################################################################################

class LepidopteraForestMosaicSupporting(object):
    def __init__(self):
        self.label = "Lepidoptera Forest Mosaic Supporting"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Lepidoptera"
        self.params = [
            parameter("Selected CPP Core Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("Supporting CPP Layer", "slp", "GPFeatureLayer", "CPPEdit\\CPP Supporting")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        cpp_core = params[0].valueAsText
        cpp_supporting = params[1].valueAsText

        core_lyr = arcpy.MakeFeatureLayer_management(cpp_core, "core_lyr")
        buff = arcpy.Buffer_analysis(core_lyr, "memory\\core_buff", "1000 Feet")
        with arcpy.da.SearchCursor(buff, 'SHAPE@') as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_slp(cpp_core)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_supporting, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Lepidoptera Wetland Core
######################################################################################################################################################

class LepidopteraWetlandCore(object):
    def __init__(self):
        self.label = "Lepidoptera Wetland Core"
        self.category = "Lepidoptera"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("NWI Layer", "NWI", "GPFeatureLayer"),
            parameter("Wenger Buffer", "wenger", "GPFeatureLayer"),
            parameter("Unmapped Wetland", "wetland", "GPFeatureLayer", "", "Optional"),
            parameter("Core extent radius", "core_radius", "GPLinearUnit")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        nwi = params[2].valueAsText
        wenger = params[3].valueAsText
        unmapped_wetland = params[4].valueAsText
        core_radius = params[5].valueAsText

        specID = "Lepidoptera_Wetland_20130118"

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        inferred_extent = bufferFeatures(srcfeatures, eoid, core_radius)
        selection_buffer = bufferFeatures(srcfeatures, eoid, "200 Meters")

        nwi_clipped = arcpy.Clip_analysis(nwi,inferred_extent,"memory\\nwi_clipped")
        wenger_clipped = arcpy.Clip_analysis(wenger,inferred_extent,"memory\\wenger_clipped")
        merge_features = [nwi_clipped,wenger_clipped]
        if unmapped_wetland:
            wetland_clip = arcpy.Clip_analysis(wetland,inferred_extent,"memory\\wetland_clip")
            merge_features.append(wetland_clip)

        wetland_clipped = arcpy.Merge_management(merge_features,"memory\\wetland_clipped")
        wetland_dissolve = arcpy.Dissolve_management(wetland_clipped,"memory\\wetland_dissolve","","",False)

        wetland_lyr = arcpy.MakeFeatureLayer_management(wetland_dissolve,"wetland_lyr")
        wetland_lyr = arcpy.SelectLayerByLocation_management(wetland_lyr,"INTERSECT",selection_buffer)
        select_adjacent_features(wetland_lyr,"200 Meters")
        desc = arcpy.Describe(wetland_lyr)
        if desc.FIDSet == '':
            arcpy.AddWarning("No NWI or Wenger habitat is within 200m of source features.")
            sys.exit()
        else:
            wetland_selection = arcpy.FeatureClassToFeatureClass_conversion(wetland_lyr,"memory","wetland_selection")

        wetland_buffer = arcpy.Buffer_analysis(wetland_selection,"memory\\wetland_buffer","200 Meters")
        dissolve_lyr = arcpy.Dissolve_management(wetland_buffer, "memory\\dissolve_lyr")

        with arcpy.da.SearchCursor(dissolve_lyr, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        notes = "Remove unsuitable habitat and ensure all potential unmapped wetland habitat has been added."

        values = calc_attr_core(eoid, eo_ptreps, specID, notes)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Lepidoptera Wetland Supporting
######################################################################################################################################################

class LepidopteraWetlandSupporting(object):
    def __init__(self):
        self.label = "Lepidoptera Wetland Supporting"
        self.category = "Lepidoptera"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("Supporting CPP Layer", "slp", "GPFeatureLayer", "CPPEdit\\CPP Supporting"),
            parameter("NWI Layer", "NWI", "GPFeatureLayer"),
            parameter("Wenger Buffer", "wenger", "GPFeatureLayer"),
            parameter("Core extent radius", "core_radius", "GPLinearUnit"),
            parameter("Supporting extent radius", "supporting_radius", "GPLinearUnit")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        cpp_core = params[0].valueAsText
        cpp_supporting = params[1].valueAsText
        nwi = params[2].valueAsText
        wenger = params[3].valueAsText
        core_radius = params[4].valueAsText
        supporting_radius = params[5].valueAsText

        with arcpy.da.SearchCursor(cpp_core,"EO_ID") as cursor:
            for row in cursor:
                eoid = row[0]

        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        merge_features = []

        core_buff = arcpy.Buffer_analysis(cpp_core, "memory\\core_buff", "100 Meters")
        merge_features.append(core_buff)

        selection_buffer = bufferFeatures(srcfeatures, eoid, core_radius)
        inferred_extent = bufferFeatures(srcfeatures, eoid, supporting_radius)

        nwi_clip = arcpy.Clip_analysis(nwi,inferred_extent,"memory\\nwi_clip")
        nwi_lyr = arcpy.MakeFeatureLayer_management(nwi_clip,"nwi_lyr")
        nwi_lyr = arcpy.SelectLayerByLocation_management(nwi_lyr,"INTERSECT",selection_buffer,"","NEW_SELECTION")
        select_adjacent_features(nwi_lyr)
        desc = arcpy.Describe(nwi_lyr)
        if desc.FIDSet == '':
            pass
        else:
            nwi_selection = arcpy.FeatureClassToFeatureClass_conversion(nwi_lyr,"memory","nwi_selection")
            nwi_buff = arcpy.Buffer_analysis(nwi_selection,"memory\\nwi_buff","60 Meters")
            merge_features.append(nwi_buff)

        wenger_clip = arcpy.Clip_analysis(wenger,inferred_extent,"memory\\wenger_clip")
        wenger_lyr = arcpy.MakeFeatureLayer_management(wenger_clip,"wenger_lyr")
        wenger_lyr = arcpy.SelectLayerByLocation_management(wenger_lyr,"INTERSECT",selection_buffer,"","NEW_SELECTION")
        select_adjacent_features(wenger_lyr)
        desc = arcpy.Describe(wenger_lyr)
        if desc.FIDSet == '':
            pass
        else:
            wenger_selection = arcpy.FeatureClassToFeatureClass_conversion(wenger_lyr,"memory","wenger_selection")
            wenger_buff = arcpy.Buffer_analysis(wenger_selection,"memory\\wenger_buff","30 Meters")
            merge_features.append(wenger_buff)

        wetland_merge = arcpy.Merge_management(merge_features,"memory\\wetland_merge")
        wetland_dissolve = arcpy.Dissolve_management(wetland_merge,"memory\\wetland_clipped")
        merge_to_poly = arcpy.FeatureToPolygon_management(wetland_dissolve, "memory\\merge_to_poly")
        diss = arcpy.Dissolve_management(merge_to_poly, "memory\\diss")

        with arcpy.da.SearchCursor(diss, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_slp(cpp_core)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_supporting, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Northern Cricket Frog Core
######################################################################################################################################################

class NorthernCricketFrogCore(object):
    def __init__(self):
        self.label = "Northern Cricket Frog Core"
        self.category = "Amphibians"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("NWI Layer", "NWI", "GPFeatureLayer"),
            parameter("Stream/Riverbank Habitat Layer", "streams", "GPFeatureLayer"),
            parameter("Unmapped Wetland", "wetland", "GPFeatureLayer", "", "Optional")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        NWI = params[2].valueAsText
        streams = params[3].valueAsText
        wetland = params[4].valueAsText

        specID = "Amphibians_Northern_Cricket_Frog_20130225"

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        clip_geom = bufferFeatures(srcfeatures, eoid, 1300)

        merge_features = []

        NWI_lyr = arcpy.MakeFeatureLayer_management(NWI, "NWI_lyr", "WETLAND_TYPE <> 'Riverine'")

        if wetland:
            NWI_lyr = arcpy.Merge_management([NWI_lyr,wetland],"memory\\NWI_combine")

        NWI_lyr = arcpy.SelectLayerByLocation_management(NWI_lyr,"INTERSECT",clip_geom)
        select_adjacent_features(NWI_lyr)
        NWI_buff = arcpy.Buffer_analysis(NWI_lyr,"memory\\NWI_buff",1300)
        merge_features.append(NWI_buff)

        stream_clip = arcpy.Clip_analysis(streams,clip_geom,"memory\\stream_clip")
        stream_buff = arcpy.Buffer_analysis(stream_clip,"memory\\stream_buff",1300)
        merge_features.append(stream_buff)

        merge_lyr = arcpy.Merge_management(merge_features, "memory\\merge_lyr")
        dissolve_lyr = arcpy.Dissolve_management(merge_lyr, "memory\\dissolve_lyr")
        with arcpy.da.SearchCursor(dissolve_lyr, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_core(eoid, eo_ptreps, specID)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Northern Cricket Frog Supporting
######################################################################################################################################################

class NorthernCricketFrogSupporting(object):
    def __init__(self):
        self.label = "Northern Cricket Frog Supporting"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Amphibians"
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("LiDAR GDB", "lidar_gdb", "DEWorkspace"),
            parameter("PA County Layer", "pa_county", "GPFeatureLayer"),
            parameter("Supporting CPP Layer", "slp", "GPFeatureLayer", "CPPEdit\\CPP Supporting")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        core = params[0].valueAsText
        lidar_gdb = params[1].valueAsText
        pa_county = params[2].valueAsText
        slp = params[3].valueAsText

        slp_buff = "120 Meters"
        slp_limit = "1000000 Meters"

        watershed_geom = localWatershed(core, lidar_gdb, pa_county)
        slp_geom = supportingWatershed(core, watershed_geom, slp_buff, slp_limit)

        merge_to_poly = arcpy.FeatureToPolygon_management(slp_geom, "memory\\merge_to_poly")
        diss = arcpy.Dissolve_management(merge_to_poly, "memory\\diss")

        with arcpy.da.SearchCursor(diss,"SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_slp(core, drawn_notes="Used CPP watershed tool.")
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(slp, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Timber Rattlesnake Supporting
######################################################################################################################################################

class TimberRattlesnakeSupporting(object):
    def __init__(self):
        self.label = "Timber Rattlesnake Supporting"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Reptiles"
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("Supporting CPP Layer", "supporting", "GPFeatureLayer", "CPPEdit\\CPP Supporting"),
            parameter("WPC's 25ac Forest Patches", "forest_patches", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        core = params[0].valueAsText
        supporting = params[1].valueAsText
        forest_patches = params[2].valueAsText

        with arcpy.da.SearchCursor(core,"EO_ID") as cursor:
            for row in cursor:
                eoid = row[0]

        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        buff_9km = bufferFeatures(srcfeatures, eoid, 9000)
        buff_100m = bufferFeatures(srcfeatures, eoid, 100)

        # Select forest blocks within 9km of occurrence
        forest_lyr = arcpy.MakeFeatureLayer_management(forest_patches, "forest_lyr")
        forest_lyr = arcpy.SelectLayerByLocation_management(forest_lyr,"INTERSECT",buff_9km,"","NEW_SELECTION")

        # Make feature layer of forest blocks within 9km
        forest_9km = arcpy.CopyFeatures_management(forest_lyr, "memory\\forest_9km")
        forest_9km = arcpy.SelectLayerByLocation_management(forest_9km,"INTERSECT",buff_100m,"","NEW_SELECTION")

        # Select any forest blocks adjacent, within 200m, to the selected forest blocks
        select_adjacent_features(forest_9km,"200 Meters")
        # Buffer the forest blocks by 100m
        forest_buff = arcpy.Buffer_analysis(forest_9km, "forest_buff", "100 Meters", dissolve_option="ALL")

        merge = arcpy.Merge_management([core, forest_buff], "memory\\merge")
        merge_to_poly = arcpy.FeatureToPolygon_management(merge, "memory\\merge_to_poly")
        diss = arcpy.Dissolve_management(merge_to_poly, "memory\\diss")

        notes = "Remove unsuitable habitat and separation barriers like 4-ln highways. Connect adjacent core habitats that are within 9km of the occurrence with intact forest block corridors along the ridgeline."

        with arcpy.da.SearchCursor(diss, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_slp(core, drawn_notes=notes)
        values.append(geom)

        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(supporting, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Blue Spotted Salamander Core
######################################################################################################################################################

class BlueSpottedSalamanderCore(object):
    def __init__(self):
        self.label = "Blue Spotted Salamander Core"
        self.category = "Amphibians"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("NWI Layer", "NWI", "GPFeatureLayer"),
            parameter("Unmapped Wetland", "wetland", "GPFeatureLayer", "", "Optional")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        nwi = params[2].valueAsText
        unmapped_wetland = params[3].valueAsText

        specID = "Amphibians_Blue_Spotted_Salamander_20130225"

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        inferred_extent = bufferFeatures(srcfeatures, eoid, "305 Meters")

        if unmapped_wetland:
            nwi = arcpy.Merge_management([nwi,unmapped_wetland],"memory\\nwi")

        nwi_lyr = arcpy.MakeFeatureLayer_management(nwi, "nwi_lyr", "WETLAND_TYPE <> 'Riverine'")
        nwi_lyr = arcpy.SelectLayerByLocation_management(nwi_lyr,"INTERSECT",inferred_extent,"","NEW_SELECTION")

        desc = arcpy.Describe(nwi_lyr)
        if desc.FIDSet == '':
            arcpy.AddWarning("No NWI or added wetland habitat is contiguous with the inferred extent polygon.")
            sys.exit()

        select_adjacent_features(nwi_lyr,"0 Meters")

        wetland_buffer = arcpy.Buffer_analysis(nwi_lyr, "memory\\wetland_buffer", "305 Meters")
        dissolve_lyr = arcpy.Dissolve_management(wetland_buffer, "memory\\dissolve_lyr")

        with arcpy.da.SearchCursor(dissolve_lyr, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        notes = "Remove unsuitable habitat and ensure all potential unmapped wetland habitat has been added."

        values = calc_attr_core(eoid, eo_ptreps, specID, notes)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Rough Green Snake Core
######################################################################################################################################################

class RoughGreenSnakeCore(object):
    def __init__(self):
        self.label = "Rough Green Snake Core"
        self.category = "Reptiles"
        self.canRunInBackground = False
        self.description = """
        """
        self.params = [
            parameter("EO ID of record for which you are creating CPP:", "eoid", "GPLong"),
            parameter("Core CPP Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("WPC 25ac Forest Blocks", "forest", "GPFeatureLayer")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        cpp_core = params[1].valueAsText
        forest = params[2].valueAsText

        specID = "Reptiles_Rough_Green_Snake_20130220"

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept", "Biotics\\eo_sourceln", "Biotics\\eo_sourcepy"]

        select_geom = bufferFeatures(srcfeatures, eoid, 67)

        forest_lyr = arcpy.MakeFeatureLayer_management(forest, "forest_lyr")
        arcpy.SelectLayerByLocation_management(forest_lyr,"INTERSECT",select_geom,"","NEW_SELECTION")
        forest_buff = arcpy.Buffer_analysis(forest_lyr,"memory\\forest_buff",67)

        feat_to_poly = arcpy.FeatureToPolygon_management(forest_buff, "memory\\merge_to_poly")
        diss = arcpy.Dissolve_management(feat_to_poly, "memory\\diss")
        with arcpy.da.SearchCursor(diss, "SHAPE@") as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_core(eoid, eo_ptreps, specID)
        values.append(geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Status", "SpecID", "ELSUBID", "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core, fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
## Rough Green Snake Supporting - TAKES BATCH CORES
######################################################################################################################################################

class RoughGreenSnakeSupporting(object):
    def __init__(self):
        self.label = "Rough Green Snake Supporting"
        self.category = "Reptiles"
        self.canRunInBackground = False
        self.description = """Takes multiple cores!
        """
        self.params = [
            parameter("Selected CPP Core Layer", "cpp_core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("Wenger Buffer", "wenger", "GPFeatureLayer"),
            parameter("Supporting CPP Layer", "slp", "GPFeatureLayer", "CPPEdit\\CPP Supporting")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        cpp_core = params[0].valueAsText
        wenger = params[1].valueAsText
        cpp_supporting = params[2].valueAsText

        core_lyr = arcpy.MakeFeatureLayer_management(cpp_core, "core_lyr")
        buff = arcpy.Buffer_analysis(core_lyr, "memory\\core_buff", 120)
        buff_diss = arcpy.Dissolve_management(buff,"memory\\buff_diss")
        envelope = arcpy.MinimumBoundingGeometry_management(buff_diss, os.path.join("memory", "envelope"), "CONVEX_HULL")

        clip_buff = arcpy.Buffer_analysis(core_lyr, "memory\\clip_buff", 2000)
        wenger_clip = arcpy.Clip_analysis(wenger, clip_buff, "memory\\wenger_buff")
        wenger_single = arcpy.MultipartToSinglepart_management(wenger_clip, "memory\\wenger_single")

        wenger_single = arcpy.SelectLayerByLocation_management(wenger_single, "INTERSECT", core_lyr, "", "NEW_SELECTION")
        wenger_select = arcpy.CopyFeatures_management(wenger_single,"memory\\wenger_select")

        merge_features = arcpy.Merge_management([envelope,wenger_select], "memory\\merge_features")
        merge_diss = arcpy.Dissolve_management(merge_features, "memory\\merge_diss")

        with arcpy.da.SearchCursor(merge_diss, 'SHAPE@') as cursor:
            for row in cursor:
                geom = row[0]

        with arcpy.da.SearchCursor(core_lyr,"EO_ID") as cursor:
            eos = sorted({row[0] for row in cursor})

        for eo in eos:
            arcpy.SelectLayerByAttribute_management(cpp_core,"NEW_SELECTION","EO_ID = {0}".format(eo))
            values = calc_attr_slp(cpp_core)
            values.append(geom)
            fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                    "BioticsExportDate", "SHAPE@"]
            with arcpy.da.InsertCursor(cpp_supporting, fields) as cursor:
                cursor.insertRow(values)





######################################################################################################################################################
## General Watershed Supporting
######################################################################################################################################################

class GeneralWatershedSupportingTool(object):
    def __init__(self):
        # Override the label and description in the superclass
        self.label = "General Watershed Supporting Tool"
        self.category = "General CPP Tools"
        self.description = ""
        self.params = [
            parameter("Selected CPP Core", "core", "GPFeatureLayer", "CPPEdit\\CPP Core"),
            parameter("Minimum Buffer Distance", "buff_dist", "GPLinearUnit"),
            parameter("LiDAR GDB", "lidar_gdb", "DEWorkspace"),
            parameter("PA County Layer", "pa_county", "GPFeatureLayer"),
            parameter("Supporting CPP Layer", "slp", "GPFeatureLayer", "CPPEdit\\CPP Supporting")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        core = params[0].valueAsText
        buff_dist = params[1].valueAsText
        lidar_gdb = params[2].valueAsText
        pa_county = params[3].valueAsText
        slp = params[4].valueAsText

        watershed_geom = localWatershed(core, lidar_gdb, pa_county)
        slp_geom = supportingWatershed(core, watershed_geom, buff_dist, 10000)

        values = calc_attr_slp(core, drawn_notes="Used CPP watershed tool.")
        values.append(slp_geom)
        fields = ["SNAME", "EO_ID", "DrawnBy", "DrawnDate", "DrawnNotes", "Project", "Status", "SpecID", "ELSUBID",
                  "BioticsExportDate", "SHAPE@"]
        with arcpy.da.InsertCursor(slp, fields) as cursor:
            cursor.insertRow(values)

        return
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
                      HellbenderMudpuppyCore]  # <<<<<< ADD TOOLS HERE >>>>>>>>

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
        NWI = params[3].valueAsText
        ch93streams = params[4].valueAsText
        nhd_flowline = params[5].valueAsText
        waterbodies = params[6].valueAsText


        eo_ptreps = "Biotics\\eo_ptreps"
        specID = "Reptiles_Eastern_Redbelly_Turtle_20140930"

        merge_features = []

        hab_buff = arcpy.Buffer_analysis(habitat, "memory\\hab_buff", 250, "", "", "ALL")
        merge_features.append(hab_buff)
        clip_lyr = arcpy.Buffer_analysis(habitat, "memory\\clip_lyr", 750, "", "", "ALL")

        nwi = arcpy.MakeFeatureLayer_management(NWI, "nwi")
        ch93 = arcpy.MakeFeatureLayer_management(ch93streams, "ch93")
        nhd_lyr = arcpy.MakeFeatureLayer_management(nhd_flowline, "nhd_lyr", '"STREAMORDE" >= 3')
        waterbodies_lyr = arcpy.MakeFeatureLayer_management(waterbodies, "waterbodies_lyr")

        arcpy.SelectLayerByLocation_management(nwi, "INTERSECT", hab_buff, "", "NEW_SELECTION")
        arcpy.SelectLayerByLocation_management(ch93, "INTERSECT", hab_buff, "", "NEW_SELECTION")
        ch93_length = 0
        while ch93_length < 1000:
            arcpy.SelectLayerByLocation_management(ch93,"INTERSECT",ch93,"","ADD_TO_SELECTION")
            ch93_length = 0
            with arcpy.da.SearchCursor(ch93,"Shape_Length") as cursor:
                for row in cursor:
                    ch93_length = ch93_length + row[0]

        arcpy.SelectLayerByLocation_management(waterbodies_lyr, "INTERSECT", habitat, 1000, "NEW_SELECTION")
        arcpy.SelectLayerByLocation_management(waterbodies_lyr, "INTERSECT", nwi, "", "SUBSET_SELECTION")
        waterbodies_nwi_buff = arcpy.Buffer_analysis(waterbodies_lyr, "memory\\waterbodies_nwi_buff", 250, "", "", "ALL")
        merge_features.append(waterbodies_nwi_buff)

        arcpy.SelectLayerByLocation_management(waterbodies_lyr, "INTERSECT", habitat, 1000, "NEW_SELECTION")
        arcpy.SelectLayerByLocation_management(waterbodies_lyr, "INTERSECT", ch93, "", "SUBSET_SELECTION")
        waterbodies_ch93_buff = arcpy.Buffer_analysis(waterbodies_lyr, "memory\\waterbodies_ch93_buff", 250, "", "", "ALL")
        merge_features.append(waterbodies_ch93_buff)

        arcpy.SelectLayerByLocation_management(nhd_lyr, "INTERSECT", habitat, 750, "NEW_SELECTION")
        nhd_clip = arcpy.Clip_analysis(nhd_lyr, clip_lyr, "memory\\nhd_clip")
        nhd_dissolve = arcpy.Dissolve_management(nhd_clip,"memory\\nhd_dissolve","","","",True)
        arcpy.SelectLayerByLocation_management(nhd_dissolve,"INTERSECT",hab_buff,"","NEW_SELECTION")
        nhd_buff = arcpy.Buffer_analysis(nhd_dissolve, "memory\\nhd_buff", 250, "", "", "ALL")
        merge_features.append(nhd_buff)

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
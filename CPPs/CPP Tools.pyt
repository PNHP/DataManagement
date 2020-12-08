#-------------------------------------------------------------------------------
# Name:        CPP Tools
# Purpose:
#
# Author:      MMoore
#
# Created:     07/04/2020
# Copyright:   (c) MMoore 2020
# Licence:     <your licence>
#-------------------------------------------------------------------------------

# Import modules
import arcpy, time, datetime, sys, traceback
from getpass import getuser

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True
arcpy.env.workspace = "memory"

def parameter(displayName,name,datatype,defaultValue=None,parameterType='Required',direction='Input',multiValue=False,filterList=None):
    '''This function defines the parameter definitions for a tool. Using this
    function saves lines of code by prepopulating some of the values and also
    allows setting a default value.
    '''
    # create parameter with a few default properties
    param = arcpy.Parameter(
        displayName = displayName,
        name = name,
        datatype = datatype,
        parameterType = parameterType,
        direction = direction,
        multiValue = multiValue)
    # set new parameter to a default value
    param.value = defaultValue
    if filterList:
        param.filter.type = "ValueList"
        param.filter.list = filterList
    # return complete parameter object
    return param

def bufferFeatures(features,eoid,buff_dist):
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

    with arcpy.da.SearchCursor(sf_buff,'SHAPE@') as cursor:
        for row in cursor:
            geom = row[0]
    return geom

def calc_attr_core(eoid,eo_ptreps,specID=None,drawn_notes=None):
    query = "EO_ID = {}".format(eoid)
    with arcpy.da.SearchCursor(eo_ptreps,["SNAME","ELSUBID","EXPT_DATE"],query) as cursor:
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
    values = [sname,eoid,user,date,drawn_notes,"r",SpecID,elsubid,expt_date]
    return values

def calc_attr_slp(core_lyr,specID=None,drawn_notes=None):
    with arcpy.da.SearchCursor(core_lyr,["SNAME","EO_ID","Project","SpecID","ELSUBID","BioticsExportDate"]) as cursor:
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
    values = [sname,eoid,user,date,drawn_notes,project,"r",specID,elsubid,expt_date]
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
         'Lycom', 'Mckean': 'McKea', 'McKean': 'McKea', 'Mercer': 'Mercer', 'Mifflin': 'Miffl', 'Monroe': 'Monro',
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

    with arcpy.da.SearchCursor(cnty_lyr,"COUNTY_NAM") as cursor:
        county_name = sorted({row[0].title() for row in cursor})[0]
    county_abbr = cnty_dict[county_name]

    flow_acc = r"{0}\{1}_FlowAcc".format(lidar_gdb, county_abbr)
    flow_dir = r"{0}\{1}_FlowDir".format(lidar_gdb, county_abbr)

    spp = arcpy.sa.SnapPourPoint(input_poly,flow_acc,0,"OBJECTID")
    watershed_raster = arcpy.sa.Watershed(flow_dir,spp,"VALUE")

    watershed_temp = arcpy.RasterToPolygon_conversion(watershed_raster,"memory\\watershed_temp")
    watershed_union = arcpy.Union_analysis([watershed_temp,input_poly],"memory\\watershed_union")
    watershed = arcpy.Dissolve_management(watershed_union,"memory\\watershed")

    with arcpy.da.SearchCursor(watershed,"SHAPE@") as cursor:
        for row in cursor:
            watershed_geom = row[0]

    return watershed_geom

def supportingWatershed(core,watershed_geom,slp_buff,slp_limit):
    watershed_limit = arcpy.Buffer_analysis(core,"memory\\watershed_limit",slp_limit)
    watershed_clip = arcpy.Clip_analysis(watershed_geom,watershed_limit,"memory\\watershed_clip")
    core_buff = arcpy.Buffer_analysis(core,"memory\\core_buff",slp_buff)

    slp_union = arcpy.Union_analysis([watershed_clip,core_buff],"memory\\slp_union")
    slp_shape = arcpy.Dissolve_management(slp_union,"memory\\slp_shape")

    with arcpy.da.SearchCursor(slp_shape,"SHAPE@") as cursor:
        for row in cursor:
            slp_geom = row[0]

    return slp_geom

######################################################################################################################################################
##
######################################################################################################################################################

class Toolbox(object):
    def __init__(self):
        self.label = "CPP Tools"
        self.alias = "CPP Tools"
        self.tools = [SetDefQuery,BufferSFs,PlantSupporting,BaldEagleCore,BaldEagleSupporting] # <<<<<< ADD TOOLS HERE >>>>>>>>

######################################################################################################################################################
##
######################################################################################################################################################

class SetDefQuery(object):
    def __init__(self):
        self.label = "Set EO Definition Query"
        self.description = ""
        self.canRunInBackground = False
        self.category ="General CPP Tools"
        self.params = [
            parameter("EO ID that you wish to use for definitiona query on all Biotics and CPP layers:","eoid","GPLong")]

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
            lyr.definitionQuery = "EO_ID = {}".format(eoid)
##        lyr = m.listLayers("eo_ptreps")[0]
##        view = aprx.activeView()

######################################################################################################################################################
##
######################################################################################################################################################

class BufferSFs(object):
    def __init__(self):
        self.label = "Create CPP Core from Buffered Source Features"
        self.description = ""
        self.canRunInBackground = False
        self.category = "General CPP Tools"
        self.params = [
        parameter("EO ID of record for which you are creating CPP:","eoid","GPLong"),
        parameter("Buffer Distance","buff_dist","GPLinearUnit"),
        parameter("Core CPP Layer","cpp_core","GPFeatureLayer","CPPEdit\\CPP Core"),
        parameter("CPP Spec ID","specID","GPString","","Optional")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        eoid = params[0].valueAsText
        buff_dist = params[1].valueAsText
        cpp_core = params[2].valueAsText
        specID = params[3].valueAsText

        eo_ptreps = "Biotics\\eo_ptreps"
        srcfeatures = ["Biotics\\eo_sourcept","Biotics\\eo_sourceln","Biotics\\eo_sourcepy"]

        geom = bufferFeatures(srcfeatures,eoid,buff_dist)
        query = "EO_ID = {}".format(eoid)

        values = calc_attr_core(eoid,eo_ptreps,specID)
        values.append(geom)
        fields = ["SNAME","EO_ID","DrawnBy","DrawnDate","DrawnNotes","Status","SpecID","ELSUBID","BioticsExportDate","SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core,fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
##
######################################################################################################################################################

class PlantSupporting(object):
    def __init__(self):
        # Override the label and description in the superclass
        self.label = "Plants Supporting"
        self.category = "Plants and Community"
        self.description = ""
        plantList = ["Plants_Aquatic_20121016","Plants_Floodplain_20121016","Plants_Open_disturbed_upland_habitat_20121016",
            "Plants_Outcrop_barren_20121212","Plants_Palustrine_20120417","Plants_Scour_20121016","Plants_Shoreline_20121016",
            "Plants_Upland_forest_20121016"]
        self.params = [
        parameter("Which SpecID are you using?","specID","GPString",filterList=plantList),
        parameter("Selected CPP Core","core","GPFeatureLayer","CPPEdit\\CPP Core"),
        parameter("LiDAR GDB","lidar_gdb","DEWorkspace"),
        parameter("PA County Layer","pa_county","GPFeatureLayer"),
        parameter("Supporting CPP Layer","slp","GPFeatureLayer","CPPEdit\\CPP Supporting")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        specID = params[0].valueAsText
        core = params[1].valueAsText
        lidar_gdb = params[2].valueAsText
        pa_county = params[3].valueAsText
        slp = params[4].valueAsText

        if specID=="Plants_Aquatic_20121016":
            slp_buff= "120 Meters"
            slp_limit= "2000 Meters"
        elif specID=="Plants_Floodplain_20121016":
            slp_buff= "120 Meters"
            slp_limit= "300 Meters"
        elif specID=="Plants_Open_disturbed_upland_habitat_20121016":
            slp_buff= "120 Meters"
            slp_limit= "300 Meters"
        elif specID=="Plants_Outcrop_barren_20121212":
            slp_buff= "120 Meters"
            slp_limit= "300 Meters"
        elif specID=="Plants_Palustrine_20120417":
            slp_buff= "120 Meters"
            slp_limit=  "2000 Meters"
        elif specID=="Plants_Scour_20121016":
            slp_buff= "120 Meters"
            slp_limit= "300 Meters"
        elif specID=="Plants_Shoreline_20121016":
            slp_buff= "120 Meters"
            slp_limit= "300 Meters"
        elif specID=="Plants_Upland_forest_20121016":
            slp_buff= "120 Meters"
            slp_limit= "300 Meters"
        else:
            arcpy.AddWarning("Oh no! No valid specID was returned and we don't know why.")

        watershed_geom = localWatershed(core,lidar_gdb,pa_county)
        slp_geom = supportingWatershed(core,watershed_geom,slp_buff,slp_limit)

        values = calc_attr_slp(core,drawn_notes="Used CPP watershed tool.")
        values.append(slp_geom)
        fields = ["SNAME","EO_ID","DrawnBy","DrawnDate","DrawnNotes","Project","Status","SpecID","ELSUBID","BioticsExportDate","SHAPE@"]
        with arcpy.da.InsertCursor(slp,fields) as cursor:
            cursor.insertRow(values)

        return

######################################################################################################################################################
##
######################################################################################################################################################

class BaldEagleCore(object):
    def __init__(self):
        self.label = "Bald Eagle Core"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Birds"
        self.params = [
        parameter("EO ID of record for which you are creating CPP:","eoid","GPLong"),
        parameter("Core CPP Layer","cpp_core","GPFeatureLayer","CPPEdit\\CPP Core")]

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
        srcfeatures = ["Biotics\\eo_sourcept","Biotics\\eo_sourceln","Biotics\\eo_sourcepy"]

        geom = bufferFeatures(srcfeatures,eoid,buff_dist)

        values = calc_attr_core(eoid,eo_ptreps,specID,notes)
        values.append(geom)
        fields = ["SNAME","EO_ID","DrawnBy","DrawnDate","DrawnNotes","Status","SpecID","ELSUBID","BioticsExportDate","SHAPE@"]
        with arcpy.da.InsertCursor(cpp_core,fields) as cursor:
            cursor.insertRow(values)

######################################################################################################################################################
##
######################################################################################################################################################

class BaldEagleSupporting(object):
    def __init__(self):
        self.label = "Bald Eagle Supporting"
        self.description = ""
        self.canRunInBackground = False
        self.category = "Birds"
        self.params = [
        parameter("Selected CPP Core","core","GPFeatureLayer","CPPEdit\\CPP Core"),
        parameter("CPP Supporting Layer","supporting","GPFeatureLayer","CPPEdit\\CPP Supporting"),
        parameter("NWI Layer","NWI","GPFeatureLayer"),
        parameter("Wengerrd Buffer Layer","wengerrd","GPFeatureLayer"),
        parameter("Connection Line","connection","GPFeatureLayer","","Optional")]

    def getParameterInfo(self):
        return self.params

    def execute(self, params, messages):
        # define parameters
        core = params[0].valueAsText
        supporting = params[1].valueAsText
        NWI = params[2].valueAsText
        wengerrd = params[3].valueAsText
        connection = params[4].valueAsText

        with arcpy.da.SearchCursor(core,"EO_ID") as cursor:
            for row in cursor:
                eoid = row[0]

        buff_dist = 599
        specID = "Birds_Bald_eagle_20150317"
        notes = "PRELIMINARY - review to ensure the main foraging habitat was not buffered and merge with Wengerrd feature"

        core_buff = arcpy.Buffer_analysis(core,"memory\\core_buff",buff_dist,"","","ALL")
        nwi = arcpy.MakeFeatureLayer_management(NWI,"nwi","WETLAND_TYPE <> 'Riverine'")
        arcpy.SelectLayerByLocation_management(nwi,"INTERSECT",core_buff,"","NEW_SELECTION")

        desc = arcpy.Describe(nwi)
        if desc.FIDSet == '':
            final_buff = core_buff
        else:
            nwi_buff = arcpy.Buffer_analysis(nwi,"memory\\nwi_buff",300,"","","ALL")
            final_buff = arcpy.Merge_management([core_buff,nwi_buff],"memory\\final_buff")
            final_buff = arcpy.Dissolve_management(final_buff,"memory\\final_buff1")

        if connection:
            connection_buff = arcpy.Buffer_analysis(connection,"memory\\connection_buff",50,"","","ALL")
            final_buff = arcpy.Merge_management([final_buff,connection_buff],"memory\\final_buff2")
            final_buff = arcpy.Dissolve_management(final_buff,"memory\\final_buff3")
        else:
            pass

        with arcpy.da.SearchCursor(final_buff,'SHAPE@') as cursor:
            for row in cursor:
                geom = row[0]

        values = calc_attr_slp(core,specID,notes)
        values.append(geom)

        fields = ["SNAME","EO_ID","DrawnBy","DrawnDate","DrawnNotes","Project","Status","SpecID","ELSUBID","BioticsExportDate","SHAPE@"]
        with arcpy.da.InsertCursor(supporting,fields) as cursor:
            cursor.insertRow(values)

        wengerrd = arcpy.MakeFeatureLayer_management(wengerrd,"memory\\wengerrd")
        arcpy.SelectLayerByLocation_management(wengerrd,"INTERSECT",geom,"","NEW_SELECTION")
        with arcpy.da.SearchCursor(wengerrd,"SHAPE@") as cursor:
            for row in cursor:
                geom1 = row[0]

        notes = "PRELIMINARY - remove wengerrd 1600 meters downstream of core."
        values = calc_attr_slp(core,specID,notes)
        values.append(geom1)

        fields = ["SNAME","EO_ID","DrawnBy","DrawnDate","DrawnNotes","Project","Status","SpecID","ELSUBID","BioticsExportDate","SHAPE@"]
        with arcpy.da.InsertCursor(supporting,fields) as cursor:
            cursor.insertRow(values)
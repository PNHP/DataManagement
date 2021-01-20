#-------------------------------------------------------------------------------
# Name:         BulkLoadPrepToolbox.pyt
# Purpose:      The bulk load prep toolbox contains custom Python tools that are
#               intended to increase the efficiency of data preparation prior to
#               bulk loading into Biotics
# Version:      1.0
# Author:       MMOORE, Pennsylvania Natural Heritage Program
# Created:      02/18/2018
# Updated:      01/20/2021
# Future Ideas:
#-------------------------------------------------------------------------------

#import libraries
import arcpy, os, datetime
from arcpy import env
from arcpy.sa import *

#set environmental variables
arcpy.env.overwriteOutput = True
arcpy.env.qualifiedFieldNames = False
arcpy.env.workspace = "in_memory"

class Toolbox(object):
    def __init__(self):
        self.label = "Biotics Bulk Load Toolbox"
        self.alias = "Biotics Bulk Load Toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [TerrestrialGrouping,AquaticGrouping]

class TerrestrialGrouping(object):
    def __init__(self):
        self.label = "Terrestrial"
        self.description = """Used to prepare a feature class or shapefile for bulk load into Biotics by assigning an existing EOID/SFID or new EO/SF grouping string to observations based on separation distance."""
        self.canRunInBackground = False
        self.category = "EO/SF Separation Distance Analysis"

    def getParameterInfo(self):
        in_points = arcpy.Parameter(
            displayName = "Input feature layer for separation distance analysis",
            name = "in_points",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        in_lines = arcpy.Parameter(
            displayName = "Input feature layer for separation distance analysis",
            name = "in_lines",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")

        in_poly = arcpy.Parameter(
            displayName = "Input feature layer for separation distance analysis",
            name = "in_poly",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")

        species_code = arcpy.Parameter(
            displayName = "Species Identifier Field (values must match EO/SF species identifier field)",
            name = "species_code",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        species_code.parameterDependencies = [in_points.name]

        lu_separation = arcpy.Parameter(
            displayName = "Separation Distance Field (units must be in kilometers)",
            name = "lu_separation",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        lu_separation.parameterDependencies = [in_points.name]

        loc_uncert = arcpy.Parameter(
            displayName = "Locational Uncertainty Type Field",
            name = "loc_uncert",
            datatype = "Field",
            parameterType = "Optional",
            direction = "Input")
        loc_uncert.parameterDependencies = [in_points.name]

        loc_uncert_dist = arcpy.Parameter(
            displayName = "Locational Uncertainty Distance Field (units must be meters)",
            name = "loc_uncert_dist",
            datatype = "Field",
            parameterType = "Optional",
            direction = "Input")
        loc_uncert_dist.parameterDependencies = [in_points.name]

        eo_reps = arcpy.Parameter(
            displayName = "Existing EO Reps Layer",
            name = "eo_reps",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
##        eo_reps.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_reps"

        eo_id_field = arcpy.Parameter(
            displayName = "EO ID Field used in EO Reps Layer",
            name = "eo_id_field",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        eo_id_field.value = "EO_ID"
        eo_id_field.parameterDependencies = [eo_reps.name]

        eo_sourcept = arcpy.Parameter(
            displayName = "Existing Source Point Layer",
            name = "eo_sourcept",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
##        eo_sourcept.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_sourcept"

        eo_sourceln = arcpy.Parameter(
            displayName = "Existing Source Line Layer",
            name = "eo_sourceln",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")
##        eo_sourceln.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_sourceln"

        eo_sourcepy = arcpy.Parameter(
            displayName = "Existing Source Polygon Layer",
            name = "eo_sourcepy",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")
##        eo_sourcepy.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_sourcepy"

        sf_id_field = arcpy.Parameter(
            displayName = "SFID Field used in Source Points, Lines, and Polygon Layers",
            name = "sf_id_field",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        sf_id_field.value = "SF_ID"
        sf_id_field.parameterDependencies = [eo_sourcept.name]

        species_code_field = arcpy.Parameter(
            displayName = "Species Identifier Field (values must match input species identifier field)",
            name = "species_code_field",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        species_code_field.parameterDependencies = [eo_reps.name]

        sf_include = arcpy.Parameter(
            displayName = "Check box if you would like to include existing SF lines and polygons in source feature groupings.",
            name = "sf_include",
            datatype = "GPBoolean",
            parameterType = "optional",
            direction = "Input")

        params = [in_points,in_lines,in_poly,species_code,lu_separation,loc_uncert,loc_uncert_dist,eo_reps,eo_id_field,eo_sourcept,eo_sourceln,eo_sourcepy,sf_id_field,species_code_field,sf_include]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        arcpy.AddMessage("""Welcome to the Source Feature and EO Assigner! This tool is designed to prepare a feature class or shapefile for bulk load into Biotics by assigning an existing or new SF and EO ID grouping variable to observations based on separation distance. This used to be done manually, so sit back and enjoy all the other work you can be doing instead of this!""")

        in_points = params[0].valueAsText
        in_lines = params[1].valueAsText
        in_poly = params[2].valueAsText
        species_code = params[3].valueAsText
        lu_separation = params[4].valueAsText
        loc_uncert = params[5].valueAsText
        loc_uncert_dist = params[6].valueAsText
        eo_reps = params[7].valueAsText
        eo_id_field = params[8].valueAsText
        eo_sourcept = params[9].valueAsText
        eo_sourceln = params[10].valueAsText
        eo_sourcepy = params[11].valueAsText
        sf_id_field = params[12].valueAsText
        species_code_field = params[13].valueAsText
        sf_include = params[14].valueAsText

        arcpy.env.workspace = "in_memory"

        arcpy.AddMessage("Preparing input data...")
        #if using sf lines and polygons, all layers are buffered by 1m and merged. Otherwise, just points are buffered by 1m.
        sfs_in = [eo_sourcept]
        sfs_out = ["eo_sourcept1"]
        if str(sf_include) == "True":
            if eo_sourceln:
                sfs_in.append(eo_sourceln)
                sfs_out.append("eo_sourcln1")
            if eo_sourcepy:
                sfs_in.append(eo_sourcepy)
                sfs_out.append("eo_sourcepy1")
        else:
            pass
        for sf_in,sf_out in zip(sfs_in,sfs_out):
            arcpy.Buffer_analysis(sf_in,sf_out,1)
        sf_merge = arcpy.Merge_management(sfs_out, "sf_merge")
        sf_lyr = arcpy.MakeFeatureLayer_management(sf_merge, "sf_lyr")

        #make list of all input layers given by user
        data_in = []
        data_out = []
        if in_points:
            data_in.append(in_points)
            data_out.append("pts")
        if in_lines:
            data_in.append(in_lines)
            data_out.append("lines")
        if in_poly:
            data_in.append(in_poly)
            data_out.append("polys")

        #add join id to input features, buffer by 1m, and merge layers
        join_id = 1
        for i,o in zip(data_in,data_out):
            arcpy.AddField_management(i,"join_id","TEXT")
            with arcpy.da.UpdateCursor(i,"join_id") as cursor:
                for row in cursor:
                    row[0]=str(join_id)
                    cursor.updateRow(row)
                    join_id+=1
            arcpy.Buffer_analysis(i,o,1)
        data_merge = arcpy.Merge_management(data_out,"data_merge")
        data_lyr = arcpy.MakeFeatureLayer_management(data_merge,"data_lyr")

        #updated to account for double and float field types
        if arcpy.ListFields(data_lyr,species_code)[0].type == 'Integer' or arcpy.ListFields(data_lyr,species_code)[0].type == 'Double' or arcpy.ListFields(data_lyr,species_code)[0].type == 'Float':
            species_query = "{}={}"
        else:
            species_query = "{}='{}'"
        if arcpy.ListFields(eo_reps,species_code_field)[0].type == 'Integer' or arcpy.ListFields(eo_reps,species_code_field)[0].type == 'Double' or arcpy.ListFields(eo_reps,species_code_field)[0].type == 'Float':
            eo_species_query = "{}={}"
        else:
            eo_species_query = "{}='{}'"

        #get name of true OID field
        objectid_field = arcpy.Describe(data_lyr).OIDFieldName

        #create feature layers to allow for selections
        eo_reps = arcpy.MakeFeatureLayer_management(eo_reps, "eo_reps")

        #add EO/SF ID fields if they do not already exist
        add_fields_text = ["SF_ID","SF_NEW","EO_ID","EO_NEW"]
        for field in add_fields_text:
            if len(arcpy.ListFields(data_lyr,field)) == 0:
                arcpy.AddField_management(data_lyr,field,"TEXT","","",50)
            else:
                pass
        add_fields_int = ["UNIQUEID"]
        for field in add_fields_int:
            if len(arcpy.ListFields(data_lyr,field)) == 0:
                arcpy.AddField_management(data_lyr,field,"LONG")
            else:
                pass

        #set word index to assign words to new EO groups
        word_index = 1
        observation_num = 1

        arcpy.AddMessage("Assigning EO IDs...")
        #get total records in data_lyr for progress reporting messages
        total_obs = arcpy.GetCount_management(data_lyr)
        #start assigning loop
        search_fields = [objectid_field, "EO_ID", "EO_NEW", species_code, lu_separation]
        if loc_uncert_dist:
            search_fields.append(loc_uncert)
            search_fields.append(loc_uncert_dist)
        with arcpy.da.SearchCursor(data_lyr, search_fields) as cursor:
            for row in cursor:
                objectid = row[0]
                #if one of the EOID fields already have a value, continue on to next feature
                if row[2] != None or (row[1] != None and row[1] != 0):
                    arcpy.AddMessage("ObjectID " + str(objectid) + " EO Observation number " + str(observation_num) + "/" + str(total_obs) + " has already been assigned to a new or existing EO.")
                    pass
                else:
                    sname = row[3]
                    #separation distance plus 8m for mmu (in addition to the 1m buffer on input data)
                    distance = (row[4]*1000)+8
                    #add LU distance if LU type is estimated
                    if loc_uncert_dist:
                        if row[5].lower() == "estimated":
                            distance = distance+row[6]
                        else:
                            pass
                    else:
                        pass
                    #convert distance into string value as needed for select by tool
                    distance = str(distance)+" METERS"

                    #select feature and assign sname and separation distance variables
                    arcpy.SelectLayerByAttribute_management(data_lyr, "NEW_SELECTION", "{}={}".format(objectid_field,objectid))
                    #check for existing EO reps within separation distance of feature
                    arcpy.SelectLayerByAttribute_management(eo_reps, 'NEW_SELECTION', eo_species_query.format(species_code_field,sname))
                    arcpy.SelectLayerByLocation_management(eo_reps, "WITHIN_A_DISTANCE", data_lyr, distance, "SUBSET_SELECTION")
                    #check for selection on eo_reps layer - if there is a selection, get eoid, select all observations within the separation distance, and assign existing eoid to selected features
                    selection_num = arcpy.Describe(eo_reps).fidset
                    if selection_num is not u'':
                        with arcpy.da.SearchCursor(eo_reps, eo_id_field) as cursor:
                            #eoid = sorted({row[0] for row in cursor}, reverse=True)[0] #use this if keeping newest EO
                            eoid = ",".join(sorted({str(int(row[0])) for row in cursor})) #use this if filling with EOIDs of all EOs within separation distance
                        #set arbitrary unequal counts to start while loop
                        countBefore = 0
                        countAfter = 1
                        while(countBefore!=countAfter):
                            countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                            arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, distance, "ADD_TO_SELECTION")
                            arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", species_query.format(species_code,sname))
                            countAfter = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                        with arcpy.da.UpdateCursor(data_lyr, "EO_ID") as cursor:
                            for row in cursor:
                                row[0] = eoid
                                cursor.updateRow(row)
                        arcpy.SelectLayerByAttribute_management(data_lyr, "CLEAR_SELECTION")
                        arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned an existing EO: " + str(eoid) + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
                    #if no existing EOs selected within separation distance, select all observations within the separation distance and assign new random word
                    else:
                        countBefore = 0
                        countAfter = 1
                        while(countBefore!=countAfter):
                            countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                            arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, distance, "ADD_TO_SELECTION")
                            arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", species_query.format(species_code,sname))
                            countAfter = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                        with arcpy.da.UpdateCursor(data_lyr, "EO_NEW") as cursor:
                            for row in cursor:
                                row[0] = "new_eo_" + str(word_index) #word_list[word_index]
                                cursor.updateRow(row)
                        arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned a new EO: " + str(word_index) + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
                        word_index += 1
                observation_num += 1
                arcpy.SelectLayerByAttribute_management(data_lyr, "CLEAR_SELECTION")

        arcpy.AddMessage("Assigning SF IDs...")
        observation_num = 1
        search_fields = [objectid_field, "SF_ID", "SF_NEW", species_code]
        with arcpy.da.SearchCursor(data_lyr, search_fields) as cursor:
            for row in cursor:
                objectid = row[0]
                if row[2] != None or (row[1] != None and row[1] != 0):
                    arcpy.AddMessage("ObjectID " + str(objectid) + " SF Observation number " + str(observation_num) + "/" + str(total_obs) + " has already been assigned to a new or existing SF.")
                else:
                    sname = row[3]

                    #check for existing SFs within 9m of feature (8m because of 1m buffer on SF layers)
                    arcpy.SelectLayerByAttribute_management(data_lyr, "NEW_SELECTION", "{}={}".format(objectid_field, objectid))
                    arcpy.SelectLayerByAttribute_management(sf_lyr, 'NEW_SELECTION', eo_species_query.format(species_code_field,sname))
                    arcpy.SelectLayerByLocation_management(sf_lyr, "WITHIN_A_DISTANCE", data_lyr, "7 METERS", "SUBSET_SELECTION")
                    #check for selection on sf_merge layer - if there is a selection, get sfid, select all observations within the separation distance, and assign existing eoid to selected features
                    if arcpy.Describe('sf_lyr').fidset is not u'':
                        with arcpy.da.SearchCursor('sf_lyr', sf_id_field) as cursor:
                            #sfid = sorted({row[0] for row in cursor}, reverse=True)[0] #use this line if you want to use the newest SF ID within separation distance
                            sfid = ",".join(sorted({str(int(row[0])) for row in cursor})) # use this line if you want to list all SF IDs within separation distance
                        countBefore = 0
                        countAfter = 1
                        while(countBefore!=countAfter):
                            countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                            arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, "7 METERS", "ADD_TO_SELECTION")
                            arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", species_query.format(species_code,sname))

                            countAfter = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                        with arcpy.da.UpdateCursor(data_lyr, "SF_ID") as cursor:
                            for row in cursor:
                                row[0] = sfid
                                cursor.updateRow(row)
                        arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned an existing SF: " + str(sfid) + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
                    #if no existing SFs selected within separation distance, select all observations within the separation distance and assign new random word
                    else:
                        countBefore = 0
                        countAfter = 1
                        while(countBefore!=countAfter):
                            countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                            arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, "7 METERS", "ADD_TO_SELECTION")
                            arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", species_query.format(species_code,sname))
                            countAfter = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                        with arcpy.da.UpdateCursor(data_lyr, ["SF_NEW", "EO_NEW"]) as cursor:
                            for row in cursor:
                                if row[1] != None:
                                    sf_id = "new_sf_"+str(word_index)
                                    row[0] = sf_id
                                else:
                                    sf_id = "new_sf_"+str(word_index)
                                    row[0] = sf_id
                                cursor.updateRow(row)
                        arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned a new SF: " + sf_id + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
                        word_index += 1
                observation_num += 1
                arcpy.SelectLayerByAttribute_management(data_lyr, "CLEAR_SELECTION")

        #create unique id value for each unique source feature
        i = 1
        with arcpy.da.SearchCursor(data_lyr, "SF_ID") as cursor:
            sfid1 = sorted({row[0] for row in cursor if row[0] is not None})
        with arcpy.da.SearchCursor(data_lyr, "SF_NEW") as cursor:
            sfid2 = sorted({row[0] for row in cursor if row[0] is not None})
        sfid = sfid1 + sfid2
        sfid = [x for x in sfid if x is not None]
        sfid = [x.encode('UTF8') for x in sfid]
        for sf in sfid:
            with arcpy.da.UpdateCursor(data_lyr, ["SF_ID", "SF_NEW", "UNIQUEID"]) as cursor:
                for row in cursor:
                    if row[0] == sf:
                        row[2] = i
                        cursor.updateRow(row)
                    elif row[1] == sf:
                        row[2] = i
                        cursor.updateRow(row)
                    else:
                        pass
            i += 1

        add_fields=add_fields_int+add_fields_text
        for data in data_in:
            arcpy.JoinField_management(data,"join_id",data_lyr,"join_id",add_fields)
            arcpy.DeleteField_management(data,"join_id")
            arcpy.DeleteField_management(data,"buff_dist")

        arcpy.Delete_management("in_memory")
        return

class AquaticGrouping(object):
    def __init__(self):
        self.label = "Aquatic"
        self.description = """Used to prepare a feature class or shapefile representing aquatic species for bulk load into Biotics by assigning an existing EOID/SFID or new EO/SF grouping string to observations based on separation distance."""
        self.canRunInBackground = False
        self.category = "EO/SF Separation Distance Analysis"

    def getParameterInfo(self):
        in_points = arcpy.Parameter(
            displayName = "Input feature layer for separation distance analysis",
            name = "in_points",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        in_lines = arcpy.Parameter(
            displayName = "Input feature layer for separation distance analysis",
            name = "in_lines",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")

        in_poly = arcpy.Parameter(
            displayName = "Input feature layer for separation distance analysis",
            name = "in_poly",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")

        species_code = arcpy.Parameter(
            displayName = "Species identifier field used in input layers (values must match EO/SF species identifier field)",
            name = "species_code",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        species_code.parameterDependencies = [in_points.name]

        lu_separation = arcpy.Parameter(
            displayName = "Separation distance field (values must be in km)",
            name = "lu_separation",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        lu_separation.parameterDependencies = [in_points.name]

        eo_reps = arcpy.Parameter(
            displayName = "Existing EO reps layer",
            name = "eo_reps",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        eo_reps.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_reps"

        eo_id_field = arcpy.Parameter(
            displayName = "EOID field used in EO reps layer",
            name = "eo_id_field",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        eo_id_field.value = "EO_ID"
        eo_id_field.parameterDependencies = [eo_reps.name]

        eo_sourcept = arcpy.Parameter(
            displayName = "Existing source point layer",
            name = "eo_sourcept",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        eo_sourcept.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_sourcept"

        eo_sourceln = arcpy.Parameter(
            displayName = "Existing source line layer",
            name = "eo_sourceln",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")
        eo_sourceln.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_sourceln"

        eo_sourcepy = arcpy.Parameter(
            displayName = "Existing source polygon layer",
            name = "eo_sourcepy",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")
        eo_sourcepy.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_sourcepy"

        sf_id_field = arcpy.Parameter(
            displayName = "SFID field used in source points, lines, and polygon layers",
            name = "sf_id_field",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        sf_id_field.value = "SF_ID"
        sf_id_field.parameterDependencies = [eo_sourcept.name]

        species_code_field = arcpy.Parameter(
            displayName = "Species identifier field used in EO/SF layers (values must match input species identifier field)",
            name = "species_code_field",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        species_code_field.parameterDependencies = [eo_reps.name]

        flowlines = arcpy.Parameter(
            displayName = "NHD flowlines",
            name = "flowlines",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        flowlines.value = r'W:\Heritage\Heritage_Data\Heritage_Data_Tools\AquaticNetworkData.gdb\Aquatic_network\NHDFlowline'

        network = arcpy.Parameter(
            displayName = "Network dataset built on NHD flowlines",
            name = "network",
            datatype = "GPNetworkDatasetLayer",
            parameterType = "Required",
            direction = "Input")
        network.value = r'W:\Heritage\Heritage_Data\Heritage_Data_Tools\AquaticNetworkData.gdb\Aquatic_network\PA_network_ND'

        dams = arcpy.Parameter(
            displayName = "Dams/barrier points (must be snapped to NHD flowlines)",
            name = "dams",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")

        snap_dist = arcpy.Parameter(
            displayName = "Snap distance in meters (distance to flowline beyond which observations will not be assigned/grouped)",
            name = "snap_dist",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        snap_dist.value = "100"

        sf_include = arcpy.Parameter(
            displayName = "Check box if you would like to include existing SF lines and polygons in source feature groupings.",
            name = "sf_include",
            datatype = "GPBoolean",
            parameterType = "optional",
            direction = "Input")

        params = [in_points,in_lines,in_poly,species_code,lu_separation,eo_reps,eo_id_field,eo_sourcept,eo_sourceln,eo_sourcepy,sf_id_field,species_code_field,flowlines,network,dams,snap_dist,sf_include]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        arcpy.AddMessage("""Welcome to the Source Feature and EO Assigner! This tool is designed to prepare a feature class or shapefile for bulk load into Biotics by assigning an existing or new SFID and EOID grouping variable to observations based on separation distance. This used to be done manually, so sit back and enjoy all the other work you can be doing instead of this!""")

        in_points = params[0].valueAsText
        in_lines = params[1].valueAsText
        in_poly = params[2].valueAsText
        species_code = params[3].valueAsText
        lu_separation = params[4].valueAsText
        eo_reps = params[5].valueAsText
        eo_id_field = params[6].valueAsText
        eo_sourcept = params[7].valueAsText
        eo_sourceln = params[8].valueAsText
        eo_sourcepy = params[9].valueAsText
        sf_id_field = params[10].valueAsText
        species_code_field = params[11].valueAsText
        flowlines = params[12].valueAsText
        network = params[13].valueAsText
        dams = params[14].valueAsText
        snap_dist = params[15].valueAsText
        sf_include = params[16].valueAsText

        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = "in_memory"

        arcpy.AddMessage("Preparing input data for use in EO/SF assignment.")
        data_in = []
        data_out = []
        if in_points:
            data_in.append(in_points)
            data_out.append("pts")
        if in_lines:
            data_in.append(in_lines)
            data_out.append("lines")
        if in_poly:
            data_in.append(in_poly)
            data_out.append("polys")
        join_id1 = 1
        for i,o in zip(data_in,data_out):
            if len(arcpy.ListFields(i,"join_id")) == 0:
                arcpy.AddField_management(i,"join_id","TEXT")
            with arcpy.da.UpdateCursor(i,"join_id") as cursor:
                for row in cursor:
                    row[0]=str(join_id1)
                    cursor.updateRow(row)
                    join_id1+=1
            arcpy.FeatureVerticesToPoints_management(i,o,"ALL")
        species_pt = arcpy.Merge_management(data_out,"data_merge")
        species_pt_copy = arcpy.FeatureClassToFeatureClass_conversion(species_pt,"in_memory","species_pt_copy")

        #prepare single fc from biotics sf fcs
        sfs_in = [eo_sourcept]
        sfs_out = ["eo_sourcept1"]
        if str(sf_include) == "True":
            if eo_sourceln:
                sfs_in.append(eo_sourceln)
                sfs_out.append("eo_sourcln1")
            if eo_sourcepy:
                sfs_in.append(eo_sourcepy)
                sfs_out.append("eo_sourcepy1")
        else:
            pass
        for sf_in,sf_out in zip(sfs_in,sfs_out):
            arcpy.Buffer_analysis(sf_in,sf_out,1)
        sf_merge = arcpy.Merge_management(sfs_out, "sf_merge")
        sf_lyr = arcpy.MakeFeatureLayer_management(sf_merge, "sf_lyr")

        #delete identical points with tolerance to increase speed
        arcpy.DeleteIdentical_management(species_pt,["join_id","Shape"],"100 Meters")

        #add EO/SF ID fields if they do not already exist
        add_fields_text = ["SF_ID","SF_NEW","EO_ID","EO_NEW"]
        for field in add_fields_text:
            if len(arcpy.ListFields(species_pt,field)) == 0:
                arcpy.AddField_management(species_pt,field,"TEXT","","",100)
        add_fields_int = ["UNIQUEID"]
        for field in add_fields_int:
            if len(arcpy.ListFields(species_pt,field)) == 0:
                arcpy.AddField_management(species_pt,field,"LONG")

        #create lookup dictionary of separation distances from lookup table
        lu_sep = {f[0]: f[1] for f in arcpy.da.SearchCursor(species_pt, [species_code,lu_separation])}
        #create list of species
        with arcpy.da.SearchCursor(species_pt,species_code) as cursor:
            species_list = sorted({row[0] for row in cursor})

        if arcpy.ListFields(species_pt,species_code)[0].type == 'Integer' or arcpy.ListFields(species_pt,species_code)[0].type == 'Double' or arcpy.ListFields(species_pt,species_code)[0].type == 'Float':
            species_query = "{}={}"
        else:
            species_query = "{}='{}'"
        if arcpy.ListFields(eo_reps,species_code_field)[0].type == 'Integer' or arcpy.ListFields(eo_reps,species_code_field)[0].type == 'Double' or arcpy.ListFields(eo_reps,species_code_field)[0].type == 'Float':
            eo_species_query = "{}={}"
        else:
            eo_species_query = "{}='{}'"

        #separate buffered flowlines at dams
        if dams:
            #buffer dams by 1.1 meters
            dam_buff = arcpy.Buffer_analysis(dams,"dam_buff","1.1 Meter","FULL","FLAT")

        total_species = len(species_list)
        species_rep = 1
        group_id = 1
        for species in species_list:
            arcpy.AddMessage("Assigning EO for "+str(species_rep)+"/"+str(total_species)+": "+str(species))
            species_rep+=1
            s = arcpy.FeatureClassToFeatureClass_conversion(species_pt_copy,"in_memory","s",species_query.format(species_code,species))
            eo = arcpy.MakeFeatureLayer_management(eo_reps,"eo",eo_species_query.format(species_code_field,species))
            sf_lyr = arcpy.MakeFeatureLayer_management(sf_merge,"sf_lyr",eo_species_query.format(species_code_field,species))
            for k,v in lu_sep.items():
                if k==species:
                    distance=(v*1000)-2

            #arcpy.AddMessage("Creating service area line layer for " +str(species) + " to compare to existing EOs")
            #create service area line layer
            eo_service_area_lyr = arcpy.na.MakeServiceAreaLayer(network,"eo_service_area_lyr","Length","TRAVEL_FROM",distance,polygon_type="NO_POLYS",line_type="TRUE_LINES",overlap="OVERLAP")
            eo_service_area_lyr = eo_service_area_lyr.getOutput(0)
            subLayerNames = arcpy.na.GetNAClassNames(eo_service_area_lyr)
            eo_facilitiesLayerName = subLayerNames["Facilities"]
            eo_serviceLayerName = subLayerNames["SALines"]
            arcpy.na.AddLocations(eo_service_area_lyr, eo_facilitiesLayerName, s, "", snap_dist)
            arcpy.na.Solve(eo_service_area_lyr)
            eo_lines = arcpy.mapping.ListLayers(eo_service_area_lyr,eo_serviceLayerName)[0]
            eo_flowline_clip = arcpy.CopyFeatures_management(eo_lines,"eo_service_area")
            eo_flowline_buff = arcpy.Buffer_analysis(eo_flowline_clip,"eo_flowline_buff","1 Meter","FULL","ROUND")
            eo_flowline_diss = arcpy.Dissolve_management(eo_flowline_buff,"eo_flowline_diss",multi_part="SINGLE_PART")
            eo_join = arcpy.SpatialJoin_analysis(target_features=eo_flowline_diss,join_features=eo,out_feature_class="eo_join",join_operation="JOIN_ONE_TO_MANY",join_type = "KEEP_ALL",match_option="INTERSECT")

            for k,v in lu_sep.items():
                if k==species:
                    distance=((v*1000/2)-2)

            #arcpy.AddMessage("Creating service area line layer for " +str(species) + " separation distance grouping")
            sp_service_area_lyr = arcpy.na.MakeServiceAreaLayer(network,"sp_service_area_lyr","Length","TRAVEL_FROM",
                distance,polygon_type="NO_POLYS",line_type="TRUE_LINES",overlap="OVERLAP")
            sp_service_area_lyr = sp_service_area_lyr.getOutput(0)
            subLayerNames = arcpy.na.GetNAClassNames(sp_service_area_lyr)
            sp_facilitiesLayerName = subLayerNames["Facilities"]
            sp_serviceLayerName = subLayerNames["SALines"]
            arcpy.na.AddLocations(sp_service_area_lyr, sp_facilitiesLayerName, s, "", snap_dist)
            arcpy.na.Solve(sp_service_area_lyr)
            sp_lines = arcpy.mapping.ListLayers(sp_service_area_lyr,sp_serviceLayerName)[0]
            sp_flowline_clip = arcpy.CopyFeatures_management(sp_lines,"sp_service_area")
            sp_flowline_buff = arcpy.Buffer_analysis(sp_flowline_clip,"sp_flowline_buff","1 Meter","FULL","ROUND")
            sp_flowline_diss = arcpy.Dissolve_management(sp_flowline_buff,"sp_flowline_diss",multi_part="SINGLE_PART")

            if dams:
                #split flowline buffers at dam buffers by erasing area of dam
                flowline_erase = arcpy.Erase_analysis(sp_flowline_diss,dam_buff,"flowline_erase")
                multipart_input = flowline_erase
                #multi-part to single part to create unique polygons
                single_part = arcpy.MultipartToSinglepart_management(multipart_input,"single_part")
            else:
                single_part = sp_flowline_diss

            #create unique group id
            arcpy.AddField_management(single_part,"group_id","LONG")
            with arcpy.da.UpdateCursor(single_part,"group_id") as cursor:
                for row in cursor:
                    row[0] = group_id
                    cursor.updateRow(row)
                    group_id+=1

            sp_join = arcpy.SpatialJoin_analysis(target_features=single_part,join_features=eo_join,out_feature_class="sp_join",join_operation="JOIN_ONE_TO_MANY",join_type="KEEP_ALL",match_option="INTERSECT")
            sp_join1 = arcpy.SpatialJoin_analysis(target_features=s,join_features=sp_join,out_feature_class="join",join_operation="JOIN_ONE_TO_MANY",join_type="KEEP_ALL",match_option="INTERSECT",search_radius="200 METERS")

            arcpy.AddField_management(sp_join1,"eoid","TEXT","","",100)
            #Create empty dictionaries
            Ndi = {}
            #create SearchCursor object
            with arcpy.da.SearchCursor(sp_join1, ["group_id",eo_id_field]) as cursor:
                for row in cursor:
                    if row[1]:
                        if not row[0] in Ndi:
                            Ndi[row[0]] = [row[1]]
                        else:
                            Ndi[row[0]].append(row[1])

            Ndi = {k: list(set(v)) for k, v in Ndi.items()}

            #create UpdateCursor
            if not Ndi == True:
                with arcpy.da.UpdateCursor (sp_join1, ["group_id","eoid"]) as cursor:
                    for row in cursor:
                        if row[0] in Ndi:
                            row[1] = ",".join(map(str, Ndi[row[0]]))
                            cursor.updateRow(row)

            arcpy.DeleteIdentical_management(sp_join1,["join_id","eoid","group_id"])

            id_fill = {f[0]: [f[1],f[2]] for f in arcpy.da.SearchCursor(sp_join1, ["join_id","group_id","eoid"])}

            with arcpy.da.UpdateCursor(species_pt,["join_id","EO_NEW","EO_ID"]) as cursor:
                for row in cursor:
                    for k,v in id_fill.items():
                        if k==row[0] and v[1] is not None:
                            row[2]=str(v[1])
                            cursor.updateRow(row)
                        elif k==row[0] and v[1] is None:
                            row[1]="new_eo_"+str(v[0])
                            cursor.updateRow(row)
                        else:
                            pass

        arcpy.DeleteIdentical_management(species_pt,["join_id","EO_ID","EO_NEW"])

        #get name of true OID field
        objectid_field = arcpy.Describe(species_pt).OIDFieldName
        species_lyr = arcpy.MakeFeatureLayer_management(species_pt,"species_lyr")

        arcpy.AddMessage("Assigning source feature IDs to all records.")
        search_fields = [objectid_field, "SF_ID", "SF_NEW", species_code]
        with arcpy.da.SearchCursor(species_lyr, search_fields) as cursor:
            for row in cursor:
                objectid = row[0]
                if row[2] != None and (row[1] != None or row[1] != 0):
                    pass
                else:
                    sname = row[3]

                    #check for existing SFs within 9m of feature (8m because of 1m buffer on SF layers)
                    arcpy.SelectLayerByAttribute_management(species_lyr, "NEW_SELECTION", "{}={}".format(objectid_field, objectid))
                    arcpy.SelectLayerByAttribute_management(sf_lyr, 'NEW_SELECTION', eo_species_query.format(species_code_field,sname))
                    arcpy.SelectLayerByLocation_management(sf_lyr, "WITHIN_A_DISTANCE", species_lyr, "8 METERS", "SUBSET_SELECTION")
                    #check for selection on sf_merge layer - if there is a selection, get sfid, select all observations within the separation distance, and assign existing eoid to selected features
                    if arcpy.Describe('sf_lyr').fidset is not u'':
                        with arcpy.da.SearchCursor('sf_lyr', sf_id_field) as cursor:
                            #sfid = sorted({row[0] for row in cursor}, reverse=True)[0] #use this line if you want to use the newest SF ID within separation distance
                            sfid = ",".join(sorted({str(row[0]) for row in cursor})) # use this line if you want to list all SF IDs within separation distance
                        countBefore = 0
                        countAfter = 1
                        while(countBefore!=countAfter):
                            countBefore = int(arcpy.GetCount_management("species_lyr").getOutput(0))
                            arcpy.SelectLayerByLocation_management(species_lyr, "WITHIN_A_DISTANCE", species_lyr, "9 METERS", "ADD_TO_SELECTION")
                            arcpy.SelectLayerByAttribute_management(species_lyr, "SUBSET_SELECTION", species_query.format(species_code,sname))
                            countAfter = int(arcpy.GetCount_management("species_lyr").getOutput(0))
                        with arcpy.da.UpdateCursor(species_lyr, "SF_ID") as cursor:
                            for row in cursor:
                                row[0] = sfid
                                cursor.updateRow(row)
                    #if no existing SFs selected within separation distance, select all observations within the separation distance and assign new random word
                    else:
                        countBefore = 0
                        countAfter = 1
                        while(countBefore!=countAfter):
                            countBefore = int(arcpy.GetCount_management("species_lyr").getOutput(0))
                            arcpy.SelectLayerByLocation_management(species_lyr, "WITHIN_A_DISTANCE", species_lyr, "9 METERS", "ADD_TO_SELECTION")
                            arcpy.SelectLayerByAttribute_management(species_lyr, "SUBSET_SELECTION", species_query.format(species_code,sname))
                            countAfter = int(arcpy.GetCount_management("species_lyr").getOutput(0))
                        with arcpy.da.UpdateCursor(species_lyr, ["SF_NEW", "EO_NEW"]) as cursor:
                            for row in cursor:
                                if row[1] != None:
                                    sf_id = "new_sf_"+str(group_id)
                                    row[0] = sf_id
                                else:
                                    sf_id = "new_sf_"+str(group_id)
                                    row[0] = sf_id
                                cursor.updateRow(row)
                        group_id += 1
                arcpy.SelectLayerByAttribute_management(species_lyr, "CLEAR_SELECTION")

        #create unique id value for each unique source feature
        i = 1
        with arcpy.da.SearchCursor(species_lyr, ["SF_ID"]) as cursor:
            sfid1 = sorted({row[0] for row in cursor})
        with arcpy.da.SearchCursor(species_lyr, ["SF_NEW"]) as cursor:
            sfid2 = sorted({row[0] for row in cursor})
        sfid = sfid1 + sfid2
        sfid = [x for x in sfid if x is not None]
        for sf in sfid:
            with arcpy.da.UpdateCursor(species_lyr, ["SF_ID", "SF_NEW", "UNIQUEID"]) as cursor:
                for row in cursor:
                    if row[0] == sf:
                        row[2] = i
                        cursor.updateRow(row)
                    elif row[1] == sf:
                        row[2] = i
                        cursor.updateRow(row)
                    else:
                        pass
            i += 1

        add_fields=add_fields_int+add_fields_text
        for data in data_in:
            arcpy.JoinField_management(data,"join_id",species_lyr,"join_id",add_fields)

        for data in data_in:
            arcpy.DeleteField_management(data,"join_id")
        arcpy.Delete_management("in_memory")

        return

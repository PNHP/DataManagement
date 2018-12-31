#-------------------------------------------------------------------------------
# Name:        EO Assign
# Purpose:     Used to prepare feature class or shapefile for bulk load into
#              Biotics by assigning an existing EOID/SFID or new EO/SF grouping
#              string to observations based on separation distance.
# Author:      MMOORE
# Created:     02/13/2018
#-------------------------------------------------------------------------------

#import libraries
import arcpy, os, datetime
from arcpy import env
from arcpy.sa import *
import urllib2

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
        self.label = "Terrestrial EO/SF Grouping"
        self.description = """Used to prepare a feature class or shapefile for bulk load into Biotics by assigning an existing EOID/SFID or new EO/SF grouping string to observations based on separation distance."""
        self.canRunInBackground = False
        self.category = "EO/SF Grouping"

    def getParameterInfo(self):
        in_points = arcpy.Parameter(
            displayName = "Point feature layer to be bulk loaded",
            name = "in_points",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")

        in_lines = arcpy.Parameter(
            displayName = "Line feature layer to be bulk loaded",
            name = "in_lines",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")

        in_poly = arcpy.Parameter(
            displayName = "Polygon feature layer to be bulk loaded",
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
            displayName = "Separation Distance Field",
            name = "lu_separation",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        lu_separation.parameterDependencies = [in_points.name]

        eo_reps = arcpy.Parameter(
            displayName = "Existing EO Reps Layer",
            name = "eo_reps",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        eo_reps.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_reps"

        eo_id_field = arcpy.Parameter(
            displayName = "EOID Field used in EO Reps Layer",
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
        eo_sourcept.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_sourcept"

        eo_sourceln = arcpy.Parameter(
            displayName = "Existing Source Line Layer",
            name = "eo_sourceln",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        eo_sourceln.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_sourceln"

        eo_sourcepy = arcpy.Parameter(
            displayName = "Existing Source Polygon Layer",
            name = "eo_sourcepy",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        eo_sourcepy.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_sourcepy"

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

        params = [in_points,in_lines,in_poly,species_code,lu_separation,eo_reps,eo_id_field,eo_sourcept,eo_sourceln,eo_sourcepy,sf_id_field,species_code_field]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        arcpy.AddMessage("""Welcome to the Source Feature and EO Assigner! This tool is designed to prepare a feature class or shapefile for bulk load into Biotics by assigning an existing or new SFID and EOID grouping variable to observations based on eparation distance. This used to be done manually, so sit back and enjoy all the other work you can be doing instead of this!""")

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

        arcpy.env.workspace = "in_memory"

        arcpy.AddMessage("Preparing sf_lyr")
        #prepare single fc from biotics sf fcs
        sfs_in = [eo_sourcept,eo_sourceln,eo_sourcepy]
        sfs_out = ["eo_sourcept","eo_sourceln","eo_sourcepy"]
        for sf_in,sf_out in zip(sfs_in,sfs_out):
            arcpy.Buffer_analysis(sf_in,sf_out,1)
        sf_merge = arcpy.Merge_management(sfs_out, "sf_merge")
        sf_lyr = arcpy.MakeFeatureLayer_management(sf_merge, "sf_lyr")

        arcpy.AddMessage("Preparing data_lyr")
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

        arcpy.AddMessage("creating temp join id")
        join_id = 1
        for i,o in zip(data_in,data_out):
            arcpy.AddField_management(i,"temp_join_id","TEXT")
            with arcpy.da.UpdateCursor(i,"temp_join_id") as cursor:
                for row in cursor:
                    row[0]=str(join_id)
                    cursor.updateRow(row)
                    join_id+=1
            arcpy.Buffer_analysis(i,o,1)
        data_merge = arcpy.Merge_management(data_out,"data_merge")
        data_lyr = arcpy.MakeFeatureLayer_management(data_merge,"data_lyr")

        if arcpy.ListFields(data_lyr,species_code)[0].type == 'Integer':
            species_query = "{}={}"
        else:
            species_query = "{}='{}'"
        if arcpy.ListFields(data_lyr,species_code_field)[0].type == 'Integer':
            eo_species_query = "{}={}"
        else:
            eo_species_query = "{}='{}'"

        #get name of true OID field
        objectid_field = arcpy.Describe(data_lyr).OIDFieldName

        #create feature layers to allow for selections
        eo_reps = arcpy.MakeFeatureLayer_management(eo_reps, "eo_reps")

        #add EO/SF ID fields if they do not already exist
        add_fields = ["SF_ID","SF_NEW","UNIQUEID","EO_ID","EO_NEW"]
        for field in add_fields:
            if len(arcpy.ListFields(data_lyr,field)) == 0:
                arcpy.AddField_management(data_lyr,field,"TEXT","","",50)

        #set word index to assign words to new EO groups
        word_index = 1
        observation_num = 1

        #get total records in data_lyr for progress reporting messages
        total_obs = arcpy.GetCount_management(data_lyr)
        #start assigning loop
        search_fields = [objectid_field, "EO_ID", "EO_NEW", species_code, lu_separation]
        with arcpy.da.SearchCursor(data_lyr, search_fields) as cursor:
            for row in cursor:
                objectid = row[0]
                #if one of the EOID fields already have a value, continue on to next feature
                if row[2] != None and (row[1] != None or row[1] != 0):
                    arcpy.AddMessage("ObjectID " + str(objectid) + " EO Observation number " + str(observation_num) + "/" + str(total_obs) + " has already been assigned to a new or existing EO.")
                    pass
                else:
                    sname = row[3]
                    distance = str(row[4]*1000)+" METERS"

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
                            eoid = ",".join(sorted({str(row[0]) for row in cursor})) #use this if filling with EOIDs of all EOs within separation distance
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
                                row[0] = str(eoid)
                                cursor.updateRow(row)
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
                                row[0] = str(word_index) #word_list[word_index]
                                cursor.updateRow(row)
                        arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned a new EO: " + str(word_index) + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
                        word_index += 1
                observation_num += 1
                arcpy.SelectLayerByAttribute_management(data_lyr, "CLEAR_SELECTION")

        observation_num = 1
        search_fields = [objectid_field, "SF_ID", "SF_NEW", species_code]
        with arcpy.da.SearchCursor(data_lyr, search_fields) as cursor:
            for row in cursor:
                objectid = row[0]
                if row[2] != None and (row[1] != None or row[1] != 0):
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
                            sfid = ",".join(sorted({str(row[0]) for row in cursor})) # use this line if you want to list all SF IDs within separation distance
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
                                    sf_id = row[1] + "_" + str(word_index) #word_list[word_index]
                                    row[0] = sf_id
                                else:
                                    sf_id = str(word_index) #word_list[word_index]
                                    row[0] = sf_id
                                cursor.updateRow(row)
                        arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned a new SF: " + sf_id + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
                        word_index += 1
                observation_num += 1
                arcpy.SelectLayerByAttribute_management(data_lyr, "CLEAR_SELECTION")

        #create unique id value for each unique source feature
        i = 1
        with arcpy.da.SearchCursor(data_lyr, ["SF_ID", "SF_NEW", "UNIQUEID"]) as cursor:
            sfid1 = sorted({row[0] for row in cursor})
        with arcpy.da.SearchCursor(data_lyr, ["SF_ID", "SF_NEW", "UNIQUEID"]) as cursor:
            sfid2 = sorted({row[1] for row in cursor})
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

        for data in data_in:
            arcpy.JoinField_management(data,"temp_join_id",data_lyr,"temp_join_id",add_fields)
            arcpy.DeleteField_management(data,"temp_join_id")

        arcpy.Delete_management("in_memory")
        return

class AquaticGrouping(object):
    def __init__(self):
        self.label = "Aquatic EO/SF Grouping"
        self.description = """Used to prepare a feature class or shapefile representing aquatic species for bulk load into Biotics by assigning an existing EOID/SFID or new EO/SF grouping string to observations based on separation distance."""
        self.canRunInBackground = False
        self.category = "EO/SF Grouping"

    def getParameterInfo(self):
        in_points = arcpy.Parameter(
            displayName = "Point feature layer to be bulk loaded",
            name = "in_points",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")

        in_lines = arcpy.Parameter(
            displayName = "Line feature layer to be bulk loaded",
            name = "in_lines",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")

        in_poly = arcpy.Parameter(
            displayName = "Polygon feature layer to be bulk loaded",
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
            displayName = "Separation Distance Field",
            name = "lu_separation",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        lu_separation.parameterDependencies = [in_points.name]

        eo_reps = arcpy.Parameter(
            displayName = "Existing EO Reps Layer",
            name = "eo_reps",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        eo_reps.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_reps"

        eo_id_field = arcpy.Parameter(
            displayName = "EOID Field used in EO Reps Layer",
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
        eo_sourcept.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_sourcept"

        eo_sourceln = arcpy.Parameter(
            displayName = "Existing Source Line Layer",
            name = "eo_sourceln",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        eo_sourceln.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_sourceln"

        eo_sourcepy = arcpy.Parameter(
            displayName = "Existing Source Polygon Layer",
            name = "eo_sourcepy",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        eo_sourcepy.value = r"W:\Heritage\Heritage_Data\biotics_datasets.gdb\eo_sourcepy"

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

        flowlines = arcpy.Parameter(
            displayName = "NHD flowlines",
            name = "flowlines",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        network = arcpy.Parameter(
            displayName = "Network dataset built on NHD flowlines",
            name = "network",
            datatype = "GPNetworkDatasetLayer",
            parameterType = "Required",
            direction = "Input")

        dams = arcpy.Parameter(
            displayName = "Dams/barrier points (must be snapped to NHD flowlines)",
            name = "dams",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Input")

        snap_dist = arcpy.Parameter(
            displayName = "Snap distance in meters (distance to flowline beyond which observations are thrown out)",
            name = "snap_dist",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        snap_dist.value = "100"

        params = [in_points,in_lines,in_poly,species_code,lu_separation,eo_reps,eo_id_field,eo_sourcept,eo_sourceln,eo_sourcepy,sf_id_field,species_code_field]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        arcpy.AddMessage("""Welcome to the Source Feature and EO Assigner! This tool is designed to prepare a feature class or shapefile for bulk load into Biotics by assigning an existing or new SFID and EOID grouping variable to observations based on eparation distance. This used to be done manually, so sit back and enjoy all the other work you can be doing instead of this!""")

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


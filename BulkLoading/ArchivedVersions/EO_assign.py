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
        in_data = arcpy.Parameter(
            displayName = "Feature class or shapefile to be bulk loaded",
            name = "in_data",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        lu_class = arcpy.Parameter(
            displayName = "Location Use Class",
            name = "uid",
            datatype = "Field",
            parameterType = "Optional",
            direction = "Input")
        lu_class.parameterDependencies = [in_data.name]

        lu_separation = arcpy.Parameter(
            displayName = "Separation Distance Table",
            name = "lu_separation",
            datatype = "DETable",
            parameterType = "Required",
            direction = "Input")

        eo_reps = arcpy.Parameter(
            displayName = "Existing EO Reps Layer",
            name = "eo_reps",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        eo_sourcept = arcpy.Parameter(
            displayName = "Existing Source Point Layer",
            name = "eo_sourcept",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        eo_sourceln = arcpy.Parameter(
            displayName = "Existing Source Line Layer",
            name = "eo_sourceln",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        eo_sourcepy = arcpy.Parameter(
            displayName = "Existing Source Polygon Layer",
            name = "eo_sourcepy",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        params = [in_data,lu_class,lu_separation,eo_reps,eo_sourcept,eo_sourceln,eo_sourcepy]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        arcpy.AddMessage("""Welcome to the Source Feature and EO Assigner! This tool is designed to prepare a feature class or shapefile for bulk load into Biotics by assigning an existing or new SFID and EOID grouping variable to observations based on eparation distance. This used to be done manually, so sit back and enjoy all the other work you can be doing instead of this!""")

        in_data = params[0].valueAsText
        lu_class = params[1].valueAsText
        lu_separation = params[2].valueAsText
        eo_reps = params[3].valueAsText
        eo_sourcept = params[4].valueAsText
        eo_sourceln = params[5].valueAsText
        eo_sourcepy = params[6].valueAsText

        #get name of true OID field
        objectid_field = arcpy.Describe(in_data).OIDFieldName

        #prepare single fc from biotics sf fcs
        sfs_in = [eo_sourcept,eo_sourceln,eo_sourcepy]
        sfs_out = ["eo_sourcept","eo_sourceln","eo_sourcepy"]
        for sf_in,sf_out in zip(sfs_in,sfs_out):
            arcpy.Buffer_analysis(sf_in,sf_out,1)
        sf_merge = arcpy.Merge_management(sfs_out, "sf_merge")
        sf_lyr = arcpy.MakeFeatureLayer_management(sf_merge, "sf_lyr")

        #pull in and format word list to use for grouping strings
##        word_site = "https://svnweb.freebsd.org/csrg/share/dict/words?view=co&content-type=text/plain"
##        response = urllib2.urlopen(word_site)
##        txt = response.read()
##        word_list = txt.splitlines()
##        for word in word_list:
##            if "'" in word or "oris" in word or "nis" in word or "&" in word or "." in word or "sex" in word:
##                word_list.remove(word)

        #create feature layers to allow for selections
        data_lyr = arcpy.MakeFeatureLayer_management(in_data, "data_lyr")
        eo_reps = arcpy.MakeFeatureLayer_management(eo_reps, "eo_reps")

        #add EO/SF ID fields if they do not already exist
        if len(arcpy.ListFields(data_lyr,"SF_ID")) == 0:
            arcpy.AddField_management(data_lyr, "SF_ID", "TEXT", "", "", 50)
        if len(arcpy.ListFields(data_lyr,"SF_NEW")) == 0:
            arcpy.AddField_management(data_lyr, "SF_NEW", "TEXT", "", "", 50)
        if len(arcpy.ListFields(data_lyr,"UNIQUEID")) == 0:
            arcpy.AddField_management(data_lyr, "UNIQUEID","LONG")
        if len(arcpy.ListFields(data_lyr,"EO_ID")) == 0:
            arcpy.AddField_management(data_lyr, "EO_ID", "TEXT", "", "", 50)
        if len(arcpy.ListFields(data_lyr,"EO_NEW")) == 0:
            arcpy.AddField_management(data_lyr, "EO_NEW", "TEXT", "","", 50)

        #create lookup dictionary of separation distances from lookup table
        lu_sep = {f[0]: f[1] for f in arcpy.da.SearchCursor(lu_separation, ["SNAME", "sep_dist_km"])}

        #set word index to assign words to new EO groups
        word_index = 1
        observation_num = 1

        #get total records in data_lyr for progress reporting messages
        total_obs = arcpy.GetCount_management(data_lyr)
        #start assigning loop
        search_fields = [objectid_field, "EO_ID", "EO_NEW", "SNAME"]
        if lu_class:
            search_fields.append(lu_class)
        with arcpy.da.SearchCursor(data_lyr, search_fields) as cursor:
            for row in cursor:
                objectid = row[0]
                #if one of the EOID fields already have a value, continue on to next feature
                if row[2] != None and (row[1] != None or row[1] != 0):
                    arcpy.AddMessage("ObjectID " + str(objectid) + " EO Observation number " + str(observation_num) + "/" + str(total_obs) + " has already been assigned to a new or existing EO.")
                    pass
                else:
                    sname = row[3]
                    if lu_class:
                        lu_class_value = row[4]
                    for k,v in lu_sep.items():
                        if k==sname:
                            distance=str(v*1000)+" METERS"
                    #select feature and assign sname and separation distance variables
                    arcpy.SelectLayerByAttribute_management(data_lyr, "NEW_SELECTION", "{}={}".format(objectid_field,objectid))
                    #check for existing EO reps within separation distance of feature
                    arcpy.SelectLayerByAttribute_management(eo_reps, 'NEW_SELECTION', '"SNAME"='+"'%s'"%sname)
                    if lu_class:
                        arcpy.SelectLayerByAttribute_management(eo_reps,'SUBSET_SELECTION',"{}=={}".format(lu_class,lu_class_value))
                    arcpy.SelectLayerByLocation_management(eo_reps, "WITHIN_A_DISTANCE", data_lyr, distance, "SUBSET_SELECTION")
                    #check for selection on eo_reps layer - if there is a selection, get eoid, select all observations within the separation distance, and assign existing eoid to selected features
                    selection_num = arcpy.Describe(eo_reps).fidset
                    if selection_num is not u'':
                        with arcpy.da.SearchCursor(eo_reps, "EO_ID") as cursor:
                            #eoid = sorted({row[0] for row in cursor}, reverse=True)[0] #use this if keeping newest EO
                            eoid = ",".join(sorted({str(row[0]) for row in cursor})) #use this if filling with EOIDs of all EOs within separation distance
                        arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, distance, "ADD_TO_SELECTION")
                        arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", '"SNAME"='+"'%s'"%sname)
                        #set arbitrary unequal counts to start while loop
                        countBefore = 0
                        countAfter = 1
                        while(countBefore!=countAfter):
                            countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                            arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, distance, "ADD_TO_SELECTION")
                            arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", '"SNAME"='+"'%s'"%sname)
                            countAfter = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                        with arcpy.da.UpdateCursor(data_lyr, "EO_ID") as cursor:
                            for row in cursor:
                                row[0] = str(eoid)
                                cursor.updateRow(row)
                        arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned an existing EO: " + str(eoid) + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
                    #if no existing EOs selected within separation distance, select all observations within the separation distance and assign new random word
                    else:
                        arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, distance, "ADD_TO_SELECTION")
                        arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", '"SNAME"='+"'%s'"%sname)
                        countBefore = 0
                        countAfter = 1
                        while(countBefore!=countAfter):
                            countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                            arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, distance, "ADD_TO_SELECTION")
                            arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", '"SNAME"='+"'%s'"%sname)
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
        with arcpy.da.SearchCursor(data_lyr, [objectid_field, "SF_ID", "SF_NEW", "SNAME"]) as cursor:
            for row in cursor:
                objectid = row[0]
                if row[2] != None and (row[1] != None or row[1] != 0):
                    arcpy.AddMessage("ObjectID " + str(objectid) + " SF Observation number " + str(observation_num) + "/" + str(total_obs) + " has already been assigned to a new or existing SF.")
                else:
                    sname = row[3]
                    #check for existing SFs within 9m of feature (8m because of 1m buffer on SF layers)
                    arcpy.SelectLayerByAttribute_management(data_lyr, "NEW_SELECTION", "{}={}".format(objectid_field, objectid))
                    arcpy.SelectLayerByAttribute_management(sf_lyr, 'NEW_SELECTION', '"SNAME"='+"'%s'"%sname)
                    arcpy.SelectLayerByLocation_management(sf_lyr, "WITHIN_A_DISTANCE", data_lyr, "8 METERS", "SUBSET_SELECTION")
                    #check for selection on sf_merge layer - if there is a selection, get sfid, select all observations within the separation distance, and assign existing eoid to selected features
                    if arcpy.Describe('sf_lyr').fidset is not u'':
                        with arcpy.da.SearchCursor('sf_lyr', "SF_ID") as cursor:
                            #sfid = sorted({row[0] for row in cursor}, reverse=True)[0] #use this line if you want to use the newest SF ID within separation distance
                            sfid = ",".join(sorted({str(row[0]) for row in cursor})) # use this line if you want to list all SF IDs within separation distance
                        arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, "8 METERS", "ADD_TO_SELECTION")
                        arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", '"SNAME"='+"'%s'"%sname)
                        countBefore = 0
                        countAfter = 1
                        while(countBefore!=countAfter):
                            countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                            arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, "8 METERS", "ADD_TO_SELECTION")
                            arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", '"SNAME"='+"'%s'"%sname)
                            countAfter = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                        with arcpy.da.UpdateCursor(data_lyr, "SF_ID") as cursor:
                            for row in cursor:
                                row[0] = sfid
                                cursor.updateRow(row)
                        arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned an existing SF: " + str(sfid) + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
                    #if no existing SFs selected within separation distance, select all observations within the separation distance and assign new random word
                    else:
                        arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, "8 METERS", "ADD_TO_SELECTION")
                        arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", '"SNAME"='+"'%s'"%sname)
                        countBefore = 0
                        countAfter = 1
                        while(countBefore!=countAfter):
                            countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                            arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, "8 METERS", "ADD_TO_SELECTION")
                            arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", '"SNAME"='+"'%s'"%sname)
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
        with arcpy.da.SearchCursor("data_lyr", ["SF_ID", "SF_NEW", "UNIQUEID"]) as cursor:
            sfid1 = sorted({row[0] for row in cursor})
        with arcpy.da.SearchCursor("data_lyr", ["SF_ID", "SF_NEW", "UNIQUEID"]) as cursor:
            sfid2 = sorted({row[1] for row in cursor})
        sfid = sfid1 + sfid2
        sfid = [x for x in sfid if x is not None]
        sfid = [x.encode('UTF8') for x in sfid]
        for sf in sfid:
            with arcpy.da.UpdateCursor("data_lyr", ["SF_ID", "SF_NEW", "UNIQUEID"]) as cursor:
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

        arcpy.Delete_management("in_memory")
        return


class AquaticGrouping(object):
    def __init__(self):
        self.label = "Aquatic EO/SF Grouping"
        self.description = """Used to prepare a feature class or shapefile representing aquatic species for bulk load into Biotics by assigning an existing EOID/SFID or new EO/SF grouping string to observations based on separation distance."""
        self.canRunInBackground = False
        self.category = "EO/SF Grouping"

    def getParameterInfo(self):
        in_data = arcpy.Parameter(
            displayName = "Feature class or shapefile to be bulk loaded",
            name = "in_data",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        lu_separation = arcpy.Parameter(
            displayName = "Separation Distance Table",
            name = "lu_separation",
            datatype = "DETable",
            parameterType = "Required",
            direction = "Input")

        eo_reps = arcpy.Parameter(
            displayName = "Existing EO Reps Layer",
            name = "eo_reps",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        eo_sourcept = arcpy.Parameter(
            displayName = "Existing Source Point Layer",
            name = "eo_sourcept",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        eo_sourceln = arcpy.Parameter(
            displayName = "Existing Source Line Layer",
            name = "eo_sourceln",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        eo_sourcepy = arcpy.Parameter(
            displayName = "Existing Source Polygon Layer",
            name = "eo_sourcepy",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        params = [in_data,lu_separation,eo_reps,eo_sourcept,eo_sourceln,eo_sourcepy]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        arcpy.AddMessage("""Welcome to the Source Feature and EO Assigner! This tool is designed to prepare a feature class or shapefile for bulk load into Biotics by assigning an existing or new SFID and EOID grouping variable to observations based on eparation distance. This used to be done manually, so sit back and enjoy all the other work you can be doing instead of this!""")

        in_data = params[0].valueAsText
        lu_separation = params[1].valueAsText
        eo_reps = params[2].valueAsText
        eo_sourcept = params[3].valueAsText
        eo_sourceln = params[4].valueAsText
        eo_sourcepy = params[5].valueAsText
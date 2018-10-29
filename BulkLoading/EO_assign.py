#-------------------------------------------------------------------------------
# Name:        EO Assign
# Purpose:     Used to prepare feature class or shapefile for bulk load into
#              Biotics by assigning an existing EOID or new EO grouping string
#              to observations based on separation distance.
# Author:      MMOORE
# Created:     02/13/2018
#-------------------------------------------------------------------------------

#import libraries
import arcpy, os, datetime
from arcpy import env
from arcpy.sa import *
import urllib2

arcpy.AddMessage("""Welcome to the Source Feature and EO Assigner! This tool is designed to
prepare a feature class or shapefile for bulk load into Biotics by assigning an
existing or new SFID and EOID grouping variable to observations based on
separation distance. This used to be done manually, so sit back and enjoy all
the other work you can be doing instead of this!""")

print("""Welcome to the Source Feature and EO Assigner! This tool is designed to
prepare a feature class or shapefile for bulk load into Biotics by assigning an
existing or new SFID and EOID grouping variable to observations based on
separation distance. This used to be done manually, so sit back and enjoy all
the other work you can be doing instead of this!""")

#set environmental variables
arcpy.env.overwriteOutput = True
arcpy.env.qualifiedFieldNames = False
arcpy.env.workspace = "in_memory"

#set paths and variables to in data and lookup tables
##in_data = r'East_processing_subset2'
##lu_separation = r'lu_separationdistance'
##out_fc = r'H:/Projects/DataProcessing/BulkLoads/Data.gdb/bulkload3'
in_data = arcpy.GetParameterAsText(0)
objectid_field = arcpy.GetParameterAsText(1)
lu_separation = arcpy.GetParameterAsText(2)
eo_reps = r'W:\Heritage\Heritage_Data\Biotics_datasets.gdb\eo_reps'
bioticsdb = r'W:\Heritage\Heritage_Data\Biotics_datasets.gdb'
sfs = ["eo_sourcept", "eo_sourceln", "eo_sourcepy"]

#prepare single fc from biotics sf fcs
for sf in sfs:
    i = os.path.join(bioticsdb, sf)
    arcpy.Buffer_analysis(i, sf, 1)
sf_merge = arcpy.Merge_management(sfs, "sf_merge")
sf_lyr = arcpy.MakeFeatureLayer_management(sf_merge, "sf_lyr")


#pull in word list to use for grouping strings
word_site = "https://svnweb.freebsd.org/csrg/share/dict/words?view=co&content-type=text/plain"
response = urllib2.urlopen(word_site)
txt = response.read()
word_list = txt.splitlines()
for word in word_list:
    if "'" in word or "oris" in word or "enis" in word or "&" in word or "sex" in word:
        word_list.remove(word)

#create feature layers to allow for selections
data_lyr = arcpy.MakeFeatureLayer_management(in_data, "data_lyr")
eo_reps = arcpy.MakeFeatureLayer_management(eo_reps, "eo_reps")
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
word_index = 3
observation_num = 1
total_obs = arcpy.GetCount_management(data_lyr)
with arcpy.da.SearchCursor(data_lyr, [objectid_field, "EO_ID", "EO_NEW", "SNAME"]) as cursor:
    for row in cursor:
        objectid = row[0]
        #if EOID field already has a value, continue on to next feature
        if row[2] != None and (row[1] != None or row[1] != 0):
            arcpy.AddMessage("ObjectID " + str(objectid) + " EO Observation number " + str(observation_num) + "/" + str(total_obs) + " has already been assigned to a new or existing EO.")
            print("ObjectID " + str(objectid) + " EO Observation number " + str(observation_num) + "/" + str(total_obs) + " has already been assigned to a new or existing EO.")
            pass
        else:
            sname = row[3]
            for k,v in lu_sep.items():
                if k==sname:
                    distance=v*1000
            #select feature and assign sname and separation distance variables
            arcpy.SelectLayerByAttribute_management(data_lyr, "NEW_SELECTION", "{}={}".format(objectid_field,objectid))
            #check for existing EO reps within separation distance of feature
            arcpy.SelectLayerByAttribute_management(eo_reps, 'NEW_SELECTION', '"SNAME"='+"'%s'"%sname)
            arcpy.SelectLayerByLocation_management(eo_reps, "WITHIN_A_DISTANCE", data_lyr, distance, "SUBSET_SELECTION")
            #check for selection on eo_reps layer - if there is a selection, get eoid, select all observations within the separation distance, and assign existing eoid to selected features
            selection_num = arcpy.Describe(eo_reps).fidset
            if selection_num is not u'':
                with arcpy.da.SearchCursor(eo_reps, "EO_ID") as cursor:
                    #eoid = sorted({row[0] for row in cursor}, reverse=True)[0]
                    eoid = ",".join(sorted({str(row[0]) for row in cursor}))
                arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, distance, "ADD_TO_SELECTION")
                arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", '"SNAME"='+"'%s'"%sname)
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
                print("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned an existing EO: " + str(eoid) + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
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
                        row[0] = word_list[word_index]
                        cursor.updateRow(row)
                arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned a new EO: " + word_list[word_index] + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
                print("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned a new EO: " + word_list[word_index] + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
                word_index += 5
        observation_num += 1
        arcpy.SelectLayerByAttribute_management(data_lyr, "CLEAR_SELECTION")

observation_num = 1
with arcpy.da.SearchCursor(data_lyr, [objectid_field, "SF_ID", "SF_NEW", "SNAME"]) as cursor:
    for row in cursor:
        objectid = row[0]
        if row[2] != None and (row[1] != None or row[1] != 0):
            arcpy.AddMessage("ObjectID " + str(objectid) + " SF Observation number " + str(observation_num) + "/" + str(total_obs) + " has already been assigned to a new or existing SF.")
            print("ObjectID " + str(objectid) + " SF Observation number " + str(observation_num) + "/" + str(total_obs) + " has already been assigned to a new or existing SF.")
        else:
            sname = row[3]
            #check for existing SFs within 9m of feature (8m because of 1m buffer on SF layers)
            arcpy.SelectLayerByAttribute_management(data_lyr, "NEW_SELECTION", "{}={}".format(objectid_field, objectid))
            arcpy.SelectLayerByAttribute_management(sf_lyr, 'NEW_SELECTION', '"SNAME"='+"'%s'"%sname)
            arcpy.SelectLayerByLocation_management(sf_lyr, "WITHIN_A_DISTANCE", data_lyr, 8, "SUBSET_SELECTION")
            #check for selection on sf_merge layer - if there is a selection, get sfid, select all observations within the separation distance, and assign existing eoid to selected features
            if arcpy.Describe('sf_lyr').fidset is not u'':
                with arcpy.da.SearchCursor('sf_lyr', "SF_ID") as cursor:
                    #sfid = sorted({row[0] for row in cursor}, reverse=True)[0] #use this line if you want to use the newest SF ID within separation distance
                    sfid = ",".join(sorted({str(row[0]) for row in cursor})) # use this line if you want to list all SF IDs within separation distance
                arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, 8, "ADD_TO_SELECTION")
                arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", '"SNAME"='+"'%s'"%sname)
                countBefore = 0
                countAfter = 1
                while(countBefore!=countAfter):
                    countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                    arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, 8, "ADD_TO_SELECTION")
                    arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", '"SNAME"='+"'%s'"%sname)
                    countAfter = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                with arcpy.da.UpdateCursor(data_lyr, "SF_ID") as cursor:
                    for row in cursor:
                        row[0] = sfid
                        cursor.updateRow(row)
                arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned an existing SF: " + str(sfid) + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
                print("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned an existing SF: " + str(sfid) + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
            #if no existing SFs selected within separation distance, select all observations within the separation distance and assign new random word
            else:
                arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, 8, "ADD_TO_SELECTION")
                arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", '"SNAME"='+"'%s'"%sname)
                countBefore = 0
                countAfter = 1
                while(countBefore!=countAfter):
                    countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                    arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, 8, "ADD_TO_SELECTION")
                    arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", '"SNAME"='+"'%s'"%sname)
                    countAfter = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                with arcpy.da.UpdateCursor(data_lyr, ["SF_NEW", "EO_NEW"]) as cursor:
                    for row in cursor:
                        if row[1] != None:
                            sf_id = row[1] + "_" + word_list[word_index]
                            row[0] = sf_id
                        else:
                            sf_id = word_list[word_index]
                            row[0] = sf_id
                        cursor.updateRow(row)
                arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned a new SF: " + sf_id + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
                print("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned a new SF: " + sf_id + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
                word_index += 5
        observation_num += 1
        arcpy.SelectLayerByAttribute_management(data_lyr, "CLEAR_SELECTION")

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

##sf_stat = arcpy.Statistics_analysis("data_lyr","sf_stat",[["SF_ID","COUNT"],["SF_NEW","COUNT"]],["SF_ID","SF_NEW"])
##eo_stat = arcpy.Statistics_analysis("data_lyr","eo_stat",[["EO_ID","COUNT"],["EO_NEW","COUNT"]],["EO_ID","EO_NEW"])
##arcpy.JoinField_management("data_lyr","SF_ID",sf_stat,"SF_ID","COUNT_SF_ID")
##arcpy.JoinField_management("data_lyr","SF_NEW",sf_stat,"SF_NEW","COUNT_SF_NEW")
##arcpy.JoinField_management("data_lyr","EO_ID",eo_stat,"EO_ID","COUNT_EO_ID")
##arcpy.JoinField_management("data_lyr","EO_NEW",eo_stat,"EO_NEW","COUNT_EO_NEW")
##
##arcpy.AddField_management("data_lyr","single_SF_EO","TEXT")
##arcpy.AddField_management("data_lyr","single_visit_SF","TEXT")

##fields = ["COUNT_SF_ID","COUNT_SF_NEW","COUNT_EO_ID","COUNT_EO_NEW"]
##for field in fields:
##    with arcpy.da.UpdateCursor("data_lyr",field) as cursor:
##        for row in cursor:
##            if row[0] is None:
##                row[0] = 0
##                cursor.updateRow(row)
##            else:
##                pass
##with arcpy.da.UpdateCursor("data_lyr",["COUNT_SF_ID","COUNT_SF_NEW","COUNT_EO_ID","COUNT_EO_NEW","single_SF_EO","single_visit_SF"]) as cursor:
##    for row in cursor:
##        if row[2] > 1 or row[3] > 1:
##            row[4] = "N"
##            cursor.updateRow(row)
##        elif row[2] == 1 and row[1] > 0:
##            row[4] = "N"
##            cursor.updateRow(row)
##        elif row[3] == 1:
##            row[4] = "Y"
##            cursor.updateRow(row)
##        else:
##            row[4] = "M"
##            cursor.updateRow(row)
##        if row[0] > 0 or row[1] > 1:
##            row[5] = "N"
##            cursor.updateRow(row)
##        elif row[1] == 1:
##            row[5] = "Y"
##            cursor.updateRow(row)
##        else:
##            row[5] = "M"
##            cursor.updateRow(row)

arcpy.Delete_management("in_memory")
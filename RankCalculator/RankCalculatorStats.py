#-------------------------------------------------------------------------------
# Name:         RankCalculatorStats.pyt
# Purpose:      The Rank Calculator Stats toolbox contains custom Python tools that are
#               intended to increase the efficiency of calculating spatial characteristics that are needed
#               for entry into the rank calculator. Calculated spatial characteristics include number of observations,
#               number of occurrences, range extent, and area of occupancy.
# Version:      1.0
# Author:       MMOORE, Pennsylvania Natural Heritage Program
# Created:      11/21/2023
# Updates:
# Future Ideas:
#-------------------------------------------------------------------------------

# import libraries
import arcpy, os, datetime
from arcpy import env
from arcpy.sa import *

# set environmental variables
arcpy.env.overwriteOutput = True
arcpy.env.qualifiedFieldNames = False
arcpy.env.workspace = "memory"

class Toolbox(object):
    def __init__(self):
        self.label = "Rank Calculator Stats Toolbox"
        self.alias = "Rank Calculator Stats Toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [TerrestrialSpecies,AquaticSpecies]

class TerrestrialSpecies(object):
    def __init__(self):
        self.label = "Terrestrial Species"
        self.description = """Groups input species observations into occurrences and returns # of occurrences, range of extent, and area of occupancy for each species."""
        self.canRunInBackground = False
        self.category = "Rank Calculator Spatial Stats"

    def getParameterInfo(self):
        input_fc = arcpy.Parameter(
            displayName = "Input feature layers (if using multiple layers, they must be same geometry)",
            name = "input_fc",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            multiValue = "True",
            direction = "Input")

        species_code = arcpy.Parameter(
            displayName = "Species Identifier Field (values must match EO/SF species identifier field)",
            name = "species_code",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        species_code.parameterDependencies = [input_fc.name]

        lu_separation = arcpy.Parameter(
            displayName = "Separation Distance Field (units must be in kilometers)",
            name = "lu_separation",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        lu_separation.parameterDependencies = [input_fc.name]

        params = [input_fc,species_code,lu_separation]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        arcpy.AddMessage("""Welcome to the Source Feature and EO Assigner! This tool is designed to prepare a feature class or shapefile for bulk load into Biotics by assigning an existing or new SF and EO ID grouping variable to observations based on separation distance. This used to be done manually, so sit back and enjoy all the other work you can be doing instead of this!""")

        input_fc = params[0].valueAsText
        species_code = params[1].valueAsText
        lu_separation = params[2].valueAsText

        input_fcs = input_fc.split(';')

        for i in input_fcs:
            arcpy.AddMessage(i)

        # arcpy.env.workspace = "memory"
        #
        # arcpy.AddMessage("Preparing input data...")
        # #if using sf lines and polygons, all layers are buffered by 1m and merged. Otherwise, just points are buffered by 1m.
        # sfs_in = [eo_sourcept]
        # sfs_out = ["eo_sourcept1"]
        # if str(sf_include) == "True":
        #     if eo_sourceln:
        #         sfs_in.append(eo_sourceln)
        #         sfs_out.append("eo_sourcln1")
        #     if eo_sourcepy:
        #         sfs_in.append(eo_sourcepy)
        #         sfs_out.append("eo_sourcepy1")
        # else:
        #     pass
        # for sf_in,sf_out in zip(sfs_in,sfs_out):
        #     arcpy.Buffer_analysis(sf_in,sf_out,1)
        # sf_merge = arcpy.Merge_management(sfs_out, "sf_merge")
        # sf_lyr = arcpy.MakeFeatureLayer_management(sf_merge, "sf_lyr")
        #
        # #make list of all input layers given by user
        # data_in = []
        # data_out = []
        # if in_points:
        #     data_in.append(in_points)
        #     data_out.append("pts")
        # if in_lines:
        #     data_in.append(in_lines)
        #     data_out.append("lines")
        # if in_poly:
        #     data_in.append(in_poly)
        #     data_out.append("polys")
        #
        # #add join id to input features, buffer by 1m, and merge layers
        # join_id = 1
        # for i,o in zip(data_in,data_out):
        #     arcpy.AddField_management(i,"join_id","TEXT")
        #     with arcpy.da.UpdateCursor(i,"join_id") as cursor:
        #         for row in cursor:
        #             row[0]=str(join_id)
        #             cursor.updateRow(row)
        #             join_id+=1
        #     arcpy.Buffer_analysis(i,o,1)
        # data_merge = arcpy.Merge_management(data_out,os.path.join("memory","data_merge"))
        # data_lyr = arcpy.MakeFeatureLayer_management(data_merge,"data_lyr")
        #
        # #updated to account for double and float field types
        # if arcpy.ListFields(data_lyr,species_code)[0].type == 'Integer' or arcpy.ListFields(data_lyr,species_code)[0].type == 'Double' or arcpy.ListFields(data_lyr,species_code)[0].type == 'Float':
        #     species_query = "{}={}"
        # else:
        #     species_query = "{}='{}'"
        # if arcpy.ListFields(eo_reps,species_code_field)[0].type == 'Integer' or arcpy.ListFields(eo_reps,species_code_field)[0].type == 'Double' or arcpy.ListFields(eo_reps,species_code_field)[0].type == 'Float':
        #     eo_species_query = "{}={}"
        # else:
        #     eo_species_query = "{}='{}'"
        #
        # #get name of true OID field
        # objectid_field = arcpy.Describe(data_lyr).OIDFieldName
        #
        # #create feature layers to allow for selections
        # eo_reps = arcpy.MakeFeatureLayer_management(eo_reps, "eo_reps")
        #
        # #add EO/SF ID fields if they do not already exist
        # add_fields_text = ["SF_ID","SF_NEW","EO_ID","EO_NEW"]
        # for field in add_fields_text:
        #     if len(arcpy.ListFields(data_lyr,field)) == 0:
        #         arcpy.AddField_management(data_lyr,field,"TEXT","","",50)
        #     else:
        #         pass
        # add_fields_int = ["UNIQUEID"]
        # for field in add_fields_int:
        #     if len(arcpy.ListFields(data_lyr,field)) == 0:
        #         arcpy.AddField_management(data_lyr,field,"LONG")
        #     else:
        #         pass
        #
        # #set word index to assign words to new EO groups
        # word_index = 1
        # observation_num = 1
        #
        # arcpy.AddMessage("Assigning EO IDs...")
        # #get total records in data_lyr for progress reporting messages
        # total_obs = arcpy.GetCount_management(data_lyr)
        # #start assigning loop
        # search_fields = [objectid_field, "EO_ID", "EO_NEW", species_code, lu_separation]
        # if loc_uncert_dist:
        #     search_fields.append(loc_uncert)
        #     search_fields.append(loc_uncert_dist)
        # with arcpy.da.SearchCursor(data_lyr, search_fields) as cursor:
        #     for row in cursor:
        #         objectid = row[0]
        #         #if one of the EOID fields already have a value, continue on to next feature
        #         if row[2] != None or (row[1] != None and row[1] != 0):
        #             arcpy.AddMessage("ObjectID " + str(objectid) + " EO Observation number " + str(observation_num) + "/" + str(total_obs) + " has already been assigned to a new or existing EO.")
        #             pass
        #         else:
        #             sname = row[3]
        #             # convert separation distance into meters
        #             distance = (row[4]*1000)
        #             #add LU distance if LU type is estimated
        #             if loc_uncert_dist:
        #                 if row[5].lower() == "estimated":
        #                     distance = distance+row[6]
        #                 else:
        #                     pass
        #             else:
        #                 pass
        #             #convert distance into string value as needed for select by tool
        #             distance = str(distance)+" METERS"
        #
        #             #select feature and assign sname and separation distance variables
        #             arcpy.SelectLayerByAttribute_management(data_lyr, "NEW_SELECTION", "{}={}".format(objectid_field,objectid))
        #             #check for existing EO reps within separation distance of feature
        #             arcpy.SelectLayerByAttribute_management(eo_reps, 'NEW_SELECTION', eo_species_query.format(species_code_field,sname))
        #             arcpy.SelectLayerByLocation_management(eo_reps, "WITHIN_A_DISTANCE", data_lyr, distance-1, "SUBSET_SELECTION")
        #             #check for selection on eo_reps layer - if there is a selection, get eoid, select all observations within the separation distance, and assign existing eoid to selected features
        #             selection_num = arcpy.Describe(eo_reps).fidset
        #             if selection_num is not u'':
        #                 with arcpy.da.SearchCursor(eo_reps, eo_id_field) as cursor:
        #                     #eoid = sorted({row[0] for row in cursor}, reverse=True)[0] #use this if keeping newest EO
        #                     eoid = ",".join(sorted({str(int(row[0])) for row in cursor})) #use this if filling with EOIDs of all EOs within separation distance
        #                 #set arbitrary unequal counts to start while loop
        #                 countBefore = 0
        #                 countAfter = 1
        #                 while(countBefore!=countAfter):
        #                     countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
        #                     arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, distance-2, "ADD_TO_SELECTION")
        #                     arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", species_query.format(species_code,sname))
        #                     countAfter = int(arcpy.GetCount_management("data_lyr").getOutput(0))
        #                 with arcpy.da.UpdateCursor(data_lyr, "EO_ID") as cursor:
        #                     for row in cursor:
        #                         row[0] = eoid
        #                         cursor.updateRow(row)
        #                 arcpy.SelectLayerByAttribute_management(data_lyr, "CLEAR_SELECTION")
        #                 arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned an existing EO: " + str(eoid) + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
        #             #if no existing EOs selected within separation distance, select all observations within the separation distance and assign new random word
        #             else:
        #                 countBefore = 0
        #                 countAfter = 1
        #                 while(countBefore!=countAfter):
        #                     countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
        #                     arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, distance-2, "ADD_TO_SELECTION")
        #                     arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", species_query.format(species_code,sname))
        #                     countAfter = int(arcpy.GetCount_management("data_lyr").getOutput(0))
        #                 with arcpy.da.UpdateCursor(data_lyr, "EO_NEW") as cursor:
        #                     for row in cursor:
        #                         row[0] = "new_eo_" + str(word_index) #word_list[word_index]
        #                         cursor.updateRow(row)
        #                 arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned a new EO: " + str(word_index) + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
        #                 word_index += 1
        #         observation_num += 1
        #         arcpy.SelectLayerByAttribute_management(data_lyr, "CLEAR_SELECTION")
        #
        # arcpy.AddMessage("Assigning SF IDs...")
        # observation_num = 1
        # search_fields = [objectid_field, "SF_ID", "SF_NEW", species_code]
        # with arcpy.da.SearchCursor(data_lyr, search_fields) as cursor:
        #     for row in cursor:
        #         objectid = row[0]
        #         if row[2] != None or (row[1] != None and row[1] != 0):
        #             arcpy.AddMessage("ObjectID " + str(objectid) + " SF Observation number " + str(observation_num) + "/" + str(total_obs) + " has already been assigned to a new or existing SF.")
        #         else:
        #             sname = row[3]
        #
        #             #check for existing SFs within 9m of feature (8m because of 1m buffer on SF layers)
        #             arcpy.SelectLayerByAttribute_management(data_lyr, "NEW_SELECTION", "{}={}".format(objectid_field, objectid))
        #             arcpy.SelectLayerByAttribute_management(sf_lyr, 'NEW_SELECTION', eo_species_query.format(species_code_field,sname))
        #             arcpy.SelectLayerByLocation_management(sf_lyr, "WITHIN_A_DISTANCE", data_lyr, "7 METERS", "SUBSET_SELECTION")
        #             #check for selection on sf_merge layer - if there is a selection, get sfid, select all observations within the separation distance, and assign existing eoid to selected features
        #             if arcpy.Describe('sf_lyr').fidset is not u'':
        #                 with arcpy.da.SearchCursor('sf_lyr', sf_id_field) as cursor:
        #                     #sfid = sorted({row[0] for row in cursor}, reverse=True)[0] #use this line if you want to use the newest SF ID within separation distance
        #                     sfid = ",".join(sorted({str(int(row[0])) for row in cursor})) # use this line if you want to list all SF IDs within separation distance
        #                 countBefore = 0
        #                 countAfter = 1
        #                 while(countBefore!=countAfter):
        #                     countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
        #                     arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, "7 METERS", "ADD_TO_SELECTION")
        #                     arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", species_query.format(species_code,sname))
        #
        #                     countAfter = int(arcpy.GetCount_management("data_lyr").getOutput(0))
        #                 with arcpy.da.UpdateCursor(data_lyr, "SF_ID") as cursor:
        #                     for row in cursor:
        #                         row[0] = sfid
        #                         cursor.updateRow(row)
        #                 arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned an existing SF: " + str(sfid) + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
        #             #if no existing SFs selected within separation distance, select all observations within the separation distance and assign new random word
        #             else:
        #                 countBefore = 0
        #                 countAfter = 1
        #                 while(countBefore!=countAfter):
        #                     countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
        #                     arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, "7 METERS", "ADD_TO_SELECTION")
        #                     arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", species_query.format(species_code,sname))
        #                     countAfter = int(arcpy.GetCount_management("data_lyr").getOutput(0))
        #                 with arcpy.da.UpdateCursor(data_lyr, ["SF_NEW", "EO_NEW"]) as cursor:
        #                     for row in cursor:
        #                         if row[1] != None:
        #                             sf_id = "new_sf_"+str(word_index)
        #                             row[0] = sf_id
        #                         else:
        #                             sf_id = "new_sf_"+str(word_index)
        #                             row[0] = sf_id
        #                         cursor.updateRow(row)
        #                 arcpy.AddMessage("ObjectID " + str(objectid)  + ", along with " + str(countAfter-1) + " observations were assigned a new SF: " + sf_id + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
        #                 word_index += 1
        #         observation_num += 1
        #         arcpy.SelectLayerByAttribute_management(data_lyr, "CLEAR_SELECTION")
        #
        # #create unique id value for each unique source feature
        # i = 1
        # with arcpy.da.SearchCursor(data_lyr, "SF_ID") as cursor:
        #     sfid1 = sorted({row[0] for row in cursor if row[0] is not None})
        # with arcpy.da.SearchCursor(data_lyr, "SF_NEW") as cursor:
        #     sfid2 = sorted({row[0] for row in cursor if row[0] is not None})
        # sfid = sfid1 + sfid2
        # sfid = [x for x in sfid if x is not None]
        # for sf in sfid:
        #     with arcpy.da.UpdateCursor(data_lyr, ["SF_ID", "SF_NEW", "UNIQUEID"]) as cursor:
        #         for row in cursor:
        #             if row[0] == sf:
        #                 row[2] = i
        #                 cursor.updateRow(row)
        #             elif row[1] == sf:
        #                 row[2] = i
        #                 cursor.updateRow(row)
        #             else:
        #                 pass
        #     i += 1
        #
        # add_fields=add_fields_int+add_fields_text
        # for data in data_in:
        #     arcpy.AddMessage(data)
        #     arcpy.AddMessage(data_lyr)
        #     arcpy.management.JoinField(data,"join_id",os.path.join("memory","data_merge"),"join_id",add_fields)
        #     arcpy.DeleteField_management(data,"join_id")
        #     arcpy.DeleteField_management(data,"buff_dist")
        #
        # arcpy.Delete_management("memory")
        # return

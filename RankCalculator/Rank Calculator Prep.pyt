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
import arcpy, os
from datetime import datetime
from arcpy import env
from arcpy.sa import *

# set environmental variables
arcpy.env.overwriteOutput = True
arcpy.env.qualifiedFieldNames = False
arcpy.env.workspace = "memory"

now = datetime.now()  # current date and time
date_time = now.strftime("%Y%m%d%H%M%S")

def count_selected_features(layer):
    # Check if there is a selection
    if arcpy.Describe(layer).FIDSet:
        # Count the selected features
        result = arcpy.GetCount_management(layer)
        count = int(result.getOutput(0))
    else:
        # No selection, return 0
        count = 0
    return count

class Toolbox(object):
    def __init__(self):
        self.label = "Rank Calculator Stats Toolbox"
        self.alias = "Rank Calculator Stats Toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [TerrestrialGrouping,AquaticGrouping,TerrestrialRankCalculatorStats,AquaticRankCalculatorStats]

class TerrestrialGrouping(object):
    def __init__(self):
        self.label = "Occurrence Grouping - Terrestrial and Lentic Species"
        self.description = """Groups input species observations into occurrences and returns # of occurrences, range of extent, and area of occupancy for each species."""
        self.canRunInBackground = False
        self.category = "Occurrence Grouping"

    def getParameterInfo(self):
        input_fc = arcpy.Parameter(
            displayName = "Input feature layers (if using multiple layers, they must be same geometry)",
            name = "input_fc",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            multiValue = "True",
            direction = "Input")

        species_code = arcpy.Parameter(
            displayName = "Species Identifier Field (must be consistent across all input datasets)",
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

        output_gdb = arcpy.Parameter(
            displayName = "Output geodatabase for merged dataset and output table",
            name = "output_gdb",
            datatype = "DEWorkspace",
            parameterType = "Required",
            direction = "Input")

        params = [input_fc,species_code,lu_separation,output_gdb]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        input_fc = params[0].valueAsText
        species_code = params[1].valueAsText
        lu_separation = params[2].valueAsText
        output_gdb = params[3].valueAsText

        input_fcs = input_fc.split(';')

        data_merge = arcpy.Merge_management(input_fcs,os.path.join(output_gdb,"Occurrence_Groupings_Terrestrial_"+date_time))
        data_lyr = arcpy.MakeFeatureLayer_management(data_merge, "data_lyr")

        #updated to account for double and float field types
        if arcpy.ListFields(data_lyr,species_code)[0].type == 'Integer' or arcpy.ListFields(data_lyr,species_code)[0].type == 'Double' or arcpy.ListFields(data_lyr,species_code)[0].type == 'Float':
            species_query = "{}={}"
        else:
            species_query = "{}='{}'"

        # add field to identify occurrence grouping
        arcpy.AddField_management(data_lyr,"occurrence_id","LONG","","",25)

        objectid_field = arcpy.Describe(data_lyr).OIDFieldName

        # set index for tiebreak
        tiebreak = 1
        observation_num = 1

        arcpy.AddMessage("Grouping observations...")
        #get total records in data_lyr for progress reporting messages
        total_obs = arcpy.GetCount_management(data_lyr)
        #start assigning loop
        search_fields = [objectid_field, "occurrence_id", species_code, lu_separation]
        with arcpy.da.SearchCursor(data_lyr, search_fields) as cursor:
            for row in cursor:
                objectid = row[0]
                #if one of the EOID fields already have a value, continue on to next feature
                if row[1] is not None:
                    arcpy.AddMessage("ObjectID " + str(objectid) + " " + str(observation_num) + "/" + str(total_obs) + " has already been assigned to a new or existing EO.")
                    pass
                else:
                    sname = row[2]
                    # convert separation distance into meters
                    distance = (row[3]*1000)
                    #convert distance into string value as needed for select by tool
                    distance = str(distance)+" METERS"

                    #select feature and assign sname and separation distance variables
                    arcpy.SelectLayerByAttribute_management(data_lyr, "NEW_SELECTION", "{}={}".format(objectid_field,objectid))
                    countBefore = 0
                    countAfter = 1
                    while countBefore != countAfter:
                        countBefore = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                        arcpy.SelectLayerByLocation_management(data_lyr, "WITHIN_A_DISTANCE", data_lyr, distance, "ADD_TO_SELECTION")
                        arcpy.SelectLayerByAttribute_management(data_lyr, "SUBSET_SELECTION", species_query.format(species_code,sname))
                        countAfter = int(arcpy.GetCount_management("data_lyr").getOutput(0))
                    with arcpy.da.UpdateCursor(data_lyr, "occurrence_id") as cursor:
                        for row in cursor:
                            row[0] = tiebreak
                            cursor.updateRow(row)
                    arcpy.AddMessage("ObjectID " + str(objectid) + ", along with " + str(countAfter-1) + " observations were assigned to group: " + str(tiebreak) + ". " + str(observation_num) + "/" + str(total_obs) + " completed.")
                    tiebreak += 1
                observation_num += 1
                arcpy.SelectLayerByAttribute_management(data_lyr, "CLEAR_SELECTION")

class AquaticGrouping(object):
    def __init__(self):
        self.label = "Occurrence Grouping - Riverine Species"
        self.description = """Groups input species observations into occurrences based on upstream/downstream distances along a stream network. Requires network dataset to be built on stream layer."""
        self.canRunInBackground = False
        self.category = "Occurrence Grouping"

    def getParameterInfo(self):
        input_fc = arcpy.Parameter(
            displayName = "Input feature layers (if using multiple layers, they must be same geometry)",
            name = "input_fc",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            multiValue = "True",
            direction = "Input")

        species_code = arcpy.Parameter(
            displayName = "Species Identifier Field (must be consistent across all input datasets)",
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

        network = arcpy.Parameter(
            displayName = "Network dataset built on NHD flowlines",
            name = "network",
            datatype = "GPNetworkDatasetLayer",
            parameterType = "Required",
            direction = "Input")
        network.value = r'W:\Heritage\Heritage_Data\Heritage_Data_Tools\AquaticNetworkData.gdb\Aquatic_network\PA_network_ND'

        snap_dist = arcpy.Parameter(
            displayName = "Snap distance in meters (distance to flowline beyond which observations will not be assigned/grouped)",
            name = "snap_dist",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        snap_dist.value = "100"

        output_gdb = arcpy.Parameter(
            displayName = "Output geodatabase for merged dataset and output table",
            name = "output_gdb",
            datatype = "DEWorkspace",
            parameterType = "Required",
            direction = "Input")

        params = [input_fc,species_code,lu_separation,network,snap_dist,output_gdb]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        input_fc = params[0].valueAsText
        species_code = params[1].valueAsText
        lu_separation = params[2].valueAsText
        network = params[3].valueAsText
        snap_dist = params[4].valueAsText
        output_gdb = params[5].valueAsText

        input_fcs = input_fc.split(';')

        data_merge = arcpy.Merge_management(input_fcs,os.path.join(output_gdb,"Occurrence_Groupings_Riverine_"+date_time))
        data_lyr = arcpy.MakeFeatureLayer_management(data_merge, "data_lyr")

        join_id = 1
        if len(arcpy.ListFields(data_lyr,"join_id")) == 0:
            arcpy.AddField_management(data_lyr,"join_id","TEXT")
        with arcpy.da.UpdateCursor(data_lyr,"join_id") as cursor:
            for row in cursor:
                row[0] = str(join_id)
                cursor.updateRow(row)
                join_id += 1

        # add field to identify occurrence grouping
        arcpy.AddField_management(data_lyr,"occurrence_id","LONG","","",25)

        # updated to account for double and float field types
        if arcpy.ListFields(data_lyr,species_code)[0].type == 'Integer' or arcpy.ListFields(data_lyr,species_code)[0].type == 'Double' or arcpy.ListFields(data_lyr,species_code)[0].type == 'Float':
            species_query = "{}={}"
        else:
            species_query = "{}='{}'"

        #create lookup dictionary of separation distances from lookup table
        lu_sep = {f[0]: f[1] for f in arcpy.da.SearchCursor(data_lyr, [species_code,lu_separation])}

        #create list of species
        with arcpy.da.SearchCursor(data_lyr,species_code) as cursor:
            species_list = sorted({row[0] for row in cursor})

        total_species = len(species_list)
        species_rep = 1
        group_id = 1
        for species in species_list:
            arcpy.AddMessage("Assigning occurrence IDs for species "+str(species)+": "+str(species_rep)+"/"+str(total_species))
            species_rep += 1
            s = arcpy.FeatureClassToFeatureClass_conversion(data_lyr,"memory","s",species_query.format(species_code,species))
            for k,v in lu_sep.items():
                if k == species:
                    distance = v*1000

            # arcpy.AddMessage("Creating service area line layer for " +str(species) + " separation distance grouping")
            sp_service_area_lyr = arcpy.na.MakeServiceAreaLayer(network, "sp_service_area_lyr", "Length", "TRAVEL_FROM", distance, polygon_type="NO_POLYS", line_type="TRUE_LINES", overlap="OVERLAP")
            sp_service_area_lyr = sp_service_area_lyr.getOutput(0)
            subLayerNames = arcpy.na.GetNAClassNames(sp_service_area_lyr)
            sp_facilitiesLayerName = subLayerNames["Facilities"]
            sp_serviceLayerName = subLayerNames["SALines"]
            arcpy.na.AddLocations(sp_service_area_lyr, sp_facilitiesLayerName, s, "", snap_dist)
            try:
                arcpy.na.Solve(sp_service_area_lyr)
            except:
                arcpy.AddMessage("No species occurrences were within the snap distance of the network flowlines for species: "+str(species))
                pass
            else:
                sp_lines = sp_service_area_lyr.listLayers(sp_serviceLayerName)[0]
                sp_flowline_clip = arcpy.CopyFeatures_management(sp_lines, "sp_service_area")
                sp_flowline_buff = arcpy.Buffer_analysis(sp_flowline_clip, "sp_flowline_buff", "1 Meter", "FULL", "ROUND")
                single_part = arcpy.Dissolve_management(sp_flowline_buff, "single_part", multi_part="SINGLE_PART")

                #create unique group id
                arcpy.AddField_management(single_part,"group_id","LONG")
                with arcpy.da.UpdateCursor(single_part,"group_id") as cursor:
                    for row in cursor:
                        row[0] = group_id
                        cursor.updateRow(row)
                        group_id += 1

                sp_join = arcpy.SpatialJoin_analysis(target_features=s,join_features=single_part,out_feature_class="sp_join",join_operation="JOIN_ONE_TO_MANY",join_type="KEEP_ALL",match_option="INTERSECT",search_radius="200 METERS")

                id_fill = {f[0]: [f[1]] for f in arcpy.da.SearchCursor(sp_join, ["join_id", "group_id"])}

                with arcpy.da.UpdateCursor(data_merge,["join_id","occurrence_id"]) as cursor:
                    for row in cursor:
                        for k,v in id_fill.items():
                            if k == row[0] and v[0] is not None:
                                row[1] = v[0]
                                cursor.updateRow(row)
                            else:
                                pass

class TerrestrialRankCalculatorStats(object):
    def __init__(self):
        self.label = "Rank Calculator Stats - Terrestrial"
        self.description = """Takes the output from the occurrence grouping tool and returns # of occurrences, range of extent, and area of occupancy for each species."""
        self.canRunInBackground = False
        self.category = "Rank Calculator Stats"

    def getParameterInfo(self):
        input_fc = arcpy.Parameter(
            displayName = "Occurrence layer",
            name = "input_fc",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            multiValue = "False",
            direction = "Input")

        grouping_field = arcpy.Parameter(
            displayName = "Occurrence grouping field (if there is not a field indicating occurrence group, leave blank)",
            name = "grouping_field",
            datatype = "Field",
            parameterType = "Optional",
            direction = "Input")
        grouping_field.parameterDependencies = [input_fc.name]

        species_code = arcpy.Parameter(
            displayName = "Species Identifier Field",
            name = "species_code",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        species_code.parameterDependencies = [input_fc.name]

        output_gdb = arcpy.Parameter(
            displayName = "Output geodatabase output table",
            name = "output_gdb",
            datatype = "DEWorkspace",
            parameterType = "Required",
            direction = "Input")

        params = [input_fc,grouping_field,species_code,output_gdb]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        input_fc = params[0].valueAsText
        grouping_field = params[1].valueAsText
        species_code = params[2].valueAsText
        output_gdb = params[3].valueAsText

        arcpy.AddMessage("creating table")
        rank_stats = arcpy.CreateTable_management(output_gdb,"RankCalculatorStats_Terrestrial_"+date_time)
        field_type = arcpy.ListFields(input_fc,species_code)[0].type
        field_length = arcpy.ListFields(input_fc, species_code)[0].length
        arcpy.AddMessage("adding fields")
        arcpy.AddField_management(rank_stats,species_code,field_type,"","",field_length)
        arcpy.AddField_management(rank_stats,"range_extent_km2","Double")
        arcpy.AddField_management(rank_stats,"occupancy_area_km2","Double")
        arcpy.AddField_management(rank_stats,"occurrence_num","LONG")
        arcpy.AddField_management(rank_stats,"obs_num","LONG")

########################################################################################################################
## Calculate occurrence number and observation number for each species
########################################################################################################################
        if grouping_field:
            arcpy.AddMessage("calculating stats with grouping field")
            sum_stat = arcpy.Statistics_analysis(input_fc, os.path.join("memory", "sum_stat"), [[grouping_field, "Unique"]], [species_code])
            occ_field = "UNIQUE_"+grouping_field
        else:
            arcpy.AddMessage("calculating stats without grouping field")
            sum_stat = arcpy.Statistics_analysis(input_fc, os.path.join("memory", "sum_stat"), [[species_code, "Count"]], [species_code])
            occ_field = "COUNT_" + species_code

        arcpy.AddMessage("creating insert list")
        row_insert = []
        with arcpy.da.SearchCursor(sum_stat, [species_code, "FREQUENCY", occ_field]) as cursor:
            for row in cursor:
                values = tuple([row[0], row[1], row[2]])
                row_insert.append(values)
        arcpy.AddMessage("inserting list")
        for insert in row_insert:
            with arcpy.da.InsertCursor(rank_stats, [species_code, "obs_num", "occurrence_num"]) as cursor:
                cursor.insertRow(insert)

########################################################################################################################
## Calculate range extent for each species
########################################################################################################################
        arcpy.AddMessage("calculating range extent")
        convex_hull = arcpy.MinimumBoundingGeometry_management(input_fc,os.path.join("memory","convex_hull"),"CONVEX_HULL","LIST",species_code)
        convex_dict = {row[0]:round(row[1].getArea("GEODESIC","SQUAREKILOMETERS"),3) for row in arcpy.da.SearchCursor(convex_hull, [species_code,"SHAPE@"])}
        with arcpy.da.UpdateCursor(rank_stats,[species_code,"range_extent_km2"]) as cursor:
            for row in cursor:
                for k,v in convex_dict.items():
                    if k == row[0]:
                        row[1] = v
                        cursor.updateRow(row)

########################################################################################################################
## Calculate area of occupancy for each species
########################################################################################################################

        arcpy.AddMessage("calculating area of extent")
        grid = arcpy.GenerateTessellation_management(os.path.join("memory","grid"),input_fc,"SQUARE","4 SquareKilometers")
        grid_lyr = arcpy.MakeFeatureLayer_management(grid,"grid_lyr")
        input_lyr = arcpy.MakeFeatureLayer_management(input_fc,"input_lyr")

        #updated to account for double and float field types
        if arcpy.ListFields(input_lyr,species_code)[0].type == 'Integer' or arcpy.ListFields(input_lyr,species_code)[0].type == 'Double' or arcpy.ListFields(input_lyr,species_code)[0].type == 'Float':
            species_query = "{}={}"
        else:
            species_query = "{}='{}'"

        AOO_dict = {}
        species_list = sorted({row[0] for row in arcpy.da.SearchCursor(rank_stats,species_code)})
        for species in species_list:
            arcpy.SelectLayerByAttribute_management(input_lyr,"NEW_SELECTION",species_query.format(species_code,species))
            arcpy.SelectLayerByLocation_management(grid_lyr,"INTERSECT",input_lyr,"","NEW_SELECTION")

            count = count_selected_features(grid_lyr)
            km2 = count*4
            AOO_dict[species] = km2

        with arcpy.da.UpdateCursor(rank_stats,[species_code,"occupancy_area_km2"]) as cursor:
            for row in cursor:
                for k,v in AOO_dict.items():
                    if k == row[0]:
                        row[1] = v
                        cursor.updateRow(row)

class AquaticRankCalculatorStats(object):
    def __init__(self):
        self.label = "Rank Calculator Stats - Aquatic"
        self.description = """Takes the output from the occurrence grouping tool and returns # of occurrences, range of extent, and area of occupancy for each species."""
        self.canRunInBackground = False
        self.category = "Rank Calculator Stats"

    def getParameterInfo(self):
        input_fc = arcpy.Parameter(
            displayName = "Occurrence layer",
            name = "input_fc",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            multiValue = "False",
            direction = "Input")

        grouping_field = arcpy.Parameter(
            displayName = "Occurrence grouping field (if there is not a field indicating occurrence group, leave blank)",
            name = "grouping_field",
            datatype = "Field",
            parameterType = "Optional",
            direction = "Input")
        grouping_field.parameterDependencies = [input_fc.name]

        species_code = arcpy.Parameter(
            displayName = "Species Identifier Field",
            name = "species_code",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        species_code.parameterDependencies = [input_fc.name]

        huc08 = arcpy.Parameter(
            displayName = "HUC08 watershed layer",
            name = "huc08",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            multiValue = "False",
            direction = "Input")

        output_gdb = arcpy.Parameter(
            displayName = "Output geodatabase for output table",
            name = "output_gdb",
            datatype = "DEWorkspace",
            parameterType = "Required",
            direction = "Input")

        params = [input_fc,grouping_field,species_code,huc08,output_gdb]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, params):
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        input_fc = params[0].valueAsText
        grouping_field = params[1].valueAsText
        species_code = params[2].valueAsText
        huc08 = params[3].valueAsText
        output_gdb = params[4].valueAsText

        arcpy.AddMessage("creating table")
        rank_stats = arcpy.CreateTable_management(output_gdb,"RankCalculatorStats_Aquatic_"+date_time)
        field_type = arcpy.ListFields(input_fc,species_code)[0].type
        field_length = arcpy.ListFields(input_fc, species_code)[0].length
        arcpy.AddMessage("adding fields")
        arcpy.AddField_management(rank_stats,species_code,field_type,"","",field_length)
        arcpy.AddField_management(rank_stats,"range_extent_km2","Double")
        arcpy.AddField_management(rank_stats,"occupancy_area_km2","Double")
        arcpy.AddField_management(rank_stats,"occurrence_num","LONG")
        arcpy.AddField_management(rank_stats,"obs_num","LONG")

########################################################################################################################
## Calculate occurrence number and observation number for each species
########################################################################################################################
        if grouping_field:
            arcpy.AddMessage("calculating stats with grouping field")
            sum_stat = arcpy.Statistics_analysis(input_fc, os.path.join("memory", "sum_stat"), [[grouping_field, "Unique"]], [species_code])
            occ_field = "UNIQUE_"+grouping_field
        else:
            arcpy.AddMessage("calculating stats without grouping field")
            sum_stat = arcpy.Statistics_analysis(input_fc, os.path.join("memory", "sum_stat"), [[species_code, "Count"]], [species_code])
            occ_field = "COUNT_" + species_code

        arcpy.AddMessage("creating insert list")
        row_insert = []
        with arcpy.da.SearchCursor(sum_stat, [species_code, "FREQUENCY", occ_field]) as cursor:
            for row in cursor:
                values = tuple([row[0], row[1], row[2]])
                row_insert.append(values)
        arcpy.AddMessage("inserting list")
        for insert in row_insert:
            with arcpy.da.InsertCursor(rank_stats, [species_code, "obs_num", "occurrence_num"]) as cursor:
                cursor.insertRow(insert)

########################################################################################################################
## Calculate range extent for each species
########################################################################################################################

        arcpy.AddMessage("calculating range extent")

        huc_lyr = arcpy.MakeFeatureLayer_management(huc08,"huc_lyr")
        input_lyr = arcpy.MakeFeatureLayer_management(input_fc,"input_lyr")

        #updated to account for double and float field types
        if arcpy.ListFields(input_lyr,species_code)[0].type == 'Integer' or arcpy.ListFields(input_lyr,species_code)[0].type == 'Double' or arcpy.ListFields(input_lyr,species_code)[0].type == 'Float':
            species_query = "{}={}"
        else:
            species_query = "{}='{}'"

        range_dict = {}
        species_list = sorted({row[0] for row in arcpy.da.SearchCursor(rank_stats,species_code)})
        for species in species_list:
            arcpy.SelectLayerByAttribute_management(input_lyr,"NEW_SELECTION",species_query.format(species_code,species))
            arcpy.SelectLayerByLocation_management(huc_lyr,"INTERSECT",input_lyr,"","NEW_SELECTION")
            # calculate area in km2 for all selected huc08 watersheds
            huc_area = sum(row[0].getArea('GEODESIC', 'SQUAREKILOMETERS') for row in arcpy.da.SearchCursor(huc_lyr, "SHAPE@"))
            range_dict[species] = huc_area

        with arcpy.da.UpdateCursor(rank_stats,[species_code,"range_extent_km2"]) as cursor:
            for row in cursor:
                for k,v in range_dict.items():
                    if k == row[0]:
                        row[1] = v
                        cursor.updateRow(row)

########################################################################################################################
## Calculate area of occupancy for each species
########################################################################################################################

        arcpy.AddMessage("calculating area of extent")
        grid = arcpy.GenerateTessellation_management(os.path.join("memory","grid"),input_fc,"SQUARE","4 SquareKilometers")
        grid_lyr = arcpy.MakeFeatureLayer_management(grid,"grid_lyr")
        input_lyr = arcpy.MakeFeatureLayer_management(input_fc,"input_lyr")

        #updated to account for double and float field types
        if arcpy.ListFields(input_lyr,species_code)[0].type == 'Integer' or arcpy.ListFields(input_lyr,species_code)[0].type == 'Double' or arcpy.ListFields(input_lyr,species_code)[0].type == 'Float':
            species_query = "{}={}"
        else:
            species_query = "{}='{}'"

        AOO_dict = {}
        species_list = sorted({row[0] for row in arcpy.da.SearchCursor(rank_stats,species_code)})
        for species in species_list:
            arcpy.SelectLayerByAttribute_management(input_lyr,"NEW_SELECTION",species_query.format(species_code,species))
            arcpy.SelectLayerByLocation_management(grid_lyr,"INTERSECT",input_lyr,"","NEW_SELECTION")

            count = count_selected_features(grid_lyr)
            km2 = count*4
            AOO_dict[species] = km2

        with arcpy.da.UpdateCursor(rank_stats,[species_code,"occupancy_area_km2"]) as cursor:
            for row in cursor:
                for k,v in AOO_dict.items():
                    if k == row[0]:
                        row[1] = v
                        cursor.updateRow(row)

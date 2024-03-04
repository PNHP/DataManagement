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
import sys

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
        self.tools = [TerrestrialGrouping,AquaticGrouping,RankCalculatorStats]

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

        output_fc = arcpy.Parameter(
            displayName = "Output geodatabase location and feature class name",
            name = "output_gdb",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Output")

        params = [input_fc,species_code,lu_separation,output_fc]
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
        output_fc = params[3].valueAsText

        input_fcs = input_fc.split(';')

        data_merge = arcpy.Merge_management(input_fcs,output_fc)
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

        output_fc = arcpy.Parameter(
            displayName = "Output location and name for merged dataset",
            name = "output_fc",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Output")

        params = [input_fc,species_code,lu_separation,network,snap_dist,output_fc]
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
        output_fc = params[5].valueAsText

        input_fcs = input_fc.split(';')

        data_merge = arcpy.Merge_management(input_fcs,output_fc)
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
                    distance = (v*1000)/2

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

                sp_join = arcpy.SpatialJoin_analysis(target_features=s,join_features=single_part,out_feature_class="sp_join",join_operation="JOIN_ONE_TO_MANY",join_type="KEEP_ALL",match_option="INTERSECT",search_radius= str(snap_dist) + " METERS")

                id_fill = {f[0]: [f[1]] for f in arcpy.da.SearchCursor(sp_join, ["join_id", "group_id"])}

                with arcpy.da.UpdateCursor(data_merge,["join_id","occurrence_id"]) as cursor:
                    for row in cursor:
                        for k,v in id_fill.items():
                            if k == row[0] and v[0] is not None:
                                row[1] = v[0]
                                cursor.updateRow(row)
                            else:
                                pass

class RankCalculatorStats(object):
    def __init__(self):
        self.label = "Rank Calculator Stats"
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
            displayName = "Optional - occurrence grouping field (if there is not a field indicating occurrence group, leave blank)",
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

        range_type = arcpy.Parameter(
            displayName = "Range Extent Type",
            name = "range_type",
            datatype = "GPString",
            parameterType = "Required",
            multiValue = "False",
            direction = "Input")
        range_type.filter.type = "ValueList"
        range_type.filter.list = ["Convex Hull","Occupied HUC Watershed"]

        huc08 = arcpy.Parameter(
            displayName = "HUC watershed layer",
            name = "huc08",
            datatype = "GPFeatureLayer",
            multiValue = "False",
            direction = "Input")

        clip_lyr = arcpy.Parameter(
            displayName = "Optional - subnational boundary used to clip range extent (if not chosen, the range extent may go beyond the subnational boundary)",
            name = "clip_lyr",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            multiValue = "False",
            direction = "Input")

        grid_sz = arcpy.Parameter(
            displayName = "Grid size for Area of Occupancy Calculation",
            name = "grid_sz",
            datatype = "GPString",
            parameterType = "Required",
            multiValue = "False",
            direction = "Input")
        grid_sz.filter.type = "ValueList"
        grid_sz.filter.list = ["2x2 km2 grid","1x1 km2 grid"]

        output_tbl = arcpy.Parameter(
            displayName = "Output location and name of output table",
            name = "output_tbl",
            datatype = "DETable",
            parameterType = "Required",
            direction = "Output")

        extent_output = arcpy.Parameter(
            displayName = "Optional - output location and name of range extent polygons used for calculation (select feature class location and name if you wish to see the range extent polygons upon which calculations are based)",
            name = "extent_output",
            datatype = "GPFeatureLayer",
            parameterType = "Optional",
            direction = "Output")

        params = [input_fc,grouping_field,species_code,range_type,huc08,clip_lyr,grid_sz,output_tbl,extent_output]
        return params

    def isLicensed(self):
        return True

    def initializeParameters(self):
        return

    def updateParameters(self, params):
        if params[3].value == "Occupied HUC Watershed":
            params[4].enabled = True
            params[4].parameterType = "Required"
        elif params[3].value == "Convex Hull":
            params[4].enabled = False
            params[4].parameterType = "Optional"
        else:
            params[4].enabled = False
            params[4].parameterType = "Optional"
        return

    def updateMessages(self, params):
        return

    def execute(self, params, messages):
        input_fc = params[0].valueAsText
        grouping_field = params[1].valueAsText
        species_code = params[2].valueAsText
        range_type = params[3].valueAsText
        huc08 = params[4].valueAsText
        clip_lyr = params[5].valueAsText
        grid_sz = params[6].valueAsText
        output_tbl = params[7].valueAsText
        extent_output = params[8].valueAsText

        arcpy.AddMessage("creating table")
        rank_stats = arcpy.CreateTable_management(os.path.dirname(output_tbl),os.path.basename(output_tbl))
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
        # if convex hull was chosen, then we will calculate the convex hull for range extent
        if range_type == "Convex Hull":
            # creating convex hull
            convex_hull = arcpy.MinimumBoundingGeometry_management(input_fc,os.path.join("memory","convex_hull"),"CONVEX_HULL","LIST",species_code)
            # if clip layer was used, then we will clip to the boundary of clip layer and use for geometry
            if clip_lyr:
                hull_clip = arcpy.Clip_analysis(convex_hull,clip_lyr,os.path.join("memory","hull_clip"))
                convex_hull = hull_clip
            # if extent output path given, copy convex hull to path location
            if extent_output:
                arcpy.CopyFeatures_management(convex_hull,extent_output)
            # create Python dictionary of area in km2 for convex polygons for each species
            convex_dict = {row[0]:round(row[1].getArea("GEODESIC","SQUAREKILOMETERS"),3) for row in arcpy.da.SearchCursor(convex_hull, [species_code,"SHAPE@"])}
            # write values from python dictionary to table
            with arcpy.da.UpdateCursor(rank_stats,[species_code,"range_extent_km2"]) as cursor:
                for row in cursor:
                    for k,v in convex_dict.items():
                        if k == row[0]:
                            row[1] = v
                            cursor.updateRow(row)

        elif range_type == "Occupied HUC Watershed":
            huc_lyr = arcpy.MakeFeatureLayer_management(huc08, "huc_lyr")
            input_lyr = arcpy.MakeFeatureLayer_management(input_fc, "input_lyr")

            if clip_lyr:
                huc_clip = arcpy.analysis.PairwiseClip(huc_lyr,clip_lyr,os.path.join("memory","huc_clip"))
                huc_lyr = arcpy.MakeFeatureLayer_management(huc_clip, "huc_lyr")

            # updated to account for double and float field types
            if arcpy.ListFields(input_lyr, species_code)[0].type == 'Integer' or \
                    arcpy.ListFields(input_lyr, species_code)[0].type == 'Double' or \
                    arcpy.ListFields(input_lyr, species_code)[0].type == 'Float':
                species_query = "{}={}"
            else:
                species_query = "{}='{}'"

            # if extent output path given, create feature class where extents will be saved and add species id field
            if extent_output:
                extent_output = arcpy.CreateFeatureclass_management(os.path.dirname(extent_output),os.path.basename(extent_output),"POLYGON", spatial_reference=input_fc)
                arcpy.AddField_management(extent_output, species_code, field_type, "", "", field_length)

            # create empty dictionary to store species id and summed area of hucs
            range_dict = {}
            species_list = sorted({row[0] for row in arcpy.da.SearchCursor(rank_stats, species_code)})
            for species in species_list:
                arcpy.SelectLayerByAttribute_management(input_lyr, "NEW_SELECTION",species_query.format(species_code, species))
                arcpy.SelectLayerByLocation_management(huc_lyr, "INTERSECT", input_lyr, "", "NEW_SELECTION")
                # calculate area in km2 for all selected huc08 watersheds
                huc_area = sum(row[0].getArea('GEODESIC', 'SQUAREKILOMETERS') for row in arcpy.da.SearchCursor(huc_lyr, "SHAPE@"))
                range_dict[species] = huc_area
                # if extent output path given, dissolve selected hucs and insert them into feature class
                if extent_output:
                    diss = arcpy.PairwiseDissolve_analysis(huc_lyr,os.path.join("memory","diss"))
                    with arcpy.da.SearchCursor(diss,"SHAPE@") as cursor:
                        for row in cursor:
                            geom = row[0]
                    with arcpy.da.InsertCursor(extent_output,[species_code,"SHAPE@"]) as cursor:
                        cursor.insertRow((species,geom))

            with arcpy.da.UpdateCursor(rank_stats, [species_code, "range_extent_km2"]) as cursor:
                for row in cursor:
                    for k, v in range_dict.items():
                        if k == row[0]:
                            row[1] = v
                            cursor.updateRow(row)

        else:
            arcpy.AddWarning("Something went wrong... contact the system administrator.")
            sys.exit()

########################################################################################################################
## Calculate area of occupancy for each species
########################################################################################################################

        arcpy.AddMessage("calculating area of extent")
        if grid_sz == "2x2 km2 grid":
            grid = arcpy.GenerateTessellation_management(os.path.join("memory","grid"),input_fc,"SQUARE","4 SquareKilometers")
        elif grid_sz == "1x1 km2 grid":
            grid = arcpy.GenerateTessellation_management(os.path.join("memory", "grid"), input_fc, "SQUARE","1 SquareKilometers")
        else:
            arcpy.AddWarning("Something went wrong with grid square creation... please contact the system administrator.")
            sys.exit()
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
            if grid_sz == "2x2 km2 grid":
                km2 = count*4
            else:
                km2 = count
            AOO_dict[species] = km2

        with arcpy.da.UpdateCursor(rank_stats,[species_code,"occupancy_area_km2"]) as cursor:
            for row in cursor:
                for k,v in AOO_dict.items():
                    if k == row[0]:
                        row[1] = v
                        cursor.updateRow(row)
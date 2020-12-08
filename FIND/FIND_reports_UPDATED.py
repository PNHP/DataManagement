#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      MMoore
#
# Created:     22/10/2020
# Copyright:   (c) MMoore 2020
# Licence:     <your licence>
#-------------------------------------------------------------------------------

# import system modules
import arcpy, os, datetime
from arcpy import env
from arcpy.sa import *

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True

# define env.workspace - this space is used for all temporary files
env.workspace = r'in_memory'

et = r"W:\\Heritage\\Heritage_Data\\Biotics_datasets.gdb\\ET"
elementGDB = r'Database Connections\\FIND.Working.pgh-gis0.sde'
counties = r'Database Connections\StateLayers.Default.pgh-gis0.sde\StateLayers.DBO.Boundaries_Political\StateLayers.DBO.County'
ReportsPath = r'P:\Conservation Programs\Natural Heritage Program\Data Management\Instructions, procedures and documentation\FIND\FIND_2020\Reports'
keep_fields = ["OID","OBJECTID","SHAPE","SHAPE_Length","SHAPE_Area","refcode","sf_desc","elem_type","elem_name","elem_found","elem_found_comm","elem_eo","eo_spec_comm","new_up","eoid","date_start","date_stop","voucher_photo","specimen_taken","specimen_count","specimen_desc","curatorial_meth","specimen_repo","id_det_by","id_date","id_initial_det","feat_meth","feat_meth_comm","loc_unc","project","dm_stat","dm_stat_date","dm_stat_comm","BioticsSFID","created_user","created_date","X","Y","last_edited_user","last_edited_date","COUNTY_NAM","feature_type","track_status"]

# file names of the five element feature classes in the FIND enterprise GDB
input_features = ["FIND.DBO.el_pt", "FIND.DBO.el_line", "FIND.DBO.comm_poly","FIND.DBO.comm_pt", "FIND.DBO.el_poly", "FIND.DBO.survey_poly"]
output_features = ["element_point","element_line","community_polygon","community_point","element_polygon","survey_polygon"]

for i,o in zip(input_features,output_features):
    f = os.path.join(elementGDB,i)
    spatial_join = arcpy.SpatialJoin_analysis(f,counties,os.path.join(env.workspace,o))

    arcpy.AddField_management(spatial_join,"feature_type","TEXT","","",50,"Feature Type")
    with arcpy.da.UpdateCursor(spatial_join,"feature_type") as cursor:
        for row in cursor:
            row[0] = o
            cursor.updateRow(row)

    tracking_dict = {}
    with arcpy.da.SearchCursor(et,["ELSUBID","EO_TRACK"]) as cursor:
        for row in cursor:
            tracking_dict[str(int(row[0]))] = row[1]

    arcpy.AddField_management(spatial_join,"track_status","TEXT","","",2,"Element Tracking Status")
    if i != "FIND.DBO.survey_poly":
        with arcpy.da.UpdateCursor(spatial_join,["elem_name","track_status"]) as cursor:
            for row in cursor:
                for k,v in tracking_dict.items():
                    if str(k)==str(row[0]):
                        row[1]=v
                        cursor.updateRow(row)
    else:
        with arcpy.da.UpdateCursor(spatial_join,"track_status") as cursor:
            for row in cursor:
                row[0] = "NA"
                cursor.updateRow(row)

    table = arcpy.TableToTable_conversion(spatial_join,env.workspace,o+"_tbl")

merge = arcpy.Merge_management(["in_memory\\element_point_tbl", "in_memory\\element_line_tbl", "in_memory\\element_polygon_tbl","in_memory\\community_polygon_tbl","in_memory\\community_point_tbl","in_memory\\survey_polygon_tbl"],r'H:\temp\temp.gdb\merge')

fields = arcpy.ListFields(merge)
dropFields = [x.name for x in fields if x.name not in keep_fields]
arcpy.DeleteField_management(merge, dropFields)

arcpy.JoinField_management(merge,"elem_name",et,"ELSUBID",["ELCODE","SNAME","SCOMNAME"])



#-------------------------------------------------------------------------------
# Name:        module2
# Purpose:
#
# Author:      mmoore
#
# Created:     09/10/2019
# Copyright:   (c) mmoore 2019
# Licence:     <your licence>
#-------------------------------------------------------------------------------

# import system modules
import arcpy, os, datetime
from arcpy import env
from arcpy.sa import *

# Set tools to overwrite existing outputs
arcpy.env.overwriteOutput = True

existing_features = r'W:\Heritage\Heritage_Data\xfer_Susan\for_Molly\BT_Revised_Indirect_Steps.gdb\Input_1_Existing_BT_Indirect_Conflict_Polys'
new_features = r'W:\Heritage\Heritage_Data\xfer_Susan\for_Molly\BT_Revised_Indirect_Steps.gdb\Input_2_New_BT_Model'
output_fc = r'W:\Heritage\Heritage_Data\xfer_Susan\for_Molly\BT_Revised_Indirect_Steps.gdb\_testData'

final_data = arcpy.FeatureClassToFeatureClass_conversion(existing_features,os.path.dirname(output_fc),os.path.basename(output_fc))
final_data = arcpy.TruncateTable_management(final_data)

data_lyr = arcpy.MakeFeatureLayer_management(existing_features,"data_lyr")

objectid_field = arcpy.Describe(data_lyr).OIDFieldName
with arcpy.da.SearchCursor(data_lyr,objectid_field) as cursor:
    for row in cursor:
        objectid = row[0]
        arcpy.SelectLayerByAttribute_management(data_lyr, "NEW_SELECTION", "{}={}".format(objectid_field,objectid))
        clip = arcpy.Clip_analysis(data_lyr,new_features,os.path.join(os.path.dirname(output_fc),"clip_temp"))
        arcpy.Append_management(clip,final_data,"TEST")
##        with arcpy.da.SearchCursor(clip,"*") as sCur:
##            with arcpy.da.InsertCursor(final_data,'*') as iCur:
##                for row in sCur:
##                    iCur.insertRow(row)

#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      mmoore
#
# Created:     29/10/2018
# Copyright:   (c) mmoore 2018
# Licence:     <your licence>
#-------------------------------------------------------------------------------

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

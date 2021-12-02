#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      MMoore
#
# Created:     30/03/2021
# Copyright:   (c) MMoore 2021
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import arcpy
import numpy as np

et_old =
et_new =
et_change =

old_elsubids = sorted({row[0] for row in arcpy.da.SearchCursor(et_old,"ELSUBID")})
new_elsubids = sorted({row[0] for row in arcpy.da.SearchCursor(et_new,"ELSUBID")})

insert_fields = ["ELSUBID","change","old_value","new_value"]

#records in new_elsubids that are not in old_elsubids, so therefore classified as added
print("Checking for ELSUBID additions")
added_elsubids = np.setdiff1d(new_elsubids,old_elsubids)
for a in added_elsubids:
    values = [a,"ELSUBID addition",None,a]
    with arcpy.da.InsertCursor(et_change,insert_fields) as cursor:
        cursor.insertRow(values)

#records in old_elsubids that are not in new_elsubids, so therefore classified as deleted
print("Checking for ELSUBID deletions")
deleted_elsubids = np.setdiff1d(old_elsubids,new_elsubids)
for d in deleted_elsubids:
    values = [d,"ELSUBID deletion",d,None]
    with arcpy.da.InsertCursor(et_change,insert_fields) as cursor:
        cursor.insertRow(values)

old_et_dict = {int(row[0]):[row[1:]] for row in arcpy.da.SearchCursor(et_old,["ELSUBID","ELCODE","SNAME","SCOMNAME","GRANK","SRANK","EO_Track","USESA","SPROT","PBSSTATUS","SGCN","SENSITV_SP","ER_RULE"])}


change_fields = ["ELCODE","SNAME","SCOMNAME","GRANK","SRANK","EO_Track","USESA","SPROT","PBSSTATUS","SGCN","SENSITV_SP","ER_RULE"]
dict_value_index = [0,1,2,3,4,5,6,7,8,9,10,11]
for c,i in zip(change_fields,dict_value_index):
    print("Checking for changes in " + c)
    with arcpy.da.SearchCursor(et_new,["ELSUBID", c]) as cursor:
        for row in cursor:
            for k,v in old_et_dict.items():
                if k==int(row[0]):
                    if row[1] == v[0][i]:
                        pass
                    else:
                        values = [int(row[0]), c, v[0][i], row[1]]
                        with arcpy.da.InsertCursor(et_change,insert_fields) as cursor:
                            cursor.insertRow(values)
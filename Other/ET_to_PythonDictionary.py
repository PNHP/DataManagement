#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      MMoore
#
# Created:     28/01/2020
# Copyright:   (c) MMoore 2020
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import pandas as pd

et_folder = r'P:\Conservation Programs\Natural Heritage Program\Data Management\Instructions, procedures and documentation\FIND\FIND_2020\DM Documentation\Admin and maintenance\20200305_'
et_comm = r'ET_COMMOTH'
et_insect = r'ET_INSECT'
et_invert = r'ET_INVERT'
et_lep = r'ET_LEP'
et_plant = r'ET_PLANT'
et_vert = r'ET_VERT'
et_all = r'ET'

all_excel = [et_comm,et_insect,et_invert,et_lep,et_plant,et_vert]

def loadExcel(in_sheet):
    df = pd.read_excel(io=in_sheet, sheet_name="Sheet1")
    df = df[['ELEMENT_SUBNATIONAL_ID','SCIENTIFIC_NAME']]
    d = dict(zip(df.ELEMENT_SUBNATIONAL_ID, df.SCIENTIFIC_NAME))
    return d

et_comm = loadExcel(et_folder+et_comm+".xlsx")
et_insect = loadExcel(et_folder+et_insect+".xlsx")
et_invert = loadExcel(et_folder+et_invert+".xlsx")
et_lep = loadExcel(et_folder+et_lep+".xlsx")
et_plant = loadExcel(et_folder+et_plant+".xlsx")
et_vert = loadExcel(et_folder+et_vert+".xlsx")
et_all = loadExcel(et_folder+et_all+".xlsx")




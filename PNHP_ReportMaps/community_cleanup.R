if (!requireNamespace("dplyr", quietly = TRUE)) install.packages("dplyr")
require(dplyr)
if (!requireNamespace("tidyr", quietly = TRUE)) isntall.packages("tidyr")
require(tidyr)
if (!requireNamespace("arcgisbinding", quietly = TRUE)) install.packages("arcgisbinding")
require(arcgisbinding)
if (!requireNamespace("sf", quietly = TRUE)) install.packages("sf")
require(sf)

# load the arcgis license
arc.check_product()

output_gdb <- "H:/Projects/AutomatedMaps/Communities/InputData.gdb"
qc_path <- "H:/Projects/AutomatedMaps/Communities/QC"
lu_cover_path <- "H:/Projects/AutomatedMaps/Communities/lu_CoverTypeCodes_ez.csv"


#############################################
# read in community type list
comm_list_path <- "H:/Projects/AutomatedMaps/Communities/CommunityList.csv"
comm_list <- read.csv(comm_list_path)

#############################################
# cleaning up EcoObs community data
# read in EcoObs data
plots_path <- "H:/Projects/AutomatedMaps/Communities/EcoObs_Plots_Export_20241205.csv"
plots_df <- read.csv(plots_path)

# rename ELCODE field
colnames(plots_df)[colnames(plots_df) == "Assoc_Alli"] ="ELCODE"

# take out records with blank elcode, blank lat, and blank long fields
plots_df <- plots_df[!(is.na(plots_df$ELCODE) | plots_df$ELCODE==""), ]
plots_df <- plots_df[!(is.na(plots_df$Lat) | plots_df$Lat==""), ]
plots_df <- plots_df[!(is.na(plots_df$Long) | plots_df$Long==""), ]

# break out rows that have comma delimited values in ELCODE column and return as multiple rows
plots_df <- plots_df %>%
  separate_rows(ELCODE)

# join name field to plots dataframe by ELCODE keys
plots_df <- left_join(plots_df, comm_list, by="ELCODE")

missing_elcodes <- plots_df[(is.na(plots_df$PA_Community_Name)), ]
write.csv(missing_elcodes, paste(qc_path,"plots_data_missing_elcodes.csv", sep = "/"))

plots_df <- plots_df[!(is.na(plots_df$PA_Community_Name)), ]

plots_sf <- st_as_sf(plots_df, coords=c("Long","Lat"), crs="+proj=longlat +datum=WGS84 +no_defs +ellps=WGS84 +towgs84=0,0,0")
plots_sf <- st_transform(plots_sf, crs=st_crs("EPSG:3857")) # reproject to the web mercator
arc.write(path=paste(output_gdb,"plots_sf",sep="/"), plots_sf, overwrite=TRUE) # write a feature class into the geodatabase


###########################################
# QC for SGL cover typing data - before bringing in here, run Feature to Point tool to get centroids in ArcGIS
# read in SGL cover type centroids layer
sgl_path <- "H:/Projects/AutomatedMaps/Communities/InputData.gdb/SGL_typing_centroids_20241212"
sgl_open <- arc.open(sgl_path)
sgl_select <- arc.select(sgl_open, c("cover_type")) 
sgl_sf <- arc.data2sf(sgl_select)

  
# read in the lu cover type table
lu_cover <- read.csv(lu_cover_path)
# get rid of rows with na ELCODE values
lu_cover <- lu_cover[!(is.na(lu_cover$ELCODE)), ]

sgl_sf <- left_join(sgl_sf, lu_cover, by=c("cover_type"="Type"))
sgl_sf <- sgl_sf[!(is.na(sgl_sf$ELCODE)), ]

arc.write(path=paste(output_gdb,"SGL_Typing_Processed",sep="/"), sgl_sf, overwrite=TRUE) # write a feature class into the geodatabase


###########################################
# QC for DCNR cover typing data - before bringing in here, run Feature to Point tool to get centroids in ArcGIS
# read in DCNR cover type centroids layer
dcnr_path <- "H:/Projects/AutomatedMaps/Communities/InputData.gdb/DCNR_typing_centroids_20241212"
dcnr_open <- arc.open(dcnr_path)
dcnr_select <- arc.select(dcnr_open, c("Type"))
dcnr_sf <- arc.data2sf(dcnr_select)

dcnr_sf <- left_join(dcnr_sf, lu_cover, by=c("Type"="Type"))
dcnr_sf <- dcnr_sf[!(is.na(dcnr_sf$ELCODE)), ]

arc.write(path=paste(output_gdb,"DCNR_Typing_Processed",sep="/"), dcnr_sf, overwrite=TRUE) # write a feature class into the geodatabase


  
  
  
  
  
  












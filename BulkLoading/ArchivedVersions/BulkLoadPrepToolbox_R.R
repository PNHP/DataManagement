if (!requireNamespace("arcgisbinding", quietly=TRUE)) install.packages("arcgisbinding")
require(arcgisbinding)
if (!requireNamespace("dplyr", quietly=TRUE)) install.packages("dplyr")
require(dplyr)
if (!requireNamespace("sf", quietly=TRUE)) install.packages("sf")
require(sf)
if (!requireNamespace("plyr", quietly = TRUE)) install.packages("plyr")
require(plyr)

in_points = 'C:/Users/mmoore/Documents/ArcGIS/Grouping_Demo/EOAssign_DEVELOPMENT.gdb/FIND2018DYeanyBulk_point'
in_lines = ''
in_poly = 'C:/Users/mmoore/Documents/ArcGIS/Grouping_Demo/EOAssign_DEVELOPMENT.gdb/Polygon_features'
species_code = 'SNAME'
lu_separation = 'sep_dist_km'
loc_uncert = 'feat_meth_comm'
loc_uncert_dist = 'loc_unc'
eo_reps = 'W:/Heritage/Heritage_Data/biotics_datasets.gdb/eo_reps'
eo_id_field = 'EO_ID'
eo_sourcept = 'W:/Heritage/Heritage_Data/biotics_datasets.gdb/eo_sourcept'
eo_sourceln = 'W:/Heritage/Heritage_Data/biotics_datasets.gdb/eo_sourceln'
eo_sourcepy = 'W:/Heritage/Heritage_Data/biotics_datasets.gdb/eo_sourcepy'
sf_id_field = 'SF_ID'
species_code_field = 'SNAME'

arc.check_product()

if(in_points!=''){
  pts <- arc.open(in_points)
  pts <- arc.select(pts)
  pts <- arc.data2sf(pts)
  pts$join_id = paste0('a',seq.int(nrow(pts)))
  
  pts$buff_dist <- ifelse(tolower(pts[[loc_uncert]])!="estimated" | is.na(pts[[loc_uncert]])==TRUE,1,as.integer(pts[[loc_uncert_dist]])+1)
  pts_buff <- st_buffer(pts,pts$buff_dist)
}

if(in_lines!=''){
  lns <- arc.open(in_lines)
  lns <- arc.select(lns)
  lns <- arc.data2sf(lns)
  lns$join_id = paste0('b',seq.int(nrow(lns)))
  
  lns$buff_dist <- ifelse(tolower(lns[[loc_uncert]])!="estimated" | is.na(lns[[loc_uncert]])==TRUE,1,as.integer(lns[[loc_uncert_dist]])+1)
  lns_buff <- st_buffer(lns,lns$buff_dist)
}

if(in_poly!=''){
  py <- arc.open(in_poly)
  py <- arc.select(py)
  py <- arc.data2sf(py)
  py$join_id = paste0('c',seq.int(nrow(py)))
  
  py$buff_dist <- ifelse(tolower(py[[loc_uncert]])!="estimated" | is.na(py[[loc_uncert]])==TRUE,1,as.integer(py[[loc_uncert_dist]])+1)
  py_buff <- st_buffer(py,py$buff_dist)
}

if(exists('pts')){
  m <- pts_buff}
if(exists('lns')){
  m <- rbind(merge,lns_buff)}
if(exists('py')){
  m <- rbind(merge,py_buff)}

eos <- arc.open(eo_reps)
eos <- arc.select(eos)
eos <- arc.data2sf(eos)

species_list = unique(m[[species_code]])
for(species in species_list){
  df_obs <- m[which(m[[species_code]]==species),]
  buff_dist <- ((df_obs[[lu_separation]][1]*1000)/2)-0.5
  obs_buff <- st_buffer(df_obs,buff_dist)
  e <- eos[which(eos[[species_code_field]]==species),]
  eo_buff <- st_buffer(e,buff_dist)
  obs_diss <- st_union(obs_buff)
  obs_single <- st_cast(obs_diss,"POLYGON")
  obs_eo_join <- st_join(obs_single,eo_buff)
}



arc.write('C:/Users/mmoore/Documents/ArcGIS/Grouping_Demo/EOAssign_DEVELOPMENT.gdb/test_merge2',eo_buff)

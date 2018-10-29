tool_exec <- function(in_params, out_params)  #
{
  
  if (!requireNamespace("knitr", quietly = TRUE)) install.packages("knitr")
  require(knitr)
  if (!requireNamespace("sf", quietly = TRUE)) install.packages("sf")
  require(sf)
  if (!requireNamespace("sp", quietly = TRUE)) install.packages("sp")
  require(sp)
  if (!requireNamespace("ggplot2", quietly = TRUE)) install.packages("ggplot2")
  require(ggplot2)
  if (!requireNamespace("tmap", quietly = TRUE)) install.packages("tmap")
  require(tmap)
  if (!requireNamespace("tidyverse", quietly = TRUE)) install.packages("tidyverse")
  require(tidyverse)
  if (!requireNamespace("arcgisbinding", quietly = TRUE)) install.packages("arcgisbinding")
  require(arcgisbinding)
  if (!requireNamespace("grid", quietly = TRUE)) install.packages("grid")
  require(grid)
  
  survey_sites <- "H:/Scripts/FIND/Reporting/LocalFiles.gdb/SurveySites"
  survey_sites <- in_params[[1]]
  el_pt <- 'FIND/Element Point'
  el_ln <- 'FIND/Element Line'
  el_poly <- 'FIND/Element Polygon'
  comm_pt <- 'FIND/Community or Other Point'
  comm_poly <- 'FIND/Community or Other Polygon'
  working_directory <- 'H:/Scripts/FIND/Reporting'
  graphics_path <- 'H:/Scripts/FIND/Reporting/images/'
  county_lyr <- "H:/Scripts/FIND/Reporting/LocalFiles.gdb/County"
  
  selected_sites <- arc.open(survey_sites)
  ss <- arc.select(selected_sites)
  ss_shape <- arc.data2sf(ss)
  refcode_list <- ss$refcode
  extent <- st_bbox(ss_shape)
  #extent1 <- c(extent[1]-250, extent[2]-1000, extent[3]+250, extent[4]+250)
  extent_box <- st_bbox(ss_shape) %>%
    st_as_sfc()
  
  el_points <- arc.open(el_pt)
  pts_full <- arc.select(el_points)
  #pt <- subset(selected_pts_full, refcode %in% refcode_list)
  
  el_lines <- arc.open(el_ln)
  lns_full <- arc.select(el_lines)
  #ln <- subset(selected_pts_full, refcode %in% refcode_list)
  
  el_poly <- arc.open(el_poly)
  poly_full <- arc.select(el_poly)
  #poly <- subset(selected_poly_full, refcode %in% refcode_list)
  
  comm_pt <- arc.open(comm_pt)
  cpts_full <- arc.select(comm_pt)
  #cpts <- subset(selected_cpts_full, refcode %in% refcode_list)
  
  comm_poly <- arc.open(comm_poly)
  cpoly_full <- arc.select(comm_poly)
  #cpoly <- subset(selected_cpoly_full, refcode %in% refcode_list)
  
  counties <- arc.open(county_lyr)
  counties <- arc.select(counties)
  counties_shape <- arc.data2sf(counties)
  
#  survey_centroids <- st_centroid(ss_shape)
#  coords <- do.call(rbind, st_geometry(survey_centroids)) %>% 
#            as_tibble() %>% setNames(c("lon","lat"))
#  survey_centroids <- bind_cols(survey_centroids, coords)
#  ggplot()+
#    geom_sf(data=ss_shape, fill=NA, colour="grey20")+
#    theme(axis.line = element_blank(),
#          panel.grid.major = element_line(colour='transparent'),
#          panel.grid.minor = element_line(colour='transparent'),
#          panel.border = element_blank(),
#          panel.background = element_blank(),
#          axis.text.x=element_blank(),
#          axis.text.y=element_blank(),
#          axis.ticks.x=element_blank(),
#          axis.ticks.y=element_blank(),
#          axis.title=element_blank())+
#    geom_text(data=survey_centroids, mapping=aes(x=lon,y=lat,label=survey_sit))+
#    ggsave(filename=paste0(graphics_path,"map.jpg"),width=7.5,height=8,units="in", dpi=300)
  
  
  
  survey_map <- tm_shape(ss_shape,bbox=tmaptools::bb(extent))+
    tm_borders("black")+
    tm_text("survey_sit", size=1, auto.placement=FALSE, xmod=-0.5, ymod=2.2)+
    tm_compass(north=0,type="4star",size=4.25, position=c("right","top"))+
    tm_scale_bar(position=c("right", "bottom"), size=0.8)+
    tm_layout(frame=FALSE)
  
  county_map <- tm_shape(counties_shape)+
    tm_borders("gray40")+
    tm_shape(extent_box)+
    tm_borders(lwd=25, col="red")
  
  tmap_save(survey_map, paste0(graphics_path,"map.jpg"), width=7.5, insets_tm = county_map, insets_vp = viewport(0.03,0.13,width=0.45, just="left"))

  elements <- rbind(pts_full[1:80], lns_full[1:80], poly_full[1:80])
  selected_elements <- subset(elements, refcode %in% refcode_list)
  
  print("Generating the PDF report...") # report out to ArcGIS
  setwd(working_directory)
  knit2pdf(paste(working_directory,"survey_reporting.rnw",sep="/"), output="report_results.tex")   #write the pdf
  
  # create and open the pdf
  pdf.path <- paste(working_directory, paste("report_results.pdf",sep=""), sep="/")
  system(paste0('open "', pdf.path, '"'))
  
}
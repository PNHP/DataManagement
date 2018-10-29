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
if (!requireNamespace("grid", quietly = TRUE)) install.packages("grid")
require(grid)

library(arcgisbinding)
arc.check_product()

survey_sites <- "H:/Scripts/FIND/Reporting/LocalFiles.gdb/SurveySites"
county_lyr <- "H:/Scripts/FIND/Reporting/LocalFiles.gdb/County"

working_directory <- 'H:/Scripts/FIND/Reporting'
graphics_path <- 'H:/Scripts/FIND/Reporting/images/'

selected_sites <- arc.open(survey_sites)
ss <- arc.select(selected_sites)
ss_shape <- arc.data2sf(ss)

counties <- arc.open(county_lyr)
counties <- arc.select(counties)
counties_shape <- arc.data2sf(counties)

tmap_mode('view')
tm_basemap(leaflet::providers$Stamen.Watercolor)+
tm_shape(ss_shape)+
              tm_borders("black")+
              tm_text("survey_sit", size=0.7, auto.placement=FALSE, xmod=-0.5, ymod=1.6)
              

tm_shape(counties_shape)+
              tm_borders("gray40")+
              tm_shape(extent_box)+
              tm_borders(lwd=15, col="red")+
              tm_basemap('OpenStreetMap')


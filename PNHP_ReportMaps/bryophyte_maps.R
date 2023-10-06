#---------------------------------------------------------------------------------------------
# Name: state_occurrences.r
# Purpose: 
# Author: Christopher Tracey
# Created: 2021-04-21
# Updated: 2021-05-17
#
# Updates:
#   2021-05-17 - code cleanup and documentation
# 
#
# To Do List/Future Ideas:
# * add a "for internal use only" only text on internal maps!
#---------------------------------------------------------------------------------------------

library(here)
library(arcgisbinding) # this code uses the ESRI ArcGIS-R bridge to access the EO reps feature class
library(sf)
library(tidyr)
library(dplyr)
library(ggplot2)

arc.check_product()

#arc.check_portal()  # may need to update bridge to most recent version if it crashes: https://github.com/R-ArcGIS/r-bridge/issues/46
#bioticsFeatServ_path <- "https://maps.waterlandlife.org/arcgis/rest/services/PNHP/Biotics/FeatureServer"


# create a directory for this update unless it already exists
ifelse(!dir.exists(here::here("_data")), dir.create(here::here("_data")), FALSE)
ifelse(!dir.exists(here::here("_data","bryophyte_maps")), dir.create(here::here("_data","bryophyte_maps")), FALSE)

# load subnation boundary feature class. 
serverPath <- paste("C:/Users/",Sys.getenv("USERNAME"),"/AppData/Roaming/ESRI/ArcGISPro/Favorites/StateLayers_Default_pgh-gis0.sde/",sep="") #pointing to PNHP GIS infrastructure. You can change this to a local file, feature service, or the like...
county <- arc.open(paste(serverPath,"StateLayers.DBO.County", sep=""))  
county <- arc.select(county, fields=c("COUNTY_NAM"))
county <- arc.data2sf(county)

# get point reps
eo_ptrep <- arc.open("H:/temp/Bryophytes/Bryophytes.gdb/BryophyteOccurrences_counties")  # monthly exports provided by PNHP data management
eo_ptrep <- arc.select(eo_ptrep)
eo_ptrep <- arc.data2sf(eo_ptrep)

# get the current year
currentyear <- as.numeric(format(Sys.Date(), format="%Y"))
extantyear <- currentyear - 50

# assign legends and colors for the maps
eo_ptrep$extant[eo_ptrep$eventDate<extantyear] <- "Historic"
eo_ptrep$extant[eo_ptrep$eventDate>=extantyear] <- "Extant"
eo_ptrep <- eo_ptrep[order(eo_ptrep$acceptedPAName),] # sort it
eo_ptrep$extant <- as.factor(eo_ptrep$extant)

# get a list of SNAMEs
spList <- unique(eo_ptrep$acceptedPAName) # non-sensitive species

# make the Non-Sensitive series of maps
for(i in 1:length(spList)){
  eo_map <- eo_ptrep[which(eo_ptrep$acceptedPAName==spList[i]),]
  cat("Making the species maps for",spList[i],"\n")
  eo_map$acceptedPAName <- gsub("/","-",eo_map$acceptedPAName)
  # map it
  a <- ggplot() +
    geom_sf(data=county, fill=NA) +
    geom_sf(data=eo_map, aes(fill=extant)) +
    scale_fill_manual(values=c('cornflowerblue','darkred'), labels=c("<50 years",">50 years"), drop=FALSE)+
    ggtitle(expr(italic(!!unique(eo_map$acceptedPAName)))) +
    theme_void() +
    theme(legend.position="bottom") +
    theme(legend.title=element_blank())
  ggsave(filename=paste(here::here("_data","bryophyte_maps"),"/","eomap_",gsub(" ","-",unique(eo_map$acceptedPAName)),"_",gsub("-","",Sys.Date()),".png", sep=""), plot=a,
         width = 6,
         height = 4,
         units = c("in"),
         dpi = 150
  )
}


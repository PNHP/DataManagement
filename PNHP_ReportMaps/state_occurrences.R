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
ifelse(!dir.exists(here::here("_data","stateOcc")), dir.create(here::here("_data","stateOcc")), FALSE)

# load subnation boundary feature class. 
serverPath <- paste("C:/Users/",Sys.getenv("USERNAME"),"/AppData/Roaming/ESRI/ArcGISPro/Favorites/StateLayers_Default_pgh-gis0.sde/",sep="") #pointing to PNHP GIS infrastructure. You can change this to a local file, feature service, or the like...
county <- arc.open(paste(serverPath,"StateLayers.DBO.County", sep=""))  
county <- arc.select(county, fields=c("COUNTY_NAM"))
county <- arc.data2sf(county)

# get point reps
eo_ptrep <- arc.open("W:/Heritage/Heritage_Data/Biotics_datasets.gdb/eo_ptreps")  # monthly exports provided by PNHP data management
eo_ptrep <- arc.select(eo_ptrep, where_clause="EO_TRACK='Y' OR EO_TRACK='W'")
eo_ptrep <- arc.data2sf(eo_ptrep)

# get the current year
currentyear <- as.numeric(format(Sys.Date(), format="%Y"))
extantyear <- currentyear - 25

# assign legends and colors for the maps
eo_ptrep$extant[eo_ptrep$LASTOBS_YR<extantyear] <- "Historic"
eo_ptrep$extant[eo_ptrep$LASTOBS_YR>=extantyear] <- "Extant"
eo_ptrep$extant[is.na(eo_ptrep$LASTOBS_YR)] <- "Historic" # need to check if this a valid approach
eo_ptrep <- eo_ptrep[order(eo_ptrep$SNAME),] # sort it
eo_ptrep$extant <- as.factor(eo_ptrep$extant)

# get a list of SNAMEs
spList <- unique(eo_ptrep[which(eo_ptrep$SENSITV_SP!="Y"),]$SNAME) # non-sensitive species
#### TEMP  for demo  spList <- sample(spList, size=10) #### TEMP  for demo
spListSens <- unique(eo_ptrep[which(eo_ptrep$SENSITV_SP=="Y"),]$SNAME) # sensitive species
#### TEMP  for demo  spListSens <- sample(spListSens, size=10) 

# make the Non-Sensitive series of maps
for(i in 1:length(spList)){
  eo_map <- eo_ptrep[which(eo_ptrep$SNAME==spList[i]),]
  cat("Making the non-sensitive species maps for",spList[i],"\n")
  eo_map$SNAME <- gsub("/","-",eo_map$SNAME)
  # map it
  a <- ggplot() +
    geom_sf(data=county, fill=NA) +
    geom_sf(data=eo_map, aes(shape=extant, color=extant), size=2.5) +
    scale_shape_manual(values=c(17, 16), labels=c("<25 years",">25 years"), drop=FALSE)+
    scale_color_manual(values=c('cornflowerblue','darkred'), labels=c("<25 years",">25 years"),drop=FALSE)+
    ggtitle(expr(paste(!!unique(eo_map$SCOMNAME)," (",italic(!!unique(eo_map$SNAME)),")", sep=""))) +
    theme_void() +
    theme(legend.position="bottom") +
    theme(legend.title=element_blank())
  ggsave(filename=paste(here::here("_data","stateOcc"),"/","eomap_",gsub(" ","-",unique(eo_map$SNAME)),"_",gsub("-","",Sys.Date()),".png", sep=""), plot=a,
    width = 6,
    height = 4,
    units = c("in"),
    dpi = 150
  )
}

# make the Sensitive series of maps
for(i in 1:length(spListSens)){
  eo_map <- eo_ptrep[which(eo_ptrep$SNAME==spListSens[i]),]
  cat("Making the sensitive species maps for",spListSens[i],"\n")
  # map an sensitive species maps for internal use
  a <- ggplot() +
    geom_sf(data=county, fill=NA) +
    geom_sf(data=eo_map, aes(shape=extant, color=extant), size=2.5) +
    scale_shape_manual(values=c(17, 16), labels=c("<25 years",">25 years"), drop=FALSE)+
    scale_color_manual(values=c('cornflowerblue','darkred'), labels=c("<25 years",">25 years"),drop=FALSE)+
    ggtitle(expr(paste(!!unique(eo_map$SCOMNAME)," (",italic(!!unique(eo_map$SNAME)),")", sep=""))) +
    theme_void() +
    theme(legend.position="bottom") +
    theme(legend.title=element_blank())
  ggsave(filename=paste(here::here("_data","stateOcc"),"/","eomap_SENSITIVE-internal_",gsub(" ","-",unique(eo_map$SNAME)),"_",gsub("-","",Sys.Date()),".png", sep=""), plot=a,
         width = 6,
         height = 4,
         units = c("in"),
         dpi = 150
  )  
  # map sensitive species for external use  
  # do a spatial join with the counties
  eo_mapSens <- st_join(county,eo_map)
  eo_mapSens <- eo_mapSens[which(!is.na(eo_mapSens$extant)),]
  eo_mapSens <- eo_mapSens[c("COUNTY_NAM","extant","SNAME","SCOMNAME")]
  eo_mapSens <- unique(eo_mapSens)
  
  # filter out the historic EOs if the county is extant
  eo_mapSens <- eo_mapSens %>% 
    group_by(COUNTY_NAM) %>% 
    mutate(len=length(unique(extant))==1) %>%
    filter(ifelse(len==FALSE, extant=="Extant", extant %in% c("Extant","Historic")))

  # map it
  a <- ggplot() +
    geom_sf(data=county, fill=NA) +
    geom_sf(data=eo_mapSens, aes(fill=extant)) +
    scale_fill_manual(values=c('cornflowerblue','darkred'), labels=c("<25 years",">25 years"), drop=FALSE)+
    ggtitle(expr(paste(!!unique(eo_mapSens$SCOMNAME)," (",italic(!!unique(eo_mapSens$SNAME)),")", sep=""))) +
    theme_void() +
    theme(legend.position="bottom") +
    theme(legend.title=element_blank())
  ggsave(filename=paste(here::here("_data","stateOcc"),"/","eomap_SENSITIVE-external_",gsub(" ","-",unique(eo_mapSens$SNAME)),"_",gsub("-","",Sys.Date()),".png", sep=""), plot=a,
         width = 6,
         height = 4,
         units = c("in"),
         dpi = 150
  )
}

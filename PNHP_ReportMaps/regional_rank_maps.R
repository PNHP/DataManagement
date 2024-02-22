#---------------------------------------------------------------------------------------------
# Name: regional_rank_maps.r
# Purpose: 
# Author: Christopher Tracey
# Created: 2021-04-27
# Updated: 2021-05-17
#
# Updates:
#   2021-05-17 - code cleanup and documentation
# 
#
# To Do List/Future Ideas:
# * 
#---------------------------------------------------------------------------------------------

#load the packages
library(tidyverse)
library(here)
library(natserv)
library(arcgisbinding)

arc.check_product() # get the arc license

# create a directory for this update unless it already exists
ifelse(!dir.exists(here::here("_data")), dir.create(here::here("_data")), FALSE)
ifelse(!dir.exists(here::here("_data","regRank")), dir.create(here::here("_data","regRank")), FALSE)

# load spatial information from local geodatabase
template_RegionalStatus <- arc.open(here::here("PNHP_ReportMaps.gdb","template_RegionalStatusInset")) # load the state boundaries
template_RegionalStatus <- arc.select(template_RegionalStatus)
template_RegionalStatus <- arc.data2sf(template_RegionalStatus)

# load the species list
species <- read.csv(here("tracked_species_universal_id_pa_20170530.csv"), stringsAsFactors=FALSE)

# build th UID
species$UID <- paste("ELEMENT_GLOBAL",species$ELEMENT_GLOBAL_OU_UID,species$ELEMENT.GLOBAL.UNIVERSAL.KEY,sep=".")

# test of the for loop
#get a list of SNAMEs to run the loop
snames <-species[c("ELCODE","SNAME","UID")]
#snames <- snames[substr(snames$ELCODE,1,1)=="P",] # only plants
snames <- droplevels(snames)
snames <- unique(snames)
snames <- snames[order(snames$SNAME),] 

#### TEMP  for demo  snames <- snames[sample(nrow(snames), 10), ] 

# loop to get the data and make the maps
for (i in 1:length(snames$UID)) {  
  res <- list() # initialize an empty list
  delayedAssign("do.next", {next}) # some error catching if the results come back empty
  tryCatch(res <- ns_id(uid=snames$UID[i]), finally=print(snames$SNAME[i]), error=function(e) force(do.next)) 
  
  # put the rank list into a variable for below
  constatus_US <- as.data.frame(res$elementNationals$elementSubnationals[match("US", res$elementNationals$nation$isoCode)]) 
  constatus_US <- jsonlite::flatten(constatus_US) # gets rid of the nested data frame
  constatus_CA <- as.data.frame(res$elementNationals$elementSubnationals[match("CA", res$elementNationals$nation$isoCode)])
  constatus_CA <- jsonlite::flatten(constatus_CA) # gets rid of the nested data frame
  # this handles species for which there are no conservation statuses...
  if(all(constatus_CA==0)&all(constatus_US==0)){
    cat("There is no conservation statuses for this species, skipping...\n")
  } else {
    # combine the US and CA data. 
    constatus <- bind_rows(constatus_US, constatus_CA)
    rm(constatus_US, constatus_CA) # clean up
    # select the lower of a seasonal rank
    
    library(stringr)
    constatus$smallest_number <- sapply(
      str_extract_all(constatus$roundedSRank, "[0-9]+"),
      function(x) min(as.integer(x))
    )
    constatus$roundedSRank <- ifelse(is.finite(constatus$smallest_number), paste("S",constatus$smallest_number, sep=""), constatus$roundedSRank) 
    
    # combine the SNR, SU, SNA status
    constatus$roundedSRank[which(constatus$roundedSRank=="SNRN")] <- "SNR/SU/SNA"
    constatus$roundedSRank[which(constatus$roundedSRank=="SNR")] <- "SNR/SU/SNA"
    constatus$roundedSRank[which(constatus$roundedSRank=="SU")] <- "SNR/SU/SNA"
    constatus$roundedSRank[which(constatus$roundedSRank=="SNA")] <- "SNR/SU/SNA"
    # make a ordered factor of all the sranks  #unique(constatus$roundedSRank)
    constatus$roundedSRank <- ordered(constatus$roundedSRank, levels=c("SX","SH","S1","S2","S3","S4","S5","SNR/SU/SNA"))
    
    tmpmap <- merge(template_RegionalStatus, constatus, by.x="subnation", by.y="subnation.subnationCode", all.x=TRUE)
    # build the plot
    a <- ggplot(data=tmpmap) +
      geom_sf(aes(fill=roundedSRank)) +
      scale_fill_manual(
        breaks=c("SX","SH","S1","S2","S3","S4","S5","SNR/SU/SNA"), 
        values=c("SX"="#666666", "SH"="#98928B", "S1"="#E96B6B", "S2"="#F7AD75", "S3"="#FDE26E", "S4"="#7CD6F5", "S5"="#668BB3", "SNR/SU/SNA"="#E5CFC3"),
        labels=c("Presumed Extirpated (SX)","Possibly Extirpated (SH)","Critically Imperiled (S1)","Imperiled (S2)","Vulnerable (S3)","Apparently Secure (S4)","Secure (S5)","No Status Rank (SNR/SU/SNA)"), drop=FALSE, na.value="white") + #
      theme_void() +
      theme(legend.position="right") +
      theme(legend.title=element_blank()) +
      theme(legend.text = element_text(size=8))
    # save the map as a png
    ggsave(filename=paste(here::here("_data","regRank"),"/","regRank_",gsub(" ","-",unique(snames$SNAME[i])),"_",gsub("-","",Sys.Date()),".png", sep=""), plot=a,
           width = 8,
           height = 6,
           units = c("in"),
           dpi = 200
    )
  }
  
}

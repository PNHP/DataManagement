# clear the environments
rm(list=ls())

if (!requireNamespace("arcgisbinding", quietly = TRUE)) install.packages("arcgisbinding")
require(arcgisbinding)
if (!requireNamespace("dplyr", quietly = TRUE)) install.packages("dplyr")
require(dplyr)
if (!requireNamespace("fuzzyjoin", quietly = TRUE)) install.packages("fuzzyjoin")
require(fuzzyjoin)
library(stringr)


# load the arcgis license
arc.check_product()

leps_data_path <- "P://Conservation Programs/Natural Heritage Program/Projects/Active projects/5276 SWG PFBC Invertebrate Species Assessment/Project Materials and Data/Lep Data/LepData.gdb/All_Moths_20240813_albers"
biotics_et <- "https://gis.waterlandlife.org/server/rest/services/PNHP/Biotics_EDIT/FeatureServer/5"
biotics_et <- "H:/temp/ET_20240813.csv"

leps_data <- arc.open(leps_data_path)
leps_data <- arc.select(leps_data)

et <- arc.open(biotics_et)
et <- arc.select(et)

et <- read.csv(biotics_et, stringsAsFactors=FALSE)

colnames(leps_data)[which(names(leps_data) == "PNHP_Scientific_Name__6_27_2024_")] <- "SNAME"
leps_data_join <- left_join(leps_data, select(et,c("SNAME","ELSUBID","ELCODE")), by = "SNAME")

sname_mismatches <- sort(unique(filter(leps_data_join, is.na(ELSUBID))$SNAME))

sname <- data.frame(sname_mismatches)

sname$sname_mismatches <- trimws(sname$sname_mismatches)
sname$sname_partial <- sub(".* ","",sname$sname_mismatches)
sname$sname_partial <- str_sub(sname$sname_partial, end = -2)

et$sname_partial <- sub(".* ","",et$SNAME)
et$sname_partial <- str_sub(et$sname_partial, end = -2)

partial_join <- left_join(sname, select(et,c("SNAME","ELSUBID","ELCODE","sname_partial")), by="sname_partial")
write.csv(partial_join,"P:/Conservation Programs/Natural Heritage Program/Projects/Active projects/5276 SWG PFBC Invertebrate Species Assessment/Project Materials and Data/Lep Data/sname_mismatches_20240813.csv")

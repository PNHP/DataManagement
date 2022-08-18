# load packages
if (!requireNamespace("arcgisbinding", quietly = TRUE)) install.packages("arcgisbinding")
require(arcgisbinding)
if (!requireNamespace("dplyr", quietly = TRUE)) install.packages("dplyr")
require(dplyr)
if (!requireNamespace("RSQLite", quietly=TRUE)) install.packages("RSQLite")
require(RSQLite)

# load the arcgis license
arc.check_product() 

et <- "W://Heritage//Heritage_Data//Biotics_datasets.gdb//ET"
db_name <- "W:/Heritage/Heritage_Data/CPP/CPP_Specs/CPP_SpecID.sqlite"
spec_folder <- "W:/Heritage/Heritage_Data/CPP/CPP_Specs"

#input = "C://Users//mmoore//Desktop//temp_databases//et_check//SpecID_Table.csv"
#input = read.csv(input,header=TRUE)
#input_filter <- input[input$TRACKING_STATUS!="",]

# load ET
et <- arc.open(et)
et <- arc.select(et)
et_filter <- filter(et,et$EO_TRACK != "N")

# load spec ids
db <- dbConnect(SQLite(), dbname = db_name)
SQLquery <- paste("SELECT ELSUBID, specid, specid_2, specid_3, specid_comments"," FROM SpecID_Table;")
spec_id <- dbGetQuery(db, statement = SQLquery)
dbDisconnect(db) # disconnect the db

# merge ET information with spec ids
spec_merge <- merge(x = spec_id, y = et, by = "ELSUBID", all.x = TRUE)
spec_columns <- c("ELSUBID","ELCODE","SNAME","SCOMNAME","specid","specid_2","specid_3","specid_comments","EO_TRACK","ER_RULE","GRANK","SRANK","USESA","SPROT","PBSSTATUS","PBSDATE","PBSQUAL","SGCN","SGCN_COM","SENSITV_SP")
spec_table <- spec_merge[,spec_columns]

date <- gsub("-","",Sys.Date())
spec_table_name <- paste0("SpecID_Table_",date,".csv")
write.csv(spec_table,paste(spec_folder,spec_table_name, sep = "/"),row.names=FALSE)

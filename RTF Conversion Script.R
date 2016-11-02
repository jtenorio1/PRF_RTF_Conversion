#install packages
install.packages("dplyr")
install.packages("tidyr")
install.packages("reshape2")

#load packages
suppressMessages(library(dplyr))
suppressMessages(library(tidyr))
suppressMessages(library(reshape2))

#----------------------------------------------------------------------------------------------------------------
#STEP1: first make the data frames to be used available and perform somecleaning of the columns

#IMPORT AND FORMAT RTF/PRF FILE
#import forecast data table and make the first row colnames
forecast <- tbl_df(CS89RTF1644)
forecast[5,3] <- forecast[5,2]
forecast <- forecast[!(is.na(forecast[,3]) | forecast[,3]==""), ]

#Create the workweek lookup table
workweeks <- forecast[1:2,]
workweeks <- workweeks[-c(1,2)]
workweeks <- t(workweeks)
workweeks <- tbl_df(workweeks)
colnames(workweeks) <- c("Workweek", "Date")
workweeks <- workweeks[-c(1),]
workweeks <- workweeks[!(is.na(workweeks[,2]) | workweeks[,2]==""), ]
workweeks <- workweeks %>% select(Date, everything())


#rename columns in forecast table
colnames(forecast) = forecast[2,]
forecast <- forecast[-c(1),]
forecast = forecast[-1,]

#drop blank colnames
drops <- c("NA", "")
forecast<- forecast[ , !(names(forecast) %in% drops)]

#Create MM matching/indexing column
mms <- forecast[,1]
mms <- mms[!(is.na(mms[,1]) | mms[,1]==""),]
mms$clength <- nchar(as.character(mms$`Due Date`))
mms <- mms[mms$clength == "6",]
mms <- mms[,-c(2)]
colnames(mms) <- "MM"

mmsrep <- rep(mms[,1],each = 6)
mmsrep <- data.frame(mmsrep)
mmsrep <- melt(mmsrep, id.var = c(), variable.name = "MM")
mmsvec <- mmsrep[['value']]
mmssort <- mms[['MM']]
mmscol <- mmsvec[order(match(mmsvec,mmssort))]
dfmmscol <- tbl_df(mmscol)
colnames(dfmmscol) <- "MM"

#finally remove any rows that don't represent a forecast indicator
colnames(forecast)[2] <- c("Forecast.Measure")

forecast <- forecast[
    forecast$Forecast.Measure == "PRFQTY" |
    forecast$Forecast.Measure == "RTFQTY" |
    forecast$Forecast.Measure == "Delta" |
    forecast$Forecast.Measure == "CummDelta" |
    forecast$Forecast.Measure == "Intel Comments" |
    forecast$Forecast.Measure == "Subcon Comments",
      ]

#Bind the MM column into forecast data and drop unneeded columns
forecast <- bind_cols(forecast,dfmmscol)
forecast <- forecast %>% select(MM, everything())
drops <- c("Due Date")
forecast <- forecast[,!(names(forecast) %in% drops)]

#IMPORT OPA Product Info File
OPA <- tbl_df(OPA.MM.Info)
colnames(OPA)[1] <- "MM"

#check it out
head(forecast)
str(RTF)

#----------------------------------------------------------------------------------------------------------------
#STEP 2: tidy up the RTF data file through transofrmations

#Unite MM and forecast, gather dates as rows, separate MM and forecast, spread the forecast type as columns
RPF_united <- forecast %>% unite(MM.Forecast, MM, Forecast.Measure, sep = "_") 
RPF_gathered <- RPF_united %>% gather(Date, value, 2:40) 
RPF_separated <- RPF_gathered %>% separate(MM.Forecast, c("MM", "Forecast.Type"))
RPF_spread <- RPF_separated %>%  spread(Forecast.Type, value)

RPF_ordered <- RPF_spread[,c(1,2,6,7,4,3,5,8)]


#----------------------------------------------------------------------------------------------------------------
#STEP 3: Format columns and add other columns needed for final output 

#join porduct info into RTF table for better product visibility
RPF_OPA <- merge(x = RPF_ordered, y = OPA[,c("MM", "Product.Type", "Product.Code")], by = "MM", all.x = TRUE)

#join porduct info into RTF table for better product visibility
RPF_OPA <- merge(x = RPF_OPA, y = workweeks[,c("Date", "Workweek")], by = "Date", all.x = TRUE)


#reorder cols in logical order
RPF_final <- RPF_OPA[,c(2,9,10,11,1,3,4,5,6,7,8)]

#sort by MM first, then by date 
RPF_final <- RPF_final[with(RPF_final, order(MM, Workweek)), ]

RPF_final <- transform(RPF_final, 
                       PRFQTY = as.numeric(PRFQTY), 
                       RTFQTY = as.numeric(RTFQTY), 
                       Delta = as.numeric(Delta),
                       CummDelta = as.numeric(CummDelta))

str(RPF_final)
head(RPF_final)

#----------------------------------------------------------------------------------------------------------------
#STEP 4: all done! Just need to save the converted RTF as a CSV. Make sure to name it properly. 

#save table as CSV
write.csv(RPF_final, file = "output.csv")






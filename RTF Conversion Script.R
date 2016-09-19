#install packages
install.packages("dplyr")
install.packages("tidyr")

#load packages
suppressMessages(library(dplyr))
suppressMessages(library(tidyr))

#----------------------------------------------------------------------------------------------------------------
#STEP1: first make the data frames to be used available and perform somecleaning of the columns

#IMPORT AND FORMAT RTF FILE
#import RTF data table and make the first row colnames
RTF <- tbl_df(input)
colnames(RTF) = RTF[1,]
RTF = RTF[-1,]

#drop blank colnames
drops <- c("NA")
RTF <- RTF[ , !(names(RTF) %in% drops)]

#IMPORT OPA Product Info File
OPA <- tbl_df(OPA.MM.Info)
colnames(OPA)[1] <- "MM"

#check it out
head(RTF)
str(RTF)

#----------------------------------------------------------------------------------------------------------------
#STEP 2: tidy up the RTF data file through transofrmations

#Unite MM and forecast, gather dates as rows, separate MM and forecast, spread the forecast type as columns
RTF_united <- RTF %>% unite(MM.Forecast, MM.Number, Forecast.Type, sep = "_") 
RTF_gathered <- RTF_united %>% gather(Date, value, 2:40) 
RTF_separated <- RTF_gathered %>% separate(MM.Forecast, c("MM", "Forecast.Type"))
RTF_spread <- RTF_separated %>%  spread(Forecast.Type, value)


#----------------------------------------------------------------------------------------------------------------
#STEP 3: Format columns and add other columns needed for final output 

#format Date as a date and insert a WWNum column
RTF_spread$Date <- as.Date(RTF_spread$Date, "%m-%d-%y")
x <- as.POSIXlt(RTF_spread$Date)
RTF_spread$WeekNum <- strftime(x, format = "%W")

#join porduct info into RTF table for better product visibility
RTF_OPA <- merge(x = RTF_spread, y = OPA[,c("MM", "Product.Type", "Product.Code")], by = "MM", all.x = TRUE)


#reorder cols in logical order
RTF_converted <- RTF_OPA[,c(1,10,11,9,2,6,7,4,3,5,8)]

#sort by MM first, then by date 
RTF_final <- RTF_converted[with(RTF_converted, order(MM, Date)), ]

RTF_final <- transform(RTF_final, 
                       PRFQTY = as.numeric(PRFQTY), 
                       RTFQTY = as.numeric(RTFQTY), 
                       Delta = as.numeric(Delta),
                       CummDelta = as.numeric(CummDelta),
                       WeekNum = as.numeric(WeekNum))

RTF_final$WeekNum <- RTF_final$WeekNum

str(RTF_final)
head(RTF_final)

#----------------------------------------------------------------------------------------------------------------
#STEP 4: all done! Just need to save the converted RTF as a CSV. Make sure to name it properly. 

#save table as CSV
write.csv(RTF_final, file = "output.csv")






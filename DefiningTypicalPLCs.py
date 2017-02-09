# -*- coding: utf-8 -*-
"""
Created on Wed Jul  6 12:16:02 2016

@author: dmogena
"""
import pandas as pd
import numpy as np
    
def main():
    #reading data from csv files
    open('DSS_Data.csv', 'r').readlines()
    data = pd.read_csv('DSS_Data.csv')
    open('DSS_quarterly_lifecycle.csv').readlines()    
    data_lifecycle = pd.read_csv('DSS_quarterly_lifecycle.csv')
    data = data.join(data_lifecycle[['avg_qty', 'avg_slope_slope', 'avg_cum_qty', 'decline_flag',
                                      'growth_flag', 'intro_flag', 'lifecycle', 'peak_period', 
                                      'slope', 'slope_slope', 'periods_to_peak']])                                  
    #Taking out skus for which there is not enough data for the life-cyle:        
    data_filtered = filter_data(data_lifecycle, data)
    #Adding calculated fields as columns
    data_filtered = calculated_fields(data_filtered)                                                                 
    #Saving filtered data in csv    
    data_filtered.to_csv('DSS_Data_Processed.csv', index = False) 
    #Filtering out noise-causing skus
    data_filtered = data_filtered[data_filtered['length'] > 2]
    #Grouping SKUs based on hierachy: vertical, mkt_seg and mkt_codename:    
    data_indexed = data_filtered.set_index(['VERTICAL', 'MKT_SEGMENT', 'MKTING_CD_NM'])
    hier_combinations = list(data_indexed.index.unique())
    #Grouping similar shape SKUs within each hierachy 
    result = pd.DataFrame()
    group_number = 0
    for hier in hier_combinations:
        specific_hier = data_indexed.loc[hier]
        sku_groups = sku_grouping(specific_hier, group_number)
        group_number =  max(group_number, sku_groups['group_index'].max())
        result = result.append(data_filtered.merge(sku_groups, on = 'hier_id'))
    result = result[result.columns[~result.columns.str.contains('Unnamed')]]  
    grouping_groups(result)
    
def filter_data(data_lifecycle, data):
       #second half of PLC
    data_max = data.iloc[data.groupby('hier_id')['qty'].agg(pd.Series.idxmax)]
    data_max = data_max.loc[data_max['QUARTER'] != '2016Q1']
    data_max = data_max.loc[data_max['QUARTER'] != '2016Q2']
    data_max_filter = list(data_max.hier_id.unique())
    data_filtered = data.loc[data['hier_id'].isin(data_max_filter)]
       #first half of PLC
    return data_filtered.loc[~data_filtered['start_period'].str.contains('2010')]
    
def calculated_fields(data_filtered):
    #Setting quarter_number column       
    quarters =  pd.DataFrame(sorted(data_filtered.QUARTER.unique()))
    quarters.index += 1
    quarters = quarters.reset_index()
    quarters = quarters.rename(columns = {'index' : 'quarter_no', 0:'QUARTER'}) 
    data_filtered = data_filtered.merge(quarters, on = 'QUARTER') 
    #Setting 'start_period_no' by SKU column
    quarter_norm_sku = data_filtered.groupby(['hier_id'])['quarter_no'].min()
    quarter_norm_sku = quarter_norm_sku.reset_index()
    quarter_norm_sku = quarter_norm_sku.rename(columns = {'quarter_no' : 'start_period_no'})
    data_filtered = data_filtered.merge(quarter_norm_sku, on = 'hier_id')
    data_filtered['quarter_norm_sku'] = data_filtered['quarter_no'] - data_filtered['start_period_no'] + 1      
    #Setting 'qty_max' and 'qty_max_bucket' by SKU column
    qty_max = data_filtered.groupby(['hier_id'])['qty'].max()
    qty_max = qty_max.reset_index()
    qty_max = qty_max.rename(columns = {'qty' : 'qty_max'}) 
    qty_max['qty_max_bucket'] = np.ceil(np.log10(qty_max['qty_max']))
    data_filtered = data_filtered.merge(qty_max, on = 'hier_id')   
    #Setting 'qty_norm_sku' column
    data_filtered['qty_norm_sku'] = data_filtered.qty / data_filtered.qty_max
    #Setting last_period by SKU column
    last_periods = data_filtered.groupby(['hier_id'])['quarter_no'].max()
    last_periods = last_periods.reset_index()
    last_periods = last_periods.rename(columns = {'quarter_no':'last_period_no'})
    data_filtered = data_filtered.merge(last_periods, on = 'hier_id')
    #Separating start_period format into year and quarter
    data_filtered['start_period_year'] = data_filtered.start_period.str[0:4]  
    data_filtered['start_period_quarter'] = data_filtered.start_period.str[4:6]     
    #Separating peak_period format into year and quarter
    data_filtered.peak_period.to_string()
    data_filtered['peak_period_year'] = data_filtered.peak_period // 100 
    data_filtered['peak_period_quarter'] = "Q" + data_filtered['peak_period'].astype(str).str[5:6]
    #Setting length column
    lengths = data_filtered.groupby(['hier_id'])['quarter_norm_sku'].max()
    lengths = lengths.reset_index()
    lengths = lengths.rename(columns = {'quarter_norm_sku' : 'length'})
    data_filtered = data_filtered.merge(lengths, on = 'hier_id') 
    #Defining overall top skus by 80% volume                                    
    data_filtered = top_skus(data_filtered, data_filtered, 'top80_flag')
    data_filtered = top_skus(data_filtered, data_filtered.loc[data_filtered['VERTICAL'] == 'DT'], 'top80_DT_flag')    
    data_filtered = top_skus(data_filtered, data_filtered.loc[data_filtered['VERTICAL'] == 'Mb'], 'top80_MB_flag')    
    data_filtered = top_skus(data_filtered, data_filtered.loc[data_filtered['VERTICAL'] == 'SvrWS'], 'top80_SERVER_flag')  
    #Setting growth_flag
    lifecycle_flag = pd.DataFrame(columns = ('hier_id','growth_flag', 'mature_flag', 'decline_flag')) 
    for hier_id in data_filtered.hier_id.unique(): 
        hier_id_data = data_filtered.loc[data_filtered['hier_id'] == hier_id][['lifecycle']].set_index('lifecycle')
        if 'growth' in hier_id_data.index:
            growth_bool_flag = 1
        else:
            growth_bool_flag  = 0   
        if 'mature' in hier_id_data.index:
            mature_bool_flag = 1
        else:
            mature_bool_flag = 0   
        if 'decline' in hier_id_data.index:
            decline_bool_flag = 1
        else:
            decline_bool_flag = 0       
        lifecycle_flag.loc[hier_id] = [hier_id, growth_bool_flag, mature_bool_flag, decline_bool_flag]
    data_filtered = data_filtered.drop('growth_flag', axis=1)    
    data_filtered = data_filtered.drop('decline_flag', axis=1)
    data_filtered = data_filtered.merge(lifecycle_flag, on = 'hier_id', how = 'left')
    #Setting total_volume and colum_bucket column    
    tot_vol = data_filtered.groupby('hier_id')['qty'].sum()   
    tot_vol = tot_vol.reset_index()
    tot_vol = tot_vol.rename(columns = {'qty' : 'volume'})
    tot_vol['vol_bucket'] = np.ceil(np.log10(tot_vol['volume']))
    data_filtered = data_filtered.merge(tot_vol, on = 'hier_id', how = 'left').fillna(0)       
    #Setting bulk_volume column
    bulk_volume = tot_vol.set_index('hier_id') * 0.95
    length_bulk = pd.DataFrame(columns = ('hier_id','length_bulk'))
    for hier_id in data_filtered.hier_id.unique():    
        hier_id_data = data_filtered.loc[data_filtered['hier_id'] == hier_id][['quarter_norm_sku','cum_qty','rev_cum_qty']].set_index('quarter_norm_sku')
        last_bulk_quarter = hier_id_data[hier_id_data['cum_qty'] > bulk_volume.loc[hier_id][0]].index[0]
        first_bulk_quarter = hier_id_data[hier_id_data['rev_cum_qty'] > bulk_volume.loc[hier_id][0]].index[0]
        length_bulk.loc[hier_id] = [hier_id, last_bulk_quarter - first_bulk_quarter + 1]
    data_filtered = data_filtered.merge(length_bulk, on = 'hier_id', how = 'left')
    return data_filtered
    
def top_skus(data_filtered, data, column_name):
    tot_vol = data.groupby('hier_id')['qty'].sum() 
    tot_vol = tot_vol.sort_values(ascending = False)  
    top_volume = tot_vol.sum() * 0.80
    top_80_hier = tot_vol.cumsum(axis = 0)
    top_80_hier = pd.DataFrame(top_80_hier[top_80_hier < top_volume])
    top_80_hier[column_name] = 1
    top_80_hier = top_80_hier.reset_index()
    top_80_hier = top_80_hier.drop('qty', 1)
    return data_filtered.merge(top_80_hier, on = 'hier_id', how = 'left').fillna(0)    
    
def sku_grouping(specific_hier, group_number):
    #constants    
    corr_treshold = 0.95
    group_len_treshold = 3
    pivot1 = pd.pivot_table(specific_hier, 'qty','hier_id','QUARTER', sum ).fillna(0)
    solitaries = []
    seen = []
    groups = []
    if len(pivot1) > 1:   
        #correlation matrix
        corr_matrix = np.corrcoef(pivot1)
        bool_corr_matrix = np.zeros(corr_matrix.shape,'i')   
        for index1 in range(len(corr_matrix)):
          for index2 in range(len(corr_matrix)):
               if corr_matrix[index1,index2] > corr_treshold and corr_matrix[index1,index2] != 1:
                  bool_corr_matrix[index1,index2] = 1            
        no_of_matches = np.sum(bool_corr_matrix, axis = 1)
        for index in range(len(corr_matrix)):
            if  no_of_matches[index] == 0:
                solitaries.append(index)
            else:
                temp = []
                temp.append(index)
                temp.extend(np.where(bool_corr_matrix[:,index] > 0)[0])
                if set(temp).isdisjoint(set(seen)): #if none of the items in temp are in seen
                    groups.append(temp)         
                else: #add to the group where there's a match
                   for group in range(len(groups)):            
                       if not set(temp).isdisjoint(set(groups[group])):
                         groups[group] = sorted(list(set(groups[group]).union(temp)))               
                seen = sorted(list(set(seen).union(temp)))    
    final_groups = []
    if groups: 
        final_groups = [groups[0]]
        for group in range(1,len(groups)):
            hasbeenadded = False
            for final_group in range(len(final_groups)):
                if not set(groups[group]).isdisjoint(set(final_groups[final_group])):
                    final_groups[final_group] = sorted(list(set(final_groups[final_group]).union(groups[group])))
                    hasbeenadded = True 
            if not hasbeenadded:
                final_groups.append(groups[group])
        
        small_group_index = np.where(np.array([len(x) for x in final_groups]) < group_len_treshold)[0]
        for x in small_group_index:
            solitaries.extend(final_groups[x])    
        final_groups = [i for j, i in enumerate(final_groups) if j not in small_group_index]           
    sku_groups = pd.DataFrame(pivot1.index)    
    sku_groups["group_index"] = 0
    for i in enumerate(final_groups):
        for j in enumerate(i[1]):   
            sku_groups.set_value(j[1] ,'group_index', i[0] + 1 + group_number)                        
    return sku_groups

def grouping_groups(data_filtered):
    #Constants:
    corr_treshold = 0.95
    group_len_treshold = 3    
    #Normalizing start_period for each group:   
    data_filtered['start_period_norm_group'] = 0
    start_periods_groups = data_filtered.groupby(['group_index'])['start_period_no'].min()
    for i in data_filtered.index:
        data_filtered.set_value(i,'start_period_norm_group',start_periods_groups[data_filtered.loc[i, 'group_index']])  
    #Normalizing quarter for each group:           
    data_filtered['quarter_norm_group'] = data_filtered['quarter_no'] - data_filtered['start_period_norm_group'] + 1
    #Pivoting data:
    pivot1 = pd.pivot_table(data_filtered, 'qty','group_index','quarter_norm_group',sum ).fillna(0)
    pivot1 = pivot1[pivot1.index > 0]
    solitaries = []
    seen = []
    groups = [] 
    #correlation matrix:
    corr_matrix = np.corrcoef(pivot1) 
    #Creating Boolean matrix for correlation coefficient greater than defined corr_treshold   
    bool_corr_matrix = np.zeros(corr_matrix.shape,'i')   
    for index1 in range(len(corr_matrix)):
      for index2 in range(len(corr_matrix)):
           if corr_matrix[index1,index2] > corr_treshold and corr_matrix[index1,index2] != 1:
              bool_corr_matrix[index1,index2] = 1       
    no_of_matches = np.sum(bool_corr_matrix, axis = 1)
    for index in range(len(corr_matrix)):
        if  no_of_matches[index] == 0:
            solitaries.append(index)
        else:
            temp = []
            temp.append(index)
            temp.extend(np.where(bool_corr_matrix[:,index] > 0)[0])
            if set(temp).isdisjoint(set(seen)): #if none of the items in temp are in seen
                groups.append(temp)         
            else: #add to the group where there's a match
               for group in range(len(groups)):            
                   if not set(temp).isdisjoint(set(groups[group])):
                     groups[group] = sorted(list(set(groups[group]).union(temp)))               
            seen = sorted(list(set(seen).union(temp)))    
    #Grouping sku groups based on correlation coefficient:
    final_groups = []
    if groups: 
        final_groups = [groups[0]]
        for group in range(1,len(groups)):
            hasbeenadded = False
            for final_group in range(len(final_groups)):
                if not set(groups[group]).isdisjoint(set(final_groups[final_group])):
                    final_groups[final_group] = sorted(list(set(final_groups[final_group]).union(groups[group])))
                    hasbeenadded = True 
            if not hasbeenadded:
                final_groups.append(groups[group])
        
        small_group_index = np.where(np.array([len(x) for x in final_groups]) < group_len_treshold)[0]
        
        for x in small_group_index:
            solitaries.extend(final_groups[x])    
        
        final_groups = [i for j, i in enumerate(final_groups) if j not in small_group_index]   
    group_groups = pd.DataFrame(pivot1.index)    
    group_groups["groups_grouped_index"] = 0
    for i in enumerate(final_groups):
        for j in enumerate(i[1]):   
            group_groups.set_value(j[1] ,"groups_grouped_index", i[0] + 1)    
    #Putting it al together ino a CSV file:
    result = pd.DataFrame()
    result = result.append(data_filtered.merge(group_groups, on = 'group_index'))
    result = result[result.columns[~result.columns.str.contains('Unnamed')]]
    result.to_csv('DSS_Data_Grouped_Groups.csv', index=False)  

main()


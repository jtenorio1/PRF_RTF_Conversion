# -*- coding: utf-8 -*-
"""
Created on Thu Jul 14 15:12:25 2016

@author: dmogena
"""
import pandas as pd
import numpy as np
import DefiningTypicalPLCs
DefiningTypicalPLCs

def main():    
    #Opening and selecting data:  
    open('DSS_Data_Grouped_Groups.csv', 'r').readlines()
    data_grouped_groups = pd.read_csv('DSS_Data_Grouped_Groups.csv')
    open('DSS_Data_Processed.csv', 'r').readlines()
    data = pd.read_csv('DSS_Data_Processed.csv')
    #Pivoting data:
    pivoted_data_grouped_groups = pd.pivot_table(data_grouped_groups, 'qty','quarter_norm_group', 'groups_grouped_index', sum).fillna(0)
    del pivoted_data_grouped_groups[0]
    #Normalizing pivoted data, which are the PLC types:
    plc_types = pivoted_data_grouped_groups /(np.max(pivoted_data_grouped_groups,0))
    plc_types.columns = ['TRADITIONAL','EXTENDED FAD','FAD','CONSERVATIVE']
    #
    pivoted_data = pd.pivot_table(data, 'qty','quarter_norm_sku', 'hier_id', sum).fillna(0)
    pivoted_data = pivoted_data/np.max(pivoted_data,0)
    plc_assignments = pd.DataFrame()
    iterables = [['PLC_type','PLC_var'],range(-13,8)] 
    plc_assignments = pd.DataFrame(columns = pd.MultiIndex.from_product(iterables))
    plc_assignments['Bestfit_type', 'Bestfit_var'] = None  
    for hier in data.hier_id.unique():
        hier_qty_original = pivoted_data[hier]
        hier_qty_offset = hier_qty_original    
        length_offset = hier_qty_original.astype(bool).sum(axis=0)    
        if max_position(hier_qty_original) < 9:
            i = 0
            while max_position(hier_qty_offset)  < 9 and i < 5:
                hier_qty_offset = hier_qty_original.shift(i).fillna(0)   
                plc_details = assign_plc_type(hier_qty_offset, plc_types)
                plc_assignments.set_value(hier, ('PLC_type', i), plc_details[0])
                plc_assignments.set_value(hier, ('PLC_var', i), plc_details[1])
                i += 1   
            i=-1
            while max_position(hier_qty_offset) > 2 and max_position(hier_qty_original) > 2 and length_offset > 3 and i > -5:
                hier_qty_offset = hier_qty_original.shift(i).fillna(0)   
                length_offset = hier_qty_offset.astype(bool).sum(axis=0)
                plc_details = assign_plc_type(hier_qty_offset, plc_types)
                plc_assignments.set_value(hier, ('PLC_type', i), plc_details[0])
                plc_assignments.set_value(hier, ('PLC_var', i), plc_details[1])
                i -= 1 
        else:
            i = 0    
            while max_position(hier_qty_offset) > 2  and length_offset > 2 and i > -5:
                hier_qty_offset = hier_qty_original.shift(i).fillna(0)
                length_offset = hier_qty_offset.astype(bool).sum(axis=0)
                plc_details = assign_plc_type(hier_qty_offset, plc_types)
                plc_assignments.set_value(hier, ('PLC_type', i), plc_details[0])
                plc_assignments.set_value(hier, ('PLC_var', i), plc_details[1])
                i -= 1             
    bestfit_var_loc = plc_assignments['PLC_var'].idxmin(axis = 1)
    plc_assignments['Bestfit_type', 'Bestfit_var'] = plc_assignments['PLC_var'].min(axis = 1)
    bestfit_var = plc_assignments['PLC_var'].min(axis = 1)       
    bestfit_type = []        
    for i in bestfit_var_loc.index:
        if np.isnan(bestfit_var_loc[i]) or bestfit_var[i] > .05:
            bestfit_type.append('NA')
        else:
            bestfit_type.append(plc_assignments['PLC_type'][bestfit_var_loc[i]][i])
    bestfit = pd.DataFrame({'PLC_var': bestfit_var, 'PLC_shape': bestfit_type, 'PLC_offset': bestfit_var_loc})
    bestfit['hier_id'] = bestfit.index
    result = data.merge(bestfit, on ='hier_id', how = 'left').fillna('NA')
    result[result.columns[~result.columns.str.contains('Unnamed')]] 
    result_pivoted = pd.pivot_table(result, 'qty',['hier_id','VERTICAL', 'MKT_SEGMENT', 'MKTING_CD_NM', 
                                                 'SERVER_MARKET_SEGMENT', 'SHIP_TGT_FAMILY', 'MMBP_DMD_FCST_FAM',      
                                                 'SKU', 'BRAND','PROCESSOR_NUMBER', 'SPEED', 'CACHE', 
                                                 'PACKAGE', 'CORE_NUMBER', 'MEMORY_SPEED', 'WATTAGE', 'GRAPHICS',
                                                 'GRAPHICS_SPEED', 'GRAPHICS_SRC_DIE', 'THREAD_NO',
                                                 'PRICE_SEGMENT', 'PLC_shape', 'PLC_var', 'PLC_offset',
                                                 'length', 'length_bulk', 'qty_max', 'qty_max_bucket', 'start_period_year',
                                                 'start_period_quarter', 'start_period_no', 'last_period_no', 
                                                 'volume', 'vol_bucket', 'peak_period_year', 'peak_period_quarter', 'periods_to_peak',
                                                 'top80_flag', 'top80_DT_flag', 'top80_MB_flag', 'top80_SERVER_flag',
                                                 'growth_flag', 'mature_flag', 'decline_flag']
                                                 ,'QUARTER', sum).fillna(0)
    result_pivoted = result_pivoted.stack()
    result_pivoted = result_pivoted.reset_index()
    result_pivoted = result_pivoted.rename(columns = { 0 : 'qty'})
    result = result_pivoted.merge(result, how = 'left').fillna(0)   
    result['PLC_var_bucket'] = round(result['PLC_var']*100,0)
    result.to_csv('DSS_Data_SKU_Lifecycle.csv', index = False)     
    
def max_position(hier_qty):
    return hier_qty[hier_qty == 1].index[0]
    
def assign_plc_type(hier_qty_norm, plc_types):
    product = plc_types.multiply(hier_qty_norm,axis=0)
    product_bool = product.where(product==0 ,1)
    delta = (plc_types.sub(hier_qty_norm,axis=0))*product_bool
    fit_var = (delta**2).sum(axis=0) / (product_bool.ix[:,0].sum()-1)
    return [fit_var.idxmin(), fit_var.min()]

main()

import pandas as pd
from IPython.display import display
import matplotlib.pyplot as plt
import numpy as np
from pyDOE import lhs
import math

#Magic Numbers
min_volume = 5     #uL per well
max_volume = 1200  #uL per well

#Transfer Volume (Property of the Pipette)
#Might want to make a Pipette Class
min_transfer = 5   #uL
max_transfer = 180 #uL

#Plate Limits
#This should probably be cleaned up
dead_volume = 50 #uL
safety_factor = 2 
DILUTION_SAFETY_FACTOR = 2
ideal_transfer_volume = 8 #uL
dilution_volume = ideal_transfer_volume


#Biomek Robot Object, Stores the State of the Robot and All plates that are on it.
class BioMek(object):
    
    def __init__(self,deck_df):
        self.deck_df = deck_df.loc[~deck_df['Target'],deck_df.columns != 'Target']
        self.goal_df = deck_df.loc[ deck_df['Target'],deck_df.columns != 'Target']
        #self.water_wells =
        
        transfer_columns = ['srcpos','srcwell','destpos','destwell','vol']
        self.transfer_df = pd.DataFrame(columns=transfer_columns)
        
        
    def transfer(self, source_plate, source_well, dest_plate, dest_well, transfer_volume):
        total_transfered = 0 #uL
        
        #Check to see if there is enough volume for the transfer!
        if transfer_volume > (self.deck_df.loc[(source_plate,source_well)]['Volume'] + dead_volume):
            raise('Transfer Pulling Too Much Volume! {}'.format(transfer_volume))
        
        
        #Add Transfer To Ledger
        while total_transfered < transfer_volume:
            if transfer_volume - total_transfered > max_transfer:
                values = [source_plate,source_well,dest_plate,dest_well,max_transfer]
                total_transfered += max_transfer
            else:
                values = [source_plate,source_well,dest_plate,dest_well,transfer_volume-total_transfered]
                total_transfered += transfer_volume-total_transfered
            
            self.transfer_df = self.transfer_df.append(dict(zip(self.transfer_df.columns,values)),ignore_index=True)
            
        
        #Update Deck State
        source_composition = self.deck_df.xs((source_plate,source_well))
        transfer = source_composition*(transfer_volume/source_composition['Volume'])

        self.deck_df.loc[(source_plate,source_well)] -= transfer
        try:
            self.deck_df.loc[(dest_plate  ,dest_well  )] += transfer
        except:
            columns = self.deck_df.reset_index().columns
            data = [dest_plate,dest_well] + [0]*(len(columns) - 2)
            new_well = pd.DataFrame(dict(zip(columns,data)),index=[0]).set_index(['Plate','Well']) + transfer
            self.deck_df = self.deck_df.append(new_well)
            
    
    def get_well_state(self,plate,well):
        
        try:
            return self.deck_df.loc[(dest_plate,dest_well)]
        except:
            columns = self.deck_df.reset_index().columns
            data = [dest_plate,dest_well] + [0]*(len(columns) - 2)
            new_well = pd.DataFrame(dict(zip(columns,data)),index=[0]).set_index(['Plate','Well'])
            self.deck_df = self.deck_df.append(new_well)
        return self.deck_df.loc[(dest_plate,dest_well)]
            
    
    def transfer_water(self,dest_plate,dest_well,transfer_volume):
        total_transfered = 0
        
        while total_transfered < transfer_volume:
            if transfer_volume - total_transfered > max_transfer:
                water_plate, water_well = self.find_water(max_transfer)
                self.transfer(water_plate,water_well,dest_plate,dest_well,max_transfer)
                total_transfered += max_transfer
            else:
                water_plate, water_well = self.find_water(transfer_volume - total_transfered)
                self.transfer(water_plate,water_well,dest_plate,dest_well,transfer_volume - total_transfered)
                total_transfered += transfer_volume - total_transfered
                
            
    def dilute(self,reagent_wells,solute,moles_needed,transfer_volume=ideal_transfer_volume):
        '''Creates a Diluted Version of the Source Plate'''
        
        #Find The Right Well
        ENOUGH_VOLUME = reagent_wells['Volume'] > min_volume * safety_factor + transfer_volume
        reagent_wells = reagent_wells.loc[ENOUGH_VOLUME]
        reagent_wells['dilution_factor'] = reagent_wells[solute]/reagent_wells['Volume']

        #Calculate Required transfer volume
        #source = reagent_wells['dilution_factor'].idxmin()
        #source = self.deck_df.loc[(source_plate,source_well)]
        #source_well_moles = source[solute]
        
        reagent_wells['dilution_volume'] = moles_needed*max_volume*reagent_wells['Volume']/(transfer_volume*reagent_wells[solute])
        #display(reagent_wells)
        reagent_wells = reagent_wells.loc[reagent_wells['dilution_volume'] < (reagent_wells['Volume'] - dead_volume)]
        #display('after',reagent_wells)
        
        if len(reagent_wells) == 0:
            reagent=solute
            print(solute)
            REAGENT_WELL = (self.deck_df.loc[:,~biomek.deck_df.columns.isin([reagent,'Volume'])] == 0).all(1)
            CONTAINS_REAGENT = (biomek.deck_df.loc[:,biomek.deck_df.columns == reagent] > 0).any(1)
            reagent_wells = self.deck_df.loc[REAGENT_WELL & CONTAINS_REAGENT]
            display(reagent_wells)
            raise('Not Enough {}! Add More To Reagent Plate.'.format(solute))        
        
        
        source = reagent_wells['dilution_factor'].idxmin()
        dilution_volume = max(min_volume,reagent_wells.loc[source]['dilution_volume'])
        
        #display(reagent_wells)
        #print('Dilution Performed!, Volume: {}'.format(dilution_volume))
        
        #Check to see if dilution volume is above minimum volume
        #if dilution_volume < min_volume:
        #    dilution_volume = min_volume
        
        
        
        
        #Transfer into New Well
        dilution_plate, dilution_well = self.allocate_well()
        self.transfer(*source,dilution_plate,dilution_well,dilution_volume)
        
        #Fill With Water
        self.transfer_water(dilution_plate,dilution_well,max_volume - dilution_volume)
        

    def allocate_well(self):
        '''Allocate a New Well'''
        plate = 'mixing_plate'
        try:
            well = len(self.deck_df.loc[plate])+1
        except:
            well = 1
            
        if well > 96:
            display(biomek.deck_df)
            display(self.transfer_df)
            raise('Too Many Wells: Implement New Plate Method')
        return (plate,well)
    
    def find_water(self,transfer_volume):
        WATER_WELL = (self.deck_df.loc[:,~self.deck_df.columns.isin(['Volume'])] == 0).all(1) & (self.deck_df.loc[:,self.deck_df.columns == 'Volume'] > (transfer_volume+dead_volume)).any(1)
        source = self.deck_df[WATER_WELL].iloc[0]
        return source.name
    
    
def concentration_to_moles(df):
    #Convert NaNs to Zeros
    df = df.fillna(value=0)
    
    #Convert Molar Concentrion to Moles
    for column in df.loc[:,~df.columns.isin(['Volume','Target'])].columns:
        df.loc[:,column] = df[column]*df['Volume']*1e-6
    return df


def read_deckfile(deck_file):
    deck_df = pd.read_csv(deck_file)
    deck_df = deck_df.set_index(['Plate','Well'])
    deck_df = concentration_to_moles(deck_df)
    return deck_df


def generate_biomek_csvs(biomek):
    #Generate 5 CSVs for BIOMEK
    water_mix_df  = biomek.transfer_df.loc[(biomek.transfer_df['destpos']=='mixing_plate') & (biomek.transfer_df['srcpos']=='water_plate')]
    water_dest_df = biomek.transfer_df.loc[(biomek.transfer_df['destpos']=='dest_plate') & (biomek.transfer_df['srcpos']=='water_plate')]
    mix_df =   biomek.transfer_df.loc[(biomek.transfer_df['destpos']=='mixing_plate') & (biomek.transfer_df['srcpos']!='water_plate')]
    src_df = biomek.transfer_df.loc[(biomek.transfer_df['destpos']=='dest_plate') & (biomek.transfer_df['srcpos']=='src_plate')] 
    dest_df =  biomek.transfer_df.loc[(biomek.transfer_df['destpos']=='dest_plate') & (biomek.transfer_df['srcpos']=='mixing_plate')]
    
    #line terminator required for csvs to be read by biomek software properly...
    water_mix_df.to_csv('biomek_files/water_mix.csv',index=False,line_terminator='\r\n')
    water_dest_df.to_csv('biomek_files/water_dest.csv',index=False,line_terminator='\r\n')
    mix_df.to_csv('biomek_files/mix.csv',index=False,line_terminator='\r\n')
    src_df.to_csv('biomek_files/src.csv',index=False,line_terminator='\r\n')
    dest_df.to_csv('biomek_files/dest.csv',index=False,line_terminator='\r\n')
    
    #Generate Tip Report
    import math
    print('')
    print('Tips Needed By Subrutine')
    operations = ['Adding Water To Mixing Plate (Done with 8 tips in method)','Adding Water to Destination Plate (Done with 8 Tips)','Diluting Stock Solutions','Adding Undilute Media To Dest','Mixing Final Media']
    for df,op in zip([water_mix_df,water_dest_df,mix_df,src_df,dest_df],operations):
        boxes = math.ceil(len(df)/96)
        print('{}: {} Tips,  {} Plates'.format(op,len(df),boxes))

    total_tips = 16 + len(mix_df) + len(dest_df)
    total_tips = len(biomek.transfer_df)
    print('')
    print('Overall Experiment Need')
    print('Total Tips Needed:',total_tips)
    print('Tip Plates Consumed:',math.ceil(total_tips/96))    
    

def compile_media(deck_df):
    biomek = BioMek(deck_df)
    #display(biomek.goal_df)
    #Iterate Through Destination Wells
    for (dest_plate,dest_well),solution in biomek.goal_df.iterrows():
        #print(dest_plate,dest_well)

        #Find Solute & Moles Needed
        for i,(reagent,moles) in enumerate(solution.loc[solution.index != 'Volume'].iteritems()):
            while moles > 0:

                #Get All Reagent Wells
                REAGENT_WELL = (biomek.deck_df.loc[:,~biomek.deck_df.columns.isin([reagent,'Volume'])] == 0).all(1)
                CONTAINS_REAGENT = (biomek.deck_df.loc[:,biomek.deck_df.columns == reagent] > 0).any(1)
                reagent_wells = biomek.deck_df.loc[REAGENT_WELL & CONTAINS_REAGENT]

                #See There Are Enough Moles in The Reagent Wells ON Deck from any Well
                reagent_wells = reagent_wells.loc[reagent_wells[reagent] > moles]


                if len(reagent_wells):
                    #Find Wells require above the minimum pipette volume
                    reagent_wells['volume_needed'] = reagent_wells['Volume']*(moles/reagent_wells[reagent])
                    ENOUGH_VOLUME = (reagent_wells['Volume'] - dead_volume > reagent_wells['volume_needed'])
                    source_wells = reagent_wells.loc[(reagent_wells['volume_needed'] > min_volume) & (reagent_wells[reagent] > moles) & ENOUGH_VOLUME]

                    #Find Wells With Enough Volume For Transfer
                    source_wells = source_wells.loc[source_wells['volume_needed'] < (source_wells['Volume'] - dead_volume)]

                    if len(source_wells):

                        #Get Least Dilute Well
                        source = source_wells['volume_needed'].idxmin()
                        transfer_volume = source_wells.loc[source]['volume_needed']

                        #Perform Transfer
                        biomek.transfer(*source,dest_plate,dest_well,transfer_volume)

                        break

                    else:
                        biomek.dilute(reagent_wells,reagent,moles,transfer_volume=ideal_transfer_volume)




                else:
                    print(solute,moles)
                    display(reagent_wells)
                    display(biomek.transfer_df)
                    display(biomek.deck_df.loc['src_plate'])
                    raise('No Valid Well')

        #Fill Remaining Volume with Water
        transfer_volume = biomek.goal_df.loc[(dest_plate,dest_well)]['Volume'] - biomek.deck_df.loc[(dest_plate,dest_well)]['Volume']
        biomek.transfer_water(dest_plate,dest_well,transfer_volume)
        
    #Create CSVs Needed
    generate_biomek_csvs(biomek)
        
def generate_initial_media(media_component_file,NUM_MEDIA=16,OVERLAY_VOLUME = 200,REAGENT_VOLUME = 1000,WELL_VOLUME = 1100,WATER_VOLUME = 1600,EXTRA_WELLS = {},OUTFILE='data/media.csv',DECKFILE='data/wells.csv',WATER_WELLS=96):
    media_df = pd.read_csv(media_component_file)
    
    #Create Source Plate
    columns = ['Plate','Well'] + [c for c in media_df['Media Components']] + ['Volume','Target']
    df = pd.DataFrame(columns=columns)

    #Work in mM concentrations
    well = 1
    for i,component in media_df.iterrows():    
        if component['Media Components'] in EXTRA_WELLS:
            for _ in range(EXTRA_WELLS[component['Media Components']]):
                row = {'Plate':'src_plate',
                       'Well':well,
                       'Volume':REAGENT_VOLUME,
                       'Target':False,
                       component['Media Components']:component['Master Solution Concentration [M]']*1e3,
                      }
                df = df.append(row, ignore_index=True)
                well +=1 
        else:
            row = {'Plate':'src_plate',
                   'Well':well,
                   'Volume':REAGENT_VOLUME,
                   'Target':False,
                   component['Media Components']:component['Master Solution Concentration [M]']*1e3,
                  }
            df = df.append(row, ignore_index=True)
            well +=1
    df = df.fillna(0)
    
    
    # Create DataFrame to Help Make Reagent Plate By Hand!
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    well_df = df.loc[:,~df.columns.isin(['Target','Volume'])].melt(id_vars=['Plate','Well'])
    well_df = well_df.loc[well_df['value']!=0].rename(columns={'variable':'Reagent'})#.set_index(['Plate','Well'])['Reagent'].to_frame()
    well_df = well_df.rename(columns={'Well':'Well Number'})

    #
    well = lambda x: '{}{}'.format(letters[int((x-1)/12)],(x-1)%12 + 1)
    well_df['Well'] = well_df['Well Number'].apply(well)
    well_df = well_df[['Plate','Well','Well Number','Reagent']]
    #display(well_df)
    
    #Create Water Plate
    for i in range(WATER_WELLS):
        row = {'Plate':'water_plate',
               'Well':i+1,
               'Volume':WATER_VOLUME,
               'Target':False,
              }
        df = df.append(row, ignore_index=True)
    df = df.fillna(0)

    n=len(media_df)
    media_array = lhs(n,NUM_MEDIA).tolist()
    m_df = media_df
    media_molarity = [((m_df['Max Concentration [mM]'] - m_df['Min Concentration [mM]'])* m + m_df['Min Concentration [mM]']).tolist() for m in media_array]  
    #print(media_molarity)

    media_data = media_molarity
    
    #Create Robolector Plate
    for i,media in enumerate(media_data):
        base_well = (math.floor((i)/8)*24 + (i) % 8) + 1
        for j in range(3):
            row = ['dest_plate',base_well + 8*j] + media_data[i] + [WELL_VOLUME,True]
            df = df.append(dict(zip(columns,row)),ignore_index=True)
            
    #Sort DF Columns By Concentration
    #sorted_components = media_df.sort_values('Min_Dilution_Factor')['Media Components']
    sorted_components = media_df['Media Components']
    column_reorder = ['Plate','Well'] + sorted_components.tolist() + ['Volume','Target']
    df = df[column_reorder]
    
    #Write out Initial Media Configuration
    df.to_csv(OUTFILE,index=False)
    well_df.to_csv(DECKFILE,index=False)
    df = df.set_index(['Plate','Well'])
    df = concentration_to_moles(df)
    return df
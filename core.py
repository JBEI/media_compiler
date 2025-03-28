from enum import Enum
from typing import List, Dict
from math import ceil, floor
import string
import pandas as pd
import numpy as np
from pyDOE import lhs
import matplotlib.pyplot as plt


pip_volume_threshold = 50  # threshold for using p300 above that volume
mix_times: int = 3         # number of times for mixing
rel_mix_volume = 0.75      # mixing volume, relative to the well volume


def find_volumes(well_volume: float,
                 stock_conc_file: str=None,
                 target_conc_file: str=None,
                 components: list=None,
                 stock_conc_val: np.ndarray=np.empty,
                 target_conc_val: np.ndarray=np.empty,
                 target_conf_df: pd.DataFrame=None,
                 culture_ratio: int=100
                 ):
    """Find volumes for target concentrations given stock concentrations"""
    
    culture_volume = well_volume / culture_ratio

    if stock_conc_file is not None:
        df_stock_conc = pd.read_csv(stock_conc_file)
        df_stock_conc = df_stock_conc.set_index("Component")
        stock_conc_val = df_stock_conc.values.ravel()
        df = df_stock_conc.copy()
    else:
        df = pd.DataFrame(columns=["Component",
                                   "Stock Concentration",
                                   "Target Concentration"])
        if components is not None:
           df["Component"] = components
        df = df.set_index("Component")

    if stock_conc_val is not None:
        df["Stock Concentration"] = stock_conc_val

    # TODO: Make it for the whole file
    if target_conc_file is not None:
        df_target_conc = pd.read_csv(target_conc_file, index_col=0)
        target_conc_val = df_target_conc.loc[0].values

    elif target_conc_val is not None:
        df["Target Concentration"] = target_conc_val
    else:
        print('Please provide target concentrations file or values.')

    target_conc_val = target_conc_val.ravel()

    # Check the conditions -  all target concentrations are <= stock; positivity;
    # sum of the ratios <= 1
    assert (stock_conc_val >= 0).all(), "Not all stock concentrations are positive!"
    assert (target_conc_val >= 0).all(), "Not all target concentrations are positive!"
    assert (target_conc_val <= stock_conc_val).all(), "Not all target concentrations are <= " \
                                                      "stock concentrations!"
    assert well_volume >= 0, "Well volume is not positive!"
    assert well_volume > culture_volume, "Well volume is not larger than culture volume!"
    # TODO: Provide better message:
    assert (np.sum([target_conc_val / stock_conc_val]) <= 1), "Requested target concentrations " \
                                                              "cannot be achieved with provided " \
                                                              "stock concentrations! "\
                                                              " (Sum of the ratios is > 1!)"

    solution_dim = len(target_conc_val)

    # Create variables A, b for solving the system Ax=b
    b = np.zeros(solution_dim + 1)

    A = np.zeros((solution_dim + 1, solution_dim + 1))
    for i in range(solution_dim):
        A[i, :] = target_conc_val[i] / stock_conc_val[i]
        A[i, i] -= 1
        b[i] = target_conc_val[i] / stock_conc_val[i]

    A[-1, :] = np.ones(solution_dim + 1)
    b[-1] = 1 - (well_volume/culture_volume)
    b = -1.0 * culture_volume * b

    volumes = np.linalg.solve(A, b)

    assert (volumes >= 0).all(), "Not all volumes in the solution are positive!"
    assert (abs(np.sum(volumes) + culture_volume - well_volume) < 0.1), "Sum of volumes from the solution is " \
                                                       "not equal to the total well volume!"

    df['Volumes[uL]'] = volumes[:-1]

    return volumes, df


def check_solubility(df, solubility, verbose=True):    
    
    components = list(df[df["Stock Concentration"] > solubility].index)
    
    if components:
        if verbose:
            print('Components for which those concentrations are not soluble:')
            for comp in components:
                print(f'\t{comp}')
    
    return components


def find_volumes_bulk(df_stock,  
                 df_target_conc=None,
                 well_volume=None,
                 min_tip_volume=None,
                 culture_ratio=None,
                 verbose=0):
    
    EPS = 0.000001
    
    df_volumes = df_target_conc.copy()
    df_volumes['Water'] = None
    
    df_conc_level = pd.DataFrame(data='high',
                                 index=df_target_conc.index,
                                 columns=df_target_conc.columns)
        
    target_conc_val = df_target_conc.values
    
    success_num = 0
    success_wat_num = 0
    
    n_samples = len(df_target_conc)

    for i in range(n_samples):
        if verbose >= 1:
            print(f'Iteration {i}:')
        success = False

        try:
            volumes, df_example = find_volumes(
                well_volume,
                components=df_stock.index,
                stock_conc_val=df_stock['High Concentration'].values, 
                target_conc_val=target_conc_val[i],
                culture_ratio=culture_ratio)
            if not (df_example['Volumes[uL]'] >= min_tip_volume - EPS).all():
                if verbose > 1:
                    print(f'High: Not all volumes are >={min_tip_volume} uL!')

                # Find volumes smaller than min transfer volume
                comp_small_vol = df_example[df_example['Volumes[uL]'] < min_tip_volume - EPS].index 
                if verbose:
                    print(f'Compoments small: {comp_small_vol}')
                
                # Assign low concentrations for those components
                for comp in comp_small_vol:
                    df_example.at[comp, 'Stock Concentration'] = df_stock.at[comp,'Low Concentration']
                    df_conc_level.iloc[i][comp] = 'low'

                # Recalculate  volumes
                volumes, df_example_new = find_volumes(
                    well_volume, 
                    components=df_stock.index,
                    stock_conc_val=df_example['Stock Concentration'].values, 
                    target_conc_val=target_conc_val[i],
                    culture_ratio=culture_ratio)
                
                if not (df_example_new['Volumes[uL]'] >= min_tip_volume - EPS).all():
                    if verbose >= 1:
                        print(f'High + Low min vol: Not all volumes are >={min_tip_volume} uL!')
                else:
                    if verbose > 1:
                        print('Success High + Low min vol')
                    success_num += 1
                    success = True
                    water_vol = volumes[-1]
                    if water_vol > 20:
                        success_wat_num += 1

            else:
                if verbose > 1:
                    print("Success High")
                success_num += 1
                success = True
                water_vol = volumes[-1]
                if water_vol > 20:
                    success_wat_num += 1

        except:
            if verbose >= 1:
                print('Failed High + Low min vol')
            pass

        if not success:
            try:
                volumes, df_example = find_volumes(
                    well_volume, 
                    components=df_stock.index,
                    stock_conc_val=df_stock['Low Concentration'].values, 
                    target_conc_val=target_conc_val[i],
                    culture_ratio=culture_ratio)

                if not (df_example['Volumes[uL]'] >= min_tip_volume - EPS).all():
                    if verbose >= 1:
                        print(f'Low: Not all volumes are >={min_tip_volume} uL!')
                else:
                    if verbose > 1:
                        print('Success Low')
                    success_num += 1
                    water_vol = volumes[-1]
                    if water_vol > 20:
                        success_wat_num += 1

            except:
                if verbose >= 1:
                    print('Failed Low')
                pass
        
        df_volumes.iloc[i] = list(volumes)
    
    print(f'Sucess rate: {100*success_num/n_samples}%')
    print(f'Sucess rate (water): {100*success_wat_num/n_samples}%')
    
    return df_volumes, df_conc_level
    

def find_dilutions(volumes):
    # TODO
    num_components = len(volumes)
    dilutions = np.ones(num_components)

    return dilutions


def round_volume(volume: np.ndarray, well_volume: int):
    """Volumes for transfers are rounded to integers if within 50-300ul and to one decimal digit if within 1-50ul 
    (taking into account pipettes' errors).
    Ceil rather than round is needed because we cannot make higher concentrations in subsequent iterations."""

    volume_rnd = volume.copy()
    for i in range(len(volume_rnd)):
        if volume[i] < pip_volume_threshold:
            volume_rnd[i] = float_round(volume[i], 1, ceil)
            if volume_rnd[i] == well_volume:
                volume_rnd[i] = float_round(volume[i], 1, round)
        else:
            volume_rnd[i] = float_round(volume[i], 0, ceil)
            if volume_rnd[i] == well_volume:
                volume_rnd[i] = float_round(volume[i], 0, round)

    return np.array(volume_rnd)


def float_round(num, places=0, direction=ceil):
    return direction(num * (10**places)) / float(10**places)


def create_media_description(series: pd.Series):
    "Creates full media description by reading columns of components concentrations"
    description = ''
    for item, value in series.iteritems():
        description += f'{item}: {value:0.6f}, '
    return description[:-2]


def designs_pairwise(art, 
                     df_rec, 
                     user_params, 
#                      initial=False, 
                     df_train=None,
                     df_control=None
                    ):

    dim = art.num_input_var

    plt.style.use('seaborn-whitegrid')

    fig = plt.figure(figsize=(35, 35))
    fig.patch.set_facecolor("white")

    X = df_rec[user_params['components']].values
    
    if df_train is not None:
        X_train = df_train[user_params['components']].values
        standard = df_train[df_train['Label']=='standard'].drop(columns='Label').values
        
    if df_control is not None:
        X_control = df_control[user_params['components']].values

    for var1 in range(dim):
        for var2 in range(var1 + 1, dim):

            ax = fig.add_subplot(dim, dim, (var2 * dim + var1 + 1))
            
            if df_train is not None:
                ax.scatter(
                    X_train[:, var1],
                    X_train[:, var2],
                    c="r",
                    marker="+",
                    s=150*df_train['OD340'],
                    lw=1,
                    label="Train data",
                )

                ax.scatter(
                    standard[:, var1],
                    standard[:, var2],
                    c="k",
                    marker="+",
                    s=150*standard[:, -1].astype(float),
                    lw=1,
                    label="Standard",
                )
            
            scale = 100 if df_train is None else 150*df_rec['OD340_pred']
            
            ax.scatter(
                X[:, var1],
                X[:, var2],
                c="g",
                marker="+",
                s=scale,
                lw=1,
                label="Recommendations",
            )
            
            if df_control is not None:
                ax.scatter(
                X_control[:, var1],
                X_control[:, var2],
                c="k",
                edgecolor="k",
                marker="+",
                s=scale,
                lw=1,
                label="Standard",
            )
            
            if df_train:
                scale = 150*df_rec['OD340_pred'].values[-1]
                ax.scatter(
                    X[-1, var1],
                    X[-1, var2],
                    c="k",
                    marker="+",
                    s=scale,
                    lw=1,
                    label="Standard",
                )
                                   
            if var2 == (dim - 1):
                ax.set_xlabel(art.input_vars[var1])
            if var1 == 0:
                ax.set_ylabel(art.input_vars[var2])
                if var2 == 0:
                    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), shadow=True)

    fig.savefig(
        f'{art.outDir}/designs_pairwise.png',
        bbox_inches="tight",
        transparent=False, 
        dpi=300
    )
    

def map_01_to_bounds(df, bounds_file, df_stand, fraction): 
    """Function that maps random designs from interval [0, 1] to our ranges defined by the bounds_file.
    
    :param df: A pandas DataFrame object with values for each component, e.g. a recommendations dataframe output from ART 
    :type df: pandas DataFrame
    :param bounds_file: The path to a bounds file (Excel or CSV format).
    :type bounds_file: string
    :param df_stand: A pandas DataFrame object with standard media concentrations. Loaded from the standard recipe file.
    :type df_stand: pandas DataFrame
    :param fraction: Fraction of the all designs you want to take values below the standard, e.g. 0.2 means 20% of all concentrations will have values lower than the standard.
    :type fraction: float
    """
    
    df_ranges = df.copy()
    
    df_bounds = pd.read_csv(bounds_file).set_index('Variable')
    
    for component in df.columns:
        lb = df_bounds.at[component, 'Min']
        ub = df_bounds.at[component, 'Max']
        stand = df_stand.at[component,'Concentration']
        
        df_ranges[component] = [
            lb + (stand - lb)*r/fraction if r < fraction else stand + (ub - stand)*(r-fraction)/(1-fraction) 
            for r in df[component]
        ]

    return df_ranges


class MediaWarning(Warning):
    pass
    
    
class NoFeasibleVolumesWarn(MediaWarning):
    def __str__(self):
        return (
            "No feasible volumes are found!"
        )
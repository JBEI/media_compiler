from enum import Enum
from typing import List, Dict
from math import ceil, floor
import string
import pandas as pd
import numpy as np
from pyDOE import lhs


pip_volume_threshold = 50  # threshold for using p300 above that volume
mix_times: int = 3         # number of times for mixing
rel_mix_volume = 0.75      # mixing volume, relative to the well volume
touch_tip_speed = 40       # [mm/s] default is 60
touch_tip_offset = -2      # -2mm from top of well for the touch tip


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
                                   "Stock Concentration[mM]",
                                   "Target Concentration[mM]"])
        if components is not None:
           df["Component"] = components
        df = df.set_index("Component")

    if stock_conc_val is not None:
        df["Stock Concentration[mM]"] = stock_conc_val

    # TODO: Make it for the whole file
    if target_conc_file is not None:
        df_target_conc = pd.read_csv(target_conc_file, index_col=0)
        target_conc_val = df_target_conc.loc[0].values

    elif target_conc_val is not None:
        df["Target Concentration[mM]"] = target_conc_val
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
    
    components = list(df[df["Stock Concentration[mM]"] > solubility].index)
    
    if components:
        if verbose:
            print('Components for which those concentrations are not soluble:')
            for comp in components:
                print(f'\t{comp}')
    
    return components


def test_volumes(df_stock, 
                 target_conc_low, 
                 target_conc_high, 
                 n_samples, 
                 well_volume,
                 min_tip_volume,
                 culture_ratio,
                 verbose=0):
    
    latin_hc = lhs(
        len(df_stock), samples=n_samples, criterion="maximin"
    )

    EPS = 0.000001

    lb = target_conc_low.ravel()
    ub = target_conc_high.ravel()

    target_conc_val = lb + latin_hc * (ub - lb)
    
    success_num = 0
    success_wat_num = 0

    for i in range(n_samples):
        if verbose >= 1:
            print(f'Iteration {i}:')
        success = False

        try:
            volumes, df_example = find_volumes(
                well_volume,
                components=df_stock.index,
                stock_conc_val=df_stock['High Concentration[mM]'].values, 
                target_conc_val=target_conc_val[i],
                culture_ratio=culture_ratio)
            if not (df_example['Volumes[uL]'] >= min_tip_volume - EPS).all():
                if verbose > 1:
                    print(f'High: Not all volumes are >={min_tip_volume} uL!')

                comp_small_vol = df_example[df_example['Volumes[uL]'] < min_tip_volume - EPS].index 
                for comp in comp_small_vol:
                    df_example.at[comp, 'Stock Concentration[mM]'] = df_stock.at[comp,'Low Concentration[mM]']

                volumes, df_example_new = find_volumes(
                    well_volume, 
                    components=df_stock.index,
                    stock_conc_val=df_example['Stock Concentration[mM]'].values, 
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
                    stock_conc_val=df_stock['Low Concentration[mM]'].values, 
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
    
    print(f'Sucess rate: {100*success_num/n_samples}%')
    print(f'Sucess rate (water): {100*success_wat_num/n_samples}%')
    

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

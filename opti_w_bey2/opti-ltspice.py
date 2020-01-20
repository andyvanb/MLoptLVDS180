from multiprocessing.spawn import freeze_support
from time import time
from run_bey import run_ltspice_meas_out
import logging
from datetime import datetime
from hyperopt import hp, tpe, fmin
from multiprocessing import Pool
import os
import re
import shutil
from distutils.dir_util import copy_tree

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL
          }
run_number = 0  # Increment on each run so was can look at what the optimizer is doing


def set_up_logging():
    now = datetime.now()
    dt_string = now.strftime("%d-%m-%Y_%H.%M.%S")
    file_name_string = 'circuit_ml_{}.log'
    file_remove_string = file_name_string.format('*')
    log_string = 'removing old logfiles as %s' % file_remove_string
    logging.info("circuit optimizer operation has begun")
    #  logging.info(log_string)
    #  os.remove(file_remove_string)
    LOG_FILENAME = file_name_string.format(dt_string)
    print(LOG_FILENAME)
    logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG, )

supply_corners = {1.8}  # Supply voltage, in V
vcm_corners = {0.8}  # Common mode input voltage in V
temp_corners = {27}  # Temperatures in C
#vcm_corners = {1, 0.8, 0.2}  # Common mode input voltage in V
#supply_corners = {1.6, 1.8, 2}  # Supply voltage, in V
# vcm_corners = { 0, 0.8, 1 } # Common mode input voltage in V
#temp_corners = { 0, 27, 90 } # Temperatures in C

# inst_state is the set of values we want to change for optimization
circuit_state = {
    "infoldsrc_w": 5e-06,
    "intailsrc_w": 5e-06,
    "in_i_l": 0.18e-06,
    "in_i_w": 1e-06,
    "infold_l": 0.18e-06,
    "infold_w": 0.65e-06,  # seed doubled from 0.5u to 1u for lower Vcm operation
    "inpair_w": 8.0e-06,
    "inpair_l": 0.18e-06,
    "pos_stg2_l": 0.18e-06,
    "pos_stg2_in_w": 1e-06,
    "stg2_mult": 6,  # multiplies up the stage 2 gain, both positive and negative
    "neg_stg2_l": 0.18e-06,
    "neg_stg2_in_w": 0.5e-06,
    "pos_stg3_l": 0.18e-06,
    "pos_stg3_w": 5e-06,
    "neg_stg3_l": 0.18e-06,
    "neg_stg3_w": 2.475e-06,
    "pos_stg4_l": 0.18e-06,
    "pos_stg4_w": 0.8e-06,
    "neg_stg4_l": 0.18e-06,
    "neg_stg4_w": 0.4e-06
}


def sim_lvds_rcvr(local_circuit_state):
    tinit = time()
    #  Constrain the amplifier stage value relationships  by multiplying both positive and negative by the same factor.
    #  Note that the multiplier is an input parameter from the circuit state and is manipulated by the optimizer.
    local_circuit_state["pos_stg2_out_w"] = local_circuit_state["pos_stg2_in_w"] * local_circuit_state["stg2_mult"]
    local_circuit_state["neg_stg2_out_w"] = local_circuit_state["neg_stg2_in_w"] * local_circuit_state["stg2_mult"]
    pass_number = 0
    global run_number
    run_number = run_number + 1
    chunk_states = []  # Iterable that has a list of simulation state objects to run against.
    for t in temp_corners:
        local_circuit_state['sim_temp'] = t
        for vcm in vcm_corners:
            local_circuit_state['vcm'] = vcm
            for supply in supply_corners:
                local_circuit_state['supply'] = supply
                pass_number = pass_number + 1
                local_circuit_state['pass_number'] = pass_number
                #  Create a list of states that we can dispatch with pool
                chunk_states.append(local_circuit_state)
    pool = Pool(processes=4)
    #foms = pool.map(run_sim, chunk_states)
    tfom = 0
    for state in chunk_states:
        tfom = tfom + run_sim(state)
    #lfom = sum(foms) / pass_number  # Use average as weighting.
    lfom = tfom / pass_number  # Use average as weighting.
    telap = time() - tinit
    oinfo = 'Completed pooled run #{:d}, run with {:d} passes, {:0.1f} s pool elapsed, run FOM of {:0.1f} ps' \
        .format(run_number, pass_number, telap, lfom)
    print(oinfo)
    return lfom


def run_sim(local_circuit_state):
    subdir_name = 'pool_dir_{}'.format(local_circuit_state['pass_number'])
    local_circuit_state['working_dir'] = subdir_name
    results = run_ltspice_meas_out("lvds_rcvr_testbed_v3.asc", params=local_circuit_state)
    if results['fail'] or results['data'].empty:
        tp_delta = 1000  # Place an artificially high FOM if it does not simulate
    else:
        nmval = results["data"].set_index('Name')['Value'].to_dict()
        tp_delta = abs(
            (nmval['tpdr'] - nmval['tpdf']) * 1e12)  # Multiply up to picoseconds to make it readable
    t = local_circuit_state['sim_temp']
    vcm = local_circuit_state['vcm']
    supply = local_circuit_state['supply']
    pass_number = local_circuit_state['pass_number']
    info = 'run #{:d}, pass #{:d} t={:0.1f} C, vcm={:0.1f} V, supply={:0.1f} V, fail={}, ' \
           ' this_fom={:0.1f} ps'.format(run_number, pass_number, t, vcm, supply, results['fail'], tp_delta)
    print(info)
    logging.info(info)
    return tp_delta


def add_spreads(seed_circuit_state, spread=0.05):
    spread_circuit_state = {}
    for key in seed_circuit_state:
        val = seed_circuit_state[key]
        lower_lim = val * (1 - spread)
        upper_lim = val * (1 + spread)
        #  May be changed from hp.uniform to hp.choice to avoid 'assert prior_sigma > 0' error.
        #  Instead tried reversing the order of the two numerical arguments, which made it operate without error.
        #  Needed to have the lesser value (lower_lim) listed first in the function args.
        spread_circuit_state[key] = hp.uniform(str(key), lower_lim, upper_lim)
    return spread_circuit_state

SIM_BASEDIR_NAME = 'base_sim_dir'  # has the master copy of the simulation file set
SIM_SUBDIR_NAME = 'pool_dir_'  # Where the simulation files for each subprocess are placed

def prepare_sim_dirs():
    dir_count = len(supply_corners) * len(vcm_corners) * len(temp_corners)
    dirs = next(os.walk('.'))[1]
    print('First clean up the old directories, contents maybe unknown...')
    for old_dir in dirs:
        matched = re.search(SIM_SUBDIR_NAME, old_dir)
        if matched != None:
            shutil.rmtree(old_dir)
    print('Then copy from the known base directory with circuit simulation into the subdirs for the corners')
    for pass_number in range(dir_count):
        subdir_name = SIM_SUBDIR_NAME + '{}'.format(pass_number + 1)
        copy_tree(SIM_BASEDIR_NAME, subdir_name)

start_time = time()
set_up_logging()
logging.info(" %i unique circuit parameters are allowed to vary" % len(circuit_state))
prepare_sim_dirs()
circuit_state_bey = add_spreads(circuit_state, spread=0.1)
# Single line bayesian optimization of circuit
if __name__ == '__main__':
    freeze_support()
    best = fmin(fn=sim_lvds_rcvr, space=circuit_state_bey, algo=tpe.suggest, max_evals=1)
    print('Best={}'.format(best))
print('Total elapsed time: {:0.1f} seconds'.format(time() - start_time))
# logging.info("FOM = %0.2f" % FOM)

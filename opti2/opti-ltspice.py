import os
from time import time
from typing import Any, Union

from run_ltspice import run_ltspice_meas_out
import logging
from datetime import datetime

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL,
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


# supply_corners = {1.8}  # Supply voltage, in V
# vcm_corners = {0.8}  # Common mode input voltage in V
vcm_corners = {1, 0.8, 0.2}  # Common mode input voltage in V
temp_corners = {0, 90}  # Temperatures in C
supply_corners = {1.6, 1.8, 2}  # Supply voltage, in V
# vcm_corners = { 0, 0.8, 1 } # Common mode input voltage in V
# temp_corners = { 0, 27, 90 } # Temperatures in C

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


def sim_lvds_rcvr():
    tinit = time()
    #  Constrain the stage values by multiplying both positive and negative by the same factor.
    #  Note that the multiplier is an input parameter from the circuit state and is manipulated by the optimizer.
    circuit_state["pos_stg2_out_w"] = circuit_state["pos_stg2_in_w"] * circuit_state["stg2_mult"]
    circuit_state["neg_stg2_out_w"] = circuit_state["neg_stg2_in_w"] * circuit_state["stg2_mult"]
    fom_sum = 0
    num_of_passes = 0
    for t in temp_corners:
        circuit_state['sim_temp'] = t
        for vcm in vcm_corners:
            circuit_state['vcm'] = vcm
            for supply in supply_corners:
                circuit_state['supply'] = supply
                results = run_ltspice_meas_out("lvds_rcvr_testbed_v3.asc", params=circuit_state)
                num_of_passes += 1
                if results['fail'] or results['data'].empty:
                    tp_delta = 1000  # Place an artificially high FOM if it does not simulate
                else:
                    nmval = results["data"].set_index('Name')['Value'].to_dict()
                    tp_delta = abs(
                        (nmval['tpdr'] - nmval['tpdf']) * 1e12)  # Multiply up to picoseconds to make it readable
                fom_sum = fom_sum + tp_delta  # Sum of all of the FOM's for later averaging
                info = 'run #{:d}, pass #{:d} t={:0.1f} C, vcm={:0.1f} V, supply={:0.1f} V, fail={}, sum_fom={:0.1f} ' \
                       'ps, this_fom={:0.1f} ps'.format(run_number, num_of_passes, t, vcm, supply, results['fail'],
                                                        fom_sum,
                                                        tp_delta)
                print(info)
                logging.info(info)
    lfom: Union[float, Any] = fom_sum / num_of_passes  # Use average as weighting.
    telap = time() - tinit
    oinfo = 'Completed run #{:d}, run with {:d} passes, {:0.1f} s elapsed, run FOM of {:0.1f} ps'\
        .format(run_number, num_of_passes, telap, lfom)
    print(oinfo)
    return lfom


set_up_logging()
logging.info(" %i unique circuit parameters are allowed to vary" % len(circuit_state))
fom = sim_lvds_rcvr()
print('Resulting final FOM={:0.1f}'.format(fom))
# Later look for the WC of all the corners. For now just optimize
# print("Initial FOM: Tpd_rise - Tpd_fall = %0.0f ps" % tp_delta)
# FOM = tp_delta
# logging.info("FOM = %0.2f" % FOM)

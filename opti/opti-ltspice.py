import numpy as np
from run_ltspice import run_ltspice_meas_out
import matplotlib.pyplot as plt
import logging
from datetime import datetime

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL,
          }


def set_up_logging():
    now = datetime.now()
    dt_string = now.strftime("%d-%m-%Y_%H.%M.%S")
    LOG_FILENAME = 'circuit_ml_{}.log'.format(dt_string)
    logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG, )


# inst_state is the set of values we want to change for optimization
inst_state = {
    "supply": "1.8 ",
    "inpair_w": "10.0u",
    "inpair_l": "0.18u",
    "infold_l": "0.18u",
    "infold_w": "0.5u",
    "infoldsrc_w": "5u",
    "intailsrc_w": "5u",
    "pos_mirror_l": "0.18u",
    "pos_mirror_w": "1u",
    "pos_stg2_in_l": "0.18u",
    "pos_stg2_in_w": "1u",
    "pos_stg2_out_l": "0.18u",
    "pos_stg2_out_w": "4u",
    "neg_stg2_in_l": "0.18u",
    "neg_stg2_in_w": "0.5u",
    "neg_stg2_out_l": "0.18u",
    "neg_stg2_out_w": "2u",
    "pos_stg3_l": "0.18u",
    "pos_stg3_w": "5u",
    "neg_stg3_l": "0.18u",
    "neg_stg3_w": "3u",
    "pos_stg4_l": "0.18u",
    "pos_stg4_w": "1.1u",
    "neg_stg4_l": "0.18u",
    "neg_stg4_w": "0.4u"
}
set_up_logging()
results = run_ltspice_meas_out("lvds_rcvr_testbed_v3.asc", params=inst_state)

# print(results["run_time"])
# print(results["data"])
print(results)
nmval = results["data"].set_index('Name')['Value'].to_dict()
tp_delta = (nmval['tpdr']-nmval['tpdf'])*1e12
print("Tpd_rise - Tpd_fall = %0.0f ps" % tp_delta)
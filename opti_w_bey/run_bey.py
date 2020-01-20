#!/usr/bin/env python3
from time import time

import os
import filecmp
from shutil import copyfile
import sys
import logging
import pandas as pd
import re


def run_ltspice_meas_out(simname, **kwargs):
    start_time = time()
    default_ltspice_command = "C:\Program Files\LTC\LTspiceXVII\XVIIx64.exe -Run -b "
    if sys.platform == "linux":
        default_ltspice_command = 'wine C:\\\\Program\\ Files\\\\LTC\\\\LTspiceXVII\\\\XVIIx64.exe -Run -b '

    ltspice_command = kwargs.get("ltspice_command", default_ltspice_command)
    params = kwargs.get("params", {})
    simname = simname.replace(".asc", "")

    with open("param.txt_", "w") as f:
        for key in params:
            f.write(".param {}={}\n".format(key, params[key]))
        f.write("\n")
        f.close()

    sth_changed = False

    # check if we ran the simulation before with exact same input, can save time
    if os.path.isfile('param.txt') and filecmp.cmp('param.txt_', 'param.txt'):
        logging.info("param.txt has not changed")
    else:
        sth_changed = True
        copyfile('param.txt_', 'param.txt')

    # do not execute ltspice if nothing has changed
    if sth_changed:
        if sys.platform == "linux":
            os.system(ltspice_command + " {:s}.asc".format(simname))
        else:
            import subprocess
            subprocess.run([*ltspice_command.split(), "{:s}.asc".format(simname)])
    else:
        logging.info("simulation input data did not change.")

    os.remove("param.txt_")
    fail = False
    outfile = "{}.log".format(simname)
    outfile_cleaned = "{}_cleaned.log".format(simname)  # First select only the lines with valid .measures in them
    fail_pattern = re.compile(".*FAIL|.*[Ee]rror")
    pattern = re.compile("[a-z]*=")
    with open(outfile, "r") as outf:
        with open(outfile_cleaned, "w") as cleanf:
            for line in outf.readlines():
                if fail_pattern.match(line) is not None:
                    fail = True
                if pattern.match(line):
                    cleanline = line.replace("=", " ").split()
                    cleanf.write("{}={}\n".format(cleanline[0], cleanline[1]))
            cleanf.close()
    if fail:
        logging.info("simulation of {:s}.asc recorded FAIL in output".format(simname))
    columns = ["Name", "Value"]  # Next make a Pandas dataframe for the results
    data = pd.read_csv(outfile_cleaned, sep="=", names=columns, header=None)
    results = {"run_time": time() - start_time, "fail": fail, "sim_was_run": sth_changed, "data": data}

    logging.info(  # We are so going to want to know how much time each simulation takes
        "Sim run of {}, new={}, time={}".format(simname, sth_changed, results["run_time"]))
    return results

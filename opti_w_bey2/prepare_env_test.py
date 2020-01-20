import os
import re
import shutil
from distutils.dir_util import copy_tree
import subprocess

# supply_corners = {1.8}  # Supply voltage, in V
# vcm_corners = {0.8}  # Common mode input voltage in V
# temp_corners = {27}  # Temperatures in C
from re import search

vcm_corners = {1, 0.8, 0.2}  # Common mode input voltage in V
supply_corners = {1.6, 1.8, 2}  # Supply voltage, in V
temp_corners = {0, 27, 90}  # Temperatures in C


dir_count = len(supply_corners) * len(vcm_corners) * len(temp_corners)
dirs = next(os.walk('.'))[1]
SIM_BASEDIR_NAME = 'base_sim_dir'  # has the master copy of the simulation file set
SIM_SUBDIR_NAME = 'pool_dir_'  # Where the simulation files for each subprocess are placed
#  First clean up the old directories, contents maybe unknown...
for old_dir in dirs:
    matched = re.search(SIM_SUBDIR_NAME, old_dir)
    if matched != None:
        shutil.rmtree(old_dir)
#  Then copy from the base directory with circuit simulation into the subdirs for the corners
for pass_number in range(dir_count):
    subdir_name = 'pool_dir_{}'.format(pass_number + 1)
    copy_tree(SIM_BASEDIR_NAME, subdir_name)

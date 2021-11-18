#!/usr/bin/env python
import sys
sys.tracebacklimit = 0
MIN_PYTHON=(3,6)
assert sys.version_info >= MIN_PYTHON, "requires Python Version >= 3.6"


import fsspec
import shutil
import os
from math import ceil,floor
from osgeo import gdal
import subprocess as sp
import concurrent.futures as cf
from multiprocessing import cpu_count
from pathlib import Path
import datetime

print('all required modules are available')

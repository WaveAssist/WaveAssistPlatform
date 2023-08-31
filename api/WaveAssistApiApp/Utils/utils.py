##PYTHON IMPORTS
import glob
import struct
import collections
import datetime
from multiprocessing import Queue, Pool
##Custom
from WaveAssistApiApp.Utils.constants import *

from time import sleep
from zipfile import ZipFile

import shutil
import os
import json
from WaveAssistApiApp.Utils.Logger import Logger
##Logger

logger = Logger()

def has_access(client_object, project_key):
    project_list = client_object.project_set.filter(project_key=project_key)
    if project_list.count() > 0:
        return True
    else:
        return False
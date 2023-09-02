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

def does_user_have_node_access(client_object, node_object):
    # project object has node_array
    node_array = client_object.project_set.all().values_list('node_array', flat=True)
    return node_object.id in node_array



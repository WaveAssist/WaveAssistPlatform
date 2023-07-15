# import the necessary packages
import Utils.utils
from Utils.config import *
from Utils.constants import *


import logging
import logging.handlers
from logging.handlers import *

##CUSTOM IMPORTS
import logging
from logging.handlers import RotatingFileHandler

class Logger:
    def __init__(self):
        ##Logger
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(threadName)s] %(message)s')
        self.logger = logging.getLogger("EngineLogger")
        handler = RotatingFileHandler(PROJECT_LOGS_PATH,maxBytes=100000,backupCount=100)
        self.logger.addHandler(handler)


        ##URLLIBs
        urllib3_logger = logging.getLogger('urllib3')
        urllib3_logger.setLevel(logging.CRITICAL)


    def log(self,level,message):
        print(str(message))
        if hasattr(self.logger,level):
            getattr(self.logger, str(level))(str(message))


    def warning(self,message):
        self.log('warning',message)
    def error(self,message):
        self.log('error',message)
    def info(self,message):
        self.log('info',message)
    def debug(self,message):
        self.log('debug',message)


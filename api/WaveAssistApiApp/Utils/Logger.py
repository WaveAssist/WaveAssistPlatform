# import the necessary packages
from WaveAssistApiApp.Utils.constants import *
import logging
import logging.handlers
from logging.handlers import *

##CUSTOM IMPORTS
import logging
from logging.handlers import RotatingFileHandler

class Logger:
    def __init__(self):
        ##Logger
        # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(threadName)s] %(message)s')
        logging.basicConfig(level=logging.INFO)

        self.logger = logging.getLogger("APILogger")

        ##URLLIBs
        urllib3_logger = logging.getLogger('urllib3')
        urllib3_logger.setLevel(logging.CRITICAL)


    def log(self,level,message):
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


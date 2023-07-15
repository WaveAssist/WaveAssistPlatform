import datetime
import statistics
from Utils.config import *
import Utils.utils as utils


class Timer:
    def __init__(self,name=''):
        # store the start time, end time, and total number of frames
        # that were examined between the start and end intervals
        self._start = None
        self._end = None
        self.history = []
        self.name = name
        self.count = 0


    def start(self):
        # start the timer
        self._start = datetime.datetime.now()
        self.count = self.count + 1
        return self

    def reset(self):
        # start the timer
        self._start = datetime.datetime.now()
        
    def stop(self):
        # stop the timer
        self._end = datetime.datetime.now()


    def elapsed(self):
        # return the total number of seconds between the start and
        # end interval
        return (self._end - self._start).total_seconds()


    def print_elapsed(self,opt_string=''):
        self.stop()
        elapsed = self.elapsed()
        self.history.append(elapsed)
        self.reset()
        if self.count % LOG_NUMBER == 0:
            utils.logger.info(opt_string + ':: Engine Working ::' + str(self.name) + "::Average::" + str(self.calculate_average()) + " & Median = " + str(self.calculate_median()) + " & count = "  + str(self.count))
            utils.logger.warning(self.history)
            self.history = []
            self.count = 0
        return

    def calculate_average(self):
        total_time = 0.0
        for historical_time in self.history:
            total_time = float(historical_time) + total_time
        if len(self.history) == 0:
            return 0
        return total_time/len(self.history)

    def calculate_median(self):
        return statistics.median(self.history)


    def crossed_one_second(self):
        # return the total number of seconds between the start and
        # end interval
        current_time = datetime.datetime.now()
        return (current_time - self._start).total_seconds() >= 1


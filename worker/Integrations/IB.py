from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import random
from datetime import datetime
import threading
import time
from datetime import timedelta
import pandas as pd
import logging
import pytz
ist = pytz.timezone('Asia/Kolkata')
logging.getLogger("ibapi").setLevel(logging.CRITICAL)  # Set level higher than CRITICAL

class IBapi(EWrapper, EClient):
    tick_data_dictionary = {}
    last_refreshed = None

    def __init__(self):
        EClient.__init__(self, self)

    def tickPrice(self, reqId, tickType, price, attrib):
        super().tickPrice(reqId, tickType, price, attrib)
        if price == 0 or price is None:
            return

        self.last_refreshed = datetime.now(ist)

        if tickType == 4:  ##Last Price
            if reqId in self.tick_data_dictionary:
                self.tick_data_dictionary[reqId]['price'] = price
            else:
                self.tick_data_dictionary[reqId] = {'price': price}

        elif tickType == 1:  ##Bid Price
            if reqId in self.tick_data_dictionary:
                self.tick_data_dictionary[reqId]['bid_price'] = price
            else:
                self.tick_data_dictionary[reqId] = {'bid_price': price}
        elif tickType == 2:  ##Ask Price
            if reqId in self.tick_data_dictionary:
                self.tick_data_dictionary[reqId]['ask_price'] = price
            else:
                self.tick_data_dictionary[reqId] = {'ask_price': price}


class IBConnection(object):

    def run_loop(self):
        self.app.run()

    def connect_ib(self):
        client_id = random.randint(100, 1000)
        ib_port = 7496

        print("Connecting to IB: " + str(self.ib_url) + ":" + str(ib_port))
        app = IBapi()
        app.connect(self.ib_url, ib_port, client_id)
        api_thread = threading.Thread(target=self.run_loop, daemon=True, args=(app,))
        api_thread.start()

        time.sleep(1)

        print("Did connect: " + str(app.isConnected()))
        return app, api_thread

    def __init__(self):
        self.ib_url = '18.210.163.209'
        self.app, self.api_thread = self.connect_ib()

    def fetch_and_refresh_ib_app_if_needed(self):
        if self.app.isConnected():
            return self.app
        else:
            # Retry IB connection
            self.app.disconnect()
            self.app, self.api_thread = self.connect_ib()
            time.sleep(2)
            return self.app

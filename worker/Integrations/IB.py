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

# Disable log messages from the 'ibapi.decoder' logger
logging.getLogger('ibapi.decoder').setLevel(logging.ERROR)
logging.getLogger().setLevel(logging.ERROR)

class IBapi(EWrapper, EClient):
    tick_data_dictionary = {}

    def __init__(self):
        EClient.__init__(self, self)

    def tickPrice(self, reqId, tickType, price, attrib):
        super().tickPrice(reqId, tickType, price, attrib)
        if price == 0 or price is None:
            return


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


def run_loop(app):
    app.run()


def connect_ib(ib_url):
    client_id = random.randint(100,1000)
    ib_port = 7496

    print("Connecting to IB: " + str(ib_url) + ":" + str(ib_port))
    app = IBapi()
    app.connect(ib_url, ib_port, client_id)
    api_thread = threading.Thread(target=run_loop, daemon=True, args=(app,))
    api_thread.start()

    time.sleep(1)

    print("Did connect: " + str(app.isConnected()))
    return app, api_thread

app, api_thread = connect_ib("18.210.163.209")
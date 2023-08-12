#
# ##############Final code here
# from ibapi.client import EClient
# from ibapi.wrapper import EWrapper
# from ibapi.contract import Contract
# import random
# from datetime import datetime
# import threading
# import time
# from datetime import timedelta
# import pandas as pd
#
#
#
#
#
# class IBapi(EWrapper, EClient):
#     future_price = 0
#     is_next_month = True
#     is_set = False
#
#
#     def __init__(self):
#         EClient.__init__(self, self)
#
#     def tickPrice(self, reqId, tickType, price, attrib):
#         super().tickPrice(reqId, tickType, price, attrib)
#         if reqId in [3001, 3002] and tickType in [4,6,7,9]: ##Futures - Last Price
#             if not self.is_set:
#
#                 ##update the future price as price
#                 self.future_price = price
#                 self.is_set = True
#                 if reqId == 3001:
#                     print("Setting next month price to: " + str(price))
#                     self.is_next_month = True
#
#                 elif reqId == 3002:
#                     print("Setting subsequent month price to: " + str(price))
#                     self.is_next_month = False
#
#
#
# def fetch_future_contracts(app):
#     today = datetime.today()
#     # Get the first day of next month and the month after that using timedelta
#     next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
#     two_months_after = (next_month.replace(day=1) + timedelta(days=32)).replace(day=1)
#     # Convert the dates to strings in the yyyymm format
#     next_month_str = next_month.strftime("%Y%m")
#     two_months_after_str = two_months_after.strftime("%Y%m")
#
#     # Create contract object
#     futures_contract_next = Contract()
#     futures_contract_next.symbol = 'CL'
#     futures_contract_next.secType = 'FUT'
#     futures_contract_next.exchange = 'NYMEX'
#     futures_contract_next.currency = 'USD'
#     futures_contract_next.lastTradeDateOrContractMonth = next_month_str
#
#     futures_contract_subsquent = Contract()
#     futures_contract_subsquent.symbol = 'CL'
#     futures_contract_subsquent.secType = 'FUT'
#     futures_contract_subsquent.exchange = 'NYMEX'
#     futures_contract_subsquent.currency = 'USD'
#     futures_contract_subsquent.lastTradeDateOrContractMonth = two_months_after_str
#
#
#     app.reqMktData(3001, futures_contract_next, '', True, False, [])
#     time.sleep(15) ##Wait before checking next month
#     app.reqMktData(3002, futures_contract_subsquent, '', True, False, [])
#     return
#
#
#
# def run_loop(app):
#     app.run()
#
#
# def connect_ib(ib_url):
#     client_id = random.randint(100,1000)
#     ib_port = 7496
#
#     print("Connecting to IB: " + str(ib_url) + ":" + str(ib_port))
#     app = IBapi()
#     app.connect(ib_url, ib_port, client_id)
#     time.sleep(5)
#
#
#     api_thread = threading.Thread(target=run_loop, daemon=True, args=(app,))
#     api_thread.start()
#
#     time.sleep(5)
#
#     print("Did connect: " + str(app.isConnected()))
#
#     return app, api_thread
#
#
# def load_future_price_and_month_status(ib_url):
#     ##Loads the future price and which month it belongs to
#
#
#
#     app, api_thread = connect_ib(ib_url)
#     fetch_future_contracts(app)
#
#
#
#     time.sleep(10)
#     for i in range(0,10):
#         print("############### Looping to check if future price is set")
#         if app.is_set:
#             print("Future price is set")
#             app.disconnect()
#             api_thread.join()
#             return app.future_price, app.is_next_month
#         else:
#             print("Future price is not set")
#             time.sleep(10)
#     return None, None
#
#
#
#
# def load_options_data(future_spot_price, is_next_month):
#
#         print('Updating options contracts')
#         today = datetime.today()
#
#         next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
#         one_months_after = (next_month.replace(day=1) + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
#
#         selected_month = next_month if is_next_month else one_months_after
#
#         strike_range = 0.5
#         load_next_strikes_count = 40
#         itm_strikes_count = 10
#
#         ##Next/Previous closest 50 divisible strike to spot
#         call_strike_price = future_spot_price + (strike_range - future_spot_price % strike_range) ##Picks the next strike. If it is exact 50, then it will go to next.
#         put_strike_price = future_spot_price - (future_spot_price % strike_range)
#
#         call_strike_price = call_strike_price - itm_strikes_count * strike_range
#         put_strike_price = put_strike_price + itm_strikes_count * strike_range
#
#         future_dict = {
#             'name': 'CL',
#             'expiry': str(selected_month),
#             'strike': future_spot_price,
#             'option_type': 'F',
#             'instrument_type': 'Futures',
#             'exchange': 'NYMEX',
#             'connection_type': 'IB',
#             'ib_symbol': 'CL',
#             'ib_id': '5001'
#         }
#
#
#         all_crude_oil_dict_array = []
#         all_crude_oil_dict_array.append(future_dict)
#         ib_id_counter = 1
#         for i in range(0,load_next_strikes_count):
#             call_crude_oil_dict = {
#                 'name': 'CL',
#                 'expiry': str(selected_month),
#                 'strike': call_strike_price,
#                 'option_type': 'CE',
#                 'instrument_type': 'Options',
#                 'exchange': 'NYMEX',
#                 'connection_type': 'IB',
#                 'ib_symbol': 'CL',
#                 'ib_id': ib_id_counter
#             }
#             ib_id_counter += 1
#             all_crude_oil_dict_array.append(call_crude_oil_dict)
#
#             put_crude_oil_dict = {
#                 'name': 'CL',
#                 'expiry': str(selected_month),
#                 'strike': put_strike_price,
#                 'option_type': 'PE',
#                 'instrument_type': 'Options',
#                 'exchange': 'NYMEX',
#                 'connection_type': 'IB',
#                 'ib_symbol': 'CL',
#                 'ib_id': ib_id_counter
#             }
#             ib_id_counter += 1
#             all_crude_oil_dict_array.append(put_crude_oil_dict)
#             call_strike_price = call_strike_price + strike_range
#             put_strike_price = put_strike_price - strike_range
#
#
#         print("All CL Dict Array Length: " + str(all_crude_oil_dict_array))
#
#
#         return all_crude_oil_dict_array
#
#
#
#
# ##Main Code
#
# try:
#     print("Starting IB Refresh:  " + str(WAU359P1D1))
#     ib_url = '18.210.163.209'
#     should_refresh = str(WAU359P1D1[WAU359P1D1['name'] == 'should_refresh_ib']['value'].values[0])
#
#     if should_refresh != '1':
#         print("Not refreshing IB strikes")
#         return None, None
#
#     print("Starting IB Refresh...")
#     future_strike_price, next_month_status = load_future_price_and_month_status(ib_url)
#
#     if future_strike_price is None or next_month_status is None:
#         print("Error in fetching IB future price or next month status")
#         return None, None
#
#     all_crude_oil_dict_array = load_options_data(future_strike_price, next_month_status)
#
#     output_df = pd.DataFrame(all_crude_oil_dict_array)
#     WAU359P1D1['value'][WAU359P1D1['name'] == 'should_refresh_ib'] = 0
#     print("All IB data updated!!!!!" + str(len(all_crude_oil_dict_array)))
#     print(output_df)
#     return WAU359P1D1, output_df
#
# except Exception as e:
#     print("Error in fetching IB Strikes: " + str(e))
#     return None, None
#
#
#

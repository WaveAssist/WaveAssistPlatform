#
# from ibapi.contract import Contract
# import pandas as pd
#
#
# def fetch_options_contracts(WAU359P1D4):
#     def create_contract(row):
#         expiry_month_string = pd.to_datetime(row['expiry']).strftime("%Y%m")
#
#         if row['instrument_type'] == 'Futures':
#             contract = Contract()
#             contract.symbol = row['name']
#             contract.secType = 'FUT'
#             contract.exchange = row['exchange']
#             contract.currency = 'USD'
#             contract.lastTradeDateOrContractMonth = expiry_month_string
#             return contract
#         else:
#             contract = Contract()
#             contract.symbol = row['name']
#             contract.secType = 'FOP'
#             contract.exchange = row['exchange']
#             contract.currency = 'USD'
#             contract.tradingClass = 'LO'
#             contract.lastTradeDateOrContractMonth = expiry_month_string
#             contract.strike = row['strike']
#             contract.right = 'C' if row['option_type'] == 'CE' else 'P'
#             return contract
#
#
#     # Create an array of contract objects
#     contract_object_array = []
#     ib_id_array = []
#     for _,row in WAU359P1D4.iterrows():
#         contract_object = create_contract(row)
#         ib_id = row['ib_id']
#         contract_object_array.append(contract_object)
#         ib_id_array.append(ib_id)
#
#     return contract_object_array, ib_id_array
#
# ##Main Code
#
#
# def refresh_subscribe(output_df):
#     output_df.drop_duplicates(subset='ib_id', keep='first', inplace=True)
#
#     contract_object_array, ib_id_array = fetch_options_contracts(output_df)
#     for i, contract in enumerate(contract_object_array):
#         ib_id = ib_id_array[i]
#         # try:
#         #     ib_app.cancelMktData(ib_id)
#         # except:
#         #     pass
#         ib_app.reqMktData(ib_id, contract, '', False, False, [])
#     return
#
#
# try:
#     print("Refreshing subscription for IB strikes")
#     refresh_subscribe(WAU359P1D4)
# except Exception as e:
#     print("Error in refreshing IB subscription: " + str(e))
#

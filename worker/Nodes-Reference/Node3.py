#
#
# try:
#     from time import sleep
#     import pandas as pd
#     from datetime import datetime
#     import pytz
#     ist = pytz.timezone('Asia/Kolkata')
#
#
#     zerodha_symbol_array = WAU359P1D2['zerodha_symbol'].values.tolist()
#
#     # Initialise
#
#     ##Add MCX: prefix to each element in zerodha_symbol_array if not already present
#     zerodha_symbol_array = ['MCX:' + x if x[:4] != 'MCX:' else x for x in zerodha_symbol_array]
#     quotes_dict = kite.quote(zerodha_symbol_array)
#     tick_data_dictionary = {}
#     ##For key and value in quotes_dict
#     for key, value in quotes_dict.items():
#         price = value['last_price']
#         bid_price = value['depth']['buy'][0]['price']
#         ask_price = value['depth']['sell'][0]['price']
#         ##Remove MCX prefix from key
#         key = key[4:]
#         tick_data_dictionary[key] = {
#             'price': price,
#             'bid_price': bid_price,
#             'ask_price': ask_price
#         }
#
#
#     ##Format tick_data_dictionary
#     output_df = pd.DataFrame.from_dict(tick_data_dictionary, orient='index')
#
#     # Add 'instrument_token' as a new column
#     output_df.reset_index(inplace=True)
#     output_df.rename(columns={'index': 'zerodha_symbol'}, inplace=True)
#
#
#     ##Check length of output_df
#     if len(output_df) == 0:
#         print("No data received from Zerodha")
#         return None, None
#
#     ##Get value of IB Updated column from WAU359P1D16
#     zerodha_updated = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")
#     zerodha_dict = {'Zerodha Updated': zerodha_updated}
#
#
#     print("Loaded Zerodha Options Data for : " + str(len(output_df)))
#     return output_df, pd.DataFrame([zerodha_dict], index=[0])
# except:
#     return None, None
#
#
#
#

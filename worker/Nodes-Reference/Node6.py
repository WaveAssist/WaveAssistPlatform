# try:
#     import pandas as pd
#     import math
#
#     call_put_columns_to_round = ['entry_price', 'exit_price', 'parity', 'delta_hedge', 'current_hedge']
#
#     # Round off the specified columns to two decimals
#     WAU359P1D7[call_put_columns_to_round] = WAU359P1D7[call_put_columns_to_round].round(2)
#     WAU359P1D8[call_put_columns_to_round] = WAU359P1D8[call_put_columns_to_round].round(2)
#
#
#     call_put_column_mapping = {
#         'zerodha_strike_price': 'Zerodha Strike',
#         'ib_strike_price': 'IB Strike',
#         'zerodha_price': 'Zerodha Price',
#         'ib_price': 'IB Price',
#         'type': 'Type',
#         'entry_price': 'Entry Price',
#         'exit_price': 'Exit Price',
#         'parity': 'Parity',
#         'delta_hedge': 'Delta Hedge',
#         'current_hedge': 'Currency Hedge'
#     }
#
#     # Rename the columns using the dictionary
#     WAU359P1D7.rename(columns=call_put_column_mapping, inplace=True)
#     WAU359P1D8.rename(columns=call_put_column_mapping, inplace=True)
#
#
#     WAU359P1D9['Name'] = "CRUDEOIL"
#     column_mapping = {
#         'expiry': 'Expiry',
#         'strike': 'Strike',
#         'option_type': 'Option Type',
#         'price': 'Price',
#         'bid_price': 'Bid Price',
#         'ask_price': 'Ask Price'
#     }
#     # Rename the columns using the dictionary
#     WAU359P1D9.rename(columns=column_mapping, inplace=True)
#     # Drop the unwanted columns (zerodha_id and connection_type)
#     WAU359P1D9.drop(columns=['zerodha_id', 'connection_type','zerodha_symbol','name','instrument_type','exchange'], inplace=True)
#
#
#     column_mapping = {
#         'ib_symbol':'Name',
#         'expiry': 'Expiry',
#         'strike': 'Strike',
#         'option_type': 'Option Type',
#         'price': 'Price',
#         'bid_price': 'Bid Price',
#         'ask_price': 'Ask Price'
#     }
#     # Rename the columns using the dictionary
#     WAU359P1D10.rename(columns=column_mapping, inplace=True)
#     # Drop the unwanted columns
#     WAU359P1D10.drop(columns=['ib_id','connection_type','instrument_type','exchange'], inplace=True)
#
#
#
#     # Reorder the columns of df  WAU359P1D7
#     # to Zerodha Strike	IB Strike	Zerodha Price	IB Price	Entry Price	Exit Price	Parity	Delta Hedge	Currency Hedge	Type
#
#     WAU359P1D7 = WAU359P1D7[['Zerodha Strike','IB Strike','Zerodha Price','IB Price','Entry Price','Exit Price','Parity','Delta Hedge','Currency Hedge']]
#
#
#     ## Reorder the columns of df  WAU359P1D8
#     # to Zerodha Strike	IB Strike	Zerodha Price	IB Price	Entry Price	Exit Price	Parity	Delta Hedge	Currency Hedge	Type
#
#     WAU359P1D8 = WAU359P1D8[['Zerodha Strike','IB Strike','Zerodha Price','IB Price','Entry Price','Exit Price','Parity','Delta Hedge','Currency Hedge']]
#
#
#     ## Reorder the columns of df  WAU359P1D9
#     # to Name	Expiry	Strike	Option Type  Bid Price	Ask Price	Price
#
#     WAU359P1D9 = WAU359P1D9[['Name','Expiry','Strike','Option Type','Bid Price','Ask Price','Price']]
#
#
#     ## Same for  WAU359P1D10
#     WAU359P1D10 = WAU359P1D10[['Name','Expiry','Strike','Option Type','Bid Price','Ask Price','Price']]
#
#
#
#     ## format WAU359P1D10 expiry column to remove 00:00:00 from string expiry date
#     WAU359P1D10['Expiry'] = WAU359P1D10['Expiry'].str.slice(0,10)
#
#
#     ## from df WAU359P1D7 format column Delta Hedge to remove decimal point
#     # WAU359P1D7['Delta Hedge'] = WAU359P1D7['Delta Hedge'].astype(int)
#
#
#     # do same for df WAU359P1D8 for column Currency Hedge
#     # WAU359P1D7['Currency Hedge'] = WAU359P1D7['Currency Hedge'].astype(int)
#
#
#     # WAU359P1D8['Delta Hedge'] = WAU359P1D8['Delta Hedge'].astype(int)
#     # WAU359P1D8['Currency Hedge'] = WAU359P1D8['Delta Hedge'].astype(int)
#
#
#     ##In WAU359P1D7 remove duplicates on column Zerodha Strike
#     WAU359P1D7.drop_duplicates(subset=['Zerodha Strike'], keep='first', inplace=True)
#
#     ##In WAU359P1D8 remove duplicates on column Zerodha Strike
#     WAU359P1D8.drop_duplicates(subset=['Zerodha Strike'], keep='first', inplace=True)
#
#     WAU359P1D7.dropna(inplace=True)
#     WAU359P1D8.dropna(inplace=True)
#     WAU359P1D9.dropna(inplace=True)
#     WAU359P1D10.dropna(inplace=True)
#
#     return WAU359P1D7,WAU359P1D8,WAU359P1D9,WAU359P1D10
# except:
#     return None, None, None, None
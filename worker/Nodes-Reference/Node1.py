# from kiteconnect import KiteConnect
# from datetime import datetime
# from datetime import timedelta
# import pandas as pd
#
# def load_zerodha_option_symbols(kite, spot_price, selected_month, selected_year):
#
#     selected_symbols = []
#     strike_range = 100
#     load_next_strikes_count = 30
#     itm_strikes_count = 10
#
#     ##Next/Previous closest 50 divisible strike to spot
#     call_strike_price = spot_price + (
#                 strike_range - spot_price % strike_range)  ##Picks the next strike. If it is exact 50, then it will go to next.
#     put_strike_price = spot_price - (spot_price % strike_range)
#
#     call_strike_price = call_strike_price - strike_range * itm_strikes_count
#     put_strike_price = put_strike_price + strike_range * itm_strikes_count
#
#     for i in range(0, load_next_strikes_count):
#         call_symbol = 'CRUDEOIL' + selected_year + selected_month + str(call_strike_price) + 'CE'
#         selected_symbols.append(call_symbol)
#
#         put_symbol = 'CRUDEOIL' + selected_year + selected_month + str(put_strike_price) + 'PE'
#         selected_symbols.append(put_symbol)
#
#         call_strike_price = call_strike_price + strike_range
#         put_strike_price = put_strike_price - strike_range
#
#     return selected_symbols
#
#
# def load_zerodha_futures_data(kite):
#     # Get current month
#     current_month = datetime.now().strftime('%b').upper()
#     current_year = datetime.now().strftime('%y')
#     # Get next month
#     next_month = (datetime.now() + timedelta(days=30)).strftime('%b').upper()
#     next_year = (datetime.now() + timedelta(days=30)).strftime('%y')
#
#     current_month_fut_contract = 'MCX:CRUDEOIL' + current_year + current_month + 'FUT'
#     next_month_fut_contract = 'MCX:CRUDEOIL' + next_year + next_month + 'FUT'
#
#     quotes = kite.quote(current_month_fut_contract, next_month_fut_contract)
#
#     ##Check if quotes contain response key as current_month_fut_contract, then use that, else other
#     if current_month_fut_contract in quotes:
#         fut_contract_data = quotes[current_month_fut_contract]
#         selected_month = current_month
#         selected_year = current_year
#         selected_contract = current_month_fut_contract
#     else:
#         fut_contract_data = quotes[next_month_fut_contract]
#         selected_month = next_month
#         selected_year = next_year
#         selected_contract = next_month_fut_contract
#
#     ##Extract the last_price & net_change from the fut_contract_data
#     future_price = fut_contract_data['last_price']
#     future_instrument_token = fut_contract_data['instrument_token']
#
#     return future_price, selected_month, selected_year, selected_contract, future_instrument_token
#
#
#
# ##Main code
#
#
#
# try:
#     should_refresh = str(WAU359P1D1[WAU359P1D1['name'] == 'should_refresh_zerodha']['value'].values[0])
#
#     if should_refresh != '1':
#         print("Not refreshing zerodha strikes")
#         return None, None
#
#     future_price, selected_month,selected_year,zerodha_future_symbol, future_instrument_token = load_zerodha_futures_data(kite)
#     zerodha_options_symbols = load_zerodha_option_symbols(kite, future_price, selected_month, selected_year)
#
#
#     # print("Zerodha Options Symbols: ", zerodha_options_symbols)
#
#
#     all_mcx_instruments = kite.instruments(exchange='MCX')
#     all_crude_oil_objects_array = []
#     zerodha_data_array = []
#
#
#     for instrument_dict in all_mcx_instruments:
#         trading_symbol = instrument_dict['tradingsymbol']
#         # print(trading_symbol)
#         if trading_symbol in zerodha_options_symbols:
#             instrument_dict = {
#                     'zerodha_id': instrument_dict['instrument_token'],
#                     'zerodha_symbol': instrument_dict['tradingsymbol'],
#                     'name': instrument_dict['name'],
#                     'expiry': str(instrument_dict['expiry']),
#                     'strike': instrument_dict['strike'],
#                     'option_type': instrument_dict['instrument_type'],
#                     'instrument_type': 'Options',
#                     'exchange': instrument_dict['exchange'],
#                     'connection_type': 'Zerodha'
#                 }
#
#             zerodha_data_array.append(instrument_dict)
#
#
#     ##Futures
#     future_expiry = datetime.strptime(selected_month+selected_year, '%b%y')
#     zerodha_futures_dict = {
#         'zerodha_id': str(future_instrument_token),
#         'zerodha_symbol': zerodha_future_symbol[4:],
#         'name': 'CRUDEOIL FUTURES',
#         'expiry': str(future_expiry),
#         'strike': future_price,
#         'option_type': 'F',
#         'instrument_type': 'Futures',
#         'exchange': 'MCX',
#         'connection_type': 'Zerodha'
#     }
#     zerodha_data_array.append(zerodha_futures_dict)
#
#     output_df = pd.DataFrame(zerodha_data_array)
#     WAU359P1D1['value'][WAU359P1D1['name'] == 'should_refresh_zerodha'] = 0
#     print("All zerodha data updated!!!!!" + str(len(zerodha_data_array)))
#     return WAU359P1D1, output_df
#
# except Exception as e:
#     print("Error in Zerodha Node: " +  str(e))
#     return None, None
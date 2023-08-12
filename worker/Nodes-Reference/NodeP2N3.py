# from kiteconnect import KiteConnect
# import pandas as pd
# from datetime import datetime
# from py_vollib.black_scholes.implied_volatility import implied_volatility
# from py_vollib.black_scholes.greeks.analytical import delta
# from py_vollib.black_scholes import black_scholes
#
#
# interest_rate = 0
#
# def add_option_strikes(data, df, expiry, for_skewness=False):
#     option_expiries = df[df['instrument_type']=='CE'].groupby(['name','expiry']).first().reset_index()
#     option_expiries = option_expiries.groupby('name').apply(
#         lambda x: x.iloc[expiry] if len(x) >= 2 else None).reset_index(drop=True)
#     option_expiries = option_expiries[['name', 'expiry']]
#     expiry_instruments = pd.merge(df, option_expiries, on = ['name','expiry'])
#     merged_df = pd.merge(data, expiry_instruments, on=['name','exchange'], how='right')
#     merged_df = merged_df[merged_df['instrument_type'] == 'CE']
#     if for_skewness:
#         merged_df = merged_df[(merged_df['strike'] >= merged_df[f'fut_price_{expiry}'] * (1 - 0.01)) &
#                               (merged_df['strike'] <= merged_df[f'fut_price_{expiry}'] * (1 + 0.15))]
#     elif expiry == 0:
#         merged_df = merged_df[(merged_df['strike'] >= merged_df[f'fut_price_{expiry}'] * (1 - 0.008)) &
#                               (merged_df['strike'] <= merged_df[f'fut_price_{expiry}'] * (1 + 0.008))]
#     elif expiry == 1:
#         merged_df = merged_df[(merged_df['strike'] >= merged_df[f'fut_price_{expiry}'] * (1 - 0.015)) &
#                               (merged_df['strike'] <= merged_df[f'fut_price_{expiry}'] * (1 + 0.02))]
#     else:
#         merged_df = merged_df[(merged_df['strike'] >= merged_df[f'fut_price_{expiry}'] * (1 - 0.015)) &
#                               (merged_df['strike'] <= merged_df[f'fut_price_{expiry}'] * (1 + 0.02))]
#
#     merged_df = merged_df.sort_values(['name', 'expiry', 'strike'], ascending=[True, True, True])
#     live_data_atm_strike = merged_df #.groupby('name').head(5).reset_index()
#     live_data_atm_strike.rename(columns={'expiry': f'opt_expiry_{expiry}',
#                                          'strike': f'strike_{expiry}'}, inplace=True)
#     live_data_atm_strike[f'kite_opt_symbol_{expiry}'] = live_data_atm_strike['exchange'] + ':' + \
#                                                         live_data_atm_strike['tradingsymbol']
#     live_data_atm_strike = live_data_atm_strike.drop(['instrument_type',
#                                                       'instrument_token', 'tradingsymbol'], axis=1)
#     return live_data_atm_strike
#
#
#
#
# class KiteQuote:
#     def __init__(self, data_dict):
#         self.data = self.process_data(data_dict)
#
#     def process_data(self, data_dict):
#         # Perform your desired processing on the input data dictionary
#         # For example, calculate additional fields or modify existing ones
#         # processed_data = data_dict
#         processed_data = {}
#         price_mid = (data_dict['depth']['buy'][0]['price'] + data_dict['depth']['sell'][0]['price']) / 2
#         # to account for closed market condition take ltp if bid ask is not available
#         price = price_mid if price_mid != 0 else data_dict['last_price']
#         processed_data['mid_price'] = price
#         processed_data['bid_price'] = data_dict['depth']['buy'][0]['price']
#         processed_data['ask_price'] = data_dict['depth']['sell'][0]['price']
#         processed_data['last_price'] = data_dict['last_price']
#         processed_data['open'] = data_dict['ohlc']['open']
#         processed_data['high'] = data_dict['ohlc']['high']
#         processed_data['low'] = data_dict['ohlc']['low']
#         processed_data['close'] = data_dict['ohlc']['close']
#         processed_data['volume'] = data_dict['volume']
#         processed_data['oi'] = data_dict['oi']
#         processed_data['last_trade_time'] = data_dict['last_trade_time']
#         return processed_data
#
#     def __getattr__(self, key):
#         if key in self.data:
#             return self.data[key]
#         else:
#             raise AttributeError(f"'KiteQuote' object has no attribute '{key}'")
#
#
#
# def add_option_greeks(data, expiry):
#     expiry_month = 'Current month' if expiry == 0 else 'Far month'
#     data[f'opt_expiry_{expiry}_date'] = pd.to_datetime(data[f'opt_expiry_{expiry}'])
#     today = datetime.now().date()
#     data[f'days_to_expiry_{expiry}'] = data[f'opt_expiry_{expiry}_date'].apply(
#         lambda x: 0.5/365 if x.date() == today else (x.date() - today).days / 365)
#
#     def calculate_iv(row):
#         if row[f'fut_price_{expiry}'] - row[f'strike_{expiry}'] <= row[f'option_price_{expiry}']:
#             try:
#                 iv = implied_volatility(row[f'option_price_{expiry}'], row[f'fut_price_{expiry}'], row[f'strike_{expiry}'],
#                                         row[f'days_to_expiry_{expiry}'],
#                                         interest_rate, 'c')
#                 return iv
#             except:
#                 print("Error in calculating IV:",
#                       row['name'], row[f'option_price_{expiry}'], round(row[f'fut_price_{expiry}'],2),
#                       ' Strike: ',row[f'strike_{expiry}'])
#                 return ''
#         else:
#             # print(expiry_month, 'option < intrinsic for', row['name'], 'Strike:', row[f'strike_{expiry}'])
#             return ''
#
#     def calculate_delta(row):
#         if row[f'iv_{expiry}']:
#             try:
#                 delta_value = delta('c', row[f'fut_price_{expiry}'], row[f'strike_{expiry}'],
#                                      row[f'days_to_expiry_{expiry}'], interest_rate, row[f'iv_{expiry}'])
#                 return delta_value
#             except:
#                 print("Error in calculating delta, here is data: Script", row['name'], row[f'fut_price_{expiry}'],
#                       row[f'strike_{expiry}'], row[f'iv_{expiry}'])
#                 return ''
#         else:
#             return ''
#
#     data[f'iv_{expiry}'] = data.apply(calculate_iv, axis=1)
#     data[f'delta_{expiry}'] = data.apply(calculate_delta, axis=1)
#     data.drop([f'days_to_expiry_{expiry}', f'opt_expiry_{expiry}_date'], axis=1, inplace=True)
#     return data
#
#
# def add_option_price(kite, data, expiry, atm_only=True):
#     symbols = data[f'kite_opt_symbol_{expiry}'].to_numpy()
#     chunk_size = 500  # Number of symbols per API call
#     quote_array = {}
#     # print(f'Getting option prices for {len(symbols)} symbols')
#     # Split the symbols list into chunks
#     symbol_chunks = [symbols[i:i + chunk_size] for i in range(0, len(symbols), chunk_size)]
#     # Iterate over each symbol chunk
#     for chunk in symbol_chunks:
#         chunk_quote = kite.quote(chunk)
#         for key, value in chunk_quote.items():
#             quote_array[key] = value
#     rows = []
#     for key, value in quote_array.items():
#         kite_quote = KiteQuote(value)
#         row = {f'option_price_{expiry}': kite_quote.mid_price, f'option_oi_{expiry}': kite_quote.oi,
#                f'kite_opt_symbol_{expiry}': key}
#         rows.append(row)
#
#     option_price_live = pd.DataFrame(rows)
#     option_price_live = pd.merge(data, option_price_live, on=f'kite_opt_symbol_{expiry}')
#     if atm_only:
#         option_price_live_high_oi = option_price_live.sort_values(['name', f'option_oi_{expiry}'], ascending=[True, False])
#         option_price_live_high_oi = option_price_live_high_oi.groupby('name').head(1).reset_index()
#         option_price_live_high_oi.drop([f'kite_opt_symbol_{expiry}',f'option_oi_{expiry}', 'index'], axis=1, inplace=True)
#     else:
#         option_price_live_high_oi = option_price_live.sort_values(['name', f'strike_{expiry}'], ascending=[True, True])
#         option_price_live_high_oi.drop([f'kite_opt_symbol_{expiry}'], axis=1, inplace=True)
#     return option_price_live_high_oi
#
#
#
# zerodha_api_key = WAU359P2D1[WAU359P2D1['name'] == 'zerodha_api_key']['value'].values[0]
# access_token = WAU359P2D1[WAU359P2D1['name'] == 'zerodha_access_token']['value'].values[0]
# kite = KiteConnect(api_key=zerodha_api_key)
# kite.set_access_token(access_token)
#
#
# ##for 0
# options_df_0 = add_option_strikes(WAU359P2D3, WAU359P2D2, 0, for_skewness=False)
# options_df_0 = add_option_price(kite, options_df_0, 0, atm_only=True)
# options_df_0 = add_option_greeks(options_df_0, 0)
#
#
# options_df_1 = add_option_strikes(WAU359P2D4, WAU359P2D2, 1, for_skewness=False)
# options_df_1 = add_option_price(kite, options_df_1, 1, atm_only=True)
# options_df_1 = add_option_greeks(options_df_1, 1)
#
#
# return options_df_0, options_df_1
#
#
#
#
#
#

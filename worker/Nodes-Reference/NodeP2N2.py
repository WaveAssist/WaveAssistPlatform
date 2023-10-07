# from kiteconnect import KiteConnect
# import pandas as pd
#
# def get_future_price(df, expiry):
#     fut_df = df[df['instrument_type'] == 'FUT'].sort_values(['name', 'expiry'], ascending=[True, True])
#     fut_df = fut_df.groupby('name').apply(
#         lambda x: x.iloc[expiry] if len(x) >= 2 else None).reset_index(drop=True)
#     fut_df['kite_symbol'] = fut_df['exchange'] + ':' + fut_df['tradingsymbol']
#     fut_df = fut_df.sort_values('exchange', ascending=False).dropna().reset_index()
#     fut_df.rename(columns={'expiry': f'fut_expiry_{expiry}'}, inplace=True)
#     return fut_df[['exchange', 'name', 'kite_symbol', f'fut_expiry_{expiry}']]
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
#
# def get_fut_symbols_for_expiry(df, expiry):
#     fut_df = df[df['instrument_type'] == 'FUT'].sort_values(['name', 'expiry'], ascending=[True, True])
#     fut_df = fut_df.groupby('name').apply(
#         lambda x: x.iloc[expiry] if len(x) >= 2 else None).reset_index(drop=True)
#     fut_df['kite_symbol'] = fut_df['exchange'] + ':' + fut_df['tradingsymbol']
#     fut_df = fut_df.sort_values('exchange', ascending=False).dropna().reset_index()
#     fut_df.rename(columns={'expiry': f'fut_expiry_{expiry}'}, inplace=True)
#     return fut_df[['exchange', 'name', 'kite_symbol', f'fut_expiry_{expiry}']]
#
#
#
# def load_fut_df(expiry, WAU359P2D2, kite):
#     data = get_fut_symbols_for_expiry(WAU359P2D2, expiry)
#     fut_quotes = kite.quote(data.kite_symbol)
#     rows = []
#     for key, value in fut_quotes.items():
#         kite_quote = KiteQuote(value)
#         row = {'kite_symbol': key, f'fut_price_{expiry}': kite_quote.mid_price,
#                f'fut_high_{expiry}': kite_quote.high, f'fut_low_{expiry}': kite_quote.low}
#         rows.append(row)
#     price_df = pd.DataFrame(rows)
#     fut_df = pd.merge(data, price_df, on='kite_symbol')
#     fut_df.dropna(inplace=True)
#     return fut_df
#
#
# zerodha_api_key = WAU359P2D1[WAU359P2D1['name'] == 'zerodha_api_key']['value'].values[0]
# access_token = WAU359P2D1[WAU359P2D1['name'] == 'zerodha_access_token']['value'].values[0]
# kite = KiteConnect(api_key=zerodha_api_key)
# kite.set_access_token(access_token)
#
#
# ##Fetch values from df WAU359P2D2 with exchange as NFO
# WAU359P2D2 = WAU359P2D2[WAU359P2D2['exchange'] == 'NFO']
#
# fut_df_0 = load_fut_df(0, WAU359P2D2, kite)
# fut_df_1 = load_fut_df(1, WAU359P2D2, kite)
#
#
# return fut_df_0, fut_df_1
#
#
#

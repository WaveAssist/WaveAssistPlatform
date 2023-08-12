# import pandas as pd
# import math
#
#
# def sort_dict(dictionary_array, key_to_sort, is_ascending):
#     sorted_array = sorted(dictionary_array, key=lambda k: k[key_to_sort], reverse=not is_ascending)
#     return sorted_array
#
#
# ##Main code
#
# dollar_rate = float(WAU359P1D1[WAU359P1D1['name'] == 'dollar_rate']['value'].values[0])
#
#
# merged_calls = []
# merged_puts = []
#
#
# ##Add values of df WAU359P1D2 into WAU359P1D5 based on zerodha_id of WAU359P1D2  and instrument_token of WAU359P1D5
# zerodha_df = WAU359P1D5.merge(WAU359P1D2, on='zerodha_symbol', how='left')
# ib_df = WAU359P1D6.merge(WAU359P1D4, on='ib_id', how='left')
#
# ##Drop duplicates from zerodha_df and ib_df based on zerodha_symbol and ib_id respectively
# zerodha_df.drop_duplicates(subset=['zerodha_symbol'], inplace=True)
# ib_df.drop_duplicates(subset=['ib_id'], inplace=True)
#
# for _,row in zerodha_df.iterrows():
#     zerodha_strike_price = float(row['strike'])
#     zerodha_price = row['price']
#     zerodha_ask_price = row['ask_price']
#     zerodha_bid_price = row['bid_price']
#     converted_strike_price = zerodha_strike_price / dollar_rate
#     zerodha_option_type = row['option_type']
#     zerodha_instrument_type = row['instrument_type']
#
#     if zerodha_instrument_type != 'Options': ##Handle futures here
#         continue
#
#
#     final_zerodha_price = converted_strike_price
#     if zerodha_option_type == 'CE':
#         ##converted_strike_price be rounded down to the nearest 0.5 value - floor
#         final_zerodha_price = math.floor(converted_strike_price)
#         if converted_strike_price - final_zerodha_price >= 0.5:
#             final_zerodha_price += 0.5
#     elif zerodha_option_type == 'PE':
#         ##converted_strike_price be rounded up to the nearest 0.5 value - ceil
#         final_zerodha_price = math.ceil(converted_strike_price)
#         if final_zerodha_price - converted_strike_price >= 0.5:
#             final_zerodha_price -= 0.5
#
#     for _,row in ib_df.iterrows():
#         ib_strike_price = float(row['strike'])
#         ib_price = float(row['price'])
#         ib_option_type = row['option_type']
#         instrument_type = row['instrument_type']
#         ib_bid_price = float(row['bid_price'])
#         ib_ask_price = float(row['ask_price'])
#
#         if instrument_type != 'Options': ##Handle futures here
#             continue
#
#
#         # print("IB Price: " + str(ib_strike_price) + " Zerodha Price: " + str(final_zerodha_price) + " IB Option Type: " + str(ib_option_type) + " Zerodha Option Type: " + str(zerodha_option_type))
#         if ib_strike_price == final_zerodha_price and ib_option_type == zerodha_option_type:
#
#             entry_price = zerodha_bid_price - ib_ask_price * dollar_rate
#             exit_price = zerodha_ask_price - ib_bid_price * dollar_rate
#
#             ##Parity = dollar_rate * ib_price – zerodha_price
#             parity = (zerodha_bid_price + zerodha_ask_price) / 2 - (
#                         ib_bid_price + ib_ask_price) / 2 * dollar_rate
#
#             # Delta hedge = (IB_strike – mcx_strike/dollar) * implied_fx_rate
#             delta_hedge = abs(ib_strike_price - zerodha_strike_price / dollar_rate) * dollar_rate
#
#             # Curr hedge = (zerodha strike / IB strike) - dollar_rate
#             current_hedge = 100 * (zerodha_strike_price / ib_strike_price - dollar_rate)
#
#
#
#             output_dict = {
#                 'zerodha_strike_price': zerodha_strike_price,
#                 'ib_strike_price': ib_strike_price,
#                 'zerodha_price': zerodha_price,
#                 'ib_price': ib_price,
#                 'type': zerodha_option_type,
#                 'entry_price': entry_price,
#                 'exit_price': exit_price,
#                 'parity': parity,
#                 'delta_hedge': delta_hedge,
#                 'current_hedge': current_hedge
#             }
#             if zerodha_option_type == 'CE':
#                 merged_calls.append(output_dict)
#             elif zerodha_option_type == 'PE':
#                 merged_puts.append(output_dict)
#
# merged_calls = sort_dict(merged_calls, 'zerodha_strike_price', True)
# merged_puts = sort_dict(merged_puts, 'zerodha_strike_price', False)
#
#
#
# return pd.DataFrame(merged_calls), pd.DataFrame(merged_puts), zerodha_df, ib_df
# import pandas as pd
# dollar_rate = float(WAU359P1D1[WAU359P1D1['name'] == 'dollar_rate']['value'].values[0])
#
# # find first value for 'strike' column in WAU359P1D2 where 'instrument_type'is 'Futures'
# zerodha_future_symbol = WAU359P1D2[WAU359P1D2['instrument_type'] == 'Futures']['zerodha_symbol'].values[0]
# ib_future_id = WAU359P1D4[WAU359P1D4['instrument_type'] == 'Futures']['ib_id'].values[0]
#
#
#
#
#
# ##get the price from df WAU359P1D5 where zerodha_symvol matches zerodha_future_symbol
# try:
#     zerodha_spot = float(WAU359P1D5[WAU359P1D5['zerodha_symbol'] == zerodha_future_symbol]['price'].values[0])
# except:
#     zerodha_spot = WAU359P1D2[WAU359P1D2['instrument_type'] == 'Futures']['strike'].values[0]
#
# ##Same for IB Spot
# try:
#     ib_spot = float(WAU359P1D6[WAU359P1D6['ib_id'] == ib_future_id]['price'].values[0])
# except:
#     ib_spot = WAU359P1D4[WAU359P1D4['instrument_type'] == 'Futures']['strike'].values[0]
#
#
#
# live_dollar_rate = float(zerodha_spot/ib_spot)
# output_dict = {}
# output_dict['Zerodha Spot'] = zerodha_spot
# output_dict['IB Spot'] = ib_spot
# output_dict['Implied Dollar Rate'] = dollar_rate
#
# # round off the live_dollar_rate to 2 decimals
# live_dollar_rate = round(live_dollar_rate, 2)
#
# output_dict['Live Dollar Rate'] = live_dollar_rate
#
# try:
#     zerodha_updated = WAU359P1D17.loc[0,"Zerodha Updated"]
# except:
#     zerodha_updated = 0
#
# try:
#     ib_updated = WAU359P1D18.loc[0,"IB Updated"]
# except:
#     ib_updated = 0
#
# bottom_numbers_dict = {}
# bottom_numbers_dict['Zerodha Updated'] = zerodha_updated
# bottom_numbers_dict['IB Updated'] = ib_updated
#
#
# # return output_dict as pandas
# return pd.DataFrame([output_dict], index=[0]), pd.DataFrame([bottom_numbers_dict], index=[0])
#
#

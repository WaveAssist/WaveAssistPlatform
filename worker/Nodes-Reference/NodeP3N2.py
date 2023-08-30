import os
import requests
import csv
import pandas as pd
from io import StringIO as StringIO
import pandas as pd


def get_future_symbol(df, name):
    future_df = df[(df['instrument_type'] == 'FUT') & (df['name'] == name)].sort_values(['expiry'], ascending=[True])
    symbol = future_df.iloc[0]['exchange']   + ":" + future_df.iloc[0]['tradingsymbol']
    return symbol


def load_options_strikes(name, future_ltp, df, option_type, interval):
    all_options_df = df[(df['instrument_type'] == option_type) & (df['name'] == name)].groupby(['expiry'])
    all_current_expiry_df = all_options_df.first().reset_index()
    return all_current_expiry_df



should_refresh_strikes = str(WAU359P3D1.loc[WAU359P3D1['name'] == 'should_refresh_strikes', 'value'].iloc[0])
if should_refresh_strikes != '1':
    print("Not refreshing zerodha strikes")
    return None, None


name =  WAU359P3D2.option[0]
option_type = WAU359P3D2.option[1]
interval = float(WAU359P3D2.strategy[1])

print("Refreshing zerodha strikes for: " + name + " " + option_type + " " + str(interval))

##Get symbols & price
future_symbol = get_future_symbol(WAU359P3D3, name)

print("Future Symbol: " + future_symbol)

zerodha_api_key = WAU359P3D1.loc[WAU359P3D1['name'] == 'zerodha_api_key', 'value'].iloc[0]
zerodha_access_token = WAU359P3D1.loc[WAU359P3D1['name'] == 'zerodha_access_token', 'value'].iloc[0]


kite = KiteConnect(api_key=zerodha_api_key)
kite.set_access_token(zerodha_access_token)

## get LTP for future_symbol
fut_quote = kite.quote(future_symbol)

print("Fut Quote: " + str(fut_quote))

fut_ltp = fut_quote[future_symbol]['last_price']

print("Future LTP: " + str(fut_ltp))

all_current_expiry_df = load_options_strikes(name, fut_ltp, WAU359P3D3, option_type, interval)

WAU359P3D1['value'][WAU359P3D1['name'] == 'should_refresh_strikes'] = 0

print("All zerodha data updated!!!!!" + str(len(all_current_expiry_df)))

return WAU359P3D1, all_current_expiry_df

import os
import requests
import csv
import pandas as pd
from io import StringIO as StringIO
import pandas as pd


def get_future_symbol(df, name):
    future_df = df[(df['instrument_type'] == 'FUT') & (df['name'] == name)].sort_values(['expiry'], ascending=[True])
    symbol = future_df.iloc[0]['exchange'] + ":" + future_df.iloc[0]['tradingsymbol']
    return symbol


def load_options_strikes(df, name, option_type):
    ##From DF, fetch symbols with name & option_type and first expiry (current expiry)
    all_df = df[(df['instrument_type'] == option_type) & (df['name'] == name)].sort_values(['expiry'],
                                                                                            ascending=[True])
    current_expiry = all_df.iloc[0]['expiry']
    all_current_expiry_df = all_df[(all_df['expiry'] == current_expiry)]
    return all_current_expiry_df





name = ivdashboard_input.option[0]
option_type = ivdashboard_input.option[1]
interval = float(ivdashboard_input.strategy[1])
first_strike = float(ivdashboard_input.first_strike[0])

all_current_expiry_df = load_options_strikes(ivdashboard_zerodha_symbols, name, option_type)

##Generate strikes array as first_strike + internal for 20 strikes
strikes = []
for i in range(0, 20):
    strikes.append(first_strike + interval * i)

##make strikes into a df with column name as strike
strikes_df = pd.DataFrame(strikes, columns=['strike'])

print(strikes_df)
print(all_current_expiry_df)

merged_df = pd.merge(all_current_expiry_df, strikes_df, how='inner', on='strike')

print(merged_df)
merged_df['kite_symbol'] = merged_df['exchange'] + ":" + merged_df['tradingsymbol']

##Get the quotes for all the symbols
all_quotes = kite.quote(merged_df['kite_symbol'].tolist())

for key, value in all_quotes.items():
    price = value['last_price']
    bid_price = value['depth']['buy'][0]['price']
    ask_price = value['depth']['sell'][0]['price']
    mid_price = (bid_price + ask_price) / 2
    merged_df.loc[merged_df['kite_symbol'] == key, 'price'] = price
    merged_df.loc[merged_df['kite_symbol'] == key, 'bid_price'] = bid_price
    merged_df.loc[merged_df['kite_symbol'] == key, 'ask_price'] = ask_price
    merged_df.loc[merged_df['kite_symbol'] == key, 'mid_price'] = mid_price

return merged_df




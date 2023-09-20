import os
import requests
import csv
import pandas as pd
from io import StringIO as StringIO
import pandas as pd


def fetch_symbol_data(symbol, ivdashboard_zerodha_symbols):
    ##Check if ivdashboard_zerodha_symbols has any row for column name as symbol
    try:
        select_df = ivdashboard_zerodha_symbols[ivdashboard_zerodha_symbols['name'].str.casefold() == symbol.casefold()]
        if len(select_df) > 0:
            print("Using existing symbols")
            return select_df
    except:
        pass ##Continue further, load new symbols


    print("Fetching new symbols")
    instrument_url = "https://api.kite.trade/instruments"
    # Retrieve the CSV dump
    response = requests.get(instrument_url)
    if response.status_code == 200:
        # Convert the response content to a string
        content_str = response.text
        instruments_df = pd.read_csv(StringIO(content_str))
        instruments_df = instruments_df[instruments_df['exchange'] == 'NFO']
        instruments_df = instruments_df[instruments_df['name'].str.casefold() == symbol.casefold()]
        print("All zerodha stocks Loaded!!!!!" + str(len(instruments_df)))
        return instruments_df
    else:
        print("Failed to retrieve data. Status code:", response.status_code)
        return None



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



def process_data(ivdashboard_input, ivdashboard_zerodha_symbols):

    name = ivdashboard_input.option[0]
    option_type = ivdashboard_input.option[1]
    interval = float(ivdashboard_input.strategy[1])
    first_strike = float(ivdashboard_input.first_strike[0])
    should_run = float(ivdashboard_input.first_strike[1])

    if should_run == 0:
        return None, None

    zerodha_symbols = fetch_symbol_data(name, ivdashboard_zerodha_symbols)
    all_current_expiry_df = load_options_strikes(zerodha_symbols, name, option_type)

    ##Generate strikes array as first_strike + internal for 20 strikes
    strikes = []
    for i in range(0, 20):
        strikes.append(first_strike + interval * i)


    ##make strikes into a df with column name as strike
    strikes_df = pd.DataFrame(strikes, columns=['strike'])
    merged_df = pd.merge(all_current_expiry_df, strikes_df, how='inner', on='strike')
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


    columns_array = ['strike' ,'mid_price']
    for col in ['c1', 'c2', 'c3', 'c4', 'c5', 'c6']:
        difference = float(ivdashboard_input[col][0])
        ratio = float(ivdashboard_input[col][1])

        new_column_name = col ## + '--' + str(ratio) + '--' + str(difference)
        # Sort the DataFrame by 'strike' in ascending order
        merged_df.sort_values(by='strike', inplace=True)

        # Calculate the integer shift value
        shift_value = int(difference / interval)

        # Add a new column by performing the specified calculation
        temp_result = merged_df['mid_price'] - (ratio * merged_df['mid_price'].shift(-shift_value).fillna(0))

        # Apply rounding to the intermediate result and assign it to the new column
        merged_df[new_column_name] = round(temp_result, 1)

        columns_array.append(new_column_name)


    merged_df = merged_df[columns_array]
    merged_df['mid_price'] = merged_df['mid_price'].round(1)
    merged_df.fillna(0, inplace=True)

    return merged_df, zerodha_symbols




df_0, sym_0 = process_data(ivdashboard_input, ivdashboard_zerodha_symbols)
df_1, sym_1 = process_data(ivdashboard_input_1, ivdashboard_zerodha_symbols)
df_2, sym_2 = process_data(ivdashboard_input_2, ivdashboard_zerodha_symbols)
df_3, sym_3 = process_data(ivdashboard_input_3, ivdashboard_zerodha_symbols)

##Merge all sym into one df
zerodha_symbols = pd.DataFrame()
arr = [sym_0, sym_1, sym_2, sym_3]
for s_df in arr:
    if s_df is not None:
        zerodha_symbols = pd.concat([zerodha_symbols, s_df], ignore_index=True)

return df_0, df_1, df_2, df_3, zerodha_symbols


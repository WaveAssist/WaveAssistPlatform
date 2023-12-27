
from datetime import datetime
import pandas as pd
import pytz
import requests
import json
ist = pytz.timezone('Asia/Kolkata')

auth_token = 'REMOVED_CREDENTIAL'

##This will fetch data from API and return 3 df.
##1. vyapak_IB_strikes
##2. vyapak_IB_options
##3. vyapak_IB_updated ##Date

def fetch_df_from_api():
    try:
        url = "http://127.0.0.1:8000/loadCLData/"
        data_dict = {
            "token": auth_token,
        }
        response_of_api = requests.post(url,
                                        verify=False,
                                        data=data_dict,
                                        timeout=3)
        response_code = str(response_of_api.status_code)
        if response_code == '200':
            response_json = response_of_api.json()
            if response_code == '200' and response_json['success'] == '1':
                response_data = response_json['data']
                data_df = pd.DataFrame(response_data)
                return data_df
        return None
    except Exception as e:
        print("Error in fetching CL API: " + str(e))
        return None


try:
    df = fetch_df_from_api()
    # Convert DataFrame
    df['expiry'] = df['Ser/Exp']
    df['strike'] = df['StrikePrice']
    df['instrument_type'] = df.apply(lambda row: 'Futures' if row['StrikePrice'] == 0 else 'Options', axis=1)
    df['exchange'] = 'NYMEX'
    df['connection_type'] = 'IB'
    df['ib_symbol'] = df['Symbol']
    df['name'] = df['Symbol']

    df['option_type'] = df.apply(lambda row: 'F' if row['StrikePrice'] == 0 else 'Option', axis=1)
    df['ib_id'] = range(1, len(df) + 1)  # Generate incremental IB IDs

    print(df)

    # Create the new DataFrame
    prices_array = []

    # Iterate through the original DataFrame and add rows to the new DataFrame
    for _, row in df.iterrows():
        ib_id = row['ib_id']
        bid_price = float(row['BuyPrice'])
        ask_price = float(row['SellPrice'])
        price = (bid_price + ask_price) / 2  # Calculate the average price
        prices_array.append([ib_id, bid_price, ask_price, price])
    prices_df = pd.DataFrame(prices_array, columns=['ib_id', 'bid_price', 'ask_price', 'price'])

    # Select columns
    df = df[['name', 'expiry', 'strike', 'option_type', 'instrument_type', 'exchange', 'connection_type', 'ib_symbol',
             'ib_id']]



    ##Fill Nan values with 0
    df.fillna(0, inplace=True)
    prices_df.fillna(0, inplace=True)


    if len(df) == 0:
        print("No data returned from CL")
        return None, None, None

    ib_updated = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")
    ib_dict = {'IB Updated': ib_updated}
    updated_df = pd.DataFrame([ib_dict], index=[0])

    print("CL Data updated for " + str(len(prices_df)) + " strikes")

    print(prices_df)
    print(df)
    print(updated_df)

    ##Return
    return prices_df, df, updated_df


except Exception as e:
    print("Error in fetching CRUDE OIL CL Data: " + str(e))
    return None, None, None



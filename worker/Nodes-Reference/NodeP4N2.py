import time

import pandas as pd
from datetime import datetime
from datetime import timedelta as td

print("Starting CAGR LOAD")
print("Test: " + str(kite.profile()))

should_refresh_cagr = str(CAGR_input_df[CAGR_input_df['name'] == 'should_refresh_cagr']['value'].values[0])
if should_refresh_cagr == "0":
    return None, None

## Get data from Zerodha for each stock in WAU431P1D3
today_date = datetime.now().strftime("%Y-%m-%d")
##Date 1900 days ago
start_date = (datetime.now() - td(days=1990)).strftime("%Y-%m-%d")
CAGR_stocks_df = CAGR_stocks_df.head(100)
cagr_array = []
##Iterate through WAU431P1D3
for index, row in CAGR_stocks_df.iterrows():
    print("Starting with row: " + str(row['name']))
    try:
        instrument_token = row['instrument_token']
        instrument_name = row['name']
        symbol = row['tradingsymbol']
        ##Get data from Zerodha
        historical_data = kite.historical_data(instrument_token, start_date, today_date, 'day', continuous=False, oi=False)
        history_df = pd.DataFrame(historical_data)
        ##Get 7 day, 14 day, 30 day, 60 day, 90 day, 180 day, 270 day, 1 year, 2 year, 3 year, 4 year & 5 year CAGR
        n_days_array = [30, 90, 180, 270, 365, 730, 1095, 1460]
        for n_days in n_days_array:
            try:
                ending_value = history_df['close'].iloc[-1]
                beginning_value = history_df['close'].iloc[-n_days]
                number_of_years = n_days / 365.25  # Assuming 365.25 days in a year
                CAGR = ((ending_value / beginning_value) ** (1 / number_of_years) - 1) * 100
                ##Round CAGR to 2 decimals
                CAGR = round(CAGR, 2)

                cagr_dict = {'instrument_name': instrument_name, 'symbol': symbol,
                             'n_days': n_days, 'CAGR': CAGR}
                cagr_array.append(cagr_dict)
                print("CAGR for " + str(row['name']) + " is: " + str(CAGR)  + 'with Begning_value ' + str(beginning_value) + ' and ending value ' + str(ending_value))
            except Exception as e:
                print("SKipping CAGR for: " + str(row['name']) + " " + str(e))
                continue
        time.sleep(0.5)
    except Exception as e:
        print("Error for row: " + str(row['name']) + " " + str(e))
        continue

df = pd.DataFrame(cagr_array)

cagr_data = {}
for cagr_dict in cagr_array:
    key = (cagr_dict['instrument_name'], cagr_dict['symbol'])
    cagr_data.setdefault(key, {})[cagr_dict['n_days']] = cagr_dict['CAGR']

final_data = []
for key, cagrs in cagr_data.items():
    instrument_name, symbol = key
    row = {'instrument_name': instrument_name, 'symbol': symbol}
    for n_days in [7, 14, 30, 60, 90, 180, 270, 365, 730, 1095, 1460, 1825]:
        row[f'{n_days}_day_CAGR'] = cagrs.get(n_days, 0)  # Set CAGR to 0 if not present
    final_data.append(row)

CAGR_df = pd.DataFrame(final_data)
CAGR_input_df['value'][CAGR_input_df['name'] == 'should_refresh_cagr'] = 0
return CAGR_df, CAGR_input_df
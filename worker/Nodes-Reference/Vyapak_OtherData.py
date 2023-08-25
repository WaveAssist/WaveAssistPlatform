import pandas as pd
dollar_rate = float(vyapak_input[vyapak_input['name'] == 'dollar_rate']['value'].values[0])


# find first value for 'strike' column in WAU359P1D2 where 'instrument_type'is 'Futures'
zerodha_spot = vyapak_zerodha_data[vyapak_zerodha_data['Option Type'] == 'F']['Price'].values[0]
ib_spot = vyapak_IB_data[vyapak_IB_data['Option Type'] == 'F']['Price'].values[0]

live_dollar_rate = float(zerodha_spot/ib_spot)

output_dict = {}
output_dict['Zerodha Spot'] = zerodha_spot
output_dict['IB Spot'] = ib_spot
output_dict['Selected Dollar Rate'] = dollar_rate

# round off the live_dollar_rate to 2 decimals
live_dollar_rate = round(live_dollar_rate, 2)

output_dict['Live Dollar Rate'] = live_dollar_rate

try:
    zerodha_updated = vyapak_zerodha_updated.loc[0,"Zerodha Updated"]
except:
    zerodha_updated = 0

try:
    ib_updated = vyapak_IB_updated.loc[0,"IB Updated"]
except:
    ib_updated = 0

bottom_numbers_dict = {}
bottom_numbers_dict['Zerodha Updated'] = zerodha_updated
bottom_numbers_dict['IB Updated'] = ib_updated


# return output_dict as pandas
return pd.DataFrame([bottom_numbers_dict], index=[0]), pd.DataFrame([output_dict], index=[0])



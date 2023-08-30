from datetime import datetime
import pandas as pd
import pytz
ist = pytz.timezone('Asia/Kolkata')
from ibapi.contract import Contract


def fetch_options_contracts(WAU359P1D3):
    def create_contract(row):
        expiry_month_string = pd.to_datetime(row['expiry']).strftime("%Y%m")

        if row['instrument_type'] == 'Futures':
            contract = Contract()
            contract.symbol = row['name']
            contract.secType = 'FUT'
            contract.exchange = row['exchange']
            contract.currency = 'USD'
            contract.lastTradeDateOrContractMonth = expiry_month_string
            return contract
        else:
            contract = Contract()
            contract.symbol = row['name']
            contract.secType = 'FOP'
            contract.exchange = row['exchange']
            contract.currency = 'USD'
            contract.tradingClass = 'LO'
            contract.lastTradeDateOrContractMonth = expiry_month_string
            contract.strike = row['strike']
            contract.right = 'C' if row['option_type'] == 'CE' else 'P'
            return contract


    # Create an array of contract objects
    contract_object_array = []
    ib_id_array = []
    for _,row in WAU359P1D3.iterrows():
        contract_object = create_contract(row)
        ib_id = row['ib_id']
        contract_object_array.append(contract_object)
        ib_id_array.append(ib_id)

    return contract_object_array, ib_id_array

##Main Code


def refresh_subscribe(output_df):
    ##remove duplicates based on ib_id
    output_df.drop_duplicates(subset='ib_id', keep='first', inplace=True)
    contract_object_array, ib_id_array = fetch_options_contracts(output_df)
    for i, contract in enumerate(contract_object_array):
        ib_id = ib_id_array[i]
        ib_app.reqMktData(ib_id, contract, '', False, False, [])
    return


try:
    print("Starting IB Data Load")

    refresh_subscribe(vyapak_IB_strikes)

    ##Format tick_data_dictionary
    output_df = pd.DataFrame.from_dict(ib_app.tick_data_dictionary, orient='index')

    # Add 'instrument_token' as a new column
    output_df.reset_index(inplace=True)
    output_df.rename(columns={'index': 'ib_id'}, inplace=True)

    ##Fill Nan values with 0
    output_df.fillna(0, inplace=True)

    if len(output_df) == 0:
        print("No data returned from IB")
        return None, None

    ib_updated = ib_app.last_refreshed.strftime("%Y-%m-%d %H:%M:%S")
    ib_dict = {'IB Updated': ib_updated}

    print("IB Data updated for " + str(len(output_df)) + " strikes")
    return output_df, pd.DataFrame([ib_dict], index=[0])

except Exception as e:
    print("Error in fetching IB Strikes: " + str(e))
    return None, None




##Fetching zerodha prices
# wavepredict_stockmetadata with columns exchange_specific_id	exchange_specific_symbol	name	symbol_type	exchange	symbol	source	fetched_till_timestamp
from datetime import datetime
from datetime import timedelta
import pandas as pd
from pymongo import MongoClient
CONNECTION_STRING = "REMOVED_CREDENTIAL"
from time import sleep
##Iterate through the stockmetadata

print("Starting to fetch data")
data_array = []

for index, row in wavepredict_stockmetadata.iterrows():

    try:
        sleep(0.1)
        symbol = row['symbol']
        exchange_specific_id = str(row['exchange_specific_id'])
        fetched_till_timestamp = datetime.strptime(row['fetched_till_timestamp'], '%Y-%m-%d %H:%M:%S')

        ##fetched_till_timestamp with time as 00:00:00 in datetime format
        from_date = datetime.combine(fetched_till_timestamp.date(), datetime.min.time())

        ##todays date with time as 00:00:00 in datetime format
        today_datetime = datetime.combine(datetime.now().date(), datetime.min.time())

        ##to date is 5 years from fetched_till_timestamp or today's date, whichever is earlier
        to_date = min(fetched_till_timestamp + timedelta(days=5 * 365), today_datetime)
        to_date = datetime.combine(to_date.date(), datetime.min.time()) ##Extra check to make sure time is 00:00:00

        if from_date >= to_date:
            continue

        print(f"Fetching data for {symbol} from {from_date} to {to_date}")

        ##Get data from Zerodha
        history_data = kite.historical_data(exchange_specific_id, from_date.strftime('%Y-%m-%d %H:%M:%S'), to_date.strftime('%Y-%m-%d %H:%M:%S'), 'day',
                                             continuous=False, oi=False)

        ##Convert to dataframe
        history_df = pd.DataFrame(history_data)

        wavepredict_stockmetadata.loc[index, 'fetched_till_timestamp'] = to_date.strftime('%Y-%m-%d %H:%M:%S')

        if len(history_df) == 0:
            continue

        meta_data = {'symbol': symbol,
                     'exchange_specific_id': exchange_specific_id,
                     'name': row['name'],
                     'exchange': row['exchange'],
                     'source': row['source'],
                     }
        summary_dict = {
            'meta_data': meta_data,
            'history_df': history_df
        }
        data_array.append(summary_dict)

        ##Change wavepredict_stockmetadata fetched_till_timestamp to to_date

        print(f"Completed {symbol}")
    except Exception as e:
        print(f"Error in fetching data for {symbol} - {e}")
        sleep(1)
        pass


##Insert data into mongo
if len(data_array) > 0:
    client = MongoClient(CONNECTION_STRING, 27017)
    db = client.WavePredict
    collection = db.DailyStockData

    for data_dict in data_array:
        meta_data = data_dict['meta_data']
        history_df = data_dict['history_df']
        data_array = []
        for index, row in history_df.iterrows():
            try:
                data = {
                    "timestamp": datetime.utcfromtimestamp(row['date'].timestamp()),
                    "metadata": meta_data,
                    "close": row['close'],
                    "open": row['open'],
                    "high": row['high'],
                    "low": row['low'],
                    "volume": row['volume']
                }
                data_array.append(data)
            except Exception as e:
                print(f"Error in inserting data for {meta_data['symbol']} - {e}")
                pass
        collection.insert_many(data_array)
        print(f"Inserted {len(data_array)} records for {meta_data['symbol']}")

return wavepredict_stockmetadata
import pandas as pd
import boto3
import numpy as np
import tensorflow as tf
MAX_INDUSTRY_CODE = 156
BUCKET_NAME = 'wavepredictmodels'
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime
from datetime import timedelta
from pymongo import MongoClient
CONNECTION_STRING = "REMOVED_CREDENTIAL"
ACCESS_KEY = 'REMOVED_CREDENTIAL'
SECRET_KEY = 'REMOVED_CREDENTIAL'

client = MongoClient(CONNECTION_STRING, 27017)
db = client.WavePredict
collection = db.DailyStockData
prediction_collection = db.PredictedDailyStockData

def generate_predictions(y_value, last_element, percentage=50):
    if y_value == 1:
        forecast_element = last_element + (percentage/100) * last_element
    elif y_value == -1:
        forecast_element = last_element - (percentage/100) * last_element
    else:
        forecast_element = last_element + y_value/100 * percentage * last_element
    return forecast_element

## Fetch models from s3

models_dictionary = {}

s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)
##Iterate through wavepredict_models df
for index, row in wavepredict_models.iterrows():
    model_key = row['ModelKey']
    model_name = model_key + '.keras'
    local_path = 'tmp/' + model_name
    # Download the model from S3 to the local machine
    s3.download_file(BUCKET_NAME, model_name, local_path)
    # Load the model using TensorFlow/Keras
    print("Loading model: " + model_key)
    model = tf.keras.models.load_model(local_path)
    print("Model loaded: " + model_key)
    ##Store all other details in row also to the models_dictionary
    row_dictionary = row.to_dict()
    value_dict = {
        'model': model,
        'row': row_dictionary
    }
    models_dictionary[model_key] = value_dict


## Fetch all stocks

wavepredict_stockmetadata = wavepredict_stockmetadata.sort_values(by='M1', ascending=True)

batch_size = 10
## iterate through wavepredict_stockmetadata df
for index, row in wavepredict_stockmetadata.iterrows():
    batch_size = batch_size - 1
    if batch_size <= 0:
        continue

    ##Iterate through models_dictionary
    for key, value in models_dictionary.items():
        predictions_array = []
        cutoff_date = value['row']['Cutoff']
        try:
            processed_till_timestamp = datetime.strptime(row[key], '%Y-%m-%d %H:%M:%S')
        except:
            processed_till_timestamp = datetime.strptime(cutoff_date, '%Y-%m-%d') ##Figure out how to keep cutoff date to recent.


        ##fetched_till_timestamp with time as 00:00:00 in datetime format
        from_date = datetime.combine(processed_till_timestamp.date(), datetime.min.time()) ##This is not processed.
        yesterday_date = datetime.now() - timedelta(days=1)
        to_date = datetime.combine(yesterday_date.date(), datetime.min.time()) ##This will not be processed. it will be -1 day.

        if from_date >= to_date:
            continue

        ##Loop from from_date to to_date adding 1 day each time

        while(from_date < to_date):
            try:
                from_date = from_date + timedelta(days=1)

                ##Process from_date data with from_date as the last_date of data
                n_previous = int(value['row']['Previous'])

                ##Including from_date, fetch n_previous rows of data from mongo collection collection
                stock_history_data = collection.find({'metadata.symbol': row['symbol'], 'timestamp': {'$lte': from_date}}).sort('timestamp', -1).limit(n_previous)
                stock_history_df = pd.DataFrame(stock_history_data)

                ##Sort the dataframe by timestamp in ascending order
                stock_history_df = stock_history_df.sort_values(by=['timestamp'])

                ##Prepare input data for model

                selected_columns = ['close','open','high','low','volume']
                stock_history_df = stock_history_df.sort_values(by=['timestamp'])
                select_df = stock_history_df[selected_columns]
                select_df.reset_index(inplace=True)
                select_df = select_df.drop(columns=['index'])

                dataset = np.array([select_df.values])
                ##Additional Individual Scaling of x
                x_scaled = []
                for data in dataset:
                    scaler = MinMaxScaler(feature_range=(0, 1))
                    scaled_data = scaler.fit_transform(data)
                    x_scaled.append(scaled_data)

                x_scaled = np.array(x_scaled)
                industry_code = row['industry_code']
                x = np.concatenate((x_scaled, np.full((x_scaled.shape[0], x_scaled.shape[1], 1), industry_code)), axis=2)

                percent_capped = int(value['row']['PercentCapped'])
                ## Run model
                model = value['model']

                # print("Input Shape: " + str(x.shape))
                y_pred = model.predict(x)
                y_value = y_pred[0][0]  ##ToDo - needs error handing and dynamic values
                prediction = generate_predictions(y_value, stock_history_df['close'].iloc[-1], percent_capped)

                ##Prediction Date
                n_next = int(value['row']['Next'])
                from_date_str = from_date.strftime('%Y-%m-%d')
                prediction_date_np = np.busday_offset(from_date_str, n_next, roll='forward')
                prediction_date = prediction_date_np.astype(datetime)
                prediction_date = datetime.combine(prediction_date, datetime.min.time())
                # print("Prediction Date: " + prediction_date.strftime('%Y-%m-%d') + " and Prediction: " + str(prediction) + " and symbol: " + row['symbol'] + " and model: " + key + " and date: " + from_date.strftime('%Y-%m-%d'))
                ## Save output to mongo

                meta_data = {
                    "symbol": row['symbol'],
                    "model": key,
                    "exchange": row['exchange'],
                    "start_date": from_date.strftime('%Y-%m-%d')
                }

                predictions_data = {
                    "timestamp": datetime.utcfromtimestamp(prediction_date.timestamp()),
                    "metadata": meta_data,
                    "predicted_close": float(prediction),

                }
                predictions_array.append(predictions_data)

            except Exception as e:
                print("Error with symbol: " + row['symbol'] + " and model: " + key + " and date: " + from_date.strftime('%Y-%m-%d') + " and error: " + str(e))
                continue

        prediction_collection.insert_many(predictions_array)
        print(f"Inserted {len(predictions_array)} records for symbol: " + row['symbol'] + " and model: " + key )

        ##Update last processed date in wavepredict_stockmetadata
        wavepredict_stockmetadata.loc[index, key] = to_date.strftime('%Y-%m-%d %H:%M:%S')

return wavepredict_stockmetadata


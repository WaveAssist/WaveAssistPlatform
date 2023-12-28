import pandas as pd
import boto3
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime
from datetime import timedelta
from pymongo import MongoClient
import os

CONNECTION_STRING = "REMOVED_CREDENTIAL"
BUCKET_NAME = 'wavepredictmodels'
MAX_INDUSTRY_CODE = 156

client = MongoClient(CONNECTION_STRING, 27017)
db = client.WavePredict
collection = db.DailyStockData
prediction_collection = db.PredictedDailyStockData
index_symbol = 'NIFTY 50'
TMP_PATH = 'tmp/WavePredict/'

##Create local folder for TMP_PATH if it doesn't exist
if not os.path.exists(TMP_PATH):
    os.makedirs(TMP_PATH)


def add_business_days(start_date, business_days_to_add):
    current_date = start_date
    while business_days_to_add > 0:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:  # This checks if it's a weekday (Mon-Fri)
            business_days_to_add -= 1
    return current_date


def clean_df(df, selected_columns=None):
    if selected_columns is None:
        selected_columns = ['timestamp', 'close']

    df = df[selected_columns]
    df = df.sort_values(by=['timestamp'])

    df.reset_index(inplace=True)
    df = df.drop(columns=['index'])

    # Convert the timestamp column in stock_df to datetime and extract date
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['timestamp'] = df['timestamp'].dt.date
    df = df.drop_duplicates(subset='timestamp', keep='first')
    return df


def generate_predictions(y_value, last_element, percentage=25):
    if y_value == 1:
        forecast_element = last_element + (percentage / 100) * last_element
    elif y_value == -1:
        forecast_element = last_element - (percentage / 100) * last_element
    else:
        forecast_element = last_element + y_value / 100 * percentage * last_element
    return forecast_element


def download_all_models(models_df, bucket_name):
    models_dictionary = {}
    ##Iterate through wavepredict_models df
    for index, row in models_df.iterrows():
        try:
            model_key = row['ModelKey']
            model_name = model_key + '.keras'
            local_path = TMP_PATH + model_name


            # Download the model from S3 to the local machine
            s3.download_file(bucket_name, model_name, local_path)
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

        except Exception as e:
            print("Skipping model: " + row['ModelKey'] + " due to error: " + str(e))
            continue
    return models_dictionary

## Fetch models from s3

##Select rows from wavepredict_models df where Status is 1
wavepredict_models = wavepredict_models[wavepredict_models['Status'] == 1] ##Only using active models. 0 is inactive.
models_dictionary = download_all_models(wavepredict_models, BUCKET_NAME)
print("models_dictionary loaded successfully: " + str(len(models_dictionary)))


##Fetch index data here.
index_data = collection.find({'metadata.symbol': index_symbol})
index_df = pd.DataFrame(index_data)
index_df = clean_df(index_df)
index_df = index_df.rename(columns={'close': 'index_close'})


if len(models_dictionary) == 0:
    print("No active models found. Exiting...")
    return wavepredict_processing_status


## iterate through wavepredict_stockmetadata df
for index, row in wavepredict_stockmetadata.iterrows():
    symbol = row['symbol']
    industry_code = row['industry_code']
    symbol_code = row['symbol_code']
    print("Processing symbol: " + symbol)

    try:
        stock_data = collection.find({'metadata.symbol': symbol})
        stock_df = pd.DataFrame(stock_data)
        selected_columns = ['timestamp', 'close', 'open', 'high', 'low', 'volume']
        stock_df = clean_df(stock_df, selected_columns)
    except:
        print("Skipping symbol: " + symbol + " due to error in fetching data")
        continue


    ##Iterate through models_dictionary
    for model_key, value in models_dictionary.items():
        model_dict = value['row']
        predictions_array = []
        cutoff_date = model_dict['Cutoff']
        n_previous = int(model_dict['Previous'])
        percent_capped = int(model_dict['PercentCapped'])
        n_next = int(model_dict['Next'])

        try:
            processed_till_value = wavepredict_processing_status[wavepredict_processing_status['symbol'] == symbol].iloc[0][model_key]
            processed_till_timestamp = datetime.strptime(processed_till_value, '%Y-%m-%d %H:%M:%S')
        except:
            processed_till_timestamp = datetime.strptime(cutoff_date, '%Y-%m-%d')  ##Figure out how to keep cutoff date to recent.

        ##fetched_till_timestamp with time as 00:00:00 in datetime format
        from_date = datetime.combine(processed_till_timestamp.date(), datetime.min.time())  ##This is processed.
        yesterday_date = datetime.now() - timedelta(days=1)
        to_date = datetime.combine(yesterday_date.date(),
                                   datetime.min.time())  ##This will not be processed. it will be -1 day.

        if from_date >= to_date:
            print("Skipping symbol: " + symbol + " as it is already processed till: " + str(from_date))
            continue

        x_arr = []
        last_close_arr = []
        from_date_arr = []

        ##Loop from from_date to to_date adding 1 day each time
        while (from_date < to_date):
            try:
                from_date = from_date + timedelta(days=1)
                ##Check if the from_date is not a business day
                if from_date.weekday() >= 5:
                    continue

                print("Processing date: " + str(from_date))


                ##Including from_date, fetch n_previous rows of data from mongo collection collection
                stock_history_df = stock_df[stock_df['timestamp'] <= from_date]

                ##Sort the dataframe by timestamp in ascending order. Oldest date first. Recent last. This is important.
                stock_history_df = stock_history_df.sort_values(by=['timestamp'], ascending=True)

                ##Cut here. Take the first n_previous rows
                stock_history_df = stock_history_df.tail(n_previous)

                ##Merge index_df to stock_history_df
                stock_history_df = pd.merge(stock_history_df, index_df, on='timestamp', how='left')

                ##Prepare input data for model
                selected_columns = ['close', 'open', 'high', 'low', 'volume', 'index_close']
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

                ##Add industry code to the x_scaled
                x = np.concatenate((x_scaled, np.full((x_scaled.shape[0], x_scaled.shape[1], 1), industry_code)),
                                   axis=2)
                ##Add symbol code to x
                x = np.concatenate((x, np.full((x.shape[0], x.shape[1], 1), symbol_code)), axis=2)

                expected_x_shape = (1, n_previous, 8)  ##ToDo: 8 needs to be dynamic
                if x.shape != expected_x_shape:
                    print("Wrong shape for symbol: " + row[
                        'symbol'] + " and model: " + model_key + " and date: " + from_date.strftime(
                        '%Y-%m-%d') + " and shape: " + str(x.shape) + " and expected shape: " + str(expected_x_shape))
                    continue

                x_arr.append(x)
                last_close_arr.append(stock_history_df['close'].iloc[-1])
                from_date_arr.append(from_date)


            except Exception as e:
                print("Error with symbol: " + row['symbol'] + " and model: " + model_key + " and date: " + from_date.strftime(
                    '%Y-%m-%d') + " and error: " + str(e))
                continue

        ##Predict for all x_arr

        if len(x_arr) != 0:
            ## Run model
            model = value['model']

            # print("Input Shape: " + str(x.shape))
            x_res = np.concatenate(x_arr, axis=0)

            y_pred = model.predict(x_res)

            for i in range(len(x_arr)):
                try:
                    y_value = y_pred[i][0]
                    prediction = generate_predictions(y_value, last_close_arr[i], percent_capped)

                    ##Prediction Date
                    from_date = from_date_arr[i]
                    prediction_date = add_business_days(from_date, n_next)
                    prediction_date = datetime.combine(prediction_date, datetime.min.time())

                    ## Save output to mongo
                    meta_data = {
                        "symbol": row['symbol'],
                        "model": model_key,
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
                    print("Error with predictions: " + row['symbol'] + " and model: " + model_key + " and date: " + from_date.strftime(
                        '%Y-%m-%d') + " and error: " + str(e))
                    continue

            prediction_collection.insert_many(predictions_array)
            print(f"Inserted {len(predictions_array)} records for symbol: " + row['symbol'] + " and model: " + model_key)
        else:
            print("No records to insert for symbol: " + row['symbol'] + " and model: " + model_key)

        ##Update last processed date in wavepredict_processing_status
        wavepredict_processing_status.loc[wavepredict_processing_status['symbol'] == symbol, model_key] = to_date.strftime(
            '%Y-%m-%d %H:%M:%S')

return wavepredict_processing_status


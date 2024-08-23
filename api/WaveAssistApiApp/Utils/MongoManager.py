import pandas as pd
from WaveAssistApiApp.Utils.constants import *
from pymongo import MongoClient
import WaveAssistApiApp.Utils.utils as utils
import numpy as np
import datetime
from datetime import datetime
from WaveAssistApi.settings import MONGO_CONNECTION_STRING
class MongoManager:

    ##Class Functions
    @classmethod
    def remove_id_from_array(cls, data_array):
        ##Remove any element with prefix _id from array
        updated_data_array = []
        for data in data_array:
            data = {key: value for key, value in data.items() if not key.startswith('_id')}
            data = {key: value for key, value in data.items() if not key.startswith('id')}
            updated_data_array.append(data)
        return updated_data_array

    @classmethod
    def add_row_number(cls,data_array):
        ##Add a row_number column to each element in data_array starting with 1.
        updated_data_array = []
        for data in data_array:
            data['row_number'] = data_array.index(data) + 1
            updated_data_array.append(data)
        return updated_data_array

    @classmethod
    def convert_id_in_data(cls, data_array):
        ##Convert _id to id in each element in data_array
        updated_data_array = []
        for data in data_array:
            data['id'] = str(data.pop('_id', None))
            updated_data_array.append(data)
        return updated_data_array

    @classmethod
    def manage_na(cls,data_array):
        ##Update NA values to 0
        updated_data_array = []
        for data in data_array:
            data = {key: value if value is not None else 0 for key, value in data.items()}
            updated_data_array.append(data)
        return updated_data_array


    @classmethod
    def manage_dict_formatting(cls,data_dict):
        for key, data_array in data_dict.items():
            data_dict[key] = cls.manage_formatting(data_array)
        return data_dict

    @classmethod
    def manage_formatting(cls,data_array):
        updated_data_array = []
        for data in data_array:
            data['row_number'] = data_array.index(data) + 1
            for key, value in data.items():
                if value is None:
                    value = 0
                try:
                    if np.isnan(value):
                        value = 0
                    if np.isinf(value):
                        value = 0
                except:
                    pass

                ##Check if value is of type datetime
                if isinstance(value, datetime):
                    value = value.strftime("%Y-%m-%d %H:%M:%S")
                data[key] = value
            updated_data_array.append(data)
        return updated_data_array

    ##Init Function
    def __init__(self, collection_name=None, connection_string=MONGO_CONNECTION_STRING, database_name=DB_NAME):
        self.client = MongoClient(connection_string)
        self.database = self.client[database_name]
        if collection_name is not None:
            self.collection = self.database[collection_name]


    ##Instance Functions
    def insert_or_replace_data_for_key(self, io_key, data_array):
        try:
            new_data_dict = {}
            new_data_dict[IO_DATA_KEY] = io_key
            new_data_dict[DATA_KEY] = data_array
            self.collection.replace_one({IO_DATA_KEY: io_key}, new_data_dict, upsert=True)
            return True
        except Exception as e:
            utils.logger.error("Error in insert_or_replace_data_for_key: " + io_key + ": " + str(e))
            return False

    ##Fetch data, return None if no data exists.
    def fetch_data_for_key(self, io_key):
        try:
            full_data = self.collection.find_one({IO_DATA_KEY: io_key})
            if full_data is None or len(full_data) == 0 or DATA_KEY not in full_data:
                return []

            data = full_data[DATA_KEY]
            return data

        except Exception as e:
            utils.logger.error("Error in fetch_data for key " + io_key + ": " + str(e))
            return []


    ## Fetch data for multiple keys, return an empty list if no data exists.
    def fetch_data_for_keys_array(self, io_keys_array):
        try:
            output_dict = {}
            # Fetch documents that have IO_DATA_KEY in io_keys_array
            cursor = self.collection.find({IO_DATA_KEY: {"$in": io_keys_array}})

            # Convert the cursor to a list of documents
            documents_array = list(cursor)

            if not documents_array:
                return output_dict

            for document_dict in documents_array:
                try:
                    key = document_dict[IO_DATA_KEY]
                    value = document_dict['DATA']
                    output_dict[key] = value
                except:
                    pass
            return output_dict

        except Exception as e:
            utils.logger.error("Error in fetch_data_for_keys_array: " + str(e))
            return []


    def close_connection(self):
        self.client.close()



    ##Helper functions
    def fetch_data_as_dataframe(self, io_key):
        data_fetched = self.fetch_data_for_key(io_key)
        if len(data_fetched) == 0:
            return None
        ##Check if data can be converted to proper PD dataframe
        try:
            data = pd.DataFrame(data_fetched)
            return data
        except Exception as e:
            utils.logger.error("Error in get_data_as_dataframe: " + str(e))
            return None

    def prepare_df_for_bson(self,df):
        # Convert datetime.date to datetime.datetime
        for col in df.columns:
            df[col] = df[col].apply(
                lambda x: datetime.datetime.combine(x, datetime.datetime.min.time()) if isinstance(x,
                                                                                                   datetime.date) and not isinstance(
                    x, datetime.datetime) else x)

        # Replace NaN, NaT, and pd.NA with None
        df = df.replace(np.nan, None)
        df = df.replace({pd.NaT: None})
        df = df.replace({pd.NA: None})

        # Explicitly convert datetime columns to Python datetime objects
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].apply(
                    lambda x: x.to_pydatetime() if isinstance(x, pd.Timestamp) and pd.notna(x) else x)

        return df

    ##Helper functions
    def fetch_data_as_dataframe_for_array(self, io_key_array):
        output_dict = {}
        data_fetched = self.fetch_data_for_keys_array(io_key_array)
        for key, data_array in data_fetched.items():
            ##Check if data can be converted to proper PD dataframe
            try:
                data = pd.DataFrame(data_array)
                output_dict[key] = data
            except Exception as e:
                utils.logger.error("Error in get_data_as_dataframe: " + str(e))
                output_dict[key] = pd.DataFrame()
        return output_dict



    def replace_data_as_dataframe(self,io_key,df):
        ##Fetch the data for the key, and replace the PD_DATA_KEY with the new dataframe
        try:
            df = pd.DataFrame(df)
            df = self.prepare_df_for_bson(df)
            data_df = df.to_dict(orient='records')
            return self.insert_or_replace_data_for_key(io_key,data_df)
        except Exception as e:
            utils.logger.error("Error in replace_data_as_dataframe: " + str(e))
            return False


    def delete_collection(self, collection_key):
        try:
            self.database[collection_key].drop()
            return True
        except Exception as e:
            utils.logger.error("Error in delete_collection: " + str(e))
            return False


import pandas as pd
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from Utils.constants import *
import Utils.utils as utils

class MongoManager:

    @classmethod
    def remove_id_from_array(cls, data_array):
        ##remove object ID from each element in data_array
        for data in data_array:
            data.pop('_id', None)
        return data_array


    def __init__(self, connection_string=CONNECTION_STRING, database_name=DB_NAME):
        self.client = MongoClient(connection_string)
        self.database = self.client[database_name]

    ##Insert or replace key and return the inserted/replaced ID
    def replace_data(self, io_key, data_array):
        try:
            collection = self.database[io_key]

            ##Delete all existing data in collection
            collection.delete_many({})

            print("Inserting data: " + str(data_array))
            ##Insert new data
            collection.insert_many(data_array)

            return True
        except Exception as e:
            utils.logger.error("Error in insert_data: " + str(e))
            return False

    ##Fetch data, return None if no data exists.
    def fetch_data(self, io_key):
        try:
            collection = self.database[io_key]
            data = collection.find({})
            return list(data)

        except Exception as e:
            utils.logger.error("Error in fetch_data: " + str(e))
            return None


    def close_connection(self):
        self.client.close()

    def delete_collection(self,collection_name):
        self.database[collection_name].drop()

    ##Helper functions
    def fetch_data_as_dataframe(self, io_key):
        data_fetched = self.fetch_data(io_key)

        if data_fetched is None:
            return None

        ##Check if data can be converted to proper PD dataframe
        try:
            data = pd.DataFrame(data_fetched)
            return data
        except Exception as e:
            utils.logger.error("Error in get_data_as_dataframe: " + str(e))
            return None


    def replace_data_as_dataframe(self,io_key,df):
        ##Fetch the data for the key, and replace the PD_DATA_KEY with the new dataframe
        try:
            df = pd.DataFrame(df) ##Convert to dataframe if not already, to check if it is a valid dataframe
            data_df = df.to_dict(orient='records')
            return self.replace_data(io_key,data_df)
        except Exception as e:
            utils.logger.error("Error in replace_data_as_dataframe: " + str(e))
            return False



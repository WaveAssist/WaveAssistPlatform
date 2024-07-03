import pandas as pd
from pymongo import MongoClient
from Utils.constants import *
import Utils.utils as utils


class MongoManager:
    ##Init Function
    def __init__(self, connection_string=CONNECTION_STRING, database_name=DB_NAME):
        self.client = MongoClient(connection_string)
        self.database = self.client[database_name]

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
        ##Add a row_number column to each element in data_array starting with 1..
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



    ##Instance Functions
    def insert_or_replace_data_for_key(self, io_key, data_array, collection_name):
        try:
            collection = self.database[collection_name]
            new_data_dict = {}
            new_data_dict[IO_DATA_KEY] = io_key
            new_data_dict[DATA_KEY] = data_array
            collection.replace_one({IO_DATA_KEY: io_key}, new_data_dict, upsert=True)
            return True
        except Exception as e:
            utils.logger.error("Error in insert_or_replace_data_for_key: " + io_key + ": " + str(e))
            return False

    ##Fetch data, return None if no data exists.
    def fetch_data_for_key(self, io_key, collection_name):
        try:
            collection = self.database[collection_name]
            full_data = collection.find_one({IO_DATA_KEY: io_key})
            if full_data is None or len(full_data) == 0 or DATA_KEY not in full_data:
                return None

            data = full_data[DATA_KEY]
            return data

        except Exception as e:
            utils.logger.error("Error in fetch_data for key " + io_key + ": " + str(e))
            return None

    ## Fetch data for multiple keys, return an empty list if no data exists.
    def fetch_data_for_keys_array(self, io_keys_array, collection_name):
        try:
            output_dict = {}
            collection = self.database[collection_name]
            # Fetch documents that have IO_DATA_KEY in io_keys_array
            cursor = collection.find({IO_DATA_KEY: {"$in": io_keys_array}})

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
    def fetch_data_as_dataframe_for_array(self, io_key_array, collection_name):
        output_dict = {}
        data_fetched = self.fetch_data_for_keys_array(io_key_array, collection_name)
        for key, data_array in data_fetched.items():
            ##Check if data can be converted to proper PD dataframe
            try:
                data = pd.DataFrame(data_array)
                output_dict[key] = data
            except Exception as e:
                utils.logger.error("Error in get_data_as_dataframe: " + str(e))
                output_dict[key] = pd.DataFrame()
        return output_dict


    ##Helper functions
    def fetch_data_as_dataframe(self, io_key, collection_name):
        data_fetched = self.fetch_data_for_key(io_key, collection_name)
        if data_fetched is None:
            return None
        ##Check if data can be converted to proper PD dataframe
        try:
            data = pd.DataFrame(data_fetched)
            return data
        except Exception as e:
            utils.logger.error("Error in get_data_as_dataframe: " + str(e))
            return None

    def replace_data_as_dataframe(self,io_key, df, collection_name):
        ##Fetch the data for the key, and replace the PD_DATA_KEY with the new dataframe
        try:
            df = pd.DataFrame(df)
            data_df = df.to_dict(orient='records')
            return self.insert_or_replace_data_for_key(io_key,data_df, collection_name)
        except Exception as e:
            utils.logger.error("Error in replace_data_as_dataframe: " + str(e))
            return False



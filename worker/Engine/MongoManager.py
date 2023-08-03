import pandas as pd
from pymongo import MongoClient
from Utils.constants import *
import Utils.utils as utils
from pymongo.write_concern import WriteConcern

class MongoManager:

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

    def __init__(self, connection_string=CONNECTION_STRING, database_name=DB_NAME):
        self.client = MongoClient(connection_string)
        self.database = self.client[database_name]

    # ##Insert or replace key and return the inserted/replaced ID
    def replace_data(self, io_key, data_array):
        try:
            collection = self.database[io_key]

            ##Delete all existing data in collection & Insert
            with collection.write_concern(WriteConcern(w='majority')):
                collection.delete_many({})  # Delete all existing documents
                collection.insert_many(data_array)  # Insert new data


            return True
        except Exception as e:
            utils.logger.error("Error in insert_data: " + str(e))
            return False



    def replace_data(self, io_key, data_array):
        try:
            with self.database.client.start_session() as session:
                collection = self.database[io_key]
                session.start_transaction()
                try:
                    # Delete all existing data in the collection within the transaction
                    collection.delete_many({}, session=session)
                    # Insert new data with keys auto-generated within the transaction
                    collection.insert_many(data_array, session=session)
                    # Commit the transaction once both delete and insert operations are successful
                    session.commit_transaction()
                    return True
                except Exception as e:
                    # Rollback the transaction if any error occurs during the operations
                    session.abort_transaction()
                    utils.logger.error("Error in replace_data: " + str(e))
                    return False
        except Exception as e:
            utils.logger.error("Error starting session in replace_data: " + str(e))
            return False

    def append_data(self, io_key, data_array):
        try:
            collection = self.database[io_key]

            ##Delete all existing data in collection
            # collection.delete_many({})

            # print("Inserting data: " + str(data_array))
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
            data = MongoManager.convert_id_in_data(data)

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

    def update_data_as_dataframe(self,io_key, df):
        ##Fetch the data for the key, and replace the PD_DATA_KEY with the new dataframe
        try:
            df = pd.DataFrame(df) ##Convert to dataframe if not already, to check if it is a valid dataframe
            data_df = df.to_dict(orient='records')
            return self.append_data(io_key,data_df)
        except Exception as e:
            utils.logger.error("Error in replace_data_as_dataframe: " + str(e))
            return False



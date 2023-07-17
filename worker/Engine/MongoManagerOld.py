# import pandas as pd
# from pymongo import MongoClient
# from pymongo.errors import DuplicateKeyError
# from Utils.constants import *
# import Utils.utils as utils
#
# class MongoManager:
#     def __init__(self, collection_name, connection_string=CONNECTION_STRING, database_name=DB_NAME):
#         self.client = MongoClient(connection_string)
#         self.database = self.client[database_name]
#         self.collection = self.database[collection_name]
#
#     ##Insert or replace key and return the inserted/replaced ID
#     def insert_or_replace_key(self, io_key, pd_data):
#         try:
#             data = {}
#             data[PD_DATA_KEY] = pd_data
#             data[IO_DATA_KEY] = io_key ##Extra check
#             self.collection.replace_one({IO_DATA_KEY: io_key}, data, upsert=True)
#             return True
#         except Exception as e:
#             utils.logger.error("Error in insert_data: " + str(e))
#             return False
#
#     ##Fetch data, return None if no data exists.
#     def fetch_data(self, io_key):
#         utils.logger.info("Fetching data for: " + str(io_key))
#         try:
#             data = self.collection.find_one({IO_DATA_KEY: io_key})
#             if data is None:
#                 return None
#
#             if PD_DATA_KEY in data:
#                 return data[PD_DATA_KEY]
#             else:
#                 return None
#         except Exception as e:
#             utils.logger.error("Error in fetch_data: " + str(e))
#             return None
#
#
#     def close_connection(self):
#         self.client.close()
#
#     def delete_collection(self):
#         self.collection.drop()
#
#
#     ##Helper functions
#     def fetch_data_as_dataframe(self, io_key):
#         data_fetched = self.fetch_data(io_key)
#
#         if data_fetched is None:
#             return None
#
#         ##Check if data can be converted to proper PD dataframe
#         try:
#             data = pd.DataFrame(data_fetched)
#             return data
#         except Exception as e:
#             utils.logger.error("Error in get_data_as_dataframe: " + str(e))
#             return None
#
#
#     def insert_or_replace_data_as_dataframe(self,io_key,df):
#         ##Fetch the data for the key, and replace the PD_DATA_KEY with the new dataframe
#         try:
#             df = pd.DataFrame(df) ##Convert to dataframe if not already, to check if it is a valid dataframe
#             data_df = df.to_dict(orient='records')
#             return self.insert_or_replace_key(io_key,data_df)
#         except Exception as e:
#             utils.logger.error("Error in replace_data_as_dataframe: " + str(e))
#             return False
#
#

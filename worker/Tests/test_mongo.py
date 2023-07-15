import unittest
from Engine.MongoManager import MongoManager

import Utils.utils as utils
import pandas as pd


class TestMongo(unittest.TestCase):

    def setUp(self):
       self.mongoManager = MongoManager("TestCollection")

    def tearDown(self):
        # self.mongoManager.delete_collection()
        self.mongoManager.close_connection()

    def test_insert(self):
        self.mongoManager.insert_or_replace_key("test_key", {"test_key": "test_value"})
        fetched_data = self.mongoManager.fetch_data("test_key")
        self.assertEqual(fetched_data, {"test_key": "test_value"})

    def test_pd_insert(self):
        df = pd.DataFrame([{"column1": "value1"}])
        self.mongoManager.insert_or_replace_data_as_dataframe("test_key_pd", df)
        fetched_df = self.mongoManager.fetch_data_as_dataframe("test_key_pd")

        print("fetched_df" + str(fetched_df))
        print("df"+ str(df))

        ##Check if fetched_df and df are same
        self.assertTrue(df.equals(fetched_df))
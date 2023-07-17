import unittest
from Engine.MongoManager import MongoManager

import Utils.utils as utils
import pandas as pd


class TestMongo(unittest.TestCase):

    def setUp(self):
       self.mongoManager = MongoManager()

    def tearDown(self):
        # self.mongoManager.delete_collection("TestCollection")
        self.mongoManager.close_connection()

    def test_insert(self):
        self.mongoManager.replace_data("test_key", [{"column1": "value1"}, {"column1": "value2"}])
        fetched_data = self.mongoManager.fetch_data("test_key")
        self.assertEqual(fetched_data[0]['column1'], 'value1')
        self.assertEqual(fetched_data[1]['column1'], 'value2')

    def test_pd_insert(self):
        df = pd.DataFrame([{"column1": "value1"}])
        self.mongoManager.replace_data_as_dataframe("test_key_pd", df)
        fetched_df = self.mongoManager.fetch_data_as_dataframe("test_key_pd")

        print("fetched_df" + str(fetched_df))
        print("df"+ str(df))

        ##Get the value of the first row and column1 in fetched df
        fetched_value = fetched_df.iloc[0]['column1']

        ##Check if fetched_df and df are same
        self.assertTrue(fetched_value == 'value1')
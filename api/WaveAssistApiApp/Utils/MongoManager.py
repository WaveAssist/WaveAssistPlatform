from WaveAssistApiApp.Utils.constants import *
from pymongo import MongoClient
import WaveAssistApiApp.Utils.utils as utils
from WaveAssistApi.settings import MONGO_CONNECTION_STRING
import uuid
from datetime import datetime, timezone

class MongoManager:
    ##Init Function
    def __init__(self, collection_name=None, connection_string=MONGO_CONNECTION_STRING, database_name=DB_NAME):
        self.client = MongoClient(connection_string)
        self.database = self.client[database_name]
        if collection_name is not None:
            self.collection = self.database[collection_name]

    def insert_or_replace_data_for_key(self, io_key, data, data_type='string'):
        """
        Insert or replace the document for a given key.
        """
        try:
            document = {
                IO_DATA_KEY: io_key,
                DATA_KEY: data,
                DATA_TYPE_KEY: data_type
            }
            self.collection.replace_one({IO_DATA_KEY: io_key}, document, upsert=True)
            return True
        except Exception as e:
            utils.logger.error(f"❌ Error inserting/replacing data for key '{io_key}': {str(e)}")
            return False


    def fetch_data_for_key(self, io_key):
        """
        Fetches stored data for a given key from the collection.
        Returns a tuple (data, data_type), or (None, None) if not found or error.
        """
        try:
            full_data = self.collection.find_one({IO_DATA_KEY: io_key})

            if not full_data or DATA_KEY not in full_data:
                return None, None

            data = full_data[DATA_KEY]
            data_type = full_data.get(DATA_TYPE_KEY, 'string')

            return data, data_type

        except Exception as e:
            utils.logger.error(f"❌ Error in fetch_data_for_key({io_key}): {str(e)}")
            return None, None


    def close_connection(self):
        self.client.close()


DASHBOARD_TOKENS_DB = "wa_global"
DASHBOARD_TOKENS_COLLECTION = "dashboard_tokens"


class DashboardTokenManager:
    """Manages opaque tokens that map to stored HTML dashboards."""

    def __init__(self, connection_string=MONGO_CONNECTION_STRING):
        self.client = MongoClient(connection_string)
        self.collection = self.client[DASHBOARD_TOKENS_DB][DASHBOARD_TOKENS_COLLECTION]
        self.collection.create_index("token", unique=True)

    def create_token(self, uid, project_key, environment_key, data_key):
        token = uuid.uuid4().hex
        self.collection.insert_one({
            "token": token,
            "uid": uid,
            "project_key": project_key,
            "environment_key": environment_key,
            "data_key": data_key,
            "created_at": datetime.now(timezone.utc),
        })
        return token

    def get_token(self, token):
        return self.collection.find_one({"token": token}, {"_id": 0})

    def close_connection(self):
        self.client.close()

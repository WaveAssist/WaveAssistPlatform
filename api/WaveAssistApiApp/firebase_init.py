# firebase_init.py
import firebase_admin
from firebase_admin import credentials

# WaveAssist Firebase (default app) — verifies WaveAssist login tokens. GitZoid tokens are
# verified separately via Google's public certs (see get_firebase_uid), so no second app and no
# GitZoid service-account key are needed.
def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase_admin.json")
        firebase_admin.initialize_app(cred)

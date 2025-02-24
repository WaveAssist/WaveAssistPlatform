# firebase_init.py
import firebase_admin
from firebase_admin import credentials

# Point this to your Firebase service account JSON file
def initialize_firebase():
    cred = credentials.Certificate("firebase_admin.json")
    firebase_admin.initialize_app(cred)

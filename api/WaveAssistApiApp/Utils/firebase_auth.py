import firebase_admin
from firebase_admin import auth
from firebase_admin import credentials
import json

# Initialize the Firebase app with your service account credentials

cred = credentials.Certificate('firebase_key.json')
firebase_admin.initialize_app(cred)

def verify_token(jwt_token):
    decoded_token = auth.verify_id_token(str(jwt_token))
    uid = decoded_token['uid']
    return uid

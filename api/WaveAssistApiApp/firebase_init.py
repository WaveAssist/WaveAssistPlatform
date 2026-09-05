# firebase_init.py
import firebase_admin
from firebase_admin import credentials

# WaveAssist Firebase (default app) — verifies WaveAssist login tokens. GitZoid tokens are
# verified separately via Google's public certs (see get_firebase_uid), so no second app and no
# GitZoid service-account key are needed.
def initialize_firebase():
    if firebase_admin._apps:
        return
    import os
    from django.conf import settings
    path = getattr(settings, "FIREBASE_ADMIN_CREDENTIALS", None) or os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase_admin.json")
    if not path or not os.path.exists(path):
        # No service-account key present: do not crash import/startup. Firebase token
        # verification will be unavailable until a key is provided via FIREBASE_CREDENTIALS_PATH.
        print(f"[firebase_init] no credentials at {path!r}; skipping Firebase init")
        return
    cred = credentials.Certificate(path)
    firebase_admin.initialize_app(cred)

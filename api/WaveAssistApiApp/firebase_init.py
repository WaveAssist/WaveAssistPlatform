# firebase_init.py
import firebase_admin
from firebase_admin import credentials

# Each brand has its own Firebase project, so a login token must be verified against the
# project that issued it. WaveAssist is the default app; GitZoid is a named app. GitZoid is
# OPTIONAL — if its service-account file isn't present yet, WaveAssist is completely unaffected.
def initialize_firebase():
    # WaveAssist (default app)
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase_admin.json")
        firebase_admin.initialize_app(cred)

    # GitZoid (named app) — only if its service-account JSON is available.
    try:
        firebase_admin.get_app("gitzoid")
    except ValueError:
        try:
            gz_cred = credentials.Certificate("firebase_admin_gitzoid.json")
            firebase_admin.initialize_app(gz_cred, name="gitzoid")
        except Exception:
            pass  # GitZoid Firebase not configured yet — skip silently.

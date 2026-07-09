"""Local-only, throwaway settings for testing Phase 0 against sqlite.

Isolates all local testing from the production AWS RDS MySQL configured in settings.py.
NOT for deployment. Run with:  DJANGO_SETTINGS_MODULE=WaveAssistApi.settings_localtest
"""

from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "localtest.sqlite3",  # noqa: F405
    }
}


# The historical migration chain contains MySQL-only SQL (e.g. INFORMATION_SCHEMA in 0055)
# that can't replay on sqlite. For local functional testing we disable migrations entirely
# and let `migrate --run-syncdb` build the current schema directly from the models. The real
# migration (0066) is validated separately against MySQL via `sqlmigrate`.
class _DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = _DisableMigrations()

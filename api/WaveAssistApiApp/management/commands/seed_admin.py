"""Bootstrap a usable admin account on a fresh (self-hosted) database.

A fresh Compose DB has schema but no User/Account, so nothing works until this runs.
Idempotent: safe to run on every boot. Mirrors the account-creation half of
``manage_views.get_started`` but for a single self-hosted admin — no Atlas, no Fargate.

    python manage.py seed_admin --uid <uid> --email <email> [--name ...]

Defaults come from env: WAVEASSIST_ADMIN_UID, WAVEASSIST_ADMIN_EMAIL, WAVEASSIST_ADMIN_NAME.
Prints bootstrap status. Credentials are not written to startup logs.
"""
import os
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from WaveAssistApiApp.models import User, Account
from WaveAssistApiApp.Utils import utils
from WaveAssistApiApp.Utils.constants import SHARED_OPERATOR_QUEUE


class Command(BaseCommand):
    help = "Create/ensure a single self-hosted admin User + Account (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--uid", default=os.getenv("WAVEASSIST_ADMIN_UID", ""))
        parser.add_argument("--email", default=os.getenv("WAVEASSIST_ADMIN_EMAIL", "admin@waveassist.local"))
        parser.add_argument("--name", default=os.getenv("WAVEASSIST_ADMIN_NAME", "Admin"))
        parser.add_argument("--product", default=os.getenv("WAVEASSIST_ADMIN_PRODUCT", "waveassist"))

    def handle(self, *args, **opts):
        uid = opts["uid"].strip() or uuid.uuid4().hex[:24]
        email = opts["email"].strip()
        name = opts["name"].strip() or email.split("@")[0]
        product = opts["product"].strip()

        user = User.objects.filter(username=email).first() or User.objects.filter(uid=uid).first()
        if user is not None and (user.uid != uid or user.username != email):
            raise CommandError("Admin UID/email conflicts with an existing identity. Correct the bootstrap configuration.")
        if user is None:
            user = User.objects.create(
                uid=uid,
                name=name,
                username=email,
                password="",                 # unused: this box authenticates by UID
                company_name="",
                can_create_projects=True,
                firebase_uid=f"local:{uid}",  # unique, satisfies the not-null unique column
                is_super_admin=True,
            )
            created_user = True
        else:
            created_user = False
            if not user.is_super_admin:
                user.is_super_admin = True
                user.save(update_fields=["is_super_admin"])

        account = Account.objects.filter(created_by_user=user).first()
        if account is None:
            account = Account.objects.create(
                account_name=name,
                account_uid=user.uid,
                created_by_user=user,
                celery_queue=SHARED_OPERATOR_QUEUE,
                product=product,
                mcp_token=Account.generate_mcp_token(),
            )
            created_account = True
        else:
            created_account = False
            account.ensure_mcp_token()

        # Local Mongo identity (no Atlas Admin API): the deployment's own Mongo + a per-account db.
        if not account.mongo_db_url:
            account.mongo_db_url = settings.MONGO_CONNECTION_STRING
            account.db_name = utils.get_database_name(user)
        if account.celery_queue != SHARED_OPERATOR_QUEUE:
            account.celery_queue = SHARED_OPERATOR_QUEUE
        account.save()

        self.stdout.write(self.style.SUCCESS(
            f"seed_admin OK (user {'created' if created_user else 'exists'}, "
            f"account {'created' if created_account else 'exists'})"
        ))
        self.stdout.write(f"  uid        : {user.uid}")
        self.stdout.write(f"  email      : {user.username}")
        self.stdout.write(f"  db_name    : {account.db_name}")
        self.stdout.write(f"  queue      : {account.celery_queue}")

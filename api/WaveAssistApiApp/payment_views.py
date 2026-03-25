import base64
import hashlib
import hmac
import json
import os
import uuid
from decimal import Decimal, InvalidOperation

import requests
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Account, BillingSubscription, Payment, PaymentWebhookEvent, User
from .Utils.constants import *
from .Utils.responseParser import ResponseParser
from .Utils.utils import logger, fetch_credits_from_openrouter


VALID_UPGRADE_PLANS = {
    "plus": {"credits": 10, "price_usd": 9.99},
    "pro": {"credits": 25, "price_usd": 19.99},
}


def _safe_decimal(raw_value, field_name):
    try:
        decimal_value = Decimal(str(raw_value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Invalid {field_name} format")
    return decimal_value


def _dodo_api_base_url():
    return os.environ.get("DODO_PAYMENTS_BASE_URL", DODO_DEFAULT_BASE_URL).rstrip("/")


def _dodo_api_key():
    return os.environ.get("DODO_PAYMENTS_API_KEY", DODO_DEFAULT_API_KEY)


def _dodo_webhook_secret():
    return os.environ.get(
        "DODO_PAYMENTS_WEBHOOK_SECRET",
        DODO_DEFAULT_WEBHOOK_SECRET,
    )


def _dodo_request(method, path, payload=None, timeout=20):
    api_key = _dodo_api_key()
    if not api_key:
        raise RuntimeError("DODO_PAYMENTS_API_KEY is not configured")

    url = f"{_dodo_api_base_url()}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        json=payload,
        timeout=timeout,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Dodo API call failed ({response.status_code}): {response.text[:500]}"
        )

    if not response.text:
        return {}
    return response.json()



def _get_user_and_account(uid):
    if not uid:
        raise ValueError("UID is required")
    try:
        user_object = User.objects.get(uid=uid)
    except User.DoesNotExist as exc:
        raise ValueError("User not found") from exc

    try:
        account_object = Account.objects.get(created_by_user=user_object)
    except Account.DoesNotExist as exc:
        raise ValueError("Account not found") from exc

    return user_object, account_object


def _extract_plan_name(description):
    if description and description.startswith("plan_upgrade:"):
        return description.split(":", 1)[1]
    return ""


def _utc_dt(raw_value):
    if not raw_value:
        return None
    if isinstance(raw_value, str):
        dt = parse_datetime(raw_value)
        if dt:
            return dt
    return None


def create_checkout(request):
    uid = request.POST.get("uid", "")
    use_case = request.POST.get("use_case", "").strip().lower()
    amount = request.POST.get("amount", "")
    credits_in_usd = request.POST.get("credits_in_usd", "0")
    plan_name = request.POST.get("plan_name", "").strip().lower()
    payment_type = request.POST.get("payment_type", "").strip().lower()

    if not use_case:
        if payment_type in ["plan_upgrade", "subscription", "subscription_create"]:
            use_case = "subscription"
        else:
            use_case = "credits"

    try:
        user_object, account_object = _get_user_and_account(uid)
    except ValueError as exc:
        return ResponseParser.getParsedErrorMessage(str(exc))

    if use_case not in ["credits", "subscription"]:
        return ResponseParser.getParsedErrorMessage(
            'use_case must be either "credits" or "subscription"'
        )

    try:
        customer_email = user_object.username or ""
        customer_name = user_object.name or account_object.account_name or "WaveAssist User"
        customer_payload = {"email": customer_email, "name": customer_name}

        metadata = {
            "uid": uid,
            "account_uid": account_object.account_uid,
            "use_case": use_case,
        }

        return_url = f"{FRONTEND_URL}/manage/credits?checkout=complete"

        if use_case == "subscription":
            if plan_name not in VALID_UPGRADE_PLANS:
                return ResponseParser.getParsedErrorMessage("Invalid plan_name")

            plan_config = VALID_UPGRADE_PLANS[plan_name]
            amount_decimal = Decimal(str(plan_config["price_usd"]))
            credits_decimal = Decimal(str(plan_config["credits"]))
            _plan_defaults = {
                "PLUS": DODO_DEFAULT_PLAN_PLUS_PRODUCT_ID,
                "PRO": DODO_DEFAULT_PLAN_PRO_PRODUCT_ID,
            }
            product_id = os.environ.get(
                f"DODO_PLAN_{plan_name.upper()}_PRODUCT_ID",
                _plan_defaults.get(plan_name.upper(), ""),
            )
            if not product_id:
                return ResponseParser.getParsedErrorMessage(
                    f"Missing DODO_PLAN_{plan_name.upper()}_PRODUCT_ID"
                )

            metadata["plan_name"] = plan_name
            metadata["credits_in_usd"] = str(credits_decimal)

            checkout_payload = {
                "product_cart": [{"product_id": product_id, "quantity": 1}],
                "customer": customer_payload,
                "metadata": metadata,
                "return_url": return_url,
            }
            payment_record_type = "subscription_create"
            description = f"plan_upgrade:{plan_name}"
        else:
            if not amount:
                return ResponseParser.getParsedErrorMessage("Amount is required")

            amount_decimal = _safe_decimal(amount, "amount")
            if amount_decimal <= 0:
                return ResponseParser.getParsedErrorMessage(
                    "Amount must be greater than 0"
                )

            credits_decimal = _safe_decimal(credits_in_usd, "credits")
            if credits_decimal <= 0:
                return ResponseParser.getParsedErrorMessage(
                    "credits_in_usd must be greater than 0"
                )
            if credits_decimal > amount_decimal:
                return ResponseParser.getParsedErrorMessage(
                    "credits_in_usd cannot exceed amount"
                )

            product_id = os.environ.get(
                "DODO_CREDITS_PRODUCT_ID", DODO_DEFAULT_CREDITS_PRODUCT_ID
            )
            if not product_id:
                return ResponseParser.getParsedErrorMessage(
                    "Missing DODO_CREDITS_PRODUCT_ID"
                )

            metadata["credits_in_usd"] = str(credits_decimal)

            amount_cents = int(amount_decimal * 100)
            checkout_payload = {
                "product_cart": [
                    {"product_id": product_id, "quantity": 1, "amount": amount_cents}
                ],
                "customer": customer_payload,
                "metadata": metadata,
                "return_url": return_url,
            }
            payment_record_type = "credits"
            description = request.POST.get("description", "Credits Purchase")

        dodo_response = _dodo_request("POST", "/checkouts", checkout_payload)
        checkout_id = dodo_response.get("session_id", "")
        checkout_url = dodo_response.get("checkout_url", "")
        customer_id = ""

        if not checkout_id or not checkout_url:
            logger.error(f"Dodo response missing checkout fields: {dodo_response}")
            return ResponseParser.getParsedErrorMessage(
                "Failed to initialize checkout with DodoPayments"
            )

        payment = Payment.objects.create(
            account=account_object,
            provider="dodopayments",
            amount=amount_decimal,
            currency="USD",
            credits_in_usd=credits_decimal,
            payment_type=payment_record_type,
            status="pending",
            provider_payment_id=checkout_id,
            external_checkout_id=checkout_id,
            external_customer_id=customer_id or "",
            description=description,
            metadata_json=json.dumps(metadata),
        )

        response_data = {
            "provider": "dodopayments",
            "payment_id": payment.id,
            "checkout_id": checkout_id,
            "checkout_url": checkout_url,
            "currency": "USD",
            "amount": str(amount_decimal),
            "payment_type": payment_record_type,
        }

        return ResponseParser.getParsedSuccessMessage(
            response_data,
            "success",
            "Dodo checkout created successfully",
        )
    except Exception as exc:
        logger.error(f"Failed to create Dodo checkout: {str(exc)}")
        return ResponseParser.getParsedErrorMessage(
            f"Failed to create Dodo checkout: {str(exc)}"
        )


def create_payment_order(request):
    # Backward-compatible alias used by older clients.
    return create_checkout(request)


def verify_payment(request):
    return ResponseParser.getParsedErrorMessage(
        "Manual verify is disabled. Payment status is updated via webhooks."
    )


def _verify_standard_webhook_signature(raw_body, webhook_id, webhook_timestamp, webhook_signature):
    """Verify webhook using the Standard Webhooks specification.

    Signed message = ``{webhook_id}.{webhook_timestamp}.{body}``
    HMAC-SHA256 with the secret (base64-decoded if prefixed with ``whsec_``).
    The ``webhook-signature`` header contains one or more space-separated
    versioned signatures like ``v1,<base64>``."""

    webhook_secret = _dodo_webhook_secret()
    if not webhook_secret or not webhook_secret.strip():
        logger.warning("Dodo webhook: secret is empty, rejecting (signature verification required)")
        return False

    if not webhook_id or not webhook_timestamp or not webhook_signature:
        return False

    secret = webhook_secret
    if secret.startswith("whsec_"):
        secret = secret[len("whsec_"):]
    try:
        secret_bytes = base64.b64decode(secret)
    except Exception:
        secret_bytes = secret.encode("utf-8")

    body_str = raw_body.decode("utf-8") if isinstance(raw_body, bytes) else raw_body
    signed_content = f"{webhook_id}.{webhook_timestamp}.{body_str}"
    expected = hmac.new(
        secret_bytes, signed_content.encode("utf-8"), hashlib.sha256
    ).digest()
    expected_b64 = base64.b64encode(expected).decode("utf-8")

    for part in webhook_signature.split(" "):
        part = part.strip()
        if not part:
            continue
        tag_and_sig = part.split(",", 1)
        sig_b64 = tag_and_sig[1] if len(tag_and_sig) == 2 else tag_and_sig[0]
        if hmac.compare_digest(sig_b64, expected_b64):
            return True
    return False


def _mark_payment_completed(
    payment,
    provider_payment_id="",
    customer_id="",
    subscription_id="",
    invoice_id="",
    invoice_url="",
    metadata=None,
):
    metadata = metadata or {}
    payment.status = "completed"

    if provider_payment_id:
        payment.provider_payment_id = provider_payment_id
    if customer_id:
        payment.external_customer_id = customer_id
    if subscription_id:
        payment.external_subscription_id = subscription_id
    if invoice_id:
        payment.external_invoice_id = invoice_id
    if invoice_url:
        payment.invoice_url = invoice_url
    if metadata:
        payment.metadata_json = json.dumps(metadata)

    account = payment.account
    upgrade_plan = _extract_plan_name(payment.description)

    if payment.payment_type in ["subscription_create", "subscription_renewal"] and (
        upgrade_plan in VALID_UPGRADE_PLANS
    ):
        account.plan_name = upgrade_plan
        account.save()

        if subscription_id:
            subscription, _ = BillingSubscription.objects.get_or_create(
                external_subscription_id=subscription_id,
                defaults={
                    "account": account,
                    "provider": "dodopayments",
                    "plan_name": upgrade_plan,
                },
            )
            subscription.account = account
            subscription.external_customer_id = customer_id or subscription.external_customer_id
            subscription.plan_name = upgrade_plan
            subscription.status = "active"
            subscription.metadata_json = json.dumps(metadata)
            subscription.save()

    if payment.credits_in_usd > 0 and not payment.credits_granted:
        is_renewal = payment.payment_type == "subscription_renewal"
        plan_monthly_credits = VALID_UPGRADE_PLANS.get(upgrade_plan, {}).get("credits", 0) if is_renewal else 0
        credits_added = add_credits_to_openrouter(
            account, payment.credits_in_usd,
            is_renewal=is_renewal,
            plan_monthly_credits=plan_monthly_credits,
        )
        if credits_added:
            payment.credits_granted = True
            account.credits_check_interval = CREDITS_CHECK_INTERVAL_FAST
            account.save()
        else:
            logger.error(
                f"Failed to add credits to OpenRouter for payment {payment.id}"
            )

    payment.save()


def _remove_credits_from_openrouter(account_object, credits_in_usd):
    try:
        key_hash = account_object.open_router_key_hash or ""
        if not key_hash:
            logger.error(
                f"No OpenRouter key hash for account: {account_object.account_uid}"
            )
            return False

        credit_data = fetch_credits_from_openrouter(account_object.open_router_key)
        current_limit = float(credit_data["limit"])
        credits_float = float(credits_in_usd) / WAVEASSIST_CREDIT_MULTIPLIER
        new_limit = max(0.0, current_limit - credits_float)

        url = "https://openrouter.ai/api/v1/keys"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_PROVISIONING_KEY}",
            "Content-Type": "application/json",
        }
        update_response = requests.patch(
            f"{url}/{key_hash}", json={"limit": new_limit}, headers=headers, timeout=10
        )
        update_response.raise_for_status()
        return True
    except Exception as e:
        logger.error(
            f"Unexpected error reversing credits on OpenRouter for account {account_object.account_uid}: {str(e)}"
        )
        return False


def _mark_payment_refunded(payment, metadata=None):
    metadata = metadata or {}

    if payment.status == "refunded":
        return

    account = payment.account

    # Reverse OpenRouter credits only if we had previously granted them.
    if payment.credits_granted and payment.credits_in_usd > 0:
        credits_reversed = _remove_credits_from_openrouter(account, payment.credits_in_usd)
        if not credits_reversed:
            raise RuntimeError(
                f"Failed to reverse OpenRouter credits for refunded payment {payment.id}"
            )

    payment.status = "refunded"
    if metadata:
        payment.metadata_json = json.dumps(metadata)
    payment.save()

    if payment.payment_type in ["subscription_create", "subscription_renewal"]:
        account.plan_name = "starter"
        account.save()

        subscription_id = payment.external_subscription_id or ""
        if subscription_id:
            subscription = BillingSubscription.objects.filter(
                external_subscription_id=subscription_id
            ).first()
            if subscription:
                subscription.status = "canceled"
                subscription.cancel_at_period_end = False
                subscription.canceled_at = timezone.now()
                subscription.save()


def _apply_subscription_state(
    account,
    subscription_id,
    customer_id,
    plan_name,
    status,
    cancel_at_period_end=False,
    current_period_start=None,
    current_period_end=None,
    canceled_at=None,
    metadata=None,
):
    if not subscription_id:
        return

    metadata = metadata or {}
    subscription, _ = BillingSubscription.objects.get_or_create(
        external_subscription_id=subscription_id,
        defaults={
            "account": account,
            "provider": "dodopayments",
            "plan_name": plan_name or "starter",
            "status": status or "pending",
        },
    )

    if customer_id:
        subscription.external_customer_id = customer_id
    if plan_name:
        subscription.plan_name = plan_name
    if status:
        subscription.status = status
    subscription.cancel_at_period_end = bool(cancel_at_period_end)
    subscription.current_period_start = current_period_start
    subscription.current_period_end = current_period_end
    subscription.canceled_at = canceled_at
    subscription.metadata_json = json.dumps(metadata)
    subscription.account = account
    subscription.save()

    if plan_name in VALID_UPGRADE_PLANS and status in ["active", "trialing"]:
        account.plan_name = plan_name
        account.save()
    elif status in ["canceled", "cancelled"]:
        # If cancellation is at period end, keep access until expiry.
        if not bool(cancel_at_period_end):
            account.plan_name = "starter"
            account.save()
    elif status in ["expired", "ended", "past_due", "paused"]:
        # past_due / paused: no paid access until subscription is active again.
        # Re-upgrade automatically when subscription becomes active (e.g. renewed).
        account.plan_name = "starter"
        account.save()


def _find_payment_by_event(event_data):
    # DoDo sends checkout_session_id which maps to our session_id stored at creation
    checkout_id = event_data.get("checkout_id", "")
    if checkout_id:
        payment = Payment.objects.filter(external_checkout_id=checkout_id).first()
        if payment:
            return payment
        payment = Payment.objects.filter(provider_payment_id=checkout_id).first()
        if payment:
            return payment

    # DoDo payment_id from payment.succeeded webhook
    dodo_payment_id = event_data.get("payment_id", "")
    if dodo_payment_id:
        payment = Payment.objects.filter(provider_payment_id=dodo_payment_id).first()
        if payment:
            return payment

    metadata = event_data.get("metadata", {})
    internal_id = metadata.get("payment_id")
    if internal_id:
        try:
            return Payment.objects.get(id=int(internal_id))
        except Exception:
            pass

    subscription_id = event_data.get("subscription_id", "")
    if subscription_id:
        return (
            Payment.objects.filter(external_subscription_id=subscription_id)
            .order_by("-created_at")
            .first()
        )
    return None


def _find_refund_target_payment(event_data):
    provider_payment_id = event_data.get("payment_id", "")
    if provider_payment_id:
        payment = Payment.objects.filter(provider_payment_id=provider_payment_id).first()
        if payment:
            return payment

    checkout_id = event_data.get("checkout_id", "")
    if checkout_id:
        payment = Payment.objects.filter(external_checkout_id=checkout_id).first()
        if payment:
            return payment

    invoice_id = event_data.get("invoice_id", "")
    if invoice_id:
        payment = Payment.objects.filter(external_invoice_id=invoice_id).first()
        if payment:
            return payment

    metadata = event_data.get("metadata", {})
    internal_id = metadata.get("payment_id")
    if internal_id:
        try:
            return Payment.objects.get(id=int(internal_id))
        except Exception:
            pass

    return None


def _create_renewal_payment_from_event(event_data):
    subscription_id = event_data.get("subscription_id", "")
    if not subscription_id:
        return None

    subscription = BillingSubscription.objects.filter(
        external_subscription_id=subscription_id
    ).first()
    if not subscription:
        return None

    invoice_id = event_data.get("invoice_id", "")
    provider_payment_id = (
        event_data.get("payment_id")
        or event_data.get("checkout_id")
        or invoice_id
        or f"dodo_renewal_{uuid.uuid4().hex[:20]}"
    )

    existing_payment = Payment.objects.filter(provider_payment_id=provider_payment_id).first()
    if existing_payment:
        return existing_payment

    plan_config = VALID_UPGRADE_PLANS.get(subscription.plan_name, {})
    amount = Decimal(str(plan_config.get("price_usd", 0)))
    credits = Decimal(str(plan_config.get("credits", 0)))

    return Payment.objects.create(
        account=subscription.account,
        provider="dodopayments",
        amount=amount,
        currency="USD",
        credits_in_usd=credits,
        payment_type="subscription_renewal",
        status="pending",
        provider_payment_id=provider_payment_id,
        external_checkout_id=event_data.get("checkout_id", ""),
        external_customer_id=event_data.get("customer_id", ""),
        external_subscription_id=subscription_id,
        external_invoice_id=invoice_id or "",
        invoice_url=event_data.get("invoice_url", ""),
        description=f"plan_upgrade:{subscription.plan_name}",
        metadata_json=json.dumps(event_data.get("metadata", {})),
    )


def _normalize_event_payload(payload):
    """Normalize a DoDo webhook payload into a flat dict.

    DoDo payload structure (Standard Webhooks)::

        {
            "business_id": "...",
            "type": "payment.succeeded",      # event type
            "timestamp": "ISO 8601",
            "data": {
                "payload_type": "Payment",     # or Subscription, Refund, ...
                "payment_id": "...",
                "total_amount": 999,           # cents
                "currency": "USD",
                "customer": {"customer_id": "...", "email": "..."},
                "subscription_id": "...",      # present for subscription payments
                "metadata": {...},
                ...
            }
        }
    """
    data = payload.get("data", {}) if isinstance(payload.get("data"), dict) else {}
    customer = data.get("customer", {}) if isinstance(data.get("customer"), dict) else {}
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    event_type = (payload.get("type") or "unknown").lower()

    normalized = {
        "event_id": payload.get("id") or payload.get("event_id") or uuid.uuid4().hex,
        "event_type": event_type,
        "payload_type": str(data.get("payload_type", "")).lower(),
        "status": str(data.get("status", "") or "").lower(),
        "payment_id": (
            data.get("payment_id", "")
            or data.get("original_payment_id", "")
            or data.get("parent_payment_id", "")
            or ""
        ),
        "refund_id": data.get("refund_id", "") or data.get("id", "") or "",
        "checkout_id": data.get("checkout_session_id", "")
        or data.get("checkout_id", "")
        or "",
        "customer_id": customer.get("customer_id", "")
        or data.get("customer_id", "")
        or "",
        "subscription_id": data.get("subscription_id", "") or "",
        "invoice_id": data.get("invoice_id", "") or "",
        "invoice_url": data.get("invoice_url", "") or "",
        "total_amount": data.get("total_amount", 0),
        "currency": data.get("currency", "USD"),
        "plan_name": (
            metadata.get("plan_name", "")
            or data.get("plan_name", "")
            or ""
        ).lower(),
        "metadata": metadata,
        "current_period_start": _utc_dt(data.get("current_period_start")),
        "current_period_end": _utc_dt(data.get("current_period_end")),
        "canceled_at": _utc_dt(data.get("canceled_at")),
        "cancel_at_period_end": bool(data.get("cancel_at_period_end")),
    }
    return normalized


def dodo_webhook(request):
    raw_body = request.body or b""

    webhook_id = (
        request.headers.get("webhook-id")
        or request.META.get("HTTP_WEBHOOK_ID", "")
    )
    webhook_timestamp = (
        request.headers.get("webhook-timestamp")
        or request.META.get("HTTP_WEBHOOK_TIMESTAMP", "")
    )
    webhook_signature = (
        request.headers.get("webhook-signature")
        or request.META.get("HTTP_WEBHOOK_SIGNATURE", "")
    )

    if not _verify_standard_webhook_signature(
        raw_body, webhook_id, webhook_timestamp, webhook_signature
    ):
        return ResponseParser.getParsedErrorMessage("Invalid webhook signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        return ResponseParser.getParsedErrorMessage("Invalid JSON payload")

    if not isinstance(payload, dict):
        return ResponseParser.getParsedErrorMessage("Webhook payload must be a JSON object")

    event_data = _normalize_event_payload(payload)
    webhook_event, created = PaymentWebhookEvent.objects.get_or_create(
        event_id=event_data["event_id"],
        defaults={
            "provider": "dodopayments",
            "event_type": event_data["event_type"],
            "payload_json": json.dumps(payload),
            "processed": False,
        },
    )

    if not created and webhook_event.processed:
        return ResponseParser.getParsedSuccessMessage(
            {"event_id": webhook_event.event_id},
            "success",
            "Event already processed",
        )

    webhook_event.event_type = event_data["event_type"]
    webhook_event.payload_json = json.dumps(payload)

    try:
        event_type = event_data["event_type"]

        is_payment_succeeded = event_type == "payment.succeeded"
        is_payment_failed = event_type == "payment.failed"
        is_subscription_event = event_type.startswith("subscription.")
        is_refund_event = event_type.startswith("refund.")

        if is_refund_event:
            payment = _find_refund_target_payment(event_data)
        else:
            payment = _find_payment_by_event(event_data)

        if not payment and is_payment_succeeded and event_data["subscription_id"]:
            payment = _create_renewal_payment_from_event(event_data)

        if payment and is_payment_succeeded:
            _mark_payment_completed(
                payment=payment,
                provider_payment_id=event_data["payment_id"],
                customer_id=event_data["customer_id"],
                subscription_id=event_data["subscription_id"],
                invoice_id=event_data["invoice_id"],
                invoice_url=event_data["invoice_url"],
                metadata=event_data["metadata"],
            )
        elif payment and is_payment_failed and payment.status != "completed":
            payment.status = "failed"
            payment.save()
        elif payment and is_refund_event:
            _mark_payment_refunded(
                payment=payment,
                metadata=event_data["metadata"],
            )
        elif is_refund_event and not payment:
            logger.warning(
                "Dodo refund webhook received but no matching payment found "
                f"(payment_id={event_data.get('payment_id', '')}, refund_id={event_data.get('refund_id', '')})"
            )

        if is_subscription_event and event_data["subscription_id"]:
            account = None
            if payment:
                account = payment.account
            else:
                subscription = BillingSubscription.objects.filter(
                    external_subscription_id=event_data["subscription_id"]
                ).first()
                if subscription:
                    account = subscription.account

            if account:
                sub_status_map = {
                    "subscription.active": "active",
                    "subscription.renewed": "active",
                    "subscription.on_hold": "on_hold",
                    "subscription.cancelled": "canceled",
                    "subscription.failed": "failed",
                    "subscription.expired": "expired",
                    "subscription.past_due": "past_due",
                    "subscription.paused": "paused",
                }
                effective_status = sub_status_map.get(
                    event_type,
                    event_data["status"] or "active",
                )
                inferred_plan = event_data["plan_name"]
                if not inferred_plan and payment:
                    inferred_plan = _extract_plan_name(payment.description)

                _apply_subscription_state(
                    account=account,
                    subscription_id=event_data["subscription_id"],
                    customer_id=event_data["customer_id"],
                    plan_name=inferred_plan,
                    status=effective_status,
                    cancel_at_period_end=event_data["cancel_at_period_end"],
                    current_period_start=event_data["current_period_start"],
                    current_period_end=event_data["current_period_end"],
                    canceled_at=event_data["canceled_at"],
                    metadata=event_data["metadata"],
                )

        webhook_event.processed = True
        webhook_event.processed_at = timezone.now()
        webhook_event.save()
    except Exception as exc:
        logger.error(f"Failed processing Dodo webhook: {str(exc)}")
        # Still mark processed and return 200 so DoDo does not retry forever
        # for unknown or malformed events (e.g. many event types configured).
        webhook_event.processed = True
        webhook_event.processed_at = timezone.now()
        webhook_event.save()
        return ResponseParser.getParsedSuccessMessage(
            {"event_id": webhook_event.event_id},
            "success",
            "Webhook received (processing error logged)",
        )

    return ResponseParser.getParsedSuccessMessage(
        {"event_id": webhook_event.event_id},
        "success",
        "Webhook processed successfully",
    )


def get_payment_history(request):
    """
    API to retrieve payment history for a user
    Required parameters:
    - uid: User UID
    """

    uid = request.POST.get("uid", "")

    if not uid:
        return ResponseParser.getParsedErrorMessage("UID is required")

    # Get user from UID
    try:
        user_object = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return ResponseParser.getParsedErrorMessage("User not found")

    try:
        account_object = Account.objects.get(created_by_user=user_object)
        payments = Payment.objects.filter(account=account_object).order_by(
            "-created_at"
        )

        payment_list = [payment.get_dict() for payment in payments]

        return ResponseParser.getParsedSuccessMessage(
            {"payments": payment_list},
            "success",
            "Payment history retrieved successfully",
        )

    except Account.DoesNotExist:
        return ResponseParser.getParsedErrorMessage("Account not found")
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(
            f"Failed to retrieve payment history: {str(e)}"
        )


def get_billing_overview(request):
    uid = request.POST.get("uid", "")
    try:
        _, account_object = _get_user_and_account(uid)
    except ValueError as exc:
        return ResponseParser.getParsedErrorMessage(str(exc))

    latest_subscription = (
        BillingSubscription.objects.filter(account=account_object).order_by("-updated_at").first()
    )
    recent_payments = Payment.objects.filter(account=account_object).order_by("-created_at")[:20]

    return ResponseParser.getParsedSuccessMessage(
        {
            "account_plan_name": account_object.plan_name,
            "subscription": latest_subscription.get_dict() if latest_subscription else None,
            "payments": [payment.get_dict() for payment in recent_payments],
        },
        "success",
        "Billing overview retrieved successfully",
    )


def create_portal_session(request):
    uid = request.POST.get("uid", "")
    try:
        _, account_object = _get_user_and_account(uid)
    except ValueError as exc:
        return ResponseParser.getParsedErrorMessage(str(exc))

    latest_subscription = (
        BillingSubscription.objects.filter(account=account_object).order_by("-updated_at").first()
    )
    latest_payment = Payment.objects.filter(account=account_object).order_by("-created_at").first()

    customer_id = ""
    if latest_subscription and latest_subscription.external_customer_id:
        customer_id = latest_subscription.external_customer_id
    elif latest_payment and latest_payment.external_customer_id:
        customer_id = latest_payment.external_customer_id

    if not customer_id:
        return ResponseParser.getParsedErrorMessage(
            "No billing customer found for this account"
        )

    try:
        path = f"/customers/{customer_id}/customer-portal/session"
        dodo_response = _dodo_request("POST", path)
        portal_url = dodo_response.get("link", "")

        if not portal_url:
            logger.error(f"Dodo portal response missing 'link': {dodo_response}")
            return ResponseParser.getParsedErrorMessage(
                "Failed to create billing portal session"
            )

        return ResponseParser.getParsedSuccessMessage(
            {"portal_url": portal_url},
            "success",
            "Billing portal session created successfully",
        )
    except Exception as exc:
        logger.error(f"Failed to create Dodo portal session: {str(exc)}")
        return ResponseParser.getParsedErrorMessage(
            f"Failed to create billing portal session: {str(exc)}"
        )


def add_credits_to_openrouter(account_object, credits_in_usd, is_renewal=False, plan_monthly_credits=0):
    try:
        # If user already has a key, add credits to it
        url = "https://openrouter.ai/api/v1/keys"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_PROVISIONING_KEY}",
            "Content-Type": "application/json",
        }

        # Resolve the key hash needed for PATCH.
        key_hash = account_object.open_router_key_hash or ""
        if not key_hash:
            logger.error(
                f"No OpenRouter key hash for account: {account_object.account_uid}"
            )
            return False

        if is_renewal and plan_monthly_credits > 0:
            # On renewal, enforce 3-month rollover cap before adding new credits.
            # Cap = 2x monthly (so after adding 1 new month the max possible is 3x).
            # Fetch live balance via user's own key to get accurate usage + remaining.
            credit_data = fetch_credits_from_openrouter(account_object.open_router_key)
            remaining_wa = credit_data["limit_remaining"] * WAVEASSIST_CREDIT_MULTIPLIER
            usage_or = credit_data["usage"]

            rollover_cap_wa = float(plan_monthly_credits) * 2
            capped_remaining_wa = min(remaining_wa, rollover_cap_wa)

            new_balance_wa = capped_remaining_wa + float(credits_in_usd)
            new_limit = usage_or + new_balance_wa / WAVEASSIST_CREDIT_MULTIPLIER
            logger.info(
                f"Renewal rollover cap applied for {account_object.account_uid}: "
                f"remaining_wa={remaining_wa:.2f}, cap={rollover_cap_wa:.2f}, "
                f"capped={capped_remaining_wa:.2f}, new_balance_wa={new_balance_wa:.2f}"
            )
        else:
            # First-time subscription or top-up: add on top of current limit.
            # credits_in_usd is in WaveAssist credits; convert to real OpenRouter dollars.
            credit_data = fetch_credits_from_openrouter(account_object.open_router_key)
            current_limit = credit_data["limit"]
            credits_float = float(credits_in_usd) / WAVEASSIST_CREDIT_MULTIPLIER
            new_limit = float(current_limit + credits_float)

        update_payload = {"limit": new_limit}

        update_response = requests.patch(
            f"{url}/{key_hash}", json=update_payload, headers=headers, timeout=10
        )

        update_response.raise_for_status()

        return True

    except Exception as e:
        logger.error(
            f"Unexpected error adding credits to OpenRouter for account {account_object.account_uid}: {str(e)}"
        )
        return False

import json
import uuid
import os
import razorpay
from decimal import Decimal

from .Utils.utils import logger

from .models import *
from .Utils.responseParser import ResponseParser
from .Utils.utils import create_openrouter_token
from .Utils.constants import OPENROUTER_PROVISIONING_KEY
from django.conf import settings
import requests
from .Utils.constants import *


# Initialize payment clients from environment variables
try:
    razorpay_client = razorpay.Client(
        auth=(
            os.environ.get("RAZORPAY_KEY_ID", RAZORPAY_ID),
            os.environ.get("RAZORPAY_KEY_SECRET", RAZORPAY_SECRET),
        )
    )
except:
    razorpay_client = None


def get_paypal_access_token():
    """Get PayPal V2 API access token using OAuth2 client credentials flow"""
    try:
        url = f"https://api-m.{os.environ.get('PAYPAL_MODE', 'sandbox')}.paypal.com/v1/oauth2/token"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US",
        }
        data = {"grant_type": "client_credentials"}
        auth = (
            os.environ.get("PAYPAL_CLIENT_ID", PAYPAL_SANDBOX_CLIENT_ID),
            os.environ.get("PAYPAL_CLIENT_SECRET", PAYPAL_SANDBOX_CLIENT_SECRET),
        )
        response = requests.post(url, headers=headers, data=data, auth=auth, timeout=10)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        logger.error(f"Failed to get PayPal access token: {str(e)}")
        return None


def create_payment_order(request):
    """
    Create payment order API with loader support
    Returns status indicators for frontend loader management
    """
    # Validate required parameters
    uid = request.POST.get("uid", "")
    provider = request.POST.get("provider", "").lower()
    amount = request.POST.get("amount", "")
    currency = request.POST.get("currency", "")
    credits_in_usd = request.POST.get("credits_in_usd", "0")
    description = request.POST.get("description", "Payment")

    if not uid:
        return ResponseParser.getParsedErrorMessage("UID is required")

    if not provider or provider not in ["razorpay", "paypal"]:
        return ResponseParser.getParsedErrorMessage(
            'Provider must be either "razorpay" or "paypal"'
        )

    if not amount:
        return ResponseParser.getParsedErrorMessage("Amount is required")

    try:
        amount_decimal = Decimal(amount)
        if amount_decimal <= 0:
            return ResponseParser.getParsedErrorMessage("Amount must be greater than 0")
    except:
        return ResponseParser.getParsedErrorMessage("Invalid amount format")

    # Set default currency based on provider
    if not currency:
        currency = "INR" if provider == "razorpay" else "USD"

    # Validate currency
    if currency not in ["USD", "INR"]:
        return ResponseParser.getParsedErrorMessage("Currency must be USD or INR")

    # Apply safe multiplier for INR to USD conversion
    if currency == "INR":
        safe_multiplier = 80
        max_credits_allowed = amount_decimal / safe_multiplier
    else:
        # For USD, credits can equal payment amount
        max_credits_allowed = amount_decimal

    try:
        credits_decimal = Decimal(credits_in_usd)
        if credits_decimal < 0:
            return ResponseParser.getParsedErrorMessage("Credits cannot be negative")
        if credits_decimal > max_credits_allowed:
            return ResponseParser.getParsedErrorMessage(
                f"Credits cannot exceed {max_credits_allowed} USD for {amount_decimal} {currency}"
            )
    except:
        return ResponseParser.getParsedErrorMessage("Invalid credits format")

    # Get user from UID
    try:
        user_object = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return ResponseParser.getParsedErrorMessage("User not found")

    # Get user's account
    try:
        account_object = Account.objects.get(created_by_user=user_object)
    except Account.DoesNotExist:
        return ResponseParser.getParsedErrorMessage("Account not found")

    # Create payment order based on provider
    if provider == "razorpay":
        return create_razorpay_order(
            account_object, amount_decimal, currency, description, credits_decimal
        )
    elif provider == "paypal":
        return create_paypal_order(
            account_object, amount_decimal, currency, description, credits_decimal
        )


def create_razorpay_order(
    account_object, amount, currency, description, credits_in_usd
):
    """Create RazorPay order"""

    if not razorpay_client:
        return ResponseParser.getParsedErrorMessage("RazorPay client not configured")

    try:
        # Convert amount to paise (RazorPay expects amount in smallest currency unit)
        amount_paise = int(amount * 100)

        # Create RazorPay order
        order_data = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": f"order_{uuid.uuid4().hex[:16]}",
            "notes": {
                "description": description,
                "account_id": str(account_object.account_uid),
            },
        }

        razorpay_order = razorpay_client.order.create(data=order_data)

        # Create payment record in database
        payment = Payment.objects.create(
            account=account_object,
            provider="razorpay",
            amount=amount,
            currency=currency,
            credits_in_usd=credits_in_usd,
            status="pending",
            provider_payment_id=razorpay_order["id"],
            description=description,
        )

        # Return order details for frontend
        response_data = {
            "order_id": razorpay_order["id"],
            "amount": amount_paise,
            "currency": currency,
            "payment_id": payment.id,
            "provider": "razorpay",
        }

        return ResponseParser.getParsedSuccessMessage(
            response_data, "success", "RazorPay order created successfully"
        )

    except Exception as e:
        return ResponseParser.getParsedErrorMessage(
            f"Failed to create RazorPay order: {str(e)}"
        )


def create_paypal_order(account_object, amount, currency, description, credits_in_usd):
    """Create PayPal V2 order"""
    try:
        access_token = get_paypal_access_token()
        if not access_token:
            return ResponseParser.getParsedErrorMessage(
                "Failed to authenticate with PayPal"
            )

        url = f"https://api-m.{os.environ.get('PAYPAL_MODE', 'sandbox')}.paypal.com/v2/checkout/orders"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": currency,
                        "value": f"{amount:.2f}",
                    },
                    "description": description,
                }
            ],
            "application_context": {
                "brand_name": "WaveAssist",
                "landing_page": "BILLING",  # Enables guest checkout (debit/credit card)
                "user_action": "PAY_NOW",
            },
        }
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        order_data = response.json()

        if order_data.get("status") not in ["CREATED", "APPROVED"]:
            return ResponseParser.getParsedErrorMessage("Failed to create PayPal order")

        # Create payment record in database
        db_payment = Payment.objects.create(
            account=account_object,
            provider="paypal",
            amount=amount,
            currency=currency,
            credits_in_usd=credits_in_usd,
            status="pending",
            provider_payment_id=order_data["id"],
            description=description,
        )

        response_data = {
            "order_id": order_data["id"],  # v2 Order ID (e.g., 5O190127TN364715T)
            "payment_id": db_payment.id,  # Internal DB payment ID
            "amount": f"{amount:.2f}",
            "currency": currency,
            "provider": "paypal",
        }

        return ResponseParser.getParsedSuccessMessage(
            response_data,
            "success",
            "PayPal order created successfully",
        )
    except Exception as e:
        logger.error(f"Failed to create PayPal order: {str(e)}")
        return ResponseParser.getParsedErrorMessage(
            f"Failed to create PayPal order: {str(e)}"
        )


def verify_payment(request):
    uid = request.POST.get("uid", "")
    provider_payment_id = request.POST.get("provider_payment_id", "")
    signature = request.POST.get("signature", "")  # For RazorPay
    razorpay_payment_id = request.POST.get("razorpay_payment_id", "")  # For RazorPay
    paypal_payer_id = request.POST.get("paypal_payer_id", "")  # For PayPal

    if not uid or not provider_payment_id:
        return ResponseParser.getParsedErrorMessage("Missing required parameters")

    # Get user from UID
    try:
        user_object = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return ResponseParser.getParsedErrorMessage("User not found")

    try:
        payment = Payment.objects.get(provider_payment_id=provider_payment_id)
    except Payment.DoesNotExist:
        return ResponseParser.getParsedErrorMessage("Payment not found")

    # Verify payment based on provider
    if payment.provider == "razorpay":
        return verify_razorpay_payment(
            payment, provider_payment_id, signature, razorpay_payment_id
        )
    elif payment.provider == "paypal":
        return verify_paypal_payment(payment, provider_payment_id, paypal_payer_id)
    else:
        return ResponseParser.getParsedErrorMessage("Invalid payment provider")


def verify_razorpay_payment(
    payment, provider_payment_id, signature, razorpay_payment_id
):
    """Verify RazorPay payment"""

    if not razorpay_client:
        logger.error("RazorPay client not configured")
        return ResponseParser.getParsedErrorMessage("RazorPay client not configured")

    try:
        # Verify payment signature
        params_dict = {
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_order_id": payment.provider_payment_id,
            "razorpay_signature": signature,
        }

        razorpay_client.utility.verify_payment_signature(params_dict)

        # Get payment details
        payment_details = razorpay_client.payment.fetch(razorpay_payment_id)

        if payment_details["status"] == "captured":
            payment.status = "completed"
            payment.save()

            # Add credits to OpenRouter if credits were purchased and haven't been granted yet
            if payment.credits_in_usd > 0 and not payment.credits_granted:
                credits_added = add_credits_to_openrouter(
                    payment.account, payment.credits_in_usd
                )
                if credits_added:
                    payment.credits_granted = True
                    payment.save()
                else:
                    logger.error(f"Failed to add credits to OpenRouter.")
            else:
                logger.info(f"Skipping credits addition.")

            return ResponseParser.getParsedSuccessMessage(
                payment.get_dict(), "success", "Payment verified successfully"
            )
        else:
            logger.info(f"Payment not captured.")
            payment.status = "failed"
            payment.save()

            return ResponseParser.getParsedErrorMessage("Payment verification failed")

    except Exception as e:
        logger.error(f"Exception during RazorPay payment verification: {str(e)}")
        payment.status = "failed"
        payment.save()
        return ResponseParser.getParsedErrorMessage(
            f"Payment verification failed: {str(e)}"
        )


def verify_paypal_payment(payment, provider_payment_id, payer_id):
    """Verify PayPal V2 payment"""
    try:
        access_token = get_paypal_access_token()
        if not access_token:
            return ResponseParser.getParsedErrorMessage(
                "Failed to authenticate with PayPal"
            )

        url = f"https://api-m.{os.environ.get('PAYPAL_MODE', 'sandbox')}.paypal.com/v2/checkout/orders/{provider_payment_id}/capture"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        response = requests.post(url, headers=headers, timeout=10)
        response.raise_for_status()
        capture_data = response.json()

        if capture_data.get("status") == "COMPLETED":
            payment.status = "completed"
            payment.save()

            # Add credits to OpenRouter if needed
            if payment.credits_in_usd > 0 and not payment.credits_granted:
                credits_added = add_credits_to_openrouter(
                    payment.account, payment.credits_in_usd
                )
                if credits_added:
                    payment.credits_granted = True
                    payment.save()
                else:
                    logger.error("Failed to add credits to OpenRouter")

            return ResponseParser.getParsedSuccessMessage(
                payment.get_dict(),
                "success",
                "Payment verified successfully",
            )
        else:
            payment.status = "failed"
            payment.save()
            return ResponseParser.getParsedErrorMessage("Payment capture failed")
    except Exception as e:
        logger.error(f"Exception during PayPal payment verification: {str(e)}")
        payment.status = "failed"
        payment.save()
        return ResponseParser.getParsedErrorMessage(
            f"Payment verification failed: {str(e)}"
        )


def get_payment_history(request):
    """
    GET API to retrieve payment history for a user
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


def payment_success_handler(request):
    """
    Handle PayPal V2 payment success redirect
    This view receives the redirect from PayPal and can trigger verification
    """
    order_id = request.GET.get("token")  # V2 uses 'token' parameter for order ID
    payer_id = request.GET.get("PayerID")

    if not order_id:
        return ResponseParser.getParsedErrorMessage("Order ID is required")

    # Log the success redirect for debugging
    print(
        f"PayPal V2 success redirect received - OrderID: {order_id}, PayerID: {payer_id}"
    )

    # Return success response that frontend can handle
    return ResponseParser.getParsedSuccessMessage(
        {
            "order_id": order_id,
            "payer_id": payer_id,
            "message": "Payment approved by PayPal. Please verify payment on your end.",
        },
        "success",
        "Payment approved by PayPal",
    )


def add_credits_to_openrouter(account_object, credits_in_usd):
    try:
        # If user already has a key, add credits to it
        url = "https://openrouter.ai/api/v1/keys"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_PROVISIONING_KEY}",
            "Content-Type": "application/json",
        }

        # First, get the current key details
        response = requests.get(url, headers=headers, timeout=10)

        response.raise_for_status()
        keys_data = response.json()

        # Find the user's key
        user_key = None

        for key in keys_data.get("data", []):
            if key.get("name") == account_object.account_uid:
                user_key = key
                break

        if not user_key:
            logger.error(
                f"No OpenRouter key found for account: {account_object.account_uid}"
            )
            return False

        # Update the key with additional credits
        key_hash = user_key.get("hash")
        current_limit = user_key.get("limit", 0)
        # Convert Decimal to float for JSON serialization
        credits_float = float(credits_in_usd)
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

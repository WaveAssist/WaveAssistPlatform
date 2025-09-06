import json
import uuid
import os
import razorpay
import paypalrestsdk
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
        auth=(os.environ.get('RAZORPAY_KEY_ID', RAZORPAY_ID),
              os.environ.get('RAZORPAY_KEY_SECRET', RAZORPAY_SECRET))
    )
except:
    razorpay_client = None

try:
    paypalrestsdk.configure({
        "mode": os.environ.get('PAYPAL_MODE', PAYPAL_MODE),  # sandbox or live
        "client_id": os.environ.get('PAYPAL_CLIENT_ID', PAYPAL_SANDBOX_CLIENT_ID),
        "client_secret": os.environ.get('PAYPAL_CLIENT_SECRET', PAYPAL_SANDBOX_CLIENT_SECRET)
    })
except:
    pass

PAYPAL_RETURN_URL = os.environ.get('PAYPAL_RETURN_URL', 'http://app.waveassist.io/payment/success')
PAYPAL_CANCEL_URL = os.environ.get('PAYPAL_CANCEL_URL', 'http://app.waveassist.io/payment/cancel')



def create_payment_order(request):
    
    logger.info(f"Creating payment order")

    # Validate required parameters
    uid = request.POST.get('uid', '')
    provider = request.POST.get('provider', '').lower()
    amount = request.POST.get('amount', '')
    currency = request.POST.get('currency', '')
    credits_in_usd = request.POST.get('credits_in_usd', '0')
    description = request.POST.get('description', 'Payment')
    
    if not uid:
        return ResponseParser.getParsedErrorMessage('UID is required')
    
    if not provider or provider not in ['razorpay', 'paypal']:
        return ResponseParser.getParsedErrorMessage('Provider must be either "razorpay" or "paypal"')
    
    if not amount:
        return ResponseParser.getParsedErrorMessage('Amount is required')
    
    try:
        amount_decimal = Decimal(amount)
        if amount_decimal <= 0:
            return ResponseParser.getParsedErrorMessage('Amount must be greater than 0')
    except:
        return ResponseParser.getParsedErrorMessage('Invalid amount format')
    
    # Set default currency based on provider
    if not currency:
        currency = 'INR' if provider == 'razorpay' else 'USD'
    
    # Validate currency
    if currency not in ['USD', 'INR']:
        return ResponseParser.getParsedErrorMessage('Currency must be USD or INR')
    
    # Apply safe multiplier for INR to USD conversion
    if currency == 'INR':
        safe_multiplier = 80
        max_credits_allowed = amount_decimal / safe_multiplier
    else:
        # For USD, credits can equal payment amount
        max_credits_allowed = amount_decimal
    
    try:
        credits_decimal = Decimal(credits_in_usd)
        if credits_decimal < 0:
            return ResponseParser.getParsedErrorMessage('Credits cannot be negative')
        if credits_decimal > max_credits_allowed:
            return ResponseParser.getParsedErrorMessage(f'Credits cannot exceed {max_credits_allowed} USD for {amount_decimal} {currency}')
    except:
        return ResponseParser.getParsedErrorMessage('Invalid credits format')
    
    
    # Get user from UID
    try:
        user_object = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return ResponseParser.getParsedErrorMessage('User not found')
    
    # Get user's account
    try:
        account_object = Account.objects.get(created_by_user=user_object)
    except Account.DoesNotExist:
        return ResponseParser.getParsedErrorMessage('Account not found')
    
    # Create payment order based on provider
    if provider == 'razorpay':
        return create_razorpay_order(account_object, amount_decimal, currency, description, credits_decimal)
    elif provider == 'paypal':
        return create_paypal_order(account_object, amount_decimal, currency, description, credits_decimal)


def create_razorpay_order(account_object, amount, currency, description, credits_in_usd):
    """Create RazorPay order"""
    
    if not razorpay_client:
        return ResponseParser.getParsedErrorMessage('RazorPay client not configured')
    
    try:
        # Convert amount to paise (RazorPay expects amount in smallest currency unit)
        amount_paise = int(amount * 100)
        
        # Create RazorPay order
        order_data = {
            'amount': amount_paise,
            'currency': currency,
            'receipt': f'order_{uuid.uuid4().hex[:16]}',
            'notes': {
                'description': description,
                'account_id': str(account_object.account_uid)
            }
        }
        
        razorpay_order = razorpay_client.order.create(data=order_data)
        
        # Create payment record in database
        payment = Payment.objects.create(
            account=account_object,
            provider='razorpay',
            amount=amount,
            currency=currency,
            credits_in_usd=credits_in_usd,
            status='pending',
            provider_payment_id=razorpay_order['id'],
            description=description
        )
        
        # Return order details for frontend
        response_data = {
            'order_id': razorpay_order['id'],
            'amount': amount_paise,
            'currency': currency,
            'payment_id': payment.id,
            'provider': 'razorpay'
        }
        
        return ResponseParser.getParsedSuccessMessage(
            response_data, 
            'success', 
            'RazorPay order created successfully'
        )
        
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f'Failed to create RazorPay order: {str(e)}')


def create_paypal_order(account_object, amount, currency, description, credits_in_usd):
    """Create PayPal order"""
    
    try:
        # Create PayPal payment
        payment_data = {
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": PAYPAL_RETURN_URL,
                "cancel_url": PAYPAL_CANCEL_URL
            },
            "transactions": [
                {
                    "item_list": {
                        "items": [
                            {
                                "name": description,
                                "sku": f"item_{uuid.uuid4().hex[:8]}",
                                "price": str(amount),
                                "currency": currency,
                                "quantity": 1
                            }
                        ]
                    },
                    "amount": {
                        "total": str(amount),
                        "currency": currency
                    },
                    "description": description
                }
            ]
        }
        
        payment = paypalrestsdk.Payment(payment_data)
        
        if payment.create():
            # Get approval URL
            approval_url = None
            for link in payment.links:
                if link.rel == "approval_url":
                    approval_url = link.href
                    break
            
            if not approval_url:
                return ResponseParser.getParsedErrorMessage('Failed to get PayPal approval URL')
            
            # Create payment record in database
            db_payment = Payment.objects.create(
                account=account_object,
                provider='paypal',
                amount=amount,
                currency=currency,
                credits_in_usd=credits_in_usd,
                status='pending',
                provider_payment_id=payment.id,
                description=description
            )
            
            # Return payment details for frontend
            response_data = {
                'payment_id': payment.id,
                'approval_url': approval_url,
                'amount': str(amount),
                'currency': currency,
                'db_payment_id': db_payment.id,
                'provider': 'paypal'
            }
            
            return ResponseParser.getParsedSuccessMessage(
                response_data, 
                'success', 
                'PayPal payment created successfully'
            )
        else:
            return ResponseParser.getParsedErrorMessage(f'Failed to create PayPal payment: {payment.error}')
            
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f'Failed to create PayPal payment: {str(e)}')


def verify_payment(request):
    uid = request.POST.get('uid', '')
    provider_payment_id = request.POST.get('provider_payment_id', '')
    signature = request.POST.get('signature', '')  # For RazorPay
    razorpay_payment_id = request.POST.get('razorpay_payment_id', '') # For RazorPay
    paypal_payer_id = request.POST.get('paypal_payer_id', '')  # For PayPal
    
    if not uid or not provider_payment_id:
        return ResponseParser.getParsedErrorMessage('Missing required parameters')
    
    # Get user from UID
    try:
        user_object = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return ResponseParser.getParsedErrorMessage('User not found')
    
    try:
        payment = Payment.objects.get(provider_payment_id=provider_payment_id)
    except Payment.DoesNotExist:
        return ResponseParser.getParsedErrorMessage('Payment not found')
    
    # Verify payment based on provider
    if payment.provider == 'razorpay':
        return verify_razorpay_payment(payment, provider_payment_id, signature, razorpay_payment_id)
    elif payment.provider == 'paypal':
        return verify_paypal_payment(payment, provider_payment_id, paypal_payer_id)
    else:
        return ResponseParser.getParsedErrorMessage('Invalid payment provider')


def verify_razorpay_payment(payment, provider_payment_id, signature, razorpay_payment_id):
    """Verify RazorPay payment"""
        
    if not razorpay_client:
        logger.error("RazorPay client not configured")
        return ResponseParser.getParsedErrorMessage('RazorPay client not configured')
    
    try:
        # Verify payment signature
        params_dict = {
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_order_id': payment.provider_payment_id,
            'razorpay_signature': signature
        }
        
        logger.info(f"Verifying RazorPay signature with params: {params_dict}")
        razorpay_client.utility.verify_payment_signature(params_dict)
        
        # Get payment details
        payment_details = razorpay_client.payment.fetch(razorpay_payment_id)
        logger.info(f"Payment details fetched: {payment_details}")
        
        if payment_details['status'] == 'captured':
            logger.info(f"Payment captured successfully. Updating payment status to completed for payment ID: {payment.id}")
            payment.status = 'completed'
            payment.save()
            
            # Add credits to OpenRouter if credits were purchased and haven't been granted yet
            logger.info(f"Checking credits for payment ID: {payment.id}, credits_in_usd: {payment.credits_in_usd}, credits_granted: {payment.credits_granted}")
            if payment.credits_in_usd > 0 and not payment.credits_granted:
                logger.info(f"Attempting to add {payment.credits_in_usd} USD credits to OpenRouter for account: {payment.account.account_uid}")
                credits_added = add_credits_to_openrouter(payment.account, payment.credits_in_usd)
                if credits_added:
                    logger.info(f"Successfully added credits to OpenRouter. Updating payment.credits_granted to True for payment ID: {payment.id}")
                    payment.credits_granted = True
                    payment.save()
                else:
                    logger.error(f"Failed to add credits to OpenRouter for payment ID: {payment.id}, account: {payment.account.account_uid}")
                    print(f"Warning: Failed to add credits to OpenRouter for payment {payment.id}")
            else:
                logger.info(f"Skipping credits addition - credits_in_usd: {payment.credits_in_usd}, credits_granted: {payment.credits_granted}")
            
            logger.info(f"RazorPay payment verification completed successfully for payment ID: {payment.id}")
            return ResponseParser.getParsedSuccessMessage(
                payment.get_dict(), 
                'success', 
                'Payment verified successfully'
            )
        else:
            logger.warning(f"Payment not captured. Status: {payment_details['status']} for payment ID: {payment.id}")
            payment.status = 'failed'
            payment.save()
            
            return ResponseParser.getParsedErrorMessage('Payment verification failed')
            
    except Exception as e:
        logger.error(f"Exception during RazorPay payment verification for payment ID: {payment.id}: {str(e)}", exc_info=True)
        payment.status = 'failed'
        payment.save()
        return ResponseParser.getParsedErrorMessage(f'Payment verification failed: {str(e)}')


def verify_paypal_payment(payment, provider_payment_id, payer_id):
    """Verify PayPal payment"""
    
    logger.info(f"Starting PayPal payment verification for payment ID: {payment.id}, provider_payment_id: {provider_payment_id}, payer_id: {payer_id}")
    
    try:
        # Get payment details from PayPal
        logger.info(f"Fetching PayPal payment details for provider_payment_id: {provider_payment_id}")
        paypal_payment = paypalrestsdk.Payment.find(provider_payment_id)
        logger.info(f"PayPal payment state: {paypal_payment.state}")
        
        # Check if payment is in 'created' state (user approved but not executed)
        if paypal_payment.state == 'created':
            logger.info("PayPal payment is in 'created' state, attempting to execute")
            if not payer_id:
                logger.error("PayerID is required to execute PayPal payment")
                return ResponseParser.getParsedErrorMessage('PayerID is required to execute PayPal payment')
            
            # Execute the payment to complete the transaction
            logger.info(f"Executing PayPal payment with payer_id: {payer_id}")
            if paypal_payment.execute({'payer_id': payer_id}):
                logger.info("PayPal payment executed successfully, fetching updated payment details")
                # Payment executed successfully, now state should be 'approved'
                paypal_payment = paypalrestsdk.Payment.find(provider_payment_id)
                logger.info(f"PayPal payment state after execution: {paypal_payment.state}")
            else:
                logger.error(f"PayPal payment execution failed: {paypal_payment.error}")
                payment.status = 'failed'
                payment.save()
                return ResponseParser.getParsedErrorMessage(f'Payment execution failed: {paypal_payment.error}')
        
        if paypal_payment.state == 'approved':
            logger.info(f"PayPal payment approved. Updating payment status to completed for payment ID: {payment.id}")
            payment.status = 'completed'
            payment.save()
            
            # Add credits to OpenRouter if credits were purchased and haven't been granted yet
            logger.info(f"Checking credits for payment ID: {payment.id}, credits_in_usd: {payment.credits_in_usd}, credits_granted: {payment.credits_granted}")
            if payment.credits_in_usd > 0 and not payment.credits_granted:
                logger.info(f"Attempting to add {payment.credits_in_usd} USD credits to OpenRouter for account: {payment.account.account_uid}")
                credits_added = add_credits_to_openrouter(payment.account, payment.credits_in_usd)
                if credits_added:
                    logger.info(f"Successfully added credits to OpenRouter. Updating payment.credits_granted to True for payment ID: {payment.id}")
                    payment.credits_granted = True
                    payment.save()
                else:
                    logger.error(f"Failed to add credits to OpenRouter for payment ID: {payment.id}, account: {payment.account.account_uid}")
                    print(f"Warning: Failed to add credits to OpenRouter for payment {payment.id}")
            else:
                logger.info(f"Skipping credits addition - credits_in_usd: {payment.credits_in_usd}, credits_granted: {payment.credits_granted}")
            
            logger.info(f"PayPal payment verification completed successfully for payment ID: {payment.id}")
            return ResponseParser.getParsedSuccessMessage(
                payment.get_dict(), 
                'success', 
                'Payment verified successfully'
            )
        else:
            logger.warning(f"PayPal payment not approved. State: {paypal_payment.state} for payment ID: {payment.id}")
            payment.status = 'failed'
            payment.save()
            return ResponseParser.getParsedErrorMessage(f'Payment verification failed. State: {paypal_payment.state}')
            
    except Exception as e:
        logger.error(f"Exception during PayPal payment verification for payment ID: {payment.id}: {str(e)}", exc_info=True)
        payment.status = 'failed'
        payment.save()
        return ResponseParser.getParsedErrorMessage(f'Payment verification failed: {str(e)}')


def get_payment_history(request):
    """
    GET API to retrieve payment history for a user
    Required parameters:
    - uid: User UID
    """
    
    uid = request.POST.get('uid', '')
    
    if not uid:
        return ResponseParser.getParsedErrorMessage('UID is required')
    
    # Get user from UID
    try:
        user_object = User.objects.get(uid=uid)
    except User.DoesNotExist:
        return ResponseParser.getParsedErrorMessage('User not found')
    
    try:
        account_object = Account.objects.get(created_by_user=user_object)
        payments = Payment.objects.filter(account=account_object).order_by('-created_at')
        
        payment_list = [payment.get_dict() for payment in payments]
        
        return ResponseParser.getParsedSuccessMessage(
            {'payments': payment_list}, 
            'success', 
            'Payment history retrieved successfully'
        )
        
    except Account.DoesNotExist:
        return ResponseParser.getParsedErrorMessage('Account not found')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f'Failed to retrieve payment history: {str(e)}')


def payment_success_handler(request):
    """
    Handle PayPal payment success redirect
    This view receives the redirect from PayPal and can trigger verification
    """
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')
    token = request.GET.get('token')
    
    if not payment_id:
        return ResponseParser.getParsedErrorMessage('Payment ID is required')
    
    # Log the success redirect for debugging
    print(f"PayPal success redirect received - PaymentID: {payment_id}, PayerID: {payer_id}, Token: {token}")
    
    # Return success response that frontend can handle
    return ResponseParser.getParsedSuccessMessage(
        {
            'payment_id': payment_id,
            'payer_id': payer_id,
            'token': token,
            'message': 'Payment approved by PayPal. Please verify payment on your end.'
        },
        'success',
        'Payment approved by PayPal'
    )


def add_credits_to_openrouter(account_object, credits_in_usd):
    """Add credits to user's OpenRouter account"""
    logger.info(f"Starting OpenRouter credits addition for account: {account_object.account_uid}, credits: {credits_in_usd} USD")
    
    try:
        # If user already has a key, add credits to it
        url = "https://openrouter.ai/api/v1/keys"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_PROVISIONING_KEY}",
            "Content-Type": "application/json",
        }
        
        logger.info(f"Making GET request to OpenRouter API: {url}")
        logger.info(f"Using authorization header with key: {OPENROUTER_PROVISIONING_KEY[:10]}...")
        
        # First, get the current key details
        response = requests.get(url, headers=headers, timeout=10)
        logger.info(f"OpenRouter API response status: {response.status_code}")
        
        response.raise_for_status()
        keys_data = response.json()
        logger.info(f"OpenRouter API response data: {keys_data}")
        
        # Find the user's key
        user_key = None
        logger.info(f"Searching for key with name: {account_object.account_uid}")
        
        for key in keys_data.get('data', []):
            logger.info(f"Checking key: {key}")
            if key.get('name') == account_object.account_uid:
                user_key = key
                logger.info(f"Found matching key: {user_key}")
                break
        
        if not user_key:
            logger.error(f"No OpenRouter key found for account: {account_object.account_uid}")
            logger.error(f"Available keys: {[key.get('name') for key in keys_data.get('data', [])]}")
            return False
        
        # Update the key with additional credits
        key_hash = user_key.get('hash')
        current_limit = user_key.get('limit', 0)
        new_limit = current_limit + credits_in_usd
        
        logger.info(f"Key details - hash: {key_hash}, current_limit: {current_limit}, new_limit: {new_limit}")
        
        update_payload = {
            "limit": new_limit
        }
        
        logger.info(f"Making PATCH request to update key with payload: {update_payload}")
        update_response = requests.patch(f"{url}/{key_hash}", json=update_payload, headers=headers, timeout=10)
        logger.info(f"OpenRouter update response status: {update_response.status_code}")
        logger.info(f"OpenRouter update response content: {update_response.text}")
        
        update_response.raise_for_status()
        
        logger.info(f"Successfully added {credits_in_usd} USD credits to OpenRouter for account: {account_object.account_uid}")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception while adding credits to OpenRouter for account {account_object.account_uid}: {str(e)}")
        logger.error(f"Response status: {getattr(e.response, 'status_code', 'N/A') if hasattr(e, 'response') else 'N/A'}")
        logger.error(f"Response content: {getattr(e.response, 'text', 'N/A') if hasattr(e, 'response') else 'N/A'}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error adding credits to OpenRouter for account {account_object.account_uid}: {str(e)}", exc_info=True)
        print(f"Error adding credits to OpenRouter: {str(e)}")
        return False

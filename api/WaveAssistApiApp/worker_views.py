import json
import uuid
from django.shortcuts import render
from .models import *
from .Utils.responseParser import ResponseParser
import pandas as pd
from io import StringIO as StringIO
from .Utils.constants import *
import WaveAssistApiApp.Utils.utils as utils
import WaveAssistApiApp.Utils.validator as validator
from datetime import datetime, timedelta
import requests
import re

def fetch_config(request): ##Test Case Pending
    uid = request.GET.get('uid', '')
    try:
        user_object = User.objects.get(uid=uid)
    except:
        return ResponseParser.getParsedErrorMessage('User not authorized or found.')

    account_uid = request.GET.get('account_id', '')
    try:
        account_object = Account.objects.get(account_uid=account_uid, created_by_user=user_object )
    except:
        return ResponseParser.getParsedErrorMessage('Account not found, or not authorized.')

    config_dict = account_object.get_dict()
    return ResponseParser.getParsedSuccessMessage(config_dict, '200', 'Config fetched successfully')

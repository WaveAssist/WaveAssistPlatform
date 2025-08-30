from django.http import JsonResponse
from httplib2.auth import params
import json

from .models import *
from .Utils.responseParser import ResponseParser
from WaveAssistApiApp.Utils.MongoManager import MongoManager
import pandas as pd
from io import StringIO as StringIO
from .Utils.constants import *
import WaveAssistApiApp.Utils.utils as utils
from WaveAssistApiApp.Utils.utils import get_param
import WaveAssistApiApp.Utils.validator as validator
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
mongo_manager= MongoManager()


@require_POST
def upload_data_file(request):
    if 'file' not in request.FILES:
        return ResponseParser.getParsedErrorMessage('Missing file in request.')

    uploaded_file = request.FILES['file']
    file_name = uploaded_file.name
    data_type = file_name.split('.')[-1].lower()
    if data_type != 'csv':
        return ResponseParser.getParsedErrorMessage('Invalid file type. Only CSV files are allowed.')

    try:
        # Read and parse CSV into DataFrame
        csv_bytes = uploaded_file.read()
        csv_string = csv_bytes.decode('utf-8')
        df = pd.read_csv(StringIO(csv_string))

        # Convert DataFrame to records (list of dicts)
        data = df.to_json(orient='records')

        # Patch request.POST so set_data_for_key can work
        request.POST = request.POST.copy()
        request.POST['data_type'] = 'dataframe'
        request.POST['data'] = data

        return set_data_for_key(request)

    except Exception as e:
        utils.logger.error(f"❌ Error processing uploaded file: {str(e)}")
        return ResponseParser.getParsedErrorMessage('Error processing uploaded file.')

@require_GET
def fetch_data(request, uid, project_key, data_run_key, data_key):
    """Fetch data for a given key from the user's environment."""
    request_params = {
        'uid': uid,
        'project_key': project_key,
        'data_run_key': data_run_key,
        'data_key': data_key
    }
    request.GET = request.GET.copy()
    request.GET.update(request_params)
    response = fetch_data_for_key(request)
    ## process response, check for success
    if response.status_code != 200:
        utils.logger.error(f"❌ Error fetching data: {response.content.decode('utf-8')}")
        return ResponseParser.getParsedErrorMessage('Error fetching data.')
    try:
        response_data = json.loads(response.content.decode('utf-8'))
        if not response_data.get('success','0') == '1':
            utils.logger.error(f"❌ Error fetching data: {response_data.get('message')}")
            return ResponseParser.getParsedErrorMessage(response_data.get('message'))

        return JsonResponse(response_data.get('data'), status=200)
    except Exception as e:
        utils.logger.error(f"❌ Error parsing response: {str(e)}")
        return ResponseParser.getParsedErrorMessage('Error parsing response from data fetch API.')



@require_GET
def fetch_data_for_key(request):
    success, message, user_object, data_run_object = validator.validate_user_and_data_run(request, READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    data_run_key = get_param(request, 'data_run_key', None) or get_param(request, 'environment_key', None)
    data_key = get_param(request, 'data_key', '')
    
    # Handle run-based parameters
    run_based = str(get_param(request, 'run_based', '0'))
    run_id = get_param(request, 'run_id', None)
    
    # Modify data_key if run_based is enabled and run_id is provided
    if run_based == '1' and run_id:
        data_key = f"{data_key}_{run_id}"

    if not data_key:
        return ResponseParser.getParsedErrorMessage("Missing 'data_key' in request")

    try:
        db_name = utils.get_database_name(user_object)
        mongo_manager.database = mongo_manager.client[db_name]
        mongo_manager.collection = mongo_manager.database[data_run_key]

        data, data_type = mongo_manager.fetch_data_for_key(data_key)
        if data is None:
            return ResponseParser.getParsedErrorMessage('Data not found')

        if data_type in ["json", "dataframe"] and isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception as e:
                pass

        output_data = {'data': data, 'data_type': data_type}
        return ResponseParser.getParsedSuccessMessage(
            output_data,
            '200',
            'Data fetched successfully.'
        )
    except Exception as e:
        utils.logger.error(f"❌ Error in fetch_data_for_key API: {str(e)}")
        return ResponseParser.getParsedErrorMessage("Server error during data fetch")



@require_POST
def set_data_for_key(request):
    """Save data for a given key into the user's environment."""
    success, message, user_object, data_run_object = validator.validate_user_and_data_run(request, READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    data_run_key = get_param(request, 'data_run_key', None) or get_param(request, 'environment_key', None)
    data_key = get_param(request, 'data_key')
    data_type = get_param(request, 'data_type', 'json')
    data = get_param(request, 'data')
    
    # Handle run-based parameters
    run_based = str(get_param(request, 'run_based', '0'))
    run_id = get_param(request, 'run_id', None)
    
    # Modify data_key if run_based is enabled and run_id is provided
    if run_based == '1' and run_id:
        data_key = f"{data_key}_{run_id}"

    if not data_key or data_key=='':
        return ResponseParser.getParsedErrorMessage("Missing 'data_key' in request.")

    if data_type in ["json", "dataframe"] and isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            pass

    try:
        db_name = utils.get_database_name(user_object)
        mongo_manager.database = mongo_manager.client[db_name]
        mongo_manager.collection = mongo_manager.database[data_run_key]

        success = mongo_manager.insert_or_replace_data_for_key(data_key, data, data_type)
        if not success:
            return ResponseParser.getParsedErrorMessage('Something went wrong while saving data.')

        return ResponseParser.getParsedSuccessMessage(
            {'data_key': data_key},
            '200',
            'Data saved successfully.'
        )
    except Exception as e:
        utils.logger.error(f"❌ Exception in set_data_for_key: {str(e)}")
        return ResponseParser.getParsedErrorMessage('Server error during data save.')

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
def fetch_data_for_key(request):
    success, message, user_object, data_run_object = validator.validate_user_and_data_run(request, READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    data_run_key = get_param(request, 'data_run_key') or get_param(request, 'environment_key')
    data_key = get_param(request, 'data_key', '')

    if not data_key:
        return ResponseParser.getParsedErrorMessage("Missing 'data_key' in request")

    try:
        db_name = utils.get_database_name(user_object)
        mongo_manager.database = mongo_manager.client[db_name]
        mongo_manager.collection = mongo_manager.database[data_run_key]

        data, data_type = mongo_manager.fetch_data_for_key(data_key)

        if data is None:
            return ResponseParser.getParsedErrorMessage('Data not found')
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

    data_run_key = get_param(request, 'data_run_key') or get_param(request, 'environment_key')
    data_key = get_param(request, 'data_key')
    data_type = get_param(request, 'data_type', 'json')
    data = get_param(request, 'data')

    if not data_key or data_key=='':
        return ResponseParser.getParsedErrorMessage("Missing 'data_key' in request.")

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


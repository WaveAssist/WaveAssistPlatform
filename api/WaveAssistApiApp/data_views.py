from .models import *
from .Utils.responseParser import ResponseParser
from WaveAssistApiApp.Utils.MongoManager import MongoManager
import pandas as pd
from io import StringIO as StringIO
from .Utils.constants import *
import WaveAssistApiApp.Utils.utils as utils
import WaveAssistApiApp.Utils.validator as validator

mongo_manager= MongoManager()


##ToDo: Write tests for all.

def upload_data_file(request):
    uploaded_file = request.FILES['file']
    data_type = uploaded_file.name.split('.')[-1].lower()
    csv_data = uploaded_file.read().decode('utf-8')
    if data_type != 'csv':
        return ResponseParser.getParsedErrorMessage('Invalid file type. Only CSV files are allowed.')

    ##call set_data_for_key api with request having csv_data
    request.POST = request.POST.copy()
    request.POST['data_type'] = 'csv'
    request.POST['csv_data'] = csv_data
    return set_data_for_key(request)


def download_data_file(request):
    ##Call fetch_data_for_key api with output_data_type as csv
    data_key = request.POST.get('data_key', '')
    request.POST = request.POST.copy()
    request.POST['output_data_type'] = 'csv'
    csv_response =  fetch_data_for_key(request)
    if csv_response.status_code != 200:
        ##Get csv string from response
        csv_string = csv_response.content.decode('utf-8')
        file_name = 'download_' + data_key
        return ResponseParser.getHTTPResponseForCSV(csv_string, file_name)


def fetch_data_for_key(request):
    success, message, user_object, data_run_object = validator.validate_user_and_data_run(request, READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)
    data_run_key = request.POST.get('data_run_key', '')
    data_key = request.POST.get('data_key', '')

    output_data_type = request.POST.get('output_data_type', 'json')
    if output_data_type not in ['json', 'csv']:
        return ResponseParser.getParsedErrorMessage('Invalid data type')

    mongo_manager.collection = mongo_manager.database[data_run_key]
    data_df = mongo_manager.fetch_data_as_dataframe(data_key)
    if data_df is None:
        data_df = pd.DataFrame()

    if output_data_type == 'csv':
        csv_string = data_df.to_csv(index=False)
        return ResponseParser.getBasicHttpResponse(csv_string)
    elif output_data_type == 'json':
        data_array = data_df.to_dict(orient='records')
        output_dictionary = {data_key: data_array}
        return ResponseParser.getParsedSuccessMessage(output_dictionary, '200', 'Data fetched successfully.')


def set_data_for_key(request):
    success, message, user_object , data_run_object = validator.validate_user_and_data_run(request, READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    data_run_key = request.POST.get('data_run_key', '')
    data_key = request.POST.get('data_key', '')

    data_type = request.POST.get('data_type', 'json')
    if data_type not in ['json', 'csv']:
        return ResponseParser.getParsedErrorMessage('Invalid data type')

    if data_type == 'csv':
        try:
            csv_data = request.POST.get('csv_data', '')
            pd_data = pd.read_csv(StringIO(csv_data))
        except Exception as e:
            return ResponseParser.getParsedErrorMessage('Invalid csv data')
    else:
        try:
            json_data = str(request.POST.get('json_data', ''))
            pd_data = pd.read_json(json_data)
        except Exception as e:
            return ResponseParser.getParsedErrorMessage('Invalid json data')

    try:
        ##Remove row_number column in pd_data if it exists
        pd_data = pd_data.drop('row_number', axis=1, errors='ignore')

        ##Save in mongo db

        mongo_manager.collection = mongo_manager.database[data_run_key]
        success = mongo_manager.replace_data_as_dataframe(data_key, pd_data)
        if not success:
            return ResponseParser.getParsedErrorMessage('Something went wrong with data saving')

        ##Response
        output_dictionary = {'data_key': data_key}
        return ResponseParser.getParsedSuccessMessage(output_dictionary, '200',
                                                        'Data saved successfully.')
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Something went wrong with data saving: ' + str(e))





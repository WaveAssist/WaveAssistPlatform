#Import Libraries. models, views, functions, etc.

from django.shortcuts import render, HttpResponse, HttpResponseRedirect
import json
import csv
from django.http import JsonResponse
from django.utils.text import slugify
import csv
from django.http import HttpResponse

class ResponseParser(object):

    @classmethod
    def getParsedErrorMessage(cls, string, error_code='E01'):
        return cls.getJsonResponseForDictionary({'success':'0', 'message':string, 'status': error_code})

    @classmethod
    def getParsedSuccessMessage(cls, data, status, message):
        return cls.getJsonResponseForDictionary({'success':'1', 'data':data, 'status':status, 'message':message})

    @classmethod
    def getJsonResponseForDictionary(cls ,dictionary):
        return JsonResponse(dictionary)

    @classmethod
    def getBasicHttpResponse(cls, message):
        return HttpResponse(message)

    @classmethod
    def getHTTPResponseForCSV(cls, csv_string, file_name="csv_download"):
        # Create a response with the CSV content
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{slugify(file_name)}.csv"'

        # Write the CSV data to the response using csv.reader to handle commas within quotes
        writer = csv.writer(response)
        reader = csv.reader(csv_string.splitlines())  # Use csv.reader to handle the CSV parsing
        for row in reader:
            if row:  # This check ensures that empty lines are not processed
                writer.writerow(row)
        return response

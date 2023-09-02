#Import Libraries. models, views, functions, etc.

from django.shortcuts import render, HttpResponse, HttpResponseRedirect
import json
import csv
from django.http import JsonResponse
from django.utils.text import slugify


class ResponseParser(object):

    @classmethod
    def getParsedErrorMessage(cls, string, error_code='E01'):
        return cls.getHTTPResponseForDictionary({'success':'0', 'message':string, 'status': error_code})

    @classmethod
    def getParsedSuccessMessage(cls, data, status, message):
        return cls.getHTTPResponseForDictionary({'success':'1', 'data':data, 'status':status, 'message':message})

    @classmethod
    def getHTTPResponseForDictionary(cls ,dictionary):
        return HttpResponse(json.dumps(dictionary, cls=json.JSONEncoder, indent=2), content_type="application/json")

    @classmethod
    def getHTTPResponseForCSV(cls, csv_string, file_name="csv_download"):
        # Create a response with the CSV content
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{slugify(file_name)}.csv"'
        # Write the CSV data to the response
        writer = csv.writer(response)
        lines = csv_string.split("\n")
        for line in lines:
            row = line.split(",")
            writer.writerow(row)
        return response

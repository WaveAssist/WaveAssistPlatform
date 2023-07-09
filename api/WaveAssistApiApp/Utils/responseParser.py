#Import Libraries. models, views, functions, etc.

from django.shortcuts import render, HttpResponse, HttpResponseRedirect
import json

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

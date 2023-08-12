# import os
# import requests
# import csv
# import pandas as pd
# from io import StringIO as StringIO
#
#
# def test():
#     instrument_url = "https://api.kite.trade/instruments"
#     # Retrieve the CSV dump
#     response = requests.get(instrument_url)
#     if response.status_code == 200:
#         # Convert the response content to a string
#         content_str = response.text
#         instruments_df = pd.read_csv(StringIO(content_str))
#         return instruments_df
#     else:
#         print("Failed to retrieve data. Status code:", response.status_code)
#         return None
#
#

import boto3
import pytz
import time
from datetime import datetime, timedelta

# Initialize the CloudWatch Logs client
# client = boto3.client('logs',
#                         aws_access_key_id='REMOVED_CREDENTIAL',
#                         aws_secret_access_key='REMOVED_CREDENTIAL',
#                       region_name='us-east-1')  # Replace 'your-region' with the appropriate AWS region
# # Parameters
# log_group_name = '/ecs/WaveAssistWorkerTasks'
# project_key = 'project_key'
#
# # Define the query string
# query_string = f"""
# fields @timestamp, @message
# | filter extra.project_key = "{project_key}"
# | sort @timestamp desc
# | limit 10
# """
#
# # Define start and end time
# start_time = int((datetime.now(pytz.UTC) - timedelta(hours=24)).timestamp())
# end_time = int((datetime.now(pytz.UTC) + timedelta(hours=12)).timestamp())
#
# # Start the query
# start_query_response = client.start_query(
#     logGroupName=log_group_name,
#     startTime=start_time,
#     endTime=end_time,
#     queryString=query_string
# )
#
# query_id = start_query_response['queryId']
# # Poll for query results
# response = None
# while True:
#     response = client.get_query_results(queryId=query_id)
#     if response['status'] in ['Complete', 'Failed', 'Cancelled']:
#         break
#     print("Query in progress...")
#     time.sleep(1)  # Wait before polling again
#
# # Process the results
# if response['status'] == 'Complete':
#     results = response['results']
#     print(f"Number of logs fetched: {len(results)}")
#     for result in results:
#         log_data = {field['field']: field['value'] for field in result}
#         print(log_data)
# else:
#     print(f"Query failed with status: {response['status']}")
print("Done")
#

import boto3
import time

session = boto3.Session(profile_name='prometheus', region_name='ap-south-1')
client = session.client('logs')
log_group = '/aws/lambda/prometheus-web'

# Get latest streams
streams = client.describe_log_streams(
    logGroupName=log_group,
    orderBy='LastEventTime',
    descending=True,
    limit=3
)

for stream in streams['logStreams']:
    print(f"\n--- Stream: {stream['logStreamName']} ---")
    events = client.get_log_events(
        logGroupName=log_group,
        logStreamName=stream['logStreamName'],
        limit=20
    )
    for event in events['events']:
        print(event['message'].strip())

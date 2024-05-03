import boto3
import pandas as pd
import Credentials as cd
import os.path

# Function to flatten tags
def flatten_tags(tags):
    flattened_tags = {}
    for tag in tags:
        flattened_tags[tag['Key']] = tag['Value']
    return flattened_tags

# Check if CSV file exists
filename = 'aws_instance_inventory_combined.csv'
file_exists = os.path.isfile(filename)

# Initialize DataFrame to store instances
df_combined = pd.DataFrame()

# Loop through each account
for account_id, credentials in cd.AccountDetails.items():
    # Extract credentials
    aws_access_key_id = credentials['aws_access_key_id']
    aws_secret_access_key = credentials['aws_secret_access_key']

    # Prompt user to enter the region
    regionName = input(f"Enter the AWS region for account {credentials['Account']}: ")

    # Connect to EC2 for the current region
    ec2_client = boto3.client('ec2',
                              aws_access_key_id=aws_access_key_id,
                              aws_secret_access_key=aws_secret_access_key,
                              region_name=regionName)

    # Get instances
    response = ec2_client.describe_instances()

    instances = []

    # Extract instance information
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            internal_ip = instance.get('PrivateIpAddress', 'N/A')
            instance_status = instance['State']['Name']
            instance_name = ''
            for tag in instance.get('Tags', []):
                if tag['Key'] == 'Name':
                    instance_name = tag['Value']
                    break
            instance_details = {
                'AccountName': credentials['Account'],
                'AccountId': account_id,
                'InstanceName': instance_name,  # Modify this to get the instance name if available
                'InstanceId': instance['InstanceId'],
                'Region': regionName,
                'InternalIpAddress': internal_ip,
                'PublicIP': instance.get('PublicIpAddress','N/A'),
                'InstanceStatus': instance_status,
                **flatten_tags(instance.get('Tags', []))  # Flatten tags and unpack as separate columns
            }
            instances.append(instance_details)

    # Convert instances to DataFrame
    df = pd.DataFrame(instances)

    # Combine DataFrame with existing data
    df_combined = pd.concat([df_combined, df], ignore_index=True)

# Reorder columns alphabetically
df_combined = df_combined.reindex(sorted(df_combined.columns), axis=1)

# Append new data to the existing CSV file or create a new one
if file_exists and os.stat(filename).st_size != 0:
    # If the file exists and contains data, read existing data and columns
    existing_data = pd.read_csv(filename)
    existing_columns = existing_data.columns.tolist()

    # Find new columns
    new_columns = [col for col in df_combined.columns if col not in existing_columns]

    # Add missing columns to existing data
    for column in new_columns:
        existing_data[column] = ''

    # Append new data to existing data
    df_combined = pd.concat([existing_data, df_combined], ignore_index=True)

# Write combined DataFrame to CSV
df_combined.to_csv(filename, index=False)

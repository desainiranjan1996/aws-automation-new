import boto3
import pandas as pd
import Credentials as cd
import os.path
from botocore.exceptions import ClientError

# Function to flatten tags
def flatten_tags(tags):
    flattened_tags = {}
    for tag in tags:
        flattened_tags[tag['Key']] = tag['Value']
    return flattened_tags

# Check if CSV file exists
filename = 'aws_s3_bucket_inventory.csv'
file_exists = os.path.isfile(filename)

# Initialize DataFrame to store buckets
df_combined = pd.DataFrame()

# Loop through each account
for account_id, credentials in cd.AccountDetails.items():
    # Extract credentials
    aws_access_key_id = credentials['aws_access_key_id']
    aws_secret_access_key = credentials['aws_secret_access_key']

    # Connect to S3
    s3_client = boto3.client('s3',
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key)

    # Get list of buckets
    response = s3_client.list_buckets()

    buckets = []

    # Extract bucket information
    for bucket in response['Buckets']:
        bucket_name = bucket['Name']
        creation_date = bucket['CreationDate']

        try:
            # Fetch bucket tags
            tags_response = s3_client.get_bucket_tagging(Bucket=bucket_name)
            tags = tags_response.get('TagSet', [])
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchTagSet':
                tags = []  # Set empty list if no tags found
            else:
                raise  # Raise exception if it's not NoSuchTagSet

        bucket_details = {
            'AccountName': credentials['Account'],
            'AccountId': account_id,
            'BucketName': bucket_name,
            'CreationDate': creation_date,
            **flatten_tags(tags)  # Flatten tags and unpack as separate columns
        }
        buckets.append(bucket_details)

    # Convert buckets to DataFrame
    df = pd.DataFrame(buckets)

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

import boto3
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
REGION = "us-east-1"

def get_aws_costs():
    try:
        client = boto3.client(
            'ce',
            region_name=REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        end = datetime.today().strftime('%Y-%m-%d')
        start = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
        response = client.get_cost_and_usage(
            TimePeriod={'Start': start, 'End': end},
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )
        return response['ResultsByTime']
    except Exception as e:
        print(f"AWS Error: {e}, falling back to mock data")
        return None

def load_mock_data():
    with open('mock_data.json') as f:
        return json.load(f)['resources']


def list_ec2_instances():
    """List all EC2 instances across the configured region."""
    try:
        ec2 = boto3.client(
            'ec2',
            region_name=REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        response = ec2.describe_instances()
        instances = []
        for reservation in response['Reservations']:
            for inst in reservation['Instances']:
                name = ''
                for tag in inst.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break
                instances.append({
                    'InstanceId': inst['InstanceId'],
                    'InstanceType': inst['InstanceType'],
                    'State': inst['State']['Name'],
                    'Region': REGION,
                    'Name': name,
                    'LaunchTime': inst.get('LaunchTime', '').isoformat() if inst.get('LaunchTime') else ''
                })
        return instances
    except Exception as e:
        print(f"EC2 List Error: {e}")
        return None


def stop_ec2_instance(instance_id):
    """Stop a running EC2 instance."""
    try:
        ec2 = boto3.client(
            'ec2',
            region_name=REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        response = ec2.stop_instances(InstanceIds=[instance_id])
        new_state = response['StoppingInstances'][0]['CurrentState']['Name']
        return {'success': True, 'state': new_state}
    except Exception as e:
        print(f"EC2 Stop Error: {e}")
        return {'success': False, 'error': str(e)}


def start_ec2_instance(instance_id):
    """Start a stopped EC2 instance."""
    try:
        ec2 = boto3.client(
            'ec2',
            region_name=REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        response = ec2.start_instances(InstanceIds=[instance_id])
        new_state = response['StartingInstances'][0]['CurrentState']['Name']
        return {'success': True, 'state': new_state}
    except Exception as e:
        print(f"EC2 Start Error: {e}")
        return {'success': False, 'error': str(e)}


def terminate_ec2_instance(instance_id):
    """Terminate an EC2 instance permanently."""
    try:
        ec2 = boto3.client(
            'ec2',
            region_name=REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        response = ec2.terminate_instances(InstanceIds=[instance_id])
        new_state = response['TerminatingInstances'][0]['CurrentState']['Name']
        return {'success': True, 'state': new_state}
    except Exception as e:
        print(f"EC2 Terminate Error: {e}")
        return {'success': False, 'error': str(e)}
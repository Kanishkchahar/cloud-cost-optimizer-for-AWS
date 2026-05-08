import boto3
import logging
from config import AWS_REGION

logger = logging.getLogger(__name__)

def get_active_resources(region=None):
    if not region:
        region = AWS_REGION
        
    infrastructure = []
    try:
        ec2 = boto3.client('ec2', region_name=region)
        
        # 1. ALL EC2 instances (running and stopped)
        instances = ec2.describe_instances()
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                name = "Unnamed"
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break
                
                state = instance['State']['Name']
                infrastructure.append({
                    "type": "EC2",
                    "id": instance['InstanceId'],
                    "detail": f"{instance['InstanceType']} - {name}",
                    "region": region,
                    "status": state
                })

        
        # 2. ALL EBS volumes
        volumes = ec2.describe_volumes()
        for vol in volumes['Volumes']:
            infrastructure.append({
                "type": "EBS",
                "id": vol['VolumeId'],
                "detail": f"{vol['Size']}GB {vol['VolumeType']}",
                "region": region,
                "status": vol['State']  # e.g., 'in-use' or 'available'
            })
            
        # 3. ALL RDS Instances
        try:
            rds = boto3.client('rds', region_name=region)
            db_instances = rds.describe_db_instances()
            for db in db_instances.get('DBInstances', []):
                db_status = db['DBInstanceStatus']
                infrastructure.append({
                    "type": "RDS",
                    "id": db['DBInstanceIdentifier'],
                    "detail": f"{db['DBInstanceClass']} ({db['Engine']})",
                    "region": region,
                    "status": db_status
                })

        except Exception as e:
            logger.warning(f"Could not fetch RDS instances: {e}")
            
    except Exception as e:
        logger.error(f"Failed to fetch infrastructure: {e}")
        
    return infrastructure

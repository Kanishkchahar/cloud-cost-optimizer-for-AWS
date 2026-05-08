import boto3
import logging
from botocore.exceptions import ClientError
from config import AWS_REGION

logger = logging.getLogger(__name__)

def perform_action(action, resource_type, resource_id):
    """Perform a specific action on a resource."""
    try:
        ec2 = boto3.client("ec2", region_name=AWS_REGION)
        
        # EC2 Actions
        if "EC2" in resource_type:
            if action == "stop":
                ec2.stop_instances(InstanceIds=[resource_id])
                logger.info(f"Stopped EC2 instance: {resource_id}")
                return True, f"Successfully requested stop for {resource_id}"
            elif action == "start":
                ec2.start_instances(InstanceIds=[resource_id])
                logger.info(f"Started EC2 instance: {resource_id}")
                return True, f"Successfully requested start for {resource_id}"
            elif action == "restart":
                ec2.reboot_instances(InstanceIds=[resource_id])
                logger.info(f"Rebooted EC2 instance: {resource_id}")
                return True, f"Successfully requested reboot for {resource_id}"
            elif action == "delete":
                ec2.terminate_instances(InstanceIds=[resource_id])
                logger.info(f"Terminated EC2 instance: {resource_id}")
                return True, f"Successfully requested termination for {resource_id}"

        # EBS Actions
        elif "EBS" in resource_type:
            if action == "delete":
                ec2.delete_volume(VolumeId=resource_id)
                logger.info(f"Deleted EBS volume: {resource_id}")
                return True, f"Successfully deleted volume {resource_id}"

        # EIP Actions
        elif "ElasticIP" in resource_type or "EIP" in resource_type:
            if action == "delete":
                response = ec2.describe_addresses(PublicIps=[resource_id])
                if response["Addresses"]:
                    allocation_id = response["Addresses"][0].get("AllocationId")
                    if allocation_id:
                        ec2.release_address(AllocationId=allocation_id)
                    else:
                        ec2.release_address(PublicIp=resource_id)
                    logger.info(f"Released EIP: {resource_id}")
                    return True, f"Successfully released IP {resource_id}"
                return False, f"Could not find Elastic IP: {resource_id}"

        # Snapshot Actions
        elif "Snapshot" in resource_type:
            if action == "delete":
                ec2.delete_snapshot(SnapshotId=resource_id)
                logger.info(f"Deleted Snapshot: {resource_id}")
                return True, f"Successfully deleted snapshot {resource_id}"
                
        # RDS Actions
        elif "RDS" in resource_type:
            rds = boto3.client("rds", region_name=AWS_REGION)
            if action == "stop":
                rds.stop_db_instance(DBInstanceIdentifier=resource_id)
                return True, f"Successfully requested stop for RDS {resource_id}"
            elif action == "start":
                rds.start_db_instance(DBInstanceIdentifier=resource_id)
                return True, f"Successfully requested start for RDS {resource_id}"
            elif action == "restart":
                rds.reboot_db_instance(DBInstanceIdentifier=resource_id)
                return True, f"Successfully requested reboot for RDS {resource_id}"
            elif action == "delete":
                rds.delete_db_instance(DBInstanceIdentifier=resource_id, SkipFinalSnapshot=True)
                return True, f"Successfully requested deletion for RDS {resource_id}"

        return False, f"Action '{action}' not supported for type '{resource_type}'"

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        logger.error(f"AWS Error on {action} {resource_id}: {error_code} - {error_msg}")
        
        # User-friendly mappings for common AWS errors
        friendly_msg = error_msg
        if "IncorrectInstanceState" in error_code:
            friendly_msg = f"Resource is not in a valid state to be {action}ped right now. It might already be {action}ped."
        elif "InvalidInstanceID" in error_code:
            friendly_msg = "Invalid instance ID provided. It may have already been terminated."
        elif "InvalidVolume.NotFound" in error_code:
            friendly_msg = "Volume could not be found. It may have already been deleted."
            
        return False, friendly_msg
        
    except Exception as e:
        logger.error(f"Action {action} failed on {resource_id}: {e}")
        return False, str(e)

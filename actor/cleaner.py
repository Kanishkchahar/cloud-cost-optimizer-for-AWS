import boto3
import logging
from config import AWS_REGION
from db.database import update_resource_status

logger = logging.getLogger(__name__)


def delete_ebs_volume(volume_id, dry_run=True):
    """Delete an EBS volume. Defaults to dry-run."""
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    if dry_run:
        print(f"  [DRY RUN] Would delete EBS volume: {volume_id}")
        return True
    try:
        ec2.delete_volume(VolumeId=volume_id)
        update_resource_status(volume_id, "deleted")
        print(f"  ✅ Deleted EBS volume: {volume_id}")
        logger.info(f"Deleted EBS volume: {volume_id}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to delete {volume_id}: {e}")
        logger.error(f"Failed to delete EBS volume {volume_id}: {e}")
        return False


def release_eip(public_ip, dry_run=True):
    """Release an Elastic IP. Defaults to dry-run."""
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    if dry_run:
        print(f"  [DRY RUN] Would release Elastic IP: {public_ip}")
        return True
    try:
        response = ec2.describe_addresses(PublicIps=[public_ip])
        allocation_id = response["Addresses"][0]["AllocationId"]
        ec2.release_address(AllocationId=allocation_id)
        update_resource_status(public_ip, "deleted")
        print(f"  ✅ Released Elastic IP: {public_ip}")
        logger.info(f"Released Elastic IP: {public_ip}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to release {public_ip}: {e}")
        logger.error(f"Failed to release EIP {public_ip}: {e}")
        return False


def delete_snapshot(snapshot_id, dry_run=True):
    """Delete an EBS snapshot. Defaults to dry-run."""
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    if dry_run:
        print(f"  [DRY RUN] Would delete snapshot: {snapshot_id}")
        return True
    try:
        ec2.delete_snapshot(SnapshotId=snapshot_id)
        update_resource_status(snapshot_id, "deleted")
        print(f"  ✅ Deleted snapshot: {snapshot_id}")
        logger.info(f"Deleted snapshot: {snapshot_id}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to delete {snapshot_id}: {e}")
        logger.error(f"Failed to delete snapshot {snapshot_id}: {e}")
        return False


def cleanup_resource(finding, dry_run=True):
    """Route cleanup to the correct handler based on resource type."""
    handlers = {
        "EBS": lambda f: delete_ebs_volume(f["id"], dry_run),
        "ElasticIP": lambda f: release_eip(f["id"], dry_run),
        "Snapshot": lambda f: delete_snapshot(f["id"], dry_run),
    }
    handler = handlers.get(finding["type"])
    if handler:
        return handler(finding)
    else:
        logger.warning(f"No cleanup handler for resource type: {finding['type']}")
        return False

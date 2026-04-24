import boto3
import logging
from config import AWS_REGION, STOPPED_EC2_EBS_ESTIMATE

logger = logging.getLogger(__name__)


def scan_stopped_ec2():
    """Find EC2 instances that are in a stopped state. Uses pagination."""
    findings = []
    try:
        ec2 = boto3.client("ec2", region_name=AWS_REGION)
        paginator = ec2.get_paginator("describe_instances")
        page_iterator = paginator.paginate(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]
        )

        for page in page_iterator:
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    instance_id = instance["InstanceId"]
                    instance_type = instance["InstanceType"]

                    # Get name tag if it exists
                    name = "unnamed"
                    for tag in instance.get("Tags", []):
                        if tag["Key"] == "Name":
                            name = tag["Value"]
                            break

                    findings.append({
                        "type": "EC2",
                        "id": instance_id,
                        "detail": f"Stopped instance '{name}' ({instance_type})",
                        "waste_usd": STOPPED_EC2_EBS_ESTIMATE,
                        "region": AWS_REGION
                    })

        logger.info(f"EC2 scan complete — {len(findings)} stopped instances found.")
    except Exception as e:
        logger.error(f"EC2 scan failed: {e}")

    return findings

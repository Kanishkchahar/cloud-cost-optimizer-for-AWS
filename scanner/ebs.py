import boto3
import logging
from config import AWS_REGION, EBS_COST_PER_GB

logger = logging.getLogger(__name__)


def scan_unattached_ebs(region=None):
    """Find EBS volumes that are not attached to any instance. Uses pagination."""
    if not region:
        region = AWS_REGION
        
    findings = []
    try:
        ec2 = boto3.client("ec2", region_name=region)
        paginator = ec2.get_paginator("describe_volumes")
        page_iterator = paginator.paginate(
            Filters=[{"Name": "status", "Values": ["available"]}]
        )

        for page in page_iterator:
            for vol in page["Volumes"]:
                size_gb = vol["Size"]
                vol_type = vol.get("VolumeType", "gp2")
                monthly_cost = size_gb * EBS_COST_PER_GB

                findings.append({
                    "type": "EBS",
                    "id": vol["VolumeId"],
                    "detail": f"{size_gb}GB unattached {vol_type} volume",
                    "waste_usd": round(monthly_cost, 2),
                    "region": region
                })


        logger.info(f"EBS scan complete — {len(findings)} unattached volumes found.")
    except Exception as e:
        logger.error(f"EBS scan failed: {e}")

    return findings

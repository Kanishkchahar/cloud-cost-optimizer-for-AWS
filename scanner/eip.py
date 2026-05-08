import boto3
import logging
from config import AWS_REGION, EIP_MONTHLY_COST

logger = logging.getLogger(__name__)


def scan_unused_eips(region=None):
    """Find Elastic IPs not associated with any resource."""
    if not region:
        region = AWS_REGION
        
    findings = []
    try:
        ec2 = boto3.client("ec2", region_name=region)
        response = ec2.describe_addresses()

        for addr in response["Addresses"]:
            if "AssociationId" not in addr:
                findings.append({
                    "type": "ElasticIP",
                    "id": addr["PublicIp"],
                    "detail": "Unassociated Elastic IP",
                    "waste_usd": EIP_MONTHLY_COST,
                    "region": region
                })


        logger.info(f"EIP scan complete — {len(findings)} unused Elastic IPs found.")
    except Exception as e:
        logger.error(f"EIP scan failed: {e}")

    return findings

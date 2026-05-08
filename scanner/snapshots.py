import boto3
import logging
from datetime import datetime, timezone, timedelta
from config import AWS_REGION, SNAPSHOT_AGE_DAYS, SNAPSHOT_COST_PER_GB

logger = logging.getLogger(__name__)


def scan_old_snapshots(region=None):
    """Find EBS snapshots older than the configured threshold. Uses pagination."""
    if not region:
        region = AWS_REGION
        
    findings = []
    try:
        ec2 = boto3.client("ec2", region_name=region)
        paginator = ec2.get_paginator("describe_snapshots")
        page_iterator = paginator.paginate(OwnerIds=["self"])

        cutoff = datetime.now(timezone.utc) - timedelta(days=SNAPSHOT_AGE_DAYS)

        for page in page_iterator:
            for snap in page["Snapshots"]:
                if snap["StartTime"] < cutoff:
                    size_gb = snap["VolumeSize"]
                    monthly_cost = size_gb * SNAPSHOT_COST_PER_GB
                    age_days = (datetime.now(timezone.utc) - snap["StartTime"]).days

                    findings.append({
                        "type": "Snapshot",
                        "id": snap["SnapshotId"],
                        "detail": f"{size_gb}GB snapshot, {age_days} days old ({snap['StartTime'].date()})",
                        "waste_usd": round(monthly_cost, 2),
                        "region": region
                    })


        logger.info(f"Snapshot scan complete — {len(findings)} old snapshots found.")
    except Exception as e:
        logger.error(f"Snapshot scan failed: {e}")

    return findings

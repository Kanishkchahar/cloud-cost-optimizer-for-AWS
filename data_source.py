"""
data_source.py — Single toggle between demo data and real AWS data.

HOW TO SWITCH TO REAL AWS DATA:
    1. Set USE_DEMO_DATA = False (line below)
    2. Run: aws configure (to set your credentials)
    3. Run: python main.py --scan

That's it. Everything else stays the same.
"""

import os
from dotenv import load_dotenv
load_dotenv()

# ============================================================
#  TOGGLE THIS IN .env FILE:  USE_DEMO_DATA=True / False
# ============================================================
USE_DEMO_DATA = os.getenv("USE_DEMO_DATA", "True").lower() in ("true", "1", "yes")
# ============================================================


# ----- DEMO DATA (all fake resources are defined here) -----

DEMO_RESOURCES = [
    # EBS Volumes — unattached
    {
        "type": "EBS",
        "id": "vol-0a3b7c9d2e1f4a5b6",
        "detail": "100GB unattached gp2 volume",
        "waste_usd": 10.00,
        "region": "us-east-1"
    },
    {
        "type": "EBS",
        "id": "vol-0f1e2d3c4b5a6978e",
        "detail": "250GB unattached gp3 volume",
        "waste_usd": 25.00,
        "region": "us-east-1"
    },
    {
        "type": "EBS",
        "id": "vol-0c8d7e6f5a4b3c2d1",
        "detail": "50GB unattached io1 volume",
        "waste_usd": 6.25,
        "region": "us-east-1"
    },

    # EC2 Instances — stopped
    {
        "type": "EC2",
        "id": "i-0a1b2c3d4e5f67890",
        "detail": "Stopped instance 'dev-server' (t3.large)",
        "waste_usd": 5.00,
        "region": "us-east-1"
    },
    {
        "type": "EC2",
        "id": "i-0b2c3d4e5f6a7b8c9",
        "detail": "Stopped instance 'staging-api' (m5.xlarge)",
        "waste_usd": 5.00,
        "region": "us-east-1"
    },
    {
        "type": "EC2",
        "id": "i-0d4e5f6a7b8c9d0e1",
        "detail": "Stopped instance 'test-worker' (c5.2xlarge)",
        "waste_usd": 5.00,
        "region": "us-east-1"
    },

    # Elastic IPs — unassociated
    {
        "type": "ElasticIP",
        "id": "52.14.88.203",
        "detail": "Unassociated Elastic IP",
        "waste_usd": 3.60,
        "region": "us-east-1"
    },
    {
        "type": "ElasticIP",
        "id": "3.22.147.91",
        "detail": "Unassociated Elastic IP",
        "waste_usd": 3.60,
        "region": "us-east-1"
    },

    # Snapshots — old
    {
        "type": "Snapshot",
        "id": "snap-0a1b2c3d4e5f67890",
        "detail": "100GB snapshot, 95 days old (2025-01-15)",
        "waste_usd": 5.00,
        "region": "us-east-1"
    },
    {
        "type": "Snapshot",
        "id": "snap-0b2c3d4e5f6a7b8c9",
        "detail": "200GB snapshot, 180 days old (2024-10-20)",
        "waste_usd": 10.00,
        "region": "us-east-1"
    },
    {
        "type": "Snapshot",
        "id": "snap-0c3d4e5f6a7b8c9d0",
        "detail": "50GB snapshot, 60 days old (2025-02-18)",
        "waste_usd": 2.50,
        "region": "us-east-1"
    },
    {
        "type": "Snapshot",
        "id": "snap-0e5f6a7b8c9d0e1f2",
        "detail": "75GB snapshot, 120 days old (2024-12-22)",
        "waste_usd": 3.75,
        "region": "us-east-1"
    },
]


# ----- DATA SOURCE FUNCTIONS -----

def get_findings():
    """
    Returns a list of wasted resource findings.
    
    - If USE_DEMO_DATA is True:  returns the demo resources above (no AWS needed)
    - If USE_DEMO_DATA is False: calls real AWS scanners (requires credentials)
    """
    if USE_DEMO_DATA:
        return _get_demo_findings()
    else:
        return _get_real_findings()


def _get_demo_findings():
    """Return demo data with slight randomization for realistic variance."""
    import random
    findings = []
    num = random.randint(6, len(DEMO_RESOURCES))
    selected = random.sample(DEMO_RESOURCES, num)
    for r in selected:
        finding = dict(r)
        finding["waste_usd"] = round(r["waste_usd"] * random.uniform(0.8, 1.3), 2)
        findings.append(finding)
    return findings


def _get_real_findings():
    """Call real AWS scanners. Requires valid AWS credentials."""
    import boto3
    import logging
    from botocore.exceptions import NoCredentialsError, ClientError
    from config import AWS_REGION
    
    logger = logging.getLogger(__name__)

    try:
        # Validate credentials first
        sts = boto3.client('sts', region_name=AWS_REGION)
        sts.get_caller_identity()
    except (NoCredentialsError, ClientError) as e:
        logger.error(f"AWS Credential validation failed: {e}")
        return []

    from scanner.ebs import scan_unattached_ebs
    from scanner.eip import scan_unused_eips
    from scanner.ec2 import scan_stopped_ec2
    from scanner.snapshots import scan_old_snapshots

    findings = []
    findings += scan_unattached_ebs()
    findings += scan_unused_eips()
    findings += scan_stopped_ec2()
    findings += scan_old_snapshots()
    return findings


def get_demo_ai_advice():
    """Returns pre-written AI advice for demo mode (no Ollama needed)."""
    return """## Recommended Actions

**1. Delete Immediately (No Risk)**
- Unattached EBS volumes (vol-0a3b7c9d, vol-0f1e2d3c, vol-0c8d7e6f) — These have no attachments and are generating pure waste.
- Unassociated Elastic IPs (52.14.88.203, 3.22.147.91) — Not linked to any resource.

**2. Review Before Deleting**
- Old snapshots — Verify no active AMIs or restore points depend on them before deletion.
- Stopped EC2 instances — Check if any team members need these for future use.

**3. Estimated Savings**
- Immediate: ~$48/month from EBS + EIPs
- After review: ~$80/month total ($956/year)

**4. Additional Recommendations**
- Set up lifecycle policies to auto-delete snapshots older than 30 days
- Create CloudWatch alarms for stopped instances exceeding 7 days
- Consider using EBS snapshot archiving for long-term storage (75% cheaper)"""


def get_ai_advice(report_text):
    """
    Get AI advice — uses demo response or real Ollama based on USE_DEMO_DATA flag.
    """
    if USE_DEMO_DATA:
        return get_demo_ai_advice()
    else:
        from analyzer.ai_advisor import get_advice
        return get_advice(report_text)

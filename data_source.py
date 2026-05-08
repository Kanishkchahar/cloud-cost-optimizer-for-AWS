import logging
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from config import AWS_REGION
from scanner.ebs import scan_unattached_ebs
from scanner.eip import scan_unused_eips
from scanner.ec2 import scan_stopped_ec2, scan_idle_ec2
from scanner.snapshots import scan_old_snapshots
from scanner.s3 import scan_s3_waste
from scanner.lambda_func import scan_lambda_waste
from analyzer.ai_advisor import get_advice
from scanner.active import get_active_resources

logger = logging.getLogger(__name__)

def get_all_regions():
    """Fetch all available regions from AWS or use user overrides."""
    from config import AWS_REGIONS
    if AWS_REGIONS:
        logger.info(f"Using user-defined target regions: {AWS_REGIONS}")
        return AWS_REGIONS
        
    try:
        ec2 = boto3.client('ec2', region_name=AWS_REGION)
        regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]
        return regions
    except Exception as e:
        logger.error(f"Failed to fetch AWS regions: {e}")
        return [AWS_REGION]



def get_findings(on_finding_cb=None):
    """Call real AWS scanners across all regions. Requires valid AWS credentials."""
    try:
        # Validate credentials first
        sts = boto3.client('sts', region_name=AWS_REGION)
        sts.get_caller_identity()
    except Exception as e:
        logger.error(f"AWS Credential validation failed or timed out: {e}")
        return []

    import concurrent.futures

    findings = []
    regions = get_all_regions()
    
    # Regional scanners
    regional_scanners = [
        scan_unattached_ebs,
        scan_unused_eips,
        scan_stopped_ec2,
        scan_idle_ec2,
        scan_old_snapshots,
        scan_lambda_waste
    ]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = {}
        
        # Submit regional scanners for all regions
        for region in regions:
            for scanner in regional_scanners:
                futures[executor.submit(scanner, region=region)] = f"{scanner.__name__} ({region})"
                
        # Submit global scanners once
        futures[executor.submit(scan_s3_waste)] = "scan_s3_waste (global)"
        
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                if result:
                    findings.extend(result)
                    if on_finding_cb:
                        on_finding_cb(result)
            except Exception as e:
                logger.error(f"Scanner {name} exception: {e}")
                
                
    return findings


def get_ai_advice(report_text):
    """Get AI advice using Ollama."""
    return get_advice(report_text)

def get_active_services():
    """Fetch all running infrastructure across all regions."""
    import concurrent.futures
    regions = get_all_regions()
    
    all_infra = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(get_active_resources, region=region): region for region in regions}
        for future in concurrent.futures.as_completed(futures):
            region = futures[future]
            try:
                result = future.result()
                if result:
                    all_infra.extend(result)
            except Exception as e:
                logger.error(f"Failed to fetch infrastructure for {region}: {e}")
                
    return all_infra


def get_live_status(resource_list):
    """
    Check if the provided list of resources still exists in AWS.
    resource_list: list of dicts with 'id', 'type', 'region'
    Returns: set of IDs that are still LIVE.
    """
    import concurrent.futures
    live_ids = set()
    
    # Group by region to minimize client creation
    by_region = {}
    for r in resource_list:
        reg = r.get('region', AWS_REGION)
        if reg not in by_region: by_region[reg] = []
        by_region[reg].append(r)
        
    def check_region(region, resources):
        found = []
        try:
            ec2 = boto3.client('ec2', region_name=region)
            
            # Check EC2s
            instance_ids = [r['id'] for r in resources if r['type'] == 'EC2']
            if instance_ids:
                resp = ec2.describe_instances(InstanceIds=instance_ids, Filters=[{'Name':'instance-state-name', 'Values':['pending','running','shutting-down','stopping','stopped']}])
                for res in resp.get('Reservations', []):
                    for inst in res.get('Instances', []):
                        found.append(inst['InstanceId'])
            
            # Check EBS
            volume_ids = [r['id'] for r in resources if r['type'] == 'EBS']
            if volume_ids:
                resp = ec2.describe_volumes(VolumeIds=volume_ids)
                for vol in resp.get('Volumes', []):
                    if vol['State'] != 'deleted':
                        found.append(vol['VolumeId'])
            
            # Check EIPs
            eip_ids = [r['id'] for r in resources if r['type'] == 'ElasticIP']
            for eid in eip_ids:
                try:
                    ec2.describe_addresses(AllocationIds=[eid])
                    found.append(eid)
                except ClientError: pass

            # Check Snapshots
            snap_ids = [r['id'] for r in resources if r['type'] == 'Snapshot']
            if snap_ids:
                resp = ec2.describe_snapshots(SnapshotIds=snap_ids)
                for snap in resp.get('Snapshots', []):
                    found.append(snap['SnapshotId'])

        except Exception as e:
            logger.warning(f"Live check failed for region {region}: {e}")
        return found

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_region, reg, res) for reg, res in by_region.items()]
        for future in concurrent.futures.as_completed(futures):
            live_ids.update(future.result())
            
    return live_ids


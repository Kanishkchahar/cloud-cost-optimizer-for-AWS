import boto3
import logging
from config import AWS_REGION, STOPPED_EC2_EBS_ESTIMATE, EC2_CPU_THRESHOLD
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def scan_stopped_ec2(region=None):
    """Find EC2 instances that are in a stopped state. Uses pagination."""
    if not region:
        region = AWS_REGION
        
    findings = []
    try:
        ec2 = boto3.client("ec2", region_name=region)
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
                        "type": "Stopped EC2",
                        "id": instance_id,
                        "detail": f"Stopped instance '{name}' ({instance_type})",
                        "waste_usd": STOPPED_EC2_EBS_ESTIMATE,
                        "region": region
                    })


        logger.info(f"EC2 scan complete — {len(findings)} stopped instances found.")
    except Exception as e:
        logger.error(f"EC2 scan failed: {e}")

    return findings


def scan_idle_ec2(region=None):
    """Find running EC2 instances with low CPU utilization using CloudWatch."""
    if not region:
        region = AWS_REGION
        
    findings = []
    try:
        import concurrent.futures
        ec2 = boto3.client("ec2", region_name=region)
        cw = boto3.client("cloudwatch", region_name=region)
        
        # Get all running instances
        instances = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )
        
        def check_instance(instance):
            instance_id = instance["InstanceId"]
            instance_type = instance["InstanceType"]
            
            # Only consider instances running for more than 24 hours
            launch_time = instance.get("LaunchTime")
            if launch_time:
                age = datetime.now(timezone.utc) - launch_time
                if age.total_seconds() < 86400: # 24 hours
                    return None

            # Fetch CPU utilization for the last 7 days
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=7)
            
            try:
                metrics = cw.get_metric_statistics(
                    Namespace="AWS/EC2",
                    MetricName="CPUUtilization",
                    Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400, # Daily average
                    Statistics=["Average"]
                )
            except Exception as e:
                logger.warning(f"Failed to get metrics for {instance_id}: {e}")
                return None
            
            datapoints = metrics.get("Datapoints", [])
            if not datapoints or len(datapoints) < 3: # Require at least 3 days of data
                return None
                
            avg_cpu = sum(d["Average"] for d in datapoints) / len(datapoints)
            
            if avg_cpu < EC2_CPU_THRESHOLD:
                name = "unnamed"
                for tag in instance.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break
                        
                return {
                    "type": "Idle EC2",
                    "id": instance_id,
                    "detail": f"Running but idle '{name}' (Avg CPU: {avg_cpu:.1f}% over {len(datapoints)} days)",
                    "waste_usd": 15.0,  # Generic estimate
                    "region": region
                }
            return None

        # Flatten instance list
        all_instances = []
        for reservation in instances["Reservations"]:
            all_instances.extend(reservation["Instances"])

        # Parallel check
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as inner_executor:
            results = list(inner_executor.map(check_instance, all_instances))
            findings = [r for r in results if r]
                    
        logger.info(f"EC2 Idle scan complete — {len(findings)} idle instances found.")
    except Exception as e:
        logger.error(f"EC2 Idle scan failed: {e}")
        
    return findings

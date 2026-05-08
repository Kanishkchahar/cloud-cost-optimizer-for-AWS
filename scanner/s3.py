import boto3
import logging
from config import AWS_REGION

logger = logging.getLogger(__name__)

def scan_s3_waste():
    findings = []
    try:
        import concurrent.futures
        s3 = boto3.client('s3', region_name=AWS_REGION)
        # S3 lists all buckets globally
        response = s3.list_buckets()
        buckets = response.get('Buckets', [])
        
        def check_bucket(bucket):
            bucket_name = bucket['Name']
            bucket_findings = []
            
            # 1. Check for empty buckets
            try:
                objects = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
                if 'Contents' not in objects:
                    bucket_findings.append({
                        "type": "S3 Bucket",
                        "id": bucket_name,
                        "detail": "Empty bucket",
                        "waste_usd": 0.00,
                        "region": "global"
                    })
            except Exception as e:
                logger.warning(f"Could not list objects in S3 bucket {bucket_name}: {e}")
                
            # 2. Check for incomplete multipart uploads
            try:
                multiparts = s3.list_multipart_uploads(Bucket=bucket_name)
                uploads = multiparts.get('Uploads', [])
                if uploads:
                    bucket_findings.append({
                        "type": "S3 Multipart",
                        "id": f"{bucket_name} (Uploads)",
                        "detail": f"{len(uploads)} incomplete multipart uploads",
                        "waste_usd": len(uploads) * 0.50,
                        "region": "global"
                    })
            except Exception as e:
                logger.warning(f"Could not check multipart uploads for {bucket_name}: {e}")
            
            return bucket_findings

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as inner_executor:
            results = list(inner_executor.map(check_bucket, buckets))
            for res in results:
                findings.extend(res)
                
    except Exception as e:
        logger.error(f"Error scanning S3: {e}")
        
    return findings

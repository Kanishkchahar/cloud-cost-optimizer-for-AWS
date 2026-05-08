# config.py — Central configuration loaded from .env file
import os
import boto3
import botocore.config
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Optimize boto3 timeouts globally to prevent long region scan hangs
_original_boto3_client = boto3.client

def _patched_boto3_client(service_name, **kwargs):
    if 'config' not in kwargs:
        kwargs['config'] = botocore.config.Config(
            connect_timeout=10,
            read_timeout=15,
            retries={'max_attempts': 3}
        )
    return _original_boto3_client(service_name, **kwargs)

boto3.client = _patched_boto3_client


# --- AWS ---
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGIONS = [r.strip() for r in os.getenv("AWS_REGIONS", "").split(",") if r.strip()]

# --- AI Models ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")


# --- Thresholds ---
SNAPSHOT_AGE_DAYS = int(os.getenv("SNAPSHOT_AGE_DAYS", "30"))
EC2_CPU_THRESHOLD = float(os.getenv("EC2_CPU_THRESHOLD", "5.0"))

# --- Database ---
DB_PATH = os.getenv("DB_PATH", "db/optimizer.db")

# --- Budget Alert ---
BUDGET_THRESHOLD = float(os.getenv("BUDGET_THRESHOLD", "50.00"))

# --- Email / SMTP ---
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_FROM = os.getenv("ALERT_FROM", "")
ALERT_TO = os.getenv("ALERT_TO", "")

# --- Cost estimates (USD per month) ---
EBS_COST_PER_GB = 0.10
EIP_MONTHLY_COST = 3.60
SNAPSHOT_COST_PER_GB = 0.05
STOPPED_EC2_EBS_ESTIMATE = 5.00

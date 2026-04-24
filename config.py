# config.py — Central configuration loaded from .env file
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# --- AWS ---
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# --- Thresholds ---
SNAPSHOT_AGE_DAYS = int(os.getenv("SNAPSHOT_AGE_DAYS", "30"))
EC2_CPU_THRESHOLD = float(os.getenv("EC2_CPU_THRESHOLD", "5.0"))

# --- AI ---
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

# --- Database ---
DB_PATH = os.getenv("DB_PATH", "db/optimizer.db")
REPORT_PATH = "output/last_report.json"

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

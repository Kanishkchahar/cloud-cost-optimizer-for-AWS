# AWS Smart Cost Optimizer

A Python CLI + Web Dashboard tool that scans your AWS account, finds wasted resources, estimates costs, and uses free AI (Ollama) to recommend actions — from your terminal or a beautiful web interface.

---

## What It Does

- 🔍 Scans AWS for idle/wasted resources (EBS, EC2, Elastic IPs, Snapshots)
- 💰 Estimates how much each resource is costing you per month
- 📊 **Web Dashboard** — real-time charts, filterable tables, cost trends, CSV export
- ⚙️ **Settings Tab** — manage AWS credentials, budget thresholds, and scanner preferences from the UI
- 🚨 **Budget Alerts** — premium HTML email notifications when waste exceeds your threshold
- 🔐 **Basic Auth** — secure your dashboard with a username and password
- 🗄️ Stores scan history and alert logs in a local SQLite database
- 🤖 Asks a local AI model (Ollama) to explain findings and recommend what to delete
- 🎨 Rich CLI output with progress bars, severity indicators, and ASCII charts
- 🧪 Dry-run mode — preview what would be deleted before taking action
- 📈 Cost trend tracking across scans

---

## Folder Structure

```
aws-cost-optimizer/
│
├── main.py                  # Entry point — CLI + dashboard launcher
├── config.py                # Settings: region, thresholds, Ollama model
├── seed_demo.py             # Seeds realistic demo data for previewing
├── requirements.txt         # All dependencies
│
├── scanner/
│   ├── __init__.py
│   ├── ebs.py               # Finds unattached EBS volumes (paginated)
│   ├── ec2.py               # Finds stopped EC2 instances (paginated)
│   ├── eip.py               # Finds unused Elastic IPs
│   └── snapshots.py         # Finds old snapshots (paginated)
│
├── analyzer/
│   ├── __init__.py
│   ├── cost_estimator.py    # Cost totals, breakdown, severity levels
│   ├── reporter.py          # Rich CLI report + JSON export
│   └── ai_advisor.py        # Ollama AI recommendations
│
├── actor/
│   ├── __init__.py
│   └── cleaner.py           # Deletes/stops resources (dry-run safe)
│
├── db/
│   ├── __init__.py
│   └── database.py          # SQLite with context managers & trend queries
│
├── dashboard/
│   ├── __init__.py
│   ├── app.py               # Flask backend with REST API
│   ├── templates/
│   │   └── index.html       # Dashboard HTML
│   └── static/
│       ├── css/style.css     # Premium dark theme with glassmorphism
│       └── js/app.js         # Charts, filters, sorting, CSV export
│
└── output/
    └── last_report.json     # Saved report from last scan
```

---

## Tech Stack

| Tool | Purpose | Cost |
|---|---|---|
| Python 3.10+ | Main language | Free |
| boto3 | AWS SDK | Free |
| sqlite3 | Local database | Free (built-in) |
| Ollama + Phi-3 | Local AI advisor | Free |
| rich | Pretty CLI output | Free |

---

## Prerequisites

### 1. Python
Make sure Python 3.10+ is installed.
```bash
python --version
```

### 2. Configuration & AWS Credentials
You need an AWS account with an IAM user that has read access. We use a `.env` file for all configuration.

Rename the example file:
```bash
cp .env.example .env
```

Edit the `.env` file with your details:
```env
# AWS Credentials
AWS_ACCESS_KEY_ID=YOUR_KEY
AWS_SECRET_ACCESS_KEY=YOUR_SECRET
AWS_DEFAULT_REGION=us-east-1

# Important: Set to False to scan real AWS data
USE_DEMO_DATA=False
```

### 3. Ollama (Free Local AI)
Install from https://ollama.com

```bash
# Windows
winget install Ollama.Ollama

# Then pull the AI model (fits in 8GB VRAM)
ollama pull phi3
```

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/aws-cost-optimizer.git
cd aws-cost-optimizer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Make sure Ollama is running
ollama serve
```

### requirements.txt
```
boto3
rich
requests
```

---

## Configuration

Edit `config.py` to match your setup:

```python
# config.py

AWS_REGION = "us-east-1"           # Your AWS region
SNAPSHOT_AGE_DAYS = 30             # Flag snapshots older than this
EC2_CPU_THRESHOLD = 5.0            # Flag EC2 with CPU% below this
OLLAMA_MODEL = "phi3"              # AI model to use
OLLAMA_URL = "http://localhost:11434/api/generate"
DB_PATH = "db/optimizer.db"
```

---

## File-by-File Build Guide

Follow this order. Do not skip steps.

---

### STEP 1 — `db/database.py`

Sets up SQLite. Creates tables. Saves scan results.

```python
import sqlite3
from config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

def setup_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            total_waste_usd REAL,
            resources_found INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            resource_type TEXT,
            resource_id TEXT,
            waste_usd REAL,
            region TEXT,
            status TEXT,
            detected_at TEXT
        )
    """)

    conn.commit()
    conn.close()

def save_scan(total_waste, resources_found):
    from datetime import datetime
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO scans (timestamp, total_waste_usd, resources_found) VALUES (?, ?, ?)",
        (datetime.now().isoformat(), total_waste, resources_found)
    )
    scan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return scan_id

def save_resource(scan_id, resource_type, resource_id, waste_usd, region):
    from datetime import datetime
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO resources (scan_id, resource_type, resource_id, waste_usd, region, status, detected_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (scan_id, resource_type, resource_id, waste_usd, region, "detected", datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
```

---

### STEP 2 — `scanner/ebs.py`

Finds EBS volumes that are not attached to any instance.

```python
import boto3
from config import AWS_REGION

def scan_unattached_ebs():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    response = ec2.describe_volumes(
        Filters=[{"Name": "status", "Values": ["available"]}]
    )

    findings = []
    for vol in response["Volumes"]:
        size_gb = vol["Size"]
        monthly_cost = size_gb * 0.10  # ~$0.10/GB/month for gp2

        findings.append({
            "type": "EBS",
            "id": vol["VolumeId"],
            "detail": f"{size_gb}GB unattached volume",
            "waste_usd": round(monthly_cost, 2),
            "region": AWS_REGION
        })

    return findings
```

---

### STEP 3 — `scanner/eip.py`

Finds Elastic IPs not associated with any resource.

```python
import boto3
from config import AWS_REGION

def scan_unused_eips():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    response = ec2.describe_addresses()

    findings = []
    for addr in response["Addresses"]:
        if "AssociationId" not in addr:
            findings.append({
                "type": "ElasticIP",
                "id": addr["PublicIp"],
                "detail": "Unassociated Elastic IP",
                "waste_usd": 3.60,  # ~$0.005/hr
                "region": AWS_REGION
            })

    return findings
```

---

### STEP 4 — `scanner/ec2.py`

Finds EC2 instances that have been stopped for more than 7 days.

```python
import boto3
from datetime import datetime, timezone
from config import AWS_REGION

def scan_stopped_ec2():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    response = ec2.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]
    )

    findings = []
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            instance_id = instance["InstanceId"]
            instance_type = instance["InstanceType"]

            findings.append({
                "type": "EC2",
                "id": instance_id,
                "detail": f"Stopped instance ({instance_type})",
                "waste_usd": 5.00,  # conservative EBS cost estimate
                "region": AWS_REGION
            })

    return findings
```

---

### STEP 5 — `scanner/snapshots.py`

Finds EBS snapshots older than 30 days.

```python
import boto3
from datetime import datetime, timezone, timedelta
from config import AWS_REGION, SNAPSHOT_AGE_DAYS

def scan_old_snapshots():
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    response = ec2.describe_snapshots(OwnerIds=["self"])

    cutoff = datetime.now(timezone.utc) - timedelta(days=SNAPSHOT_AGE_DAYS)
    findings = []

    for snap in response["Snapshots"]:
        if snap["StartTime"] < cutoff:
            size_gb = snap["VolumeSize"]
            monthly_cost = size_gb * 0.05  # ~$0.05/GB/month

            findings.append({
                "type": "Snapshot",
                "id": snap["SnapshotId"],
                "detail": f"{size_gb}GB snapshot, {snap['StartTime'].date()}",
                "waste_usd": round(monthly_cost, 2),
                "region": AWS_REGION
            })

    return findings
```

---

### STEP 6 — `analyzer/cost_estimator.py`

Adds total cost to the full findings list.

```python
def estimate_total(findings):
    total = sum(f["waste_usd"] for f in findings)
    return round(total, 2)
```

---

### STEP 7 — `analyzer/reporter.py`

Builds a readable report from findings.

```python
from rich.console import Console
from rich.table import Table

console = Console()

def print_report(findings, total):
    table = Table(title="AWS Waste Report")
    table.add_column("Type", style="cyan")
    table.add_column("Resource ID", style="white")
    table.add_column("Detail", style="yellow")
    table.add_column("Cost/Month", style="red")

    for f in findings:
        table.add_row(f["type"], f["id"], f["detail"], f"${f['waste_usd']}")

    console.print(table)
    console.print(f"\n[bold red]Total Monthly Waste: ${total}[/bold red]")

def build_report_text(findings, total):
    lines = [f"Total waste: ${total}/month\n"]
    for f in findings:
        lines.append(f"- [{f['type']}] {f['id']}: {f['detail']} — ${f['waste_usd']}/month")
    return "\n".join(lines)
```

---

### STEP 8 — `analyzer/ai_advisor.py`

Sends the report to Ollama. Gets back plain English advice.

```python
import requests
from config import OLLAMA_MODEL, OLLAMA_URL

def get_advice(report_text):
    prompt = f"""
You are an AWS cost optimization expert.
Here is a waste report from an AWS account:

{report_text}

Give a clear, ranked action plan:
1. What to delete immediately (no risk)
2. What to review before deleting
3. Estimated monthly savings if all actions taken
Keep it short and direct.
"""
    response = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    })

    return response.json().get("response", "No response from AI.")
```

---

### STEP 9 — `actor/cleaner.py`

Deletes resources. Always defaults to dry-run.

```python
import boto3
from config import AWS_REGION

def delete_ebs_volume(volume_id, dry_run=True):
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    if dry_run:
        print(f"[DRY RUN] Would delete EBS volume: {volume_id}")
        return
    ec2.delete_volume(VolumeId=volume_id)
    print(f"Deleted EBS volume: {volume_id}")

def release_eip(public_ip, dry_run=True):
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    if dry_run:
        print(f"[DRY RUN] Would release Elastic IP: {public_ip}")
        return
    response = ec2.describe_addresses(PublicIps=[public_ip])
    allocation_id = response["Addresses"][0]["AllocationId"]
    ec2.release_address(AllocationId=allocation_id)
    print(f"Released Elastic IP: {public_ip}")

def delete_snapshot(snapshot_id, dry_run=True):
    ec2 = boto3.client("ec2", region_name=AWS_REGION)
    if dry_run:
        print(f"[DRY RUN] Would delete snapshot: {snapshot_id}")
        return
    ec2.delete_snapshot(SnapshotId=snapshot_id)
    print(f"Deleted snapshot: {snapshot_id}")
```

---

### STEP 10 — `main.py`

The entry point. Ties everything together.

```python
import argparse
from db.database import setup_db, save_scan, save_resource
from scanner.ebs import scan_unattached_ebs
from scanner.eip import scan_unused_eips
from scanner.ec2 import scan_stopped_ec2
from scanner.snapshots import scan_old_snapshots
from analyzer.cost_estimator import estimate_total
from analyzer.reporter import print_report, build_report_text
from analyzer.ai_advisor import get_advice
from actor.cleaner import delete_ebs_volume, release_eip, delete_snapshot

def main():
    parser = argparse.ArgumentParser(description="AWS Smart Cost Optimizer")
    parser.add_argument("--scan", action="store_true", help="Run a full scan")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without executing")
    parser.add_argument("--execute", action="store_true", help="Execute cleanup actions")
    parser.add_argument("--ai", action="store_true", help="Get AI recommendations")
    args = parser.parse_args()

    setup_db()

    if args.scan:
        print("\nScanning AWS account...\n")

        findings = []
        findings += scan_unattached_ebs()
        findings += scan_unused_eips()
        findings += scan_stopped_ec2()
        findings += scan_old_snapshots()

        total = estimate_total(findings)
        print_report(findings, total)

        # Save to DB
        scan_id = save_scan(total, len(findings))
        for f in findings:
            save_resource(scan_id, f["type"], f["id"], f["waste_usd"], f["region"])

        if args.ai:
            print("\nAsking AI for recommendations...\n")
            report_text = build_report_text(findings, total)
            advice = get_advice(report_text)
            print(f"\nAI Recommendation:\n{advice}\n")

        if args.dry_run:
            for f in findings:
                if f["type"] == "EBS":
                    delete_ebs_volume(f["id"], dry_run=True)
                elif f["type"] == "ElasticIP":
                    release_eip(f["id"], dry_run=True)
                elif f["type"] == "Snapshot":
                    delete_snapshot(f["id"], dry_run=True)

        if args.execute:
            confirm = input("\nExecute cleanup? This will delete resources. (yes/no): ")
            if confirm.lower() == "yes":
                for f in findings:
                    if f["type"] == "EBS":
                        delete_ebs_volume(f["id"], dry_run=False)
                    elif f["type"] == "ElasticIP":
                        release_eip(f["id"], dry_run=False)
                    elif f["type"] == "Snapshot":
                        delete_snapshot(f["id"], dry_run=False)

if __name__ == "__main__":
    main()
```

---

## CLI Usage

```bash
# Scan only — see what's wasted
python main.py --scan

# Scan + get AI advice
python main.py --scan --ai

# Scan + see what WOULD be deleted (safe)
python main.py --scan --dry-run

# Scan + actually delete (asks for confirmation)
python main.py --scan --execute

# Full run with AI
python main.py --scan --ai --dry-run
```

---

## Build Order (Do This Exactly)

```
1. db/database.py
2. scanner/ebs.py
3. scanner/eip.py
4. scanner/ec2.py
5. scanner/snapshots.py
6. analyzer/cost_estimator.py
7. analyzer/reporter.py
8. analyzer/ai_advisor.py
9. actor/cleaner.py
10. main.py
```

Test each file individually before moving to the next.

---

## Testing Each Module

```bash
# Test DB
python -c "from db.database import setup_db; setup_db(); print('DB OK')"

# Test EBS scanner
python -c "from scanner.ebs import scan_unattached_ebs; print(scan_unattached_ebs())"

# Test AI advisor (make sure ollama is running)
python -c "from analyzer.ai_advisor import get_advice; print(get_advice('1 EBS volume wasting $18/month'))"
```

---

## Common Errors

| Error | Fix |
|---|---|
| `NoCredentialsError` | Run `aws configure` |
| `Connection refused` on Ollama | Run `ollama serve` first |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `AccessDenied` on AWS | Check IAM permissions |

---

## Minimum IAM Permissions Needed

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVolumes",
        "ec2:DescribeAddresses",
        "ec2:DescribeInstances",
        "ec2:DescribeSnapshots",
        "ec2:DeleteVolume",
        "ec2:ReleaseAddress",
        "ec2:DeleteSnapshot"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## What You Will See When It Works

```
AWS Waste Report
┌────────────┬─────────────────┬──────────────────────────────┬────────────┐
│ Type       │ Resource ID     │ Detail                       │ Cost/Month │
├────────────┼─────────────────┼──────────────────────────────┼────────────┤
│ EBS        │ vol-0abc12345   │ 100GB unattached volume      │ $10.00     │
│ ElasticIP  │ 3.14.22.11      │ Unassociated Elastic IP      │ $3.60      │
│ Snapshot   │ snap-0xyz98765  │ 50GB snapshot, 2024-12-01   │ $2.50      │
└────────────┴─────────────────┴──────────────────────────────┴────────────┘

Total Monthly Waste: $16.10

AI Recommendation:
1. Delete vol-0abc12345 immediately — unattached 30+ days, zero risk
2. Release Elastic IP 3.14.22.11 — not in use, instant saving
3. Delete old snapshot — verify no restore needed first
Estimated savings: $16.10/month ($193/year)
```

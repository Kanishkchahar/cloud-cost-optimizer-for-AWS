# AWS Smart Cost Optimizer ☁️💰

A comprehensive Python-based tool (CLI + Web Dashboard) that scans your AWS account for wasted and idle resources, estimates potential savings, and uses local AI (Ollama) to recommend cost-saving actions.

---

## 🌟 Features

- **🔍 Automated Scanning:** Finds idle/wasted resources including unattached EBS volumes, stopped EC2 instances, unused Elastic IPs, old snapshots, empty S3 buckets, incomplete S3 multipart uploads, and abandoned Lambda functions.
- **⚡ Multithreaded Engine:** Powered by a high-performance, concurrent scanning engine that scans across all active AWS regions in parallel to reduce scan times by 80%.

- **🚀 Live Infrastructure Management:** View both active and stopped services across your AWS environment, and perform live actions (Start, Stop, Reboot, Terminate) directly from the dashboard.
- **📈 AWS Cost Explorer Integration:** Pulls live billing data from AWS Cost Explorer to show your exact monthly spend by service.
- **💰 Cost Estimation:** Calculates exact monthly cost waste per resource based on AWS pricing.
- **📊 Interactive Web Dashboard:** A beautiful, responsive AWS-style UI with skeleton loaders, real-time charts, filterable tables, and cost trends.
- **⏰ Scheduled Auto-Scans:** Configure Windows Task Scheduler directly from the UI to run hourly, daily, or weekly background scans automatically.
- **🤖 AI-Powered Advice:** Integrates with local AI models via Ollama (e.g., Phi-3, Llama 3) to analyze reports and provide actionable cost-saving advice in plain English.
- **🚨 Budget Alerts:** Configurable threshold alerts with automated email notifications when your waste exceeds a defined budget.
- **⚙️ Settings Management:** Update AWS credentials, budget thresholds, and email configurations directly from the UI.
- **🗄️ Local Database:** Stores scan history and tracks your optimization trends over time using SQLite.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, Flask, SQLite3
- **AWS SDK:** Boto3
- **Frontend:** HTML5, Vanilla CSS (Glassmorphism UI), Vanilla JavaScript, Chart.js
- **AI Integration:** Ollama (Local AI)
- **CLI Utilities:** Rich (for terminal formatting)

---

## 📋 Prerequisites

1. **Python 3.10+** installed and added to your system PATH.
2. **AWS Account & IAM Credentials** with read access (`ec2:Describe*`).
3. **Ollama** installed locally (if you want to use the AI advisor feature).

---

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Kanishkchahar/cloud-cost-optimizer-for-AWS.git
   cd cloud-cost-optimizer-for-AWS
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Copy the example environment file and update it with your actual AWS credentials.
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```env
   # AWS Credentials
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_DEFAULT_REGION=ap-south-1
   AWS_REGIONS=ap-south-1  # (Optional) Comma-separated list of target regions to scan


   ```

4. **(Optional) Setup Local AI:**
   Install [Ollama](https://ollama.com/) and download a lightweight model:
   ```bash
   ollama pull phi3
   ollama serve
   ```

---

## 💻 Usage

### Web Dashboard
The easiest way to interact with the optimizer is through the web dashboard.
Run the following command or use the provided batch script:
```bash
python main.py --dashboard
```
*(On Windows, you can simply double-click `run_dashboard.bat`)*
Then open your browser to `http://127.0.0.1:5000`

### Command Line Interface (CLI)
You can run scans directly from your terminal with rich formatting:

```bash
# Basic scan - see what's wasted
python main.py --scan

# Scan + get AI recommendations
python main.py --scan --ai

# Scan + dry-run cleanup (safe preview of what would be deleted)
python main.py --scan --dry-run

# Scan + actually execute cleanup (will prompt for confirmation)
python main.py --scan --execute
```
*(On Windows, you can double-click `run_scan.bat` for a basic scan)*

---

## 📁 Project Structure

```
├── main.py                  # CLI & Web App Entry Point
├── config.py                # Core configuration & thresholds
├── .env                     # Secrets and Environment Config (Ignored)
├── .env.example             # Template for Environment Config
├── requirements.txt         # Python dependencies
├── dashboard/               # Flask Web Application
│   ├── app.py               # API Routes and Views
│   ├── static/              # CSS/JS Assets (Glassmorphism UI)
│   └── templates/           # HTML Views
├── scanner/                 # AWS Boto3 Scanners (EBS, EC2, EIP, Snapshots, S3, Lambda)
├── analyzer/                # Cost Estimators & AI Advisor Integrations
├── actor/                   # Cleanup scripts & Instance Management
├── notifier/                # Email alerting system
├── db/                      # SQLite Database schemas and models
├── docs/                    # Project Documentation
└── tests/                   # Unit tests
```

---

## 🔒 IAM Permissions Required

To run the application against your real AWS account, the IAM user must have the following minimum permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:RebootInstances",
        "ec2:TerminateInstances",
        "ec2:DeleteVolume",
        "ec2:ReleaseAddress",
        "ec2:DeleteSnapshot",
        "rds:Describe*",
        "rds:StartDBInstance",
        "rds:StopDBInstance",
        "rds:RebootDBInstance",
        "rds:DeleteDBInstance",
        "s3:ListAllMyBuckets",
        "s3:ListBucket",
        "s3:ListBucketMultipartUploads",
        "lambda:ListFunctions",
        "cloudwatch:GetMetricStatistics",
        "ce:GetCostAndUsage"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome!

## 📝 License
This project is open-source and available under the MIT License.

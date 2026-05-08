# AWS Smart Cost Optimizer ☁️💰

A premium, Python-powered cloud intelligence platform (CLI + Web Dashboard) designed to detect wasted AWS resources, automate infrastructure management, and provide AI-driven cost-saving recommendations.

---

## 🌟 Key Features

- **🔍 Advanced Waste Detection:** Automatically scans for unattached EBS volumes, stopped EC2 instances, unused Elastic IPs, old snapshots, empty S3 buckets, and idle Lambda functions.
- **⚡ Multithreaded Scanning:** High-performance engine that scans across multiple AWS regions in parallel, delivering results up to 80% faster.
- **🚀 Live Infrastructure Management:** View and manage healthy, active, and stopped services (Start, Stop, Reboot, Terminate) directly from the dashboard.
- **📊 Premium Glassmorphism UI:** A stunning, responsive web dashboard with animated particle backgrounds, real-time Chart.js visualizations, and skeleton loaders.
- **🤖 Triple-AI Advisor:** 
    *   **Local AI**: Integration with **Ollama** (Phi-3, Llama 3).
    *   **Cloud AI**: Powered by **Groq** (LLaMA 3.3) and **Google Gemini** for high-speed, intelligent infrastructure analysis.
    *   **Interactive AI Chat**: Chat directly with the AI advisor about your specific infrastructure waste and trends.
- **📈 Comprehensive Analytics:** Service-level breakdown, monthly/annual savings projections, and severity distribution (High/Medium/Low).
- **🚨 Budget Monitoring:** Visual gauge for budget tracking with automated email alerts (SMTP) when waste exceeds thresholds.
- **⏰ Live Monitoring:** Toggle automated background scans with a countdown timer directly from the sidebar.
- **🗄️ Scan History & Trends:** Full persistence using SQLite to track your cost optimization progress over time.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, Flask, SQLite3
- **AWS SDK:** Boto3 (EC2, S3, Lambda, Cost Explorer)
- **Frontend:** HTML5, Vanilla CSS (Glassmorphism), Vanilla JS (ES6+), Chart.js
- **AI Integration:** Groq API, Google Gemini API, Ollama (Local)
- **CLI Formatting:** Rich

---

## 📋 Prerequisites

1. **Python 3.10+** installed.
2. **AWS IAM Credentials** with `ReadOnlyAccess` (minimum) or specific permissions for cleanup (see [IAM Section](#-iam-permissions-required)).
3. **API Keys** (Optional): Groq, Gemini, or Ollama for AI features.

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

3. **Configure Environment:**
   ```bash
   cp .env.example .env
   ```
   Update `.env` with your AWS keys and preferred AI provider (Groq/Gemini/Ollama).

---

## 💻 Usage

### Web Dashboard (Recommended)
Launch the premium web interface:
```bash
python main.py --dashboard
```
*(On Windows, you can use `start_everything.bat`)*
Access via: `http://127.0.0.1:5000`

### Command Line Interface (CLI)
Run quick scans directly in your terminal:
```bash
# Basic scan
python main.py --scan

# Scan with AI recommendations
python main.py --scan --ai

# Safe cleanup preview
python main.py --scan --dry-run

# Execute cleanup (requires confirmation)
python main.py --scan --execute
```

---

## 📁 Project Structure

```
├── main.py                  # Entry Point (CLI & Web)
├── config.py                # System Thresholds & Config
├── .env                     # Secrets (Ignored)
├── .env.example             # Template Config
├── scanner/                 # Multi-service AWS Scanners
├── analyzer/                # Cost Estimators & AI Integrations
├── actor/                   # Infrastructure Management (Start/Stop/Delete)
├── dashboard/               # Flask App & Glassmorphism Assets
├── db/                      # SQLite Schema & persistence
├── notifier/                # SMTP Email Alerting
└── docs/                    # Presentation & Technical Guides
```

---

## 🔒 IAM Permissions Required

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
        "s3:ListAllMyBuckets",
        "s3:ListBucket",
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
Contributions are welcome! Please open an issue or submit a pull request for any enhancements.

## 📝 License
Distributed under the MIT License.

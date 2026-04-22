# ☁️ Cloud Cost Optimizer for AWS

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![AWS](https://img.shields.io/badge/AWS-Boto3-orange.svg)](https://aws.amazon.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A professional, high-performance cloud cost management dashboard that provides real-time insights, intelligent optimization recommendations, and automated budget alerts for AWS environments.

---

## 🚀 Overview

**Cloud Cost Optimizer** is a production-grade tool designed to help DevOps teams and IT managers reduce cloud waste. It integrates directly with **AWS Cost Explorer** and **EC2** to identify idle resources, over-provisioned instances, and unattached storage volumes.

### Key Highlights:
- **Live AWS Integration**: Real-time data fetching via Boto3.
- **Intelligent Engine**: Automated analysis of resource utilization.
- **Premium UI**: Sleek, glassmorphic dashboard with Dark/Light mode support.
- **Zero-AWS Mode**: Runs fully on high-fidelity mock data if AWS credentials are not provided.

---

## ✨ Features

### 📊 Advanced Analytics
- **Historical Cost Trends**: Visualize daily spending with stacked bar charts (grouped by service).
- **Projected Forecasting**: AI-driven month-end cost predictions based on current consumption.
- **Anomaly Detection**: Automatic flagging of unusual cost spikes using statistical analysis.
- **Regional Distribution**: Breakdown of costs across different AWS regions.

### 💡 Optimization Engine
The `analyzer.py` engine implements three primary cost-saving rules:
- **Idle VM Detection**: Identifies instances with <10% CPU usage.
- **Unattached Storage**: Flags EBS volumes not connected to any instance.
- **Right-Sizing**: Recommends downsizing for over-provisioned resources (High cost + Low usage).

### 🛠️ Active Resource Management
- **One-Click Actions**: Start, Stop, or Terminate EC2 instances directly from the dashboard.
- **Real-Time Status**: Live updates on instance states (Running, Stopped, Terminated).

### 🔔 Smart Budgeting
- **Threshold Alerts**: Set custom monthly budgets.
- **Email Notifications**: Receive automated Gmail alerts when spending exceeds your threshold.

---

## 📁 Project Structure

```bash
.
├── app.py              # Main Flask Backend (API Routes)
├── aws_connector.py    # AWS Boto3 Integration Layer
├── analyzer.py         # Optimization & Anomaly Logic
├── index.html          # Frontend Dashboard (HTML5)
├── style.css           # Premium UI Styling (Glassmorphism & Theming)
├── dashboard.js        # Frontend Logic, API Integration & Charts
├── mock_data.json      # Sample data for testing & fallback
├── .env                # Environment Variables (AWS & Email Keys)
└── requirements.txt    # Python Project Dependencies
```

---

## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/cloud-cost-optimizer-aws.git
cd cloud-cost-optimizer-aws
```

### 2. Set Up Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```env
# AWS Credentials (Optional - Falls back to mock data if empty)
AWS_ACCESS_KEY=your_access_key
AWS_SECRET_KEY=your_secret_key

# Email Alerts Configuration
SENDER_EMAIL=your_email@gmail.com
RECEIVER_EMAIL=admin_email@gmail.com
GMAIL_APP_PASSWORD=your_app_specific_password
```

---

## 🚀 Usage

1. **Start the Backend Server**:
   ```bash
   python app.py
   ```
2. **Access the Dashboard**:
   Open `http://127.0.0.1:5000` in your web browser.

---

## 🛠️ API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/summary` | `GET` | Overall cost summary & potential savings |
| `/api/historical-stacked` | `GET` | Daily costs grouped by AWS service |
| `/api/recommendations` | `GET` | List of flagged resources with optimization actions |
| `/api/instances` | `GET` | List of EC2 instances with current states |
| `/api/forecast` | `GET` | Month-end cost projection and percentage change |
| `/api/anomalies` | `GET` | List of detected cost spikes |
| `/api/check-budget` | `POST` | Validate current spending against a custom limit |

---

## 🎨 UI Aesthetics
The dashboard features a **Premium Design System**:
- **Glassmorphic Components**: Semi-transparent panels with backdrop filters.
- **Interactive Charts**: Responsive visualizations using Chart.js.
- **Responsive Layout**: Fully functional on Desktop, Tablet, and Mobile.
- **Dynamic Micro-animations**: Smooth transitions and hover effects for a premium feel.

---

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

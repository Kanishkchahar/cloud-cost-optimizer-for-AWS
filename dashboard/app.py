import sys
import os
import json
import logging
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# Add parent directory to path so we can import project modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import (
    setup_db, get_all_scans, get_scan_resources,
    get_latest_scan, get_cost_trend, save_scan, save_resource, get_alerts
)
from analyzer.cost_estimator import estimate_total, get_breakdown_by_type, get_severity
import config

logger = logging.getLogger(__name__)

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), "templates"),
            static_folder=os.path.join(os.path.dirname(__file__), "static"))
CORS(app)

from functools import wraps
from flask import Response

def check_auth(username, password):
    env_user = os.getenv("DASHBOARD_USERNAME", "")
    env_pass = os.getenv("DASHBOARD_PASSWORD", "")
    if not env_user or not env_pass:
        return True # Auth not configured
    return username == env_user and password == env_pass

def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

@app.before_request
def require_auth():
    # Only require auth if configured in .env
    if os.getenv("DASHBOARD_USERNAME") and os.getenv("DASHBOARD_PASSWORD"):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/latest-scan")
def api_latest_scan():
    scan = get_latest_scan()
    if scan:
        for r in scan.get("resources", []):
            r["severity"] = get_severity(r["waste_usd"])
        return jsonify(scan)
    return jsonify({"error": "No scans found."}), 404


@app.route("/api/scans")
def api_all_scans():
    return jsonify(get_all_scans())


@app.route("/api/scan/<int:scan_id>/resources")
def api_scan_resources(scan_id):
    resources = get_scan_resources(scan_id)
    for r in resources:
        r["severity"] = get_severity(r["waste_usd"])
    return jsonify(resources)


@app.route("/api/cost-trend")
def api_cost_trend():
    limit = request.args.get("limit", 30, type=int)
    return jsonify(get_cost_trend(limit))


@app.route("/api/summary")
def api_summary():
    scan = get_latest_scan()
    scans = get_all_scans()
    if not scan:
        return jsonify({"total_waste":0,"resources_found":0,"annual_projection":0,"trend_change":0,"last_scan":None,"total_scans":0,"breakdown":{}})

    trend_change = 0
    if len(scans) >= 2:
        trend_change = round(scans[0]["total_waste_usd"] - scans[1]["total_waste_usd"], 2)

    breakdown = {}
    for r in scan.get("resources", []):
        rtype = r["resource_type"]
        breakdown[rtype] = breakdown.get(rtype, 0) + r["waste_usd"]
    breakdown = {k: round(v, 2) for k, v in breakdown.items()}

    return jsonify({
        "total_waste": scan["total_waste_usd"],
        "resources_found": scan["resources_found"],
        "annual_projection": round(scan["total_waste_usd"] * 12, 2),
        "trend_change": trend_change,
        "last_scan": scan["timestamp"],
        "total_scans": len(scans),
        "breakdown": breakdown
    })


@app.route("/api/budget")
def api_budget():
    scan = get_latest_scan()
    total_waste = scan["total_waste_usd"] if scan else 0
    exceeded = total_waste >= config.BUDGET_THRESHOLD
    pct = (total_waste / config.BUDGET_THRESHOLD * 100) if config.BUDGET_THRESHOLD > 0 else 0
    return jsonify({
        "threshold": config.BUDGET_THRESHOLD,
        "total_waste": round(total_waste, 2),
        "exceeded": exceeded,
        "percentage": round(pct, 1),
        "overage": round(max(0, total_waste - config.BUDGET_THRESHOLD), 2)
    })


@app.route("/api/alerts")
def api_alerts():
    limit = request.args.get("limit", 50, type=int)
    return jsonify(get_alerts(limit))


@app.route("/api/scan/run", methods=["POST"])
def api_run_scan():
    import subprocess
    try:
        # Run the main.py script in scan mode using subprocess
        # We use sys.executable to ensure the same Python environment
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run([sys.executable, "main.py", "--scan"], 
                                capture_output=True, text=True, check=True,
                                env=env,
                                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return jsonify({"status": "ok", "message": "Scan completed successfully"})
    except subprocess.CalledProcessError as e:
        logger.error(f"Scan failed: {e.stderr}")
        return jsonify({"status": "error", "message": "Scan failed to run", "details": e.stderr}), 500
    except Exception as e:
        logger.error(f"Unexpected error running scan: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# --- Settings helpers ---
def _mask(val):
    if not val or len(val) <= 8 or val.startswith("your_"):
        return ""
    return val[:4] + "*" * (len(val) - 8) + val[-4:]


def _read_env():
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env[key.strip()] = val.strip()
    return env


def _write_env(env_dict):
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            lines = f.readlines()

    updated_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in env_dict:
                new_lines.append(f"{key}={env_dict[key]}\n")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    for key, val in env_dict.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}\n")

    with open(ENV_PATH, "w") as f:
        f.writelines(new_lines)


@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    env = _read_env()
    return jsonify({
        "aws": {
            "access_key": _mask(env.get("AWS_ACCESS_KEY_ID", "")),
            "secret_key": _mask(env.get("AWS_SECRET_ACCESS_KEY", "")),
            "region": env.get("AWS_DEFAULT_REGION", "us-east-1"),
            "configured": bool(env.get("AWS_ACCESS_KEY_ID", "")) and not env.get("AWS_ACCESS_KEY_ID", "").startswith("your_")
        },
        "email": {
            "smtp_host": env.get("SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": env.get("SMTP_PORT", "587"),
            "smtp_user": env.get("SMTP_USER", ""),
            "smtp_password": _mask(env.get("SMTP_PASSWORD", "")),
            "alert_from": env.get("ALERT_FROM", ""),
            "alert_to": env.get("ALERT_TO", ""),
            "configured": bool(env.get("SMTP_USER", "")) and not env.get("SMTP_USER", "").startswith("your_")
        },
        "budget": {
            "threshold": float(env.get("BUDGET_THRESHOLD", "50.00"))
        },
        "app": {
            "snapshot_age_days": env.get("SNAPSHOT_AGE_DAYS", "30"),
            "ec2_cpu_threshold": env.get("EC2_CPU_THRESHOLD", "5.0"),
            "ollama_model": env.get("OLLAMA_MODEL", "phi3"),
            "db_path": env.get("DB_PATH", "db/optimizer.db"),
            "use_demo_data": env.get("USE_DEMO_DATA", "True").lower() in ("true", "1", "yes")
        }
    })


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    try:
        data = request.get_json()
        env = _read_env()

        field_map = {
            "aws_access_key": "AWS_ACCESS_KEY_ID",
            "aws_secret_key": "AWS_SECRET_ACCESS_KEY",
            "aws_region": "AWS_DEFAULT_REGION",
            "smtp_host": "SMTP_HOST",
            "smtp_port": "SMTP_PORT",
            "smtp_user": "SMTP_USER",
            "smtp_password": "SMTP_PASSWORD",
            "alert_from": "ALERT_FROM",
            "alert_to": "ALERT_TO",
            "budget_threshold": "BUDGET_THRESHOLD",
            "snapshot_age_days": "SNAPSHOT_AGE_DAYS",
            "ec2_cpu_threshold": "EC2_CPU_THRESHOLD",
            "ollama_model": "OLLAMA_MODEL",
        }

        for field, env_key in field_map.items():
            if field in data and data[field] != "":
                val_str = str(data[field]).strip()
                if "*" in val_str:
                    continue  # Skip masked passwords
                
                # Validation
                if field in ["budget_threshold", "ec2_cpu_threshold"]:
                    try:
                        float(val_str)
                    except ValueError:
                        return jsonify({"status": "error", "message": f"Invalid number for {field}"}), 400
                elif field in ["snapshot_age_days", "smtp_port"]:
                    try:
                        int(val_str)
                    except ValueError:
                        return jsonify({"status": "error", "message": f"Invalid integer for {field}"}), 400
                        
                env[env_key] = val_str

        if "use_demo_data" in data:
            env["USE_DEMO_DATA"] = "True" if data["use_demo_data"] else "False"

        _write_env(env)

        from dotenv import load_dotenv
        load_dotenv(ENV_PATH, override=True)
        config.BUDGET_THRESHOLD = float(os.getenv("BUDGET_THRESHOLD", "50.00"))
        config.AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

        return jsonify({"status": "ok", "message": "Settings saved successfully"})
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def start_dashboard(host="127.0.0.1", port=5000):
    setup_db()
    print(f"\n🚀 Dashboard running at http://{host}:{port}\n")
    app.run(host=host, port=port, debug=True)


if __name__ == "__main__":
    start_dashboard()

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
    get_latest_scan, get_cost_trend, save_scan, save_resource, get_alerts,
    update_scan_ai_advice
)

from analyzer.cost_estimator import estimate_total, get_breakdown_by_type, get_severity
import config

import time
from functools import wraps

API_CACHE = {}
SCAN_STATUS = {"status": "idle", "message": ""}


def cached_api(ttl=300):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = request.endpoint
            now = time.time()
            force_refresh = request.args.get("force", "false").lower() == "true"
            
            if not force_refresh and cache_key in API_CACHE and now - API_CACHE[cache_key]["time"] < ttl:
                return jsonify(API_CACHE[cache_key]["data"])
            
            # Run the actual function which should return a dict
            data = f(*args, **kwargs)
            API_CACHE[cache_key] = {"data": data, "time": now}
            return jsonify(data)
        return decorated_function
    return decorator

logger = logging.getLogger(__name__)

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), "templates"),
            static_folder=os.path.join(os.path.dirname(__file__), "static"))
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable static file caching during dev
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/latest-scan")
def api_latest_scan():
    from db.database import get_all_active_resources
    resources = get_all_active_resources()
    if resources:
        for r in resources:
            r["severity"] = get_severity(r["waste_usd"])
        return jsonify({"resources": resources})
    
    # Fallback to latest scan if no "active" resources but maybe we want to show empty scan?
    scan = get_latest_scan()
    if scan:
        return jsonify(scan)
    return jsonify({"error": "No scans found."}), 404


@app.route("/api/scans")
def api_all_scans():
    return jsonify(get_all_scans())


@app.route("/api/history/clear", methods=["POST"])
def api_clear_history():
    from db.database import clear_all_scans
    try:
        clear_all_scans()
        return jsonify({"status": "ok", "message": "All scan history cleared"})
    except Exception as e:
        logger.error(f"Failed to clear history: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/scan/<int:scan_id>/resources")
def api_scan_resources(scan_id):
    resources = get_scan_resources(scan_id)
    for r in resources:
        r["severity"] = get_severity(r["waste_usd"])
    return jsonify(resources)


@app.route("/api/ai-provider")
def api_ai_provider():
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if gemini_key and gemini_key.startswith("gsk_"):
        groq_key = gemini_key
        
    if groq_key:
        return jsonify({"provider": "Groq Cloud AI"})
    elif gemini_key:
        return jsonify({"provider": "Google Gemini Cloud AI"})
    else:
        return jsonify({"provider": "Fallback AI Rules"})


@app.route("/api/cost-trend")

def api_cost_trend():
    limit = request.args.get("limit", 30, type=int)
    return jsonify(get_cost_trend(limit))


@app.route("/api/summary")
def api_summary():
    from db.database import get_all_active_resources
    resources = get_all_active_resources()
    scan = get_latest_scan()
    scans = get_all_scans()
    
    if not scan and not resources:
        return jsonify({"total_waste":0,"resources_found":0,"annual_projection":0,"trend_change":0,"last_scan":None,"total_scans":0,"breakdown":{}})

    total_waste = sum(r["waste_usd"] for r in resources)
    resources_count = len(resources)
    
    trend_change = 0
    if len(scans) >= 2:
        trend_change = round(total_waste - scans[1]["total_waste_usd"], 2)

    breakdown = {}
    for r in resources:
        rtype = r.get("resource_type") or r.get("type", "Unknown")
        breakdown[rtype] = breakdown.get(rtype, 0) + r["waste_usd"]
    breakdown = {k: round(v, 2) for k, v in breakdown.items()}

    return jsonify({
        "total_waste": round(total_waste, 2),
        "resources_found": resources_count,
        "annual_projection": round(total_waste * 12, 2),
        "trend_change": trend_change,
        "last_scan": scan["timestamp"] if scan else None,
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


@app.route("/api/alerts/clear", methods=["POST"])
def api_clear_alerts():
    from db.database import clear_all_alerts
    try:
        clear_all_alerts()
        return jsonify({"status": "ok", "message": "All alerts cleared"})
    except Exception as e:
        logger.error(f"Failed to clear alerts: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/active")
@cached_api(ttl=300)
def api_active_services():
    """Fetch all active/stopped infrastructure from AWS (cached 5 mins)."""
    from data_source import get_active_services
    all_resources = get_active_services()
    return [r for r in all_resources if r.get("status") not in ("terminated", "deleted")]


@app.route("/api/inventory")
@cached_api(ttl=300)
def api_inventory():
    """Combined inventory: active services + wasted resources, merged and deduplicated."""
    from data_source import get_active_services
    
    inventory = []
    seen_ids = set()
    
    # 1. Add wasted resources from latest scan (skip deleted)
    scan = get_latest_scan()
    if scan:
        for r in scan.get("resources", []):
            status = r.get("status", "wasted")
            if status in ("deleted", "terminated"):
                continue
            rid = r.get("resource_id") or r.get("id", "")
            if rid:
                seen_ids.add(rid)
            inventory.append({
                "type": r.get("resource_type") or r.get("type", "Unknown"),
                "id": rid,
                "detail": r.get("detail", "-"),
                "region": r.get("region", "-"),
                "status": status,
                "cost": round(float(r.get("waste_usd", 0)), 2),
                "category": "Waste"
            })
    
    # 2. Add active/stopped resources (skip duplicates and terminated/deleted)
    try:
        active_resources = get_active_services()
        if active_resources and isinstance(active_resources, list):
            for r in active_resources:
                rid = r.get("resource_id") or r.get("id", "")
                if rid in seen_ids:
                    continue
                seen_ids.add(rid)
                status = r.get("status", "unknown")
                if status in ("terminated", "shutting-down", "deleted"):
                    continue
                is_running = status in ("running", "attached", "active", "in-use", "available")
                is_stopped = status in ("stopped", "stopping")
                
                if is_running:
                    category = "Healthy / Active"
                elif is_stopped:
                    category = "Inactive"
                else:
                    category = "Other"
                
                inventory.append({
                    "type": r.get("resource_type") or r.get("type", "Unknown"),
                    "id": rid,
                    "detail": r.get("detail", "-"),
                    "region": r.get("region", "-"),
                    "status": status,
                    "cost": 0,
                    "category": category
                })
    except Exception as e:
        logger.warning(f"Could not fetch active services for inventory: {e}")
    
    return inventory


@app.route("/api/action", methods=["POST"])
def api_perform_action():
    from actor.manager import perform_action
    from db.database import update_resource_status
    data = request.get_json()
    action = data.get("action")
    resource_type = data.get("resource_type")
    resource_id = data.get("resource_id")
    
    if not all([action, resource_type, resource_id]):
        return jsonify({"status": "error", "message": "Missing required parameters"}), 400
        
    success, message = perform_action(action, resource_type, resource_id)
    if success:
        # Update DB status based on action taken
        new_status = "deleted" if action == "delete" else ("stopped" if action == "stop" else "running" if action == "start" else "detected")
        try:
            update_resource_status(resource_id, new_status)
        except Exception as e:
            logger.warning(f"Could not update DB status for {resource_id}: {e}")
        
        # Invalidate memory caches so next fetch is fresh
        API_CACHE.pop("api_active_services", None)
        API_CACHE.pop("api_inventory", None)
        
        return jsonify({"status": "ok", "message": message})
    else:
        return jsonify({"status": "error", "message": message}), 500


def _run_scan_thread():
    global SCAN_STATUS
    import subprocess
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        result = subprocess.run([sys.executable, "main.py", "--scan"],
                                capture_output=True, text=True, check=True,
                                env=env, encoding='utf-8', errors='replace',
                                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        SCAN_STATUS["status"] = "success"
        SCAN_STATUS["message"] = "Scan completed successfully"
    except subprocess.CalledProcessError as e:
        logger.error(f"Scan failed: {e.stderr}")
        SCAN_STATUS["status"] = "failed"
        SCAN_STATUS["message"] = f"Scan failed to run: {e.stderr}"
    except Exception as e:
        logger.error(f"Unexpected error running scan: {e}")
        SCAN_STATUS["status"] = "failed"
        SCAN_STATUS["message"] = str(e)

@app.route("/api/sync-status", methods=["POST"])
def api_sync_status():
    """Cross-check database resources against live AWS APIs and mark deleted ones."""
    from data_source import get_live_status
    from db.database import update_resource_status

    scan = get_latest_scan()
    if not scan:
        return jsonify({"status": "ok", "synced": 0, "message": "No scans to sync"})

    # Extract resources to check
    resources_to_check = []
    for r in scan.get("resources", []):
        rid = r.get("resource_id") or r.get("id", "")
        current_status = r.get("status", "detected")
        if rid and current_status not in ("deleted", "terminated"):
            resources_to_check.append({
                "id": rid,
                "type": r.get("resource_type") or r.get("type", ""),
                "region": r.get("region", "ap-south-1")
            })

    if not resources_to_check:
        return jsonify({"status": "ok", "synced": 0, "message": "All resources already synced"})

    # Targeted check against AWS
    try:
        live_ids = get_live_status(resources_to_check)
    except Exception as e:
        logger.warning(f"Sync status: Could not fetch live status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    synced = 0
    for r in resources_to_check:
        rid = r["id"]
        if rid not in live_ids:
            try:
                update_resource_status(rid, "deleted")
                synced += 1
            except Exception as e:
                logger.warning(f"Sync: Failed to update {rid}: {e}")

    # Invalidate caches
    API_CACHE.pop("api_active_services", None)
    API_CACHE.pop("api_inventory", None)

    return jsonify({"status": "ok", "synced": synced, "message": f"Reconciled {synced} stale resources"})

@app.route("/api/scan/run", methods=["POST"])
def api_run_scan():
    global SCAN_STATUS
    import threading
    
    if SCAN_STATUS["status"] == "running":
        return jsonify({"status": "error", "message": "Scan already in progress"}), 409
        
    SCAN_STATUS["status"] = "running"
    SCAN_STATUS["message"] = "Scan is currently running across regions"
    
    thread = threading.Thread(target=_run_scan_thread)
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "ok", "message": "Scan started successfully"})

@app.route("/api/scan/status")
def api_scan_status():
    global SCAN_STATUS
    return jsonify(SCAN_STATUS)


@app.route("/api/ai-chat", methods=["POST"])
def api_ai_chat():
    try:
        data = request.json or {}
        user_message = data.get("message", "")
        history = data.get("history", [])
        
        if not user_message:
            return jsonify({"status": "error", "message": "Message required"}), 400
            
        latest_scan = get_latest_scan()
        context_report = ""
        if latest_scan:
            resources = get_scan_resources(latest_scan["id"])
            from analyzer.cost_estimator import estimate_total
            total_waste = estimate_total(resources)
            context_report = f"Total monthly waste: ${total_waste}\nResources detected:\n"
            for res in resources:
                context_report += f"- [{res['region']}] {res['resource_type']} {res['resource_id']}: {res['detail']} (${res['waste_usd']}/mo)\n"

                
        from analyzer.ai_advisor import chat_with_ai
        reply = chat_with_ai(user_message, history, context_report)
        return jsonify({"status": "ok", "reply": reply})
    except Exception as e:
        logger.error(f"AI chat failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/api/aws-cost")

@cached_api(ttl=300)
def api_aws_cost():
    """Fetch real monthly spend from AWS Cost Explorer API, with a 5-minute cache."""
    try:
        import boto3
        from datetime import datetime, timedelta

        ce = boto3.client(
            "ce",
            region_name="us-east-1",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

        end   = datetime.utcnow().date()
        start = end.replace(day=1)  # First day of this month

        resp = ce.get_cost_and_usage(
            TimePeriod={"Start": str(start), "End": str(end)},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )

        services = []
        total = 0.0
        for group in resp["ResultsByTime"][0].get("Groups", []):
            name   = group["Keys"][0]
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            if amount > 0.001:
                services.append({"service": name, "cost": round(amount, 4)})
                total += amount

        services.sort(key=lambda x: x["cost"], reverse=True)
        
        data = {
            "status": "ok",
            "period": {"start": str(start), "end": str(end)},
            "total": round(total, 2),
            "services": services[:15],
        }
        return data
    except Exception as e:
        logger.warning(f"AWS Cost Explorer error: {e}")
        return {"status": "error", "message": str(e)}


@app.route("/api/ai-advice")
def api_ai_advice():
    """Fetch AI advice based on the latest scan report."""
    scan = get_latest_scan()
    if not scan:
        return jsonify({"status": "error", "advice": "No scans available for AI analysis."})
    
    force = request.args.get("force", "false").lower() == "true"
    
    # Check cache first (skip if force reload or contains the fallback warning)
    if not force and scan.get("ai_advice") and "unavailable" not in scan["ai_advice"]:
        return jsonify({"status": "ok", "advice": scan["ai_advice"]})

    
    from analyzer.reporter import build_report_text
    from analyzer.ai_advisor import get_advice

    
    report_text = build_report_text(scan.get("resources", []), scan.get("total_waste_usd", 0))
    advice = get_advice(report_text)
    
    # Cache if successful
    if advice and not advice.startswith("❌"):
        try:
            update_scan_ai_advice(scan["id"], advice)
        except Exception as e:
            logger.error(f"Failed to cache AI advice: {e}")
            
    return jsonify({"status": "ok", "advice": advice})



@app.route("/api/schedule", methods=["POST"])
def api_schedule_scan():
    """Create a Windows Task Scheduler task to auto-run scans."""
    try:
        import subprocess
        data = request.get_json() or {}
        frequency = data.get("frequency", "daily")   # daily | hourly | weekly
        hour      = data.get("hour", "02")
        minute    = data.get("minute", "00")

        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        python_exe  = sys.executable
        script_path = os.path.join(project_dir, "main.py")
        task_name   = "AWSCostOptimizerScan"

        schedule_map = {
            "hourly":  f"/sc HOURLY /mo 1",
            "daily":   f"/sc DAILY /st {hour}:{minute}",
            "weekly":  f"/sc WEEKLY /d MON /st {hour}:{minute}",
        }
        schedule_str = schedule_map.get(frequency, schedule_map["daily"])

        cmd = (
            f'schtasks /create /tn "{task_name}" /tr '
            f'"{python_exe} {script_path} --scan" '
            f'{schedule_str} /f'
        )
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')


        if result.returncode == 0:
            return jsonify({"status": "ok", "message": f"Auto-scan scheduled ({frequency}). Task: {task_name}"})
        else:
            return jsonify({"status": "error", "message": result.stderr.strip() or "Failed to create task"}), 500

    except Exception as e:
        logger.error(f"Schedule error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/schedule/status")
def api_schedule_status():
    """Check if the auto-scan task exists in Windows Task Scheduler."""
    try:
        import subprocess
        result = subprocess.run(
            'schtasks /query /tn "AWSCostOptimizerScan" /fo LIST',
            shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace'
        )

        if result.returncode == 0:
            lines = result.stdout.strip().splitlines()
            info = {}
            for line in lines:
                if ":" in line:
                    k, _, v = line.partition(":")
                    info[k.strip()] = v.strip()
            return jsonify({"status": "ok", "scheduled": True, "info": info})
        return jsonify({"status": "ok", "scheduled": False})
    except Exception as e:
        return jsonify({"status": "ok", "scheduled": False, "error": str(e)})


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
            "region": env.get("AWS_DEFAULT_REGION", "ap-south-1"),
            "regions": env.get("AWS_REGIONS", "ap-south-1"),
            "configured": bool(env.get("AWS_ACCESS_KEY_ID", "")) and not env.get("AWS_ACCESS_KEY_ID", "").startswith("your_")
        },
        "ai": {
            "groq_key": _mask(env.get("GROQ_API_KEY", "")),
            "gemini_key": _mask(env.get("GEMINI_API_KEY", "")),
            "ollama_model": env.get("OLLAMA_MODEL", "llama3"),
            "configured": bool(env.get("GROQ_API_KEY", "")) or bool(env.get("GEMINI_API_KEY", ""))
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
            "db_path": env.get("DB_PATH", "db/optimizer.db")
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
            "aws_regions": "AWS_REGIONS",
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
            "groq_key": "GROQ_API_KEY",
            "gemini_key": "GEMINI_API_KEY",
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



        _write_env(env)

        from dotenv import load_dotenv
        load_dotenv(ENV_PATH, override=True)
        config.BUDGET_THRESHOLD = float(os.getenv("BUDGET_THRESHOLD", "50.00"))
        config.AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")

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

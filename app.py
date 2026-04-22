from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from analyzer import analyze
from aws_connector import get_aws_costs, load_mock_data, list_ec2_instances, stop_ec2_instance, start_ec2_instance, terminate_ec2_instance
import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

def get_data():
    aws_data = get_aws_costs()
    if aws_data:
        return aws_data
    return load_mock_data()

@app.route('/api/recommendations')
def get_recommendations():
    data = load_mock_data()
    result = analyze(data)
    return jsonify(result)

@app.route('/api/summary')
def get_summary():
    data = load_mock_data()
    result = analyze(data)
    return jsonify({
        'total_daily_cost': result['total_daily_cost'],
        'total_monthly_cost': result['total_monthly_cost'],
        'potential_savings': result['potential_savings'],
        'flagged_count': len(result['flagged'])
    })

@app.route('/api/check-budget', methods=['POST'])
def check_budget():
    from flask import request
    data = request.json
    budget = data['budget']
    
    resources = load_mock_data()
    result = analyze(resources)
    monthly = result['total_monthly_cost']
    
    if monthly > budget:
        over = round(monthly - budget, 2)
        send_alert_email(budget, monthly, over)
        return jsonify({'status': 'over', 'monthly': monthly, 'over': over})
    
    return jsonify({'status': 'ok', 'monthly': monthly})

def send_alert_email(budget, monthly, over):
    sender = os.getenv('SENDER_EMAIL')
    receiver = os.getenv('RECEIVER_EMAIL')
    password = os.getenv('GMAIL_APP_PASSWORD')

    msg = MIMEText(f"""
Budget Alert — Cloud Cost Optimizer

Your monthly cloud cost has exceeded your budget.

Budget Set:     ${budget}
Current Cost:   ${monthly}
Over By:        ${over}

Login to your dashboard to review flagged resources.
    """)

    msg['Subject'] = 'Cloud Budget Alert — Limit Exceeded'
    msg['From'] = sender
    msg['To'] = receiver

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        print("Alert email sent.")
    except Exception as e:
        print(f"Email error: {e}")


@app.route('/api/historical')
def get_historical():
    aws_data = get_aws_costs()
    if not aws_data:
        return jsonify([])
    
    daily = {}
    for day in aws_data:
        date = day['TimePeriod']['Start']
        total = sum(
            float(g['Metrics']['UnblendedCost']['Amount'])
            for g in day['Groups']
        )
        daily[date] = round(total, 4)
    
    result = [{'date': k, 'cost': v} for k, v in sorted(daily.items())]
    return jsonify(result)


@app.route('/api/historical-stacked')
def get_historical_stacked():
    """Return per-service daily costs for stacked bar chart (AWS Cost Explorer style)."""
    import json

    aws_data = get_aws_costs()

    # Check if AWS data exists and has non-zero costs
    use_mock = True
    if aws_data:
        total = 0
        for day in aws_data:
            for g in day['Groups']:
                total += float(g['Metrics']['UnblendedCost']['Amount'])
        if total > 0.01:
            use_mock = False

    if use_mock:
        # Fall back to mock stacked data from mock_data.json
        with open('mock_data.json') as f:
            mock = json.load(f)
        return jsonify(mock.get('daily_costs_stacked', []))

    # Real AWS data — group by service per day
    stacked = {}
    all_services = set()
    for day in aws_data:
        date = day['TimePeriod']['Start']
        stacked[date] = {}
        for g in day['Groups']:
            svc = g['Keys'][0] if g.get('Keys') else 'Other'
            cost = float(g['Metrics']['UnblendedCost']['Amount'])
            stacked[date][svc] = round(cost, 4)
            all_services.add(svc)

    result = []
    for date in sorted(stacked.keys()):
        result.append({'date': date, 'services': stacked[date]})
    return jsonify(result)


@app.route('/api/anomalies')
def get_anomalies():
    from analyzer import detect_anomalies
    import json

    aws_data = get_aws_costs()

    # Check if AWS data has non-zero costs
    use_mock = True
    if aws_data:
        total = 0
        for day in aws_data:
            total += sum(
                float(g['Metrics']['UnblendedCost']['Amount'])
                for g in day['Groups']
            )
        if total > 0.01:
            use_mock = False

    if not use_mock:
        daily = {}
        for day in aws_data:
            date = day['TimePeriod']['Start']
            total = sum(
                float(g['Metrics']['UnblendedCost']['Amount'])
                for g in day['Groups']
            )
            daily[date] = round(total, 4)
        data = [{'date': k, 'cost': v} for k, v in sorted(daily.items())]
    else:
        # Fall back to mock daily costs
        with open('mock_data.json') as f:
            mock = json.load(f)
        data = mock.get('daily_costs', [])

    anomalies = detect_anomalies(data)
    return jsonify(anomalies)

@app.route('/api/instances')
def get_instances():
    """List all EC2 instances. Falls back to mock data if AWS fails."""
    import json
    instances = list_ec2_instances()
    if instances is not None and len(instances) > 0:
        return jsonify(instances)
    # Fall back to mock instances
    with open('mock_data.json') as f:
        mock = json.load(f)
    return jsonify(mock.get('ec2_instances', []))


@app.route('/api/instances/stop', methods=['POST'])
def stop_instance():
    """Stop an EC2 instance by ID."""
    from flask import request
    import json
    data = request.json
    instance_id = data.get('instance_id')
    if not instance_id:
        return jsonify({'success': False, 'error': 'Missing instance_id'}), 400

    result = stop_ec2_instance(instance_id)
    if result['success']:
        return jsonify(result)

    # If AWS fails, simulate stop on mock data
    with open('mock_data.json') as f:
        mock = json.load(f)
    instances = mock.get('ec2_instances', [])
    for inst in instances:
        if inst['InstanceId'] == instance_id:
            inst['State'] = 'stopping'
            break
    with open('mock_data.json', 'w') as f:
        json.dump(mock, f, indent=2)
    return jsonify({'success': True, 'state': 'stopping', 'mock': True})


@app.route('/api/instances/start', methods=['POST'])
def start_instance():
    """Start a stopped EC2 instance."""
    from flask import request
    import json
    data = request.json
    instance_id = data.get('instance_id')
    if not instance_id:
        return jsonify({'success': False, 'error': 'Missing instance_id'}), 400

    result = start_ec2_instance(instance_id)
    if result['success']:
        return jsonify(result)

    # If AWS fails, simulate start on mock data
    with open('mock_data.json') as f:
        mock = json.load(f)
    instances = mock.get('ec2_instances', [])
    for inst in instances:
        if inst['InstanceId'] == instance_id:
            inst['State'] = 'running'
            break
    with open('mock_data.json', 'w') as f:
        json.dump(mock, f, indent=2)
    return jsonify({'success': True, 'state': 'pending', 'mock': True})


@app.route('/api/instances/terminate', methods=['POST'])
def terminate_instance():
    """Terminate an EC2 instance permanently."""
    from flask import request
    import json
    data = request.json
    instance_id = data.get('instance_id')
    if not instance_id:
        return jsonify({'success': False, 'error': 'Missing instance_id'}), 400

    result = terminate_ec2_instance(instance_id)
    if result['success']:
        return jsonify(result)

    # If AWS fails, simulate terminate on mock data
    with open('mock_data.json') as f:
        mock = json.load(f)
    instances = mock.get('ec2_instances', [])
    mock['ec2_instances'] = [i for i in instances if i['InstanceId'] != instance_id]
    with open('mock_data.json', 'w') as f:
        json.dump(mock, f, indent=2)
    return jsonify({'success': True, 'state': 'terminated', 'mock': True})


@app.route('/api/forecast')
def get_forecast():
    """Calculate projected month-end cost based on daily average."""
    import json
    from datetime import datetime

    # Try to use stacked data for daily totals
    with open('mock_data.json') as f:
        mock = json.load(f)

    daily_costs = mock.get('daily_costs', [])
    if not daily_costs:
        return jsonify({'projected': 0, 'daily_avg': 0, 'days_elapsed': 0, 'days_in_month': 30})

    total = sum(d['cost'] for d in daily_costs)
    days_elapsed = len(daily_costs)
    daily_avg = total / days_elapsed if days_elapsed > 0 else 0

    today = datetime.today()
    import calendar
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    projected = daily_avg * days_in_month

    last_month = mock.get('last_month_cost', 0)
    change_pct = round(((projected - last_month) / last_month) * 100, 1) if last_month > 0 else 0

    return jsonify({
        'projected': round(projected, 2),
        'daily_avg': round(daily_avg, 2),
        'days_elapsed': days_elapsed,
        'days_in_month': days_in_month,
        'last_month': last_month,
        'change_pct': change_pct
    })


@app.route('/api/costs-by-region')
def get_costs_by_region():
    """Return cost distribution by AWS region."""
    import json
    with open('mock_data.json') as f:
        mock = json.load(f)
    return jsonify(mock.get('costs_by_region', []))


if __name__ == '__main__':
    app.run(debug=True)
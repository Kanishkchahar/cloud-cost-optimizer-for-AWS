def analyze(resources):
    flagged = []
    total_cost = 0

    for r in resources:
        total_cost += r['cost_per_day']

        # Rule 1: Idle VM
        if r['type'] == 'Virtual Machine' and r['cpu_percent'] < 10:
            flagged.append({
                'id': r['id'],
                'type': r['type'],
                'service': r['service'],
                'region': r['region'],
                'issue': 'Idle Virtual Machine',
                'current_cost': r['cost_per_day'],
                'monthly_waste': round(r['cost_per_day'] * 30, 2),
                'action': 'Stop during off-hours or terminate'
            })

        # Rule 2: Unattached storage
        elif r['type'] == 'Storage Volume' and not r['attached']:
            flagged.append({
                'id': r['id'],
                'type': r['type'],
                'service': r['service'],
                'region': r['region'],
                'issue': 'Unattached Storage Volume',
                'current_cost': r['cost_per_day'],
                'monthly_waste': round(r['cost_per_day'] * 30, 2),
                'action': 'Delete unused volume'
            })

        # Rule 3: Over-provisioned
        elif r['cost_per_day'] > 10 and r['cpu_percent'] < 20:
            flagged.append({
                'id': r['id'],
                'type': r['type'],
                'service': r['service'],
                'region': r['region'],
                'issue': 'Over-provisioned Resource',
                'current_cost': r['cost_per_day'],
                'monthly_waste': round(r['cost_per_day'] * 0.4 * 30, 2),
                'action': 'Downsize to smaller instance'
            })

    total_savings = round(sum(f['monthly_waste'] for f in flagged), 2)
    total_monthly = round(total_cost * 30, 2)

    return {
        'flagged': flagged,
        'total_daily_cost': round(total_cost, 2),
        'total_monthly_cost': total_monthly,
        'potential_savings': total_savings
    }

def detect_anomalies(daily_costs):
    if len(daily_costs) < 3:
        return []
    
    costs = [d['cost'] for d in daily_costs]
    avg = sum(costs) / len(costs)
    threshold = avg * 2 if avg > 0 else 0.01

    anomalies = []
    for d in daily_costs:
        if d['cost'] > threshold:
            anomalies.append({
                'date': d['date'],
                'cost': d['cost'],
                'average': round(avg, 4),
                'message': f"Spike detected: ${d['cost']} vs avg ${round(avg,4)}"
            })
    return anomalies
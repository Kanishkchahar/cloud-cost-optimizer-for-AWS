def estimate_total(findings):
    """Calculate total monthly waste from all findings."""
    total = sum(f["waste_usd"] for f in findings)
    return round(total, 2)


def get_breakdown_by_type(findings):
    """Break down waste by resource type for charting."""
    breakdown = {}
    for f in findings:
        rtype = f.get("type") or f.get("resource_type", "Unknown")
        breakdown[rtype] = breakdown.get(rtype, 0) + f["waste_usd"]
    return {k: round(v, 2) for k, v in breakdown.items()}


def get_severity(waste_usd):
    """Return severity level based on cost."""
    if waste_usd >= 50:
        return "high"
    elif waste_usd >= 10:
        return "medium"
    else:
        return "low"

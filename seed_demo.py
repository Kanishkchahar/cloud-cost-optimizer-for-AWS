"""
Seed the database with realistic demo data so the dashboard
can be previewed without actual AWS credentials.

All demo resources are defined in data_source.py — this script
just imports them and creates multiple scan records.

Usage:
    python seed_demo.py
"""

import random
from datetime import datetime, timedelta
from db.database import setup_db, save_scan, save_resource
from data_source import DEMO_RESOURCES


def seed():
    """Create multiple demo scans over the past 30 days."""
    setup_db()
    print("Seeding demo data...\n")

    num_scans = 12
    base_date = datetime.now() - timedelta(days=30)

    for i in range(num_scans):
        # Randomly select a subset of resources for each scan
        num_resources = random.randint(5, len(DEMO_RESOURCES))
        selected = random.sample(DEMO_RESOURCES, num_resources)

        # Add cost variance
        jittered = []
        for r in selected:
            rc = dict(r)
            rc["waste_usd"] = round(r["waste_usd"] * random.uniform(0.8, 1.3), 2)
            jittered.append(rc)

        total = round(sum(r["waste_usd"] for r in jittered), 2)
        scan_id = save_scan(total, len(jittered))

        for r in jittered:
            save_resource(scan_id, r["type"], r["id"], r["detail"], r["waste_usd"], r["region"])

        print(f"  Scan #{scan_id}: {len(jittered)} resources, ${total:.2f} waste")

    print(f"\nSeeded {num_scans} demo scans successfully!")
    print("Run the dashboard:  python main.py --dashboard")


if __name__ == "__main__":
    seed()

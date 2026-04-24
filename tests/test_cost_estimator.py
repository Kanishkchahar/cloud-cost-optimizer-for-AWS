import unittest
from analyzer.cost_estimator import estimate_total, get_breakdown_by_type, get_severity

class TestCostEstimator(unittest.TestCase):
    def setUp(self):
        self.findings = [
            {"type": "EBS", "id": "vol-1", "waste_usd": 10.00},
            {"type": "EBS", "id": "vol-2", "waste_usd": 15.50},
            {"type": "EC2", "id": "i-123", "waste_usd": 5.00},
        ]

    def test_estimate_total(self):
        total = estimate_total(self.findings)
        self.assertEqual(total, 30.50)

    def test_get_breakdown_by_type(self):
        breakdown = get_breakdown_by_type(self.findings)
        self.assertEqual(breakdown.get("EBS"), 25.50)
        self.assertEqual(breakdown.get("EC2"), 5.00)
        self.assertIsNone(breakdown.get("Snapshot"))

    def test_get_severity(self):
        self.assertEqual(get_severity(100), "high")
        self.assertEqual(get_severity(50), "high")
        self.assertEqual(get_severity(49.99), "medium")
        self.assertEqual(get_severity(10), "medium")
        self.assertEqual(get_severity(9.99), "low")
        self.assertEqual(get_severity(0), "low")

if __name__ == "__main__":
    unittest.main()

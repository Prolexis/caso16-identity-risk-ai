import unittest

import data_layer


class Caso16CoreTests(unittest.TestCase):
    def test_rules_have_required_cases(self):
        result = data_layer.run_detection("test@demo.local", "Analista de ciberseguridad")
        self.assertEqual(result["accounts_processed"], 12)
        self.assertGreaterEqual(result["findings_created"], 0)
        findings = data_layer.finding_frame()
        self.assertTrue(set(["R01", "R02", "R03", "R04", "R05", "R06"]).issubset(set(findings["rule_id"])))
        self.assertTrue(set(findings["evidence_state"]).issubset({"confirmed", "potential", "insufficient_evidence"}))

    def test_score_is_bounded(self):
        accounts = data_layer.account_frame()
        self.assertTrue(((accounts["risk_score"] >= 0) & (accounts["risk_score"] <= 100)).all())

    def test_health_is_explicit(self):
        health = data_layer.api_health()
        self.assertIn(health["status"], {"ok", "degraded"})
        self.assertEqual(health["mode"], "deterministic")


if __name__ == "__main__":
    unittest.main()

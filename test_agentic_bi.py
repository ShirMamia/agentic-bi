import unittest

from agentic_bi import DELIVERY_CONTEXT, NOISY_CONTEXT, investigate
from sample_warehouse import build_warehouse


class InvestigationTests(unittest.TestCase):
    def setUp(self):
        self.database = build_warehouse()
        self.addCleanup(self.database.close)

    def report(self, contexts=()):
        return investigate(self.database, "North", "2026-05", "2026-06", contexts)

    def test_baseline_results_and_sql_read_only(self):
        self.database.execute("PRAGMA query_only = ON")
        result = self.report()
        self.assertEqual(result["status"], "decline")
        self.assertEqual(result["focus_city"], "Haifa")
        self.assertLess(result["revenue_change"], 0)
        self.assertEqual(result["accepted_context"], [])

    def test_noisy_sources_do_not_change_sql_findings(self):
        core = self.report((DELIVERY_CONTEXT,))
        noisy = self.report((DELIVERY_CONTEXT, *NOISY_CONTEXT))
        self.assertEqual(noisy["finding"], core["finding"])
        self.assertEqual(noisy["operational_evidence"], core["operational_evidence"])
        self.assertEqual(noisy["accepted_context"], [DELIVERY_CONTEXT.text])
        self.assertEqual(noisy["excluded_context"], 3)

    def test_changed_revenue_removes_the_decline_and_hypothesis(self):
        self.database.execute("""
            UPDATE fact_daily_sales SET gross_revenue = gross_revenue * 3
            WHERE city_id = 1
            AND date_id IN (SELECT date_id FROM dim_date WHERE month = '2026-06')
        """)
        result = self.report((DELIVERY_CONTEXT,))
        self.assertEqual(result["status"], "no_decline")
        self.assertIn("rose", result["finding"])
        self.assertIsNone(result["focus_city"])
        self.assertEqual(result["accepted_context"], [])

    def test_largest_decline_changes_the_focus_city(self):
        self.database.execute("UPDATE dim_city SET region = 'North' WHERE city_id = 2")
        self.database.execute("""
            UPDATE fact_daily_sales SET gross_revenue = gross_revenue * 0.1
            WHERE city_id = 2
            AND date_id IN (SELECT date_id FROM dim_date WHERE month = '2026-06')
        """)
        result = self.report((DELIVERY_CONTEXT,))
        self.assertEqual(result["focus_city"], "Tel Aviv")
        self.assertIn("Tel Aviv", result["finding"])
        self.assertEqual(result["accepted_context"], [])

    def test_context_excluded_when_operational_signal_disappears(self):
        self.database.execute("UPDATE fact_daily_sales SET avg_delivery_minutes = 34")
        result = self.report((DELIVERY_CONTEXT,))
        self.assertEqual(result["status"], "decline")
        self.assertEqual(result["accepted_context"], [])

    def test_missing_period_does_not_imply_zero_revenue(self):
        result = investigate(self.database, "North", "2026-04", "2026-06")
        self.assertEqual(result["status"], "insufficient_data")
        self.assertNotIn("revenue_change", result)

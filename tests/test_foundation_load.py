"""A scheduled trial must count queue delay, failures and competing work."""
import unittest
from experiments.foundation_load import run_trial


class LoadTrialTests(unittest.TestCase):
    def test_queue_delay_is_included_and_background_calls_are_counted(self):
        now = [0.0]
        def wait(seconds):
            self.assertGreaterEqual(seconds, 0)
            now[0] += seconds
        def request(messages, key, model):
            now[0] += 3
            return {'usable': False, 'error': 'synthetic_failure', 'seconds': 3, 'usage': {}}
        report = run_trial('synthetic-key', updates=3, request=request, clock=lambda: now[0], sleep=wait)
        self.assertEqual(len(report['records']), 5)  # three coverage, one reminder, one extraction
        coverage = [r for r in report['records'] if r['workload'] == 'coverage']
        self.assertEqual(coverage[0]['end_to_end_seconds'], 3)
        self.assertEqual(coverage[1]['queue_seconds'], 4)
        self.assertEqual(coverage[1]['end_to_end_seconds'], 7)
        self.assertFalse(coverage[1]['deadline_met'])
        self.assertTrue(all(not r['correct'] for r in coverage))
        self.assertNotIn('synthetic-key', str(report))

    def test_unbounded_trial_is_rejected_before_requests(self):
        for updates in (0, 37, True):
            with self.assertRaises(ValueError):
                run_trial('key', updates=updates)

"""A scheduled trial must count queue delay, failures and competing work."""
import unittest
import io
import json
import tempfile
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
from experiments.foundation_load import run_trial, main


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

    def test_cli_preserves_existing_evidence_and_reports_missed_deadlines(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'load.json'
            report = {'records': [{'workload': 'coverage', 'correct': True, 'deadline_met': False}]}
            with patch('experiments.foundation_load.load_api_key', return_value='test-key'), \
                 patch('experiments.foundation_load.run_trial', return_value=report) as run, \
                 redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--output', str(output)]), 1)
                self.assertEqual(json.loads(output.read_text()), report)
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                with self.assertRaises(FileExistsError):
                    main(['--output', str(output)])
                self.assertEqual(run.call_count, 1)

    def test_missing_credentials_creates_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'load.json'
            with patch('experiments.foundation_load.load_api_key', return_value=None), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    main(['--output', str(output)])
            self.assertFalse(output.exists())

"""Bounded live-discovery transport and representative experiment contracts."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from experiments.foundation_probe import request_chat, evaluate, CASES, make_deck, main


class FoundationProbeTests(unittest.TestCase):
    def opener(self, body):
        response = io.BytesIO(json.dumps(body).encode())
        response.headers = {'x-ratelimit-limit-requests': '300', 'private-header': 'secret'}
        return Mock(return_value=response)

    def test_request_bounds_and_safe_metadata(self):
        opener = self.opener({'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}],
                             'usage': {'prompt_tokens': 100, 'completion_tokens': 30}})
        result = request_chat([{'role': 'user', 'content': 'synthetic'}], 'test-key', 'test-model', opener=opener)
        self.assertEqual(result['content'], '{}')
        self.assertEqual(result['rate_limits'], {'x-ratelimit-limit-requests': '300'})
        req = opener.call_args.args[0]
        self.assertEqual(req.full_url, 'https://api.tokenfactory.nebius.com/v1/chat/completions')
        self.assertEqual(json.loads(req.data)['max_tokens'], 1024)
        self.assertEqual(opener.call_args.kwargs['timeout'], 30)

    def test_truncation_refusal_and_missing_content_are_unusable(self):
        for choice in [
            {'finish_reason': 'length', 'message': {'content': '{}'}},
            {'finish_reason': 'stop', 'message': {'content': None}},
            {'finish_reason': 'stop', 'message': {'content': '{}', 'refusal': 'no'}},
        ]:
            result = request_chat([], 'test-key', 'model', opener=self.opener({'choices': [choice]}))
            self.assertFalse(result['usable'])

    def test_failures_are_sanitized(self):
        for error in [TimeoutError('secret'), HTTPError('url', 429, 'secret', {}, None)]:
            result = request_chat([], 'test-key', 'model', opener=Mock(side_effect=error))
            self.assertFalse(result['usable'])
            self.assertNotIn('secret', json.dumps(result))

    def test_malformed_envelopes_are_unusable(self):
        for envelope in [[], {}, {'choices': []}, {'choices': [None]}, {'choices': [{'message': []}]}]:
            result = request_chat([], 'test-key', 'model', opener=self.opener(envelope))
            self.assertFalse(result['usable'])

    def test_three_decks_have_notes_nested_structure_and_expected_statements(self):
        self.assertEqual(len(CASES), 3)
        for case in CASES:
            d = make_deck(case)
            self.assertEqual(len(d.slides), 3)
            self.assertIn(case['statements'][2], d.slides[0].speaker_notes.text)
            self.assertEqual(d.slides[1].content_fingerprint, d.slides[2].content_fingerprint)

    def test_quality_check_does_not_accept_missing_or_invented_concepts(self):
        case = CASES[0]
        d = make_deck(case)
        good = {'concepts': [
            {'ref': 'slide/0/element/0', 'text': case['statements'][0]},
            {'ref': 'slide/0/element/1/element/0/element/0', 'text': case['statements'][1]},
            {'ref': 'slide/0/notes', 'text': case['statements'][2]},
        ]}
        self.assertTrue(evaluate('extraction', json.dumps(good), case, d))
        self.assertFalse(evaluate('extraction', '{"concepts": []}', case, d))
        self.assertFalse(evaluate('extraction', 'invalid', case, d))

    def test_coverage_and_guidance_evaluation_require_expected_content(self):
        case = CASES[0]
        d = make_deck(case)
        self.assertTrue(evaluate('guidance', json.dumps({'reminder': case['statements'][2]}), case, d))
        self.assertFalse(evaluate('guidance', json.dumps({'reminder': 'invented'}), case, d))
        self.assertTrue(evaluate('coverage', json.dumps({'concepts': [
            {'id': 1, 'status': 'covered'}, {'id': 2, 'status': 'covered'},
            {'id': 3, 'status': 'not_covered'}], 'slide_complete': False}), case, d))

    def test_cli_records_failures_privately_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.json'
            with patch('experiments.foundation_probe.load_api_key', return_value='synthetic-key'), \
                 patch('experiments.foundation_probe.request_chat', side_effect=lambda *a: {
                     'usable': False, 'error': 'transport_failure', 'usage': {}, 'seconds': 1}), \
                 redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--output', str(output), '--rounds', '1']), 1)
                saved = output.read_bytes()
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                self.assertEqual(len(json.loads(saved)['records']), 27)
                self.assertNotIn(b'synthetic-key', saved)
                with self.assertRaises(FileExistsError):
                    main(['--output', str(output), '--rounds', '1'])
                self.assertEqual(output.read_bytes(), saved)

    def test_cli_all_correct_records_pass_and_missing_key_fails_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.json'
            with patch('experiments.foundation_probe.load_api_key', return_value=None), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    main(['--output', str(output)])
            self.assertFalse(output.exists())
            with patch('experiments.foundation_probe.load_api_key', return_value='synthetic-key'), \
                 patch('experiments.foundation_probe.request_chat', side_effect=lambda *a: {'usable': True, 'content': '{}'}), \
                 patch('experiments.foundation_probe.evaluate', return_value=True), redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--output', str(output), '--rounds', '1']), 0)

    def test_request_resource_bounds_and_non_json_body(self):
        opener = Mock()
        for cap in [0, True, 4097]:
            with self.assertRaises(ValueError):
                request_chat([], 'key', 'model', opener=opener, max_tokens=cap)
        with self.assertRaises(ValueError):
            request_chat([{'role': 'user', 'content': 'a' * 80_000}], 'key', 'model', opener=opener)
        opener.assert_not_called()
        for raw in [b'not json', b'a' * 1_048_577]:
            response = io.BytesIO(raw)
            response.headers = {}
            result = request_chat([], 'key', 'model', opener=Mock(return_value=response))
            self.assertFalse(result['usable'])


if __name__ == '__main__':
    unittest.main()

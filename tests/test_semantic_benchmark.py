"""Behavioral checks for the POC-preserving model comparison."""
import json
import unittest
from unittest.mock import Mock, patch

from experiments import semantic_coverage as poc
from experiments import semantic_benchmark as bench


def completion(statuses):
    return {
        'choices': [{'message': {'content': json.dumps({
            'concepts': [{'id': i, 'status': s} for i, s in enumerate(statuses, 1)],
            'slide_complete': all(s == 'covered' for s in statuses),
        })}, 'finish_reason': 'stop'}],
        'usage': {'prompt_tokens': 400, 'completion_tokens': 60},
    }


class BenchmarkTests(unittest.TestCase):
    def test_reuses_all_cases_messages_and_rotates_models(self):
        calls = []
        def request(messages, key, model):
            calls.append((model, messages))
            case = next(c for c in poc.CASES if messages == poc.build_messages(poc.SLIDE_TITLE, poc.CONCEPTS, c.transcript))
            return completion(case.expected_statuses)
        records = bench.run_benchmark('test-key', repeats=3, request_fn=request)
        self.assertEqual(len(records), 48)
        self.assertTrue(all(r['matched'] for r in records))
        for model in bench.MODELS:
            rows = [r for r in records if r['model'] == model]
            self.assertEqual(len(rows), 12)
            self.assertEqual({r['case'] for r in rows}, {c.name for c in poc.CASES})
        self.assertEqual([calls[i][0] for i in (0, 16, 32)], list(bench.MODELS[:3]))
        self.assertEqual(calls[0][1], poc.build_messages(poc.SLIDE_TITLE, poc.CONCEPTS, poc.CASES[0].transcript))
        summary = bench.summarize(records)[0]
        self.assertEqual(summary['passed'], 12)
        self.assertEqual(summary['prompt_tokens'], 4800)
        self.assertEqual(summary['completion_tokens'], 720)
        self.assertIn('| Model |', bench.comparison_table(records))

    def test_failures_are_counted_and_do_not_stop_other_cases(self):
        valid_wrong = completion(('covered', 'covered', 'covered'))
        invalid = completion(poc.CASES[0].expected_statuses)
        invalid['choices'][0]['message']['content'] = '{}'
        request = Mock(side_effect=[poc.TokenFactoryRequestError('request failed'), invalid, valid_wrong,
                                   completion(poc.CASES[3].expected_statuses)])
        rows = bench.run_benchmark('test', models=('fake',), repeats=1, request_fn=request)
        self.assertEqual([r['outcome'] for r in rows], ['request_error', 'validation_error', 'mismatch', 'pass'])
        self.assertEqual(rows[1]['usage']['completion_tokens'], 60)
        summary = bench.summarize(rows)[0]
        self.assertEqual(summary['passed'], 1)
        self.assertEqual(summary['errors'], 2)
        self.assertIsNone(summary['prompt_tokens'])

    def test_missing_usage_is_unknown_and_invalid_repeat_rejected(self):
        response = completion(poc.CASES[0].expected_statuses)
        response.pop('usage')
        rows = bench.run_benchmark('test', models=('fake',), repeats=1, request_fn=Mock(return_value=response))
        self.assertIsNone(bench.summarize(rows)[0]['completion_tokens'])
        with self.assertRaises(ValueError):
            bench.run_benchmark('test', repeats=0)

    def test_request_settings_and_original_string_interface_unchanged(self):
        response = completion(poc.CASES[0].expected_statuses)
        connection = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        connection.read.return_value = json.dumps(response).encode()
        messages = poc.build_messages(poc.SLIDE_TITLE, poc.CONCEPTS, poc.CASES[0].transcript)
        with patch.object(poc, 'urlopen', return_value=connection) as send:
            self.assertEqual(poc.request_model(messages, 'test'), response['choices'][0]['message']['content'])
            payload = json.loads(send.call_args.args[0].data)
            self.assertEqual(payload, {'model': poc.MODEL, 'messages': messages, 'temperature': 0,
                                      'max_tokens': 300, 'response_format': {'type': 'json_object'}})
            self.assertEqual(send.call_args.kwargs, {'timeout': 30})
            poc.request_completion(messages, 'test', bench.MODELS[0])
            self.assertEqual(json.loads(send.call_args.args[0].data)['model'], bench.MODELS[0])


if __name__ == '__main__':
    unittest.main()

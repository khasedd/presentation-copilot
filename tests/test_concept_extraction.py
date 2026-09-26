"""Source-grounded drafts must remain reviewable and snapshot-bound."""
import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

from presentation.adapters.google_slides import normalize_presentation
from presentation.concepts import build_messages, extract_drafts, source_units


def deck():
    payload = json.loads(Path('tests/fixtures/google_slides_presentation.json').read_text())
    return normalize_presentation(payload, fetched_at=datetime(2026, 9, 26, tzinfo=timezone.utc))


class ConceptExtractionTests(unittest.TestCase):
    def test_units_preserve_nested_text_notes_and_cell_coordinates(self):
        units = source_units(deck().slides[0])
        by_ref = {unit['ref']: unit for unit in units}
        self.assertEqual(by_ref['slide/0/element/1/element/0']['text'], 'Nested content\n')
        self.assertEqual(by_ref['slide/0/notes']['text'], 'Presenter-authored explanation.\n')
        self.assertEqual(by_ref['slide/0/element/2/cell/0/1']['text'], 'Right\n')
        self.assertNotIn('DO NOT INGEST', json.dumps(units))

    def test_valid_drafts_retain_snapshot_and_exact_support_without_mutation(self):
        original = deck()
        before = copy.deepcopy(original)
        call = Mock(return_value=json.dumps({'concepts': [{
            'ref': 'slide/0/notes', 'text': 'Presenter-authored explanation.'}]}))
        result = extract_drafts(original, call)
        self.assertEqual(original, before)
        self.assertEqual(result['snapshot_id'], original.snapshot_id)
        self.assertEqual(result['slides'][0]['status'], 'review_required')
        concept = result['slides'][0]['concepts'][0]
        self.assertEqual(concept['support_refs'], ['slide/0/notes'])
        self.assertIsNone(concept['confidence'])
        self.assertEqual(call.call_count, 1)
        self.assertEqual(result['slides'][1]['status'], 'no_supported_text')
        self.assertIn('incomplete_source', result['slides'][1]['limitations'])
        self.assertEqual(result['slides'][2]['status'], 'no_supported_text')

    def test_visual_alt_text_is_not_treated_as_visual_understanding(self):
        self.assertEqual(source_units(deck().slides[1]), [])

    def test_invalid_or_unsupported_model_claims_are_rejected(self):
        bad_results = [
            'not json', '[]', '{"concepts": [], "complete": true}',
            '{"concepts": "yes"}',
            json.dumps({'concepts': [{'ref': 'slide/1/notes', 'text': 'Invented'}]}),
            json.dumps({'concepts': [{'ref': 'slide/0/notes', 'text': 'Invented'}]}),
            json.dumps({'concepts': [{'ref': 'slide/0/notes', 'text': ''}]}),
            json.dumps({'concepts': [{'ref': 'slide/0/notes', 'text': 2}]}),
            json.dumps({'concepts': [{'ref': [], 'text': 'a'}]}),
            json.dumps({'concepts': [{'ref': 'slide/0/notes', 'text': 'Presenter', 'confidence': 1}]}),
            json.dumps({'concepts': [{'ref': 'slide/0/notes', 'text': 'Presenter'}] * 2}),
            json.dumps({'concepts': []} | {'concepts': [None]}),
            '{"concepts": [], "concepts": []}',
        ]
        for body in bad_results:
            with self.subTest(body=body):
                result = extract_drafts(deck(), lambda _: body)
                self.assertEqual(result['slides'][0]['status'], 'failed')
                self.assertEqual(result['slides'][0]['concepts'], [])
                self.assertNotIn(body, result['slides'][0].get('error', ''))

    def test_empty_model_result_never_means_slide_complete(self):
        result = extract_drafts(deck(), lambda _: '{"concepts": []}')
        self.assertEqual(result['slides'][0]['status'], 'review_required')
        self.assertNotIn('slide_complete', json.dumps(result))

    def test_failed_provider_does_not_log_content_or_abort_other_slides(self):
        result = extract_drafts(deck(), Mock(side_effect=RuntimeError('private credential')))
        self.assertEqual(result['slides'][0]['status'], 'failed')
        self.assertNotIn('private credential', json.dumps(result))
        self.assertEqual(len(result['slides']), 3)

    def test_source_size_bound_rejects_without_a_request(self):
        call = Mock()
        result = extract_drafts(deck(), call, max_source_chars=10)
        call.assert_not_called()
        self.assertEqual(result['slides'][0]['status'], 'input_limit')

    def test_messages_treat_source_instructions_as_untrusted_data(self):
        messages = build_messages(deck().slides[0])
        self.assertEqual([m['role'] for m in messages], ['system', 'user'])
        self.assertIn('untrusted', messages[0]['content'])
        self.assertEqual(json.loads(messages[1]['content'])['units'], source_units(deck().slides[0]))

    def test_nested_groups_repetition_and_reorder_keep_local_evidence(self):
        payload = json.loads(Path('tests/fixtures/google_slides_presentation.json').read_text())
        group = payload['slides'][0]['pageElements'][1]
        group['elementGroup']['children'] = [{'objectId': 'inner_group', 'elementGroup': copy.deepcopy(group['elementGroup'])}]
        payload['slides'].reverse()
        changed = normalize_presentation(payload, fetched_at=datetime.now(timezone.utc))
        units = source_units(changed.slides[2])
        self.assertTrue(any(u['ref'] == 'slide/2/element/1/element/0/element/0' for u in units))
        self.assertTrue(all(u['ref'].startswith('slide/2/') for u in units))


if __name__ == '__main__':
    unittest.main()

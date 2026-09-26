"""Three-minute, single-worker synthetic cadence trial with competing jobs."""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from experiments.foundation_probe import CASES, make_deck, messages_for, request_chat, evaluate
from experiments.semantic_coverage import MODEL, load_api_key


def run_trial(api_key, *, updates=36, request=request_chat, clock=time.monotonic, sleep=time.sleep):
    if type(updates) is not int or not 1 <= updates <= 36:
        raise ValueError('Trial must contain 1 to 36 coverage updates')
    report = {'observed_at': datetime.now(timezone.utc).isoformat(), 'model': MODEL,
              'synthetic_only': True, 'workers': 1, 'cadence_seconds': 5,
              'coverage_deadline_seconds': 5, 'updates': updates, 'records': []}
    start = clock()
    for index in range(updates):
        due = start + index * 5
        sleep(max(0, due - clock()))
        case = CASES[index % len(CASES)]
        deck = make_deck(case)
        workloads = ['coverage']
        if index % 6 == 0:
            workloads.append('guidance')
        if index % 12 == 0:
            workloads.append('extraction')
        for workload in workloads:
            began = clock()
            result = request(messages_for(workload, case, deck), api_key, MODEL)
            ended = clock()
            result.update(workload=workload, case=case['name'], update=index + 1,
                          queue_seconds=round(began - due, 6),
                          end_to_end_seconds=round(ended - due, 6),
                          deadline_met=ended - due <= 5)
            result['correct'] = result['usable'] and evaluate(workload, result.get('content'), case, deck)
            report['records'].append(result)
    report['duration_seconds'] = round(clock() - start, 6)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    key = load_api_key(os.environ)
    if not key:
        parser.error('NEBIUS_API_KEY is required locally')
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as output:
        report = run_trial(key)
        json.dump(report, output, indent=2)
        output.write('\n')
    coverage = [r for r in report['records'] if r['workload'] == 'coverage']
    passed = all(r['correct'] for r in report['records']) and all(r['deadline_met'] for r in coverage)
    print(f'{len(report["records"])} requests; coverage deadlines: {sum(r["deadline_met"] for r in coverage)}/{len(coverage)}; passed={passed}')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())

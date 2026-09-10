#!/usr/bin/env python3
"""Freeze independent visual judgments and score CP1 without importing labels.

All benchmark inputs and detailed reports are private local files. A passing
synthetic fixture validates this evaluator, never game-wide search quality.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import platform
import sqlite3
import time

VERSION = 'cp1-evaluation-v1'
STATUSES = {'relevant', 'partial', 'irrelevant', 'uncertain'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def unique(rows, field):
    if not isinstance(rows, list) or any(not isinstance(r, dict) or
            not nonempty(r.get(field)) for r in rows):
        raise ValueError(f'Expected records with {field}')
    result = {r[field]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError(f'Duplicate {field}')
    return result


def verify_views(views, cache):
    if not isinstance(views, list) or not views:
        raise ValueError('Actual hashed image evidence required')
    for view in views:
        if not isinstance(view, dict) or not nonempty(view.get('path')):
            raise ValueError('Evidence path required')
        path = Path(view['path'])
        if not path.is_absolute():
            raise ValueError('Evidence paths must be absolute')
        if str(path) not in cache:
            from PIL import Image
            content = path.read_bytes()
            try:
                with Image.open(io.BytesIO(content)) as image:
                    image.verify()
            except (OSError, SyntaxError) as exc:
                raise ValueError('Evidence must be a decodable image') from exc
            cache[str(path)] = hashlib.sha256(content).hexdigest()
        if cache[str(path)] != view.get('sha256'):
            raise ValueError('Stale or corrupt evidence')


def checks_valid(checks, query):
    checks = unique(checks, 'id')
    expected = {c['id'] for c in query['constraints']}
    if set(checks) != expected:
        raise ValueError('Every explicit constraint needs exactly one check')
    if any(c.get('verdict') not in ('pass', 'fail', 'unknown') or
           not nonempty(c.get('reason')) for c in checks.values()):
        raise ValueError('Constraint verdict and visible reason required')
    return all(c['verdict'] == 'pass' for c in checks.values())


def validate_suite(suite, verify=True):
    if suite.get('version') != VERSION:
        raise ValueError('Unsupported benchmark version')
    protocol = suite.get('protocol', {})
    for key in ('selection', 'independence', 'scope', 'reviewer', 'limitations'):
        if not nonempty(protocol.get(key)):
            raise ValueError(f'Protocol requires {key}')
    if protocol.get('independent_of_retrieval') is not True:
        raise ValueError('Independent candidate discovery required')
    queries = unique(suite.get('queries'), 'id')
    if not queries:
        raise ValueError('Empty benchmark')
    texts = set()
    for q in queries.values():
        if not nonempty(q.get('query')) or q.get('kind') not in ('model', 'texture'):
            raise ValueError('Query text and kind required')
        if q.get('game') not in ('sa', 'vc', 'gta3'):
            raise ValueError('Explicit game required')
        signature = (q['game'], q['kind'], q['query'].strip().casefold())
        if signature in texts:
            raise ValueError('Repeated request text does not add benchmark diversity')
        texts.add(signature)
        constraints = unique(q.get('constraints'), 'id')
        if any(not nonempty(c.get('requirement')) for c in constraints.values()):
            raise ValueError('Constraint requirement required')
    judgments = suite.get('judgments')
    if not isinstance(judgments, list):
        raise ValueError('Judgment array required')
    seen, cache = set(), {}
    for j in judgments:
        qid = j.get('query_id')
        if qid not in queries or j.get('status') not in STATUSES:
            raise ValueError('Unknown query or judgment status')
        keys = j.get('keys')
        if not isinstance(keys, list) or not keys or any(not nonempty(k) for k in keys):
            raise ValueError('Judgment asset keys required')
        if len(set(keys)) != len(keys):
            raise ValueError('Duplicate equivalent key')
        if len(keys) > 1 and (queries[qid]['kind'] != 'texture' or
                not nonempty(j.get('pixel_sha256')) or
                not nonempty(j.get('equivalence_provenance'))):
            raise ValueError('Only independently audited exact texture pixels may be grouped')
        for key in keys:
            if (qid, key) in seen:
                raise ValueError('Overlapping or conflicting judgments')
            seen.add((qid, key))
        if not all(nonempty(j.get(k)) for k in ('reason', 'reviewer')):
            raise ValueError('Judgment reviewer and reason required')
        all_pass = checks_valid(j.get('constraint_checks'), queries[qid])
        if j['status'] == 'relevant' and not all_pass:
            raise ValueError('Direct judgment contradicts explicit constraints')
        if verify:
            verify_views(j.get('views'), cache)
    return queries


def freeze(suite):
    validate_suite(suite)
    return {'benchmark_sha256': digest(suite), 'suite': suite}


def validate_frozen(frozen):
    suite = frozen['suite']
    if digest(suite) != frozen.get('benchmark_sha256'):
        raise ValueError('Frozen benchmark changed')
    return validate_suite(suite)


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def capture(frozen, source, out, mode='semantic', encoder_factory=None, corpus='annotations',
            evaluation_role='diagnostic'):
    """Run the public search implementation on a consistent isolated backup.

    No benchmark labels enter the encoder, annotations, vectors or ranking.
    Existing vectors are checked as-is; building them is an explicit prior step.
    """
    queries = validate_frozen(frozen)
    if mode not in ('semantic', 'hybrid', 'lexical'):
        raise ValueError('Unknown retrieval mode')
    if corpus not in ('annotations', 'metadata'):
        raise ValueError('Unknown semantic corpus')
    if evaluation_role not in ('diagnostic', 'development', 'heldout'):
        raise ValueError('Unknown evaluation role')
    source = Path(source).resolve()
    if not source.is_file():
        raise ValueError('Existing source database required')
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    snapshot = out / 'snapshot.sqlite'
    original = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
    backup = sqlite3.connect(snapshot)
    try:
        original.backup(backup)
    finally:
        backup.close()
        original.close()
    import asset_catalog as catalog
    import asset_catalog_semantic as semantic
    db = catalog.connect(snapshot)
    try:
        semantic.setup(db)
        db.commit()
        snapshot_hash = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        start = time.monotonic()
        encoder = (encoder_factory or semantic.Encoder)() if mode != 'lexical' else None
        load_seconds = time.monotonic() - start
        run = {'benchmark_sha256': frozen['benchmark_sha256'],
               'snapshot_sha256': snapshot_hash,
               'system': (encoder.identity if encoder else 'SQLite FTS5') + ':' + mode + ':' + corpus,
               'mode': mode, 'corpus': corpus if encoder else None,
               'evaluation_role': evaluation_role, 'platform': platform.platform(),
               'encoder_load_seconds': load_seconds, 'results': []}
        for q in queries.values():
            start = time.monotonic()
            if mode == 'lexical':
                hits = catalog.search(db, q['query'], limit=30, game=q['game'], kind=q['kind'])
                coverage = None
            else:
                result = semantic.search(db, encoder, q['query'], limit=30,
                    game=q['game'], kind=q['kind'], corpus=corpus, hybrid=mode == 'hybrid',
                    diversify_pixels=True)
                hits, coverage = result['results'], result['coverage']
            run['results'].append({'query_id': q['id'], 'keys': [r['key'] for r in hits],
                                   'coverage': coverage, 'seconds': time.monotonic() - start})
        run['query_seconds'] = sum(r['seconds'] for r in run['results'])
        # DB contents must remain stable throughout retrieval. Evidence files
        # are independently revalidated by search and by benchmark scoring.
        if hashlib.sha256(snapshot.read_bytes()).hexdigest() != snapshot_hash:
            raise ValueError('Catalogue changed while capturing rankings')
        write_new(out / 'run.json', run)
        write_new(out / 'benchmark.json', frozen)
        return run
    finally:
        db.close()


def evaluate(frozen, run, decisions=None, audit=None):
    """Score one fixed top-30 ranking and separate final visual decisions.

    Unknown labels never become negatives or successes. Recall counts every
    independent known positive, including candidates without embeddings.
    Equivalent pixel groups contribute once, preserving all occurrence keys.
    """
    queries = validate_frozen(frozen)
    identity = frozen['benchmark_sha256']
    if run.get('benchmark_sha256') != identity:
        raise ValueError('Ranking/benchmark mismatch')
    if not nonempty(run.get('system')) or not nonempty(run.get('snapshot_sha256')):
        raise ValueError('System and catalogue snapshot identity required')
    rows = unique(run.get('results'), 'query_id')
    if set(rows) != set(queries):
        raise ValueError('Missing or unexpected query results')
    for row in rows.values():
        keys = row.get('keys')
        if not isinstance(keys, list) or len(keys) != len(set(keys)) or any(
                not nonempty(key) for key in keys):
            raise ValueError('Ranking must contain distinct asset keys')
    final = {}
    if decisions is not None:
        if decisions.get('run_sha256') != digest(run):
            raise ValueError('Decisions belong to a different ranking run')
        if not nonempty(decisions.get('reviewer')) or not nonempty(decisions.get('protocol')):
            raise ValueError('Final reviewer and protocol required')
        final = unique(decisions.get('results'), 'query_id')
        if set(final) != set(queries):
            raise ValueError('Explicit answer or abstention required for every query')
    judgments = frozen['suite']['judgments']
    labels = {(j['query_id'], k): j for j in judgments for k in j['keys']}
    if audit is not None:
        if audit.get('run_sha256') != digest(run) or not nonempty(audit.get('reviewer')):
            raise ValueError('Independent audit must identify its ranking run and reviewer')
        audit_suite = dict(frozen['suite'], judgments=audit.get('judgments'))
        validate_suite(audit_suite)
        for j in audit_suite['judgments']:
            for key in j['keys']:
                pair = (j['query_id'], key)
                if key not in rows[j['query_id']]['keys'][:30]:
                    raise ValueError('Additional audit candidate is outside fixed top 30')
                previous = labels.get(pair)
                if previous and (previous['status'] != j['status'] or
                        {c['id']: c['verdict'] for c in previous['constraint_checks']} !=
                        {c['id']: c['verdict'] for c in j['constraint_checks']}):
                    raise ValueError('Conflicting audit requires explicit adjudication in a new benchmark')
                labels[pair] = j
    # Retrieved-only audit positives must not change the independent recall
    # denominator or redefine which original requests have known positives.
    positives = [j for j in judgments if j['status'] == 'relevant']
    positive_queries = {j['query_id'] for j in positives}
    recalled = sum(bool(set(j['keys']) & set(rows[j['query_id']]['keys'][:30]))
                   for j in positives)
    accepted = direct = unjudged = violations = answered = abstained = 0
    raw_direct = raw_judged = raw_positions = 0
    per_query = []
    evidence_cache = {}
    for qid, q in queries.items():
        ranked = rows[qid]['keys']
        top5 = ranked[:5]
        raw_positions += len(top5)
        raw_judged += sum((qid, k) in labels for k in top5)
        raw_direct += sum(labels.get((qid, k), {}).get('status') == 'relevant' for k in top5)
        known = [j for j in positives if j['query_id'] == qid]
        misses = [j['keys'] for j in known if not set(j['keys']) & set(ranked[:30])]
        item = {'query_id': qid, 'known_direct': len(known), 'missed_direct_keys': misses,
                'coverage': rows[qid].get('coverage'), 'seconds': rows[qid].get('seconds')}
        if decisions is not None:
            decision = final[qid]
            answers = unique(decision.get('accepted'), 'key')
            if decision.get('decision') != ('answered' if answers else 'abstained'):
                raise ValueError('Decision contradicts accepted answers')
            if not nonempty(decision.get('reason')):
                raise ValueError('Decision reason required')
            query_direct = 0
            for key, answer in answers.items():
                if key not in ranked[:30]:
                    raise ValueError('Final answer was not in the fixed top 30')
                if not nonempty(answer.get('reason')):
                    raise ValueError('Visible answer reason required')
                all_pass = checks_valid(answer.get('constraint_checks'), q)
                verify_views(answer.get('views'), evidence_cache)
                accepted += 1
                label = labels.get((qid, key))
                if label is None:
                    unjudged += 1
                elif label['status'] == 'relevant' and all_pass:
                    direct += 1
                    query_direct += 1
                # Negative and failed-constraint controls are assessed against
                # independent labels, not the answerer's self-reported pass.
                if not all_pass or (label and (label['status'] == 'irrelevant' or
                        any(c['verdict'] == 'fail' for c in label['constraint_checks']))):
                    violations += 1
            if qid in positive_queries and query_direct:
                answered += 1
            if not answers:
                abstained += 1
            item['accepted'] = len(answers)
            item['independent_direct_answers'] = query_direct
        per_query.append(item)
    precision = ratio(direct, accepted)
    answer_rate = ratio(answered, len(positive_queries)) if decisions is not None else None
    recall = ratio(recalled, len(positives))
    controls = sum(j['status'] == 'irrelevant' or
                   any(c['verdict'] == 'fail' for c in j['constraint_checks']) for j in judgments)
    gates = {
        'heldout_run_explicitly_declared': run.get('evaluation_role') == 'heldout',
        'at_least_24_requests': len(queries) >= 24,
        'at_least_100_independent_judgments': len(judgments) >= 100,
        'negative_controls_present': controls > 0,
        'related_distractors_present': any(j['status'] == 'partial' for j in judgments),
        'explicit_constraints_present': any(q['constraints'] for q in queries.values()),
        'final_decisions_present': decisions is not None,
        'final_review_independent_of_ground_truth': decisions is not None and
            decisions.get('independent_of_ground_truth') is True,
        'additional_audit_independent_of_answers': audit is None or
            audit.get('independent_of_answers') is True,
        'all_accepted_answers_independently_judged': decisions is not None and unjudged == 0,
        'direct_precision_at_least_85_percent': precision is not None and precision >= .85,
        'positive_answer_rate_at_least_80_percent': answer_rate is not None and answer_rate >= .80,
        'known_direct_recall_at_30_at_least_90_percent': recall is not None and recall >= .90,
        'zero_verified_control_violations': decisions is not None and violations == 0,
    }
    return {
        'version': VERSION, 'benchmark_sha256': identity, 'run_sha256': digest(run),
        'evaluation_role': run.get('evaluation_role', 'unspecified'),
        'passed': all(gates.values()), 'gates': gates,
        'requests': len(queries), 'independent_judgments': len(judgments),
        'known_direct_candidates': len(positives), 'known_positive_requests': len(positive_queries),
        'recalled_direct_at_30': recalled, 'known_direct_recall_at_30': recall,
        'raw_top5': {'positions': raw_positions, 'independently_judged': raw_judged,
                     'direct': raw_direct, 'judgment_coverage': ratio(raw_judged, raw_positions),
                     'direct_lower_bound': ratio(raw_direct, raw_positions),
                     'precision': ratio(raw_direct, raw_positions) if raw_judged == raw_positions else None},
        'final': {'accepted': accepted, 'independent_direct': direct, 'unjudged': unjudged,
                  'precision_lower_bound': precision, 'positive_requests_answered': answered,
                  'positive_answer_rate': answer_rate, 'abstentions': abstained,
                  'verified_control_violations': violations},
        'per_query': per_query,
        'limitations': 'Finite independently discovered candidate pool, not exhaustive game recall. '
                      'Unknown accepted labels block acceptance. Independence and pixel-equivalence '
                      'provenance require external review; hashes only establish unchanged inputs.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('freeze', help='Hash and validate a private benchmark before tuning')
    p.add_argument('--suite', required=True)
    p.add_argument('--out', required=True)
    p = commands.add_parser('run', help='Capture real top-30 search on an isolated database backup')
    p.add_argument('--benchmark', required=True)
    p.add_argument('--db', required=True)
    p.add_argument('--mode', choices=['semantic', 'hybrid', 'lexical'], default='semantic')
    p.add_argument('--corpus', choices=['annotations', 'metadata'], default='annotations',
                   help='Explicit separate semantic corpus; metadata hits are not visual evidence')
    p.add_argument('--role', choices=['diagnostic', 'development', 'heldout'], default='diagnostic',
                   help='Only a separately declared held-out run may pass CP1; never relabel tuned cases')
    p.add_argument('--out', required=True, help='New local directory; existing runs are never overwritten')
    p = commands.add_parser('score', help='Score rankings and independent final decisions')
    p.add_argument('--benchmark', required=True)
    p.add_argument('--run', required=True)
    p.add_argument('--decisions')
    p.add_argument('--audit', help='Optional separate blind audit of retrieved answers; never used for recall')
    p.add_argument('--out', required=True)
    args = parser.parse_args()
    if args.command == 'freeze':
        result = freeze(read(args.suite))
    elif args.command == 'run':
        result = capture(read(args.benchmark), args.db, args.out, args.mode, corpus=args.corpus,
                         evaluation_role=args.role)
        print(json.dumps({'output': str(Path(args.out).resolve() / 'run.json'),
                          'queries': len(result['results']),
                          'query_seconds': result['query_seconds']}, indent=2))
        return
    else:
        result = evaluate(read(args.benchmark), read(args.run),
                          read(args.decisions) if args.decisions else None,
                          read(args.audit) if args.audit else None)
    write_new(args.out, result)
    print(json.dumps({'output': str(Path(args.out).resolve()),
                      'benchmark_sha256': result['benchmark_sha256'],
                      'passed': result.get('passed')}, indent=2))
    if args.command == 'score' and not result['passed']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()

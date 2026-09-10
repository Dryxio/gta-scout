import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import asset_catalog_evaluate as ev


class EvaluationTests(unittest.TestCase):
    """Original toy evidence only; these passes are not CP1 game results."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.image = Path(self.tmp.name) / 'original.png'
        Image.new('RGB', (8, 8), 'red').save(self.image)
        self.views = [{'path': str(self.image),
                       'sha256': hashlib.sha256(self.image.read_bytes()).hexdigest()}]
        self.suite = {'version': ev.VERSION, 'protocol': {
            'selection': 'Original deterministic synthetic fixtures.',
            'independence': 'Test roles only, not an actual visual evaluation.',
            'independent_of_retrieval': True, 'scope': 'Synthetic',
            'reviewer': 'fixture author', 'limitations': 'No GTA claims.'},
            'queries': [], 'judgments': []}
        self.run = {'system': 'synthetic', 'snapshot_sha256': 'synthetic',
                    'evaluation_role': 'heldout', 'results': []}
        self.decisions = {'reviewer': 'synthetic answerer',
                          'independent_of_ground_truth': True,
                          'protocol': 'Synthetic independent roles', 'results': []}
        for i in range(24):
            qid = f'q{i}'
            query = {'id': qid, 'query': f'Original toy request {i}', 'kind': 'model',
                     'game': 'sa', 'constraints': [{'id': 'red', 'requirement': 'Red surface'}]}
            self.suite['queries'].append(query)
            keys = []
            for n, status in enumerate(['relevant', 'partial', 'irrelevant', 'uncertain', 'irrelevant']):
                key = f'sa:model:{i * 10 + n}'
                keys.append(key)
                self.suite['judgments'].append({
                    'query_id': qid, 'keys': [key], 'status': status,
                    'reason': 'Original synthetic label', 'reviewer': 'fixture auditor',
                    'views': copy.deepcopy(self.views),
                    'constraint_checks': self.checks('pass' if n == 0 else 'fail')})
            self.run['results'].append({'query_id': qid, 'keys': keys})
            self.decisions['results'].append({'query_id': qid, 'decision': 'answered',
                'reason': 'Original synthetic decision', 'accepted': [{
                    'key': keys[0], 'reason': 'Original red toy evidence',
                    'views': copy.deepcopy(self.views), 'constraint_checks': self.checks('pass')}]})
        self.bind()

    def checks(self, verdict):
        return [{'id': 'red', 'verdict': verdict, 'reason': 'Synthetic visual reason'}]

    def bind(self):
        self.frozen = ev.freeze(self.suite)
        self.run['benchmark_sha256'] = self.frozen['benchmark_sha256']
        self.decisions['run_sha256'] = ev.digest(self.run)

    def score(self):
        return ev.evaluate(self.frozen, self.run, self.decisions)

    def test_complete_synthetic_fixture(self):
        result = self.score()
        self.assertTrue(result['passed'])
        self.assertEqual(result['known_direct_recall_at_30'], 1)
        self.assertEqual(result['final']['precision_lower_bound'], 1)
        self.assertEqual(result['raw_top5']['precision'], .2)

    def test_self_selected_ground_truth_answers_cannot_close_checkpoint(self):
        self.decisions['independent_of_ground_truth'] = False
        self.assertFalse(self.score()['passed'])

    def test_tuned_development_run_cannot_close_checkpoint_even_with_perfect_metrics(self):
        for role in ('development', 'diagnostic', None):
            self.run['evaluation_role'] = role
            self.decisions['run_sha256'] = ev.digest(self.run)
            result = self.score()
            self.assertEqual(result['known_direct_recall_at_30'], 1)
            self.assertEqual(result['final']['precision_lower_bound'], 1)
            self.assertFalse(result['passed'])
            self.assertFalse(result['gates']['heldout_run_explicitly_declared'])

    def test_duplicate_request_text_does_not_inflate_sample_size(self):
        self.suite['queries'][1]['query'] = self.suite['queries'][0]['query']
        with self.assertRaises(ValueError):
            ev.freeze(self.suite)

    def test_capture_uses_real_search_and_preserves_source_database(self):
        import asset_catalog as catalog
        source = Path(self.tmp.name) / 'source.sqlite'
        db = catalog.connect(source)
        payload = {'record': {'name': 'Original toy request'}, 'hints': [], 'catalogSource': 'fixture'}
        db.execute('INSERT INTO assets VALUES (?,?,?,?,?,?)',
                   ('sa:model:0', 'sa', 'model', 'Original toy request', 'h', json.dumps(payload)))
        catalog.searchable(db, 'sa:model:0', 'Original toy request', payload, 'h')
        db.commit()
        db.close()
        before = source.read_bytes()
        out = Path(self.tmp.name) / 'captured'
        run = ev.capture(self.frozen, source, out, 'lexical')
        self.assertEqual(len(run['results']), 24)
        self.assertIn('sa:model:0', run['results'][0]['keys'])
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(run['snapshot_sha256'],
                         hashlib.sha256((out / 'snapshot.sqlite').read_bytes()).hexdigest())
        with self.assertRaises(FileExistsError):
            ev.capture(self.frozen, source, out, 'lexical')

    def test_capture_keeps_semantic_corpus_explicit(self):
        import asset_catalog as catalog
        import asset_catalog_semantic as semantic
        import numpy as np
        class Encoder:
            identity = 'synthetic-corpus-test'
            def encode(self, texts, query=False):
                return np.asarray([[1., 0.] for _ in texts])
        source = Path(self.tmp.name) / 'metadata.sqlite'
        db = catalog.connect(source)
        payload = {'record': {'name': 'toy'}, 'hints': [], 'catalogSource': 'fixture'}
        db.execute('INSERT INTO assets VALUES (?,?,?,?,?,?)',
                   ('sa:model:0', 'sa', 'model', 'toy', 'h', json.dumps(payload)))
        db.commit()
        semantic.build(db, Encoder(), 'metadata')
        db.close()
        metadata = ev.capture(self.frozen, source, Path(self.tmp.name) / 'metadata-run',
                              encoder_factory=Encoder, corpus='metadata')
        annotations = ev.capture(self.frozen, source, Path(self.tmp.name) / 'annotation-run',
                                 encoder_factory=Encoder)
        self.assertEqual(metadata['corpus'], 'metadata')
        self.assertEqual(metadata['results'][0]['keys'], ['sa:model:0'])
        self.assertEqual(metadata['results'][0]['coverage']['freshMetadataOnlyDocuments'], 1)
        self.assertEqual(annotations['results'][0]['keys'], [])
        self.assertNotEqual(metadata['system'], annotations['system'])

    def test_all_abstentions_do_not_pass_precision_or_answer_rate(self):
        for row in self.decisions['results']:
            row.update(decision='abstained', accepted=[])
        result = self.score()
        self.assertFalse(result['passed'])
        self.assertIsNone(result['final']['precision_lower_bound'])
        self.assertEqual(result['final']['positive_answer_rate'], 0)
        self.assertEqual(result['final']['abstentions'], 24)

    def test_missing_final_is_not_perfect_precision(self):
        result = ev.evaluate(self.frozen, self.run)
        self.assertFalse(result['passed'])
        self.assertIsNone(result['final']['precision_lower_bound'])
        self.assertIsNone(result['final']['positive_answer_rate'])

    def test_recall_includes_unannotated_candidates_and_rank_31_is_miss(self):
        self.run['results'][0]['keys'] = [f'unknown-{i}' for i in range(30)] + ['sa:model:0']
        self.run['results'][0]['coverage'] = {'freshEmbeddedDocuments': 0}
        result = ev.evaluate(self.frozen, self.run)
        self.assertEqual(result['known_direct_candidates'], 24)
        self.assertEqual(result['recalled_direct_at_30'], 23)
        self.assertIsNone(result['raw_top5']['precision'])

    def test_texture_groups_count_once_and_match_any_audited_occurrence(self):
        self.suite['queries'][0]['kind'] = 'texture'
        j = self.suite['judgments'][0]
        j.update(keys=['texture-a', 'texture-b'], pixel_sha256='audited-rgba',
                 equivalence_provenance='Synthetic exact pixel audit')
        self.run['results'][0]['keys'][0] = 'texture-b'
        self.decisions['results'][0]['accepted'][0]['key'] = 'texture-b'
        self.bind()
        self.assertEqual(self.score()['known_direct_candidates'], 24)
        self.assertEqual(self.score()['recalled_direct_at_30'], 24)

    def test_name_only_equivalence_rejected(self):
        self.suite['judgments'][0]['keys'].append('same-name')
        with self.assertRaises(ValueError):
            ev.freeze(self.suite)

    def test_accepted_negative_fails_even_if_answerer_claims_pass(self):
        self.decisions['results'][0]['accepted'][0]['key'] = 'sa:model:2'
        result = self.score()
        self.assertEqual(result['final']['verified_control_violations'], 1)
        self.assertFalse(result['passed'])

    def test_unknown_accepted_answer_blocks_acceptance(self):
        self.run['results'][0]['keys'].insert(0, 'unjudged')
        self.decisions['results'][0]['accepted'][0]['key'] = 'unjudged'
        self.bind()
        result = self.score()
        self.assertEqual(result['final']['unjudged'], 1)
        self.assertFalse(result['passed'])
        self.assertIsNone(result['raw_top5']['precision'])

    def test_separate_audit_does_not_inflate_independent_recall_denominator(self):
        self.run['results'][0]['keys'].insert(0, 'new-retrieved')
        self.decisions['results'][0]['accepted'][0]['key'] = 'new-retrieved'
        self.bind()
        j = copy.deepcopy(self.suite['judgments'][0])
        j['keys'] = ['new-retrieved']
        audit = {'run_sha256': ev.digest(self.run), 'reviewer': 'blind auditor',
                 'independent_of_answers': True, 'judgments': [j]}
        result = ev.evaluate(self.frozen, self.run, self.decisions, audit)
        self.assertTrue(result['passed'])
        self.assertEqual(result['known_direct_candidates'], 24)
        self.assertEqual(result['final']['independent_direct'], 24)
        audit['independent_of_answers'] = False
        self.assertFalse(ev.evaluate(self.frozen, self.run, self.decisions, audit)['passed'])

    def test_audit_conflict_does_not_overwrite_historical_failure(self):
        j = copy.deepcopy(self.suite['judgments'][2])
        j['status'] = 'relevant'
        j['constraint_checks'] = self.checks('pass')
        audit = {'run_sha256': ev.digest(self.run), 'reviewer': 'blind auditor',
                 'independent_of_answers': True, 'judgments': [j]}
        with self.assertRaises(ValueError):
            ev.evaluate(self.frozen, self.run, self.decisions, audit)

    def test_failed_and_unknown_answer_constraints_are_not_direct(self):
        for verdict in ('fail', 'unknown'):
            self.decisions['results'][0]['accepted'][0]['constraint_checks'] = self.checks(verdict)
            result = self.score()
            self.assertEqual(result['final']['independent_direct'], 23)
            self.assertFalse(result['passed'])

    def test_benchmark_mutation_detected(self):
        self.frozen['suite']['queries'][0]['query'] = 'tuned query'
        with self.assertRaises(ValueError):
            self.score()

    def test_evidence_change_detected_after_freeze(self):
        self.image.write_bytes(b'corrupted')
        with self.assertRaises(ValueError):
            self.score()

    def test_matching_hash_of_non_image_does_not_establish_visual_evidence(self):
        self.image.write_bytes(b'not an image')
        invalid_hash = hashlib.sha256(self.image.read_bytes()).hexdigest()
        for j in self.suite['judgments']:
            j['views'][0]['sha256'] = invalid_hash
        with self.assertRaises(ValueError):
            ev.freeze(self.suite)

    def test_consistent_blind_audit_can_explain_verdict_in_different_words(self):
        j = copy.deepcopy(self.suite['judgments'][0])
        j['constraint_checks'][0]['reason'] = 'An independently worded explanation'
        audit = {'run_sha256': ev.digest(self.run), 'reviewer': 'blind auditor',
                 'independent_of_answers': True, 'judgments': [j]}
        self.assertTrue(ev.evaluate(self.frozen, self.run, self.decisions, audit)['passed'])

    def test_missing_evidence_is_not_silently_dropped(self):
        self.image.unlink()
        with self.assertRaises(OSError):
            self.score()

    def test_judgment_overlap_rejected(self):
        self.suite['judgments'].append(copy.deepcopy(self.suite['judgments'][0]))
        with self.assertRaises(ValueError):
            ev.freeze(self.suite)

    def test_wrong_run_or_duplicate_rank_rejected(self):
        self.run['results'][0]['keys'].append('sa:model:0')
        with self.assertRaises(ValueError):
            self.score()

    def test_missing_query_not_removed_from_denominator(self):
        self.run['results'].pop()
        with self.assertRaises(ValueError):
            self.score()

    def test_missing_decision_requires_explicit_abstention(self):
        self.decisions['results'].pop()
        with self.assertRaises(ValueError):
            self.score()

    def test_final_answer_outside_fixed_pool_rejected(self):
        self.decisions['results'][0]['accepted'][0]['key'] = 'outside'
        with self.assertRaises(ValueError):
            self.score()

    def test_missing_or_duplicate_constraint_check_rejected(self):
        answer = self.decisions['results'][0]['accepted'][0]
        for checks in ([], self.checks('pass') * 2):
            answer['constraint_checks'] = checks
            with self.assertRaises(ValueError):
                self.score()

    def test_frozen_files_cannot_be_overwritten(self):
        path = Path(self.tmp.name) / 'frozen.json'
        ev.write_new(path, self.frozen)
        with self.assertRaises(FileExistsError):
            ev.write_new(path, {})

    def test_cli_failing_gate_is_nonzero_and_writes_report(self):
        root = Path(self.tmp.name)
        ev.write_new(root / 'benchmark.json', self.frozen)
        ev.write_new(root / 'run.json', self.run)
        result = subprocess.run([sys.executable, ev.__file__, 'score', '--benchmark',
            str(root / 'benchmark.json'), '--run', str(root / 'run.json'), '--out',
            str(root / 'score.json')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(ev.read(root / 'score.json')['passed'])


if __name__ == '__main__':
    unittest.main()

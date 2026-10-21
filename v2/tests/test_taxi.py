"""Artifact checks use native v2 result shapes; no Redis or v1 dependencies."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from smoke import SmokeError
from taxi import check_build


class TaxiResultTests(unittest.TestCase):
    def write(self, directory, status='success', kind='model', config=None, present=True):
        target = Path(directory)
        node = dict(resource_type=kind, config=config or {})
        (target / 'manifest.json').write_text(json.dumps({'nodes': {'fixture': node}, 'unit_tests': {}}))
        results = [{'unique_id': 'fixture', 'status': status}] if present else []
        (target / 'run_results.json').write_text(json.dumps({'results': results}))
        return target

    def test_uppercase_warn_is_only_accepted_for_explicit_warning_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            check_build(self.write(directory, 'warn', 'test', {'severity': 'WARN'}))
            for kind in ['model', 'seed', 'snapshot', 'unit_test']:
                with self.subTest(kind=kind), self.assertRaises(SmokeError):
                    check_build(self.write(directory, 'warn', kind, {'severity': 'WARN'}))
            with self.assertRaises(SmokeError):
                check_build(self.write(directory, 'warn', 'test', {'severity': 'ERROR'}))

    def test_missing_executable_results_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            for kind in ['model', 'seed', 'snapshot', 'test', 'unit_test']:
                with self.subTest(kind=kind), self.assertRaises(SmokeError):
                    check_build(self.write(directory, kind=kind, present=False))

    def test_only_ephemeral_models_may_be_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            check_build(self.write(directory, 'skipped', 'model', {'materialized': 'ephemeral'}))
            with self.assertRaises(SmokeError):
                check_build(self.write(directory, 'skipped', 'model', {'materialized': 'table'}))

    def test_all_failure_statuses_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            for status in ['fail', 'error', 'skipped', 'unknown']:
                with self.subTest(status=status), self.assertRaises(SmokeError):
                    check_build(self.write(directory, status))


if __name__ == '__main__':
    unittest.main()

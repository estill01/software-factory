"""Exercise the native release layout outside the source checkout."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[2]
MANIFEST = SOURCE / 'supervise-tracker-runs/assets/native-release-paths.json'
TRACKER = '''# Installation probe
| Block | Scope | Depends on | Status |
| --- | --- | --- | --- |
| 0 | Verify packaged owner | — | complete |
## Block 0 — Verify packaged owner
Status: complete
'''


class NativeReleaseTests(unittest.TestCase):
    def probe(self, omit_program=False):
        with tempfile.TemporaryDirectory() as temporary:
            release = Path(temporary) / 'release'
            release.mkdir()
            for relative in json.loads(MANIFEST.read_text()):
                if omit_program and relative.endswith('/program_revision.py'):
                    continue
                source, destination = SOURCE / relative, release / relative
                if source.is_dir():
                    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__'))
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)
            tracker = Path(temporary) / 'tracker.md'
            tracker.write_text(TRACKER)
            return subprocess.run(
                [sys.executable, '-I', '-B', '-c',
                 'import sys; sys.path.insert(0, sys.argv[1]); '
                 'import supervision_log as helper; '
                 'snapshot = helper.implementation_tracker_snapshot(sys.argv[2]); '
                 'assert snapshot[3][0]["status"] == "completed"; '
                 'helper.program_revision_module()._load_full_verifier(); '
                 'print("packaged-range-owner=pass")',
                 str(release / 'supervise-tracker-runs/scripts'), str(tracker)],
                cwd=temporary, capture_output=True, text=True, check=False)

    def test_manifest_resolves_range_and_full_verifier_without_source_checkout(self):
        result = self.probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'packaged-range-owner=pass')

    def test_missing_program_verifier_fails_closed(self):
        result = self.probe(omit_program=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Program revision verifier cannot be loaded', result.stderr)
        self.assertNotIn('packaged-range-owner=pass', result.stdout)


if __name__ == '__main__':
    unittest.main()

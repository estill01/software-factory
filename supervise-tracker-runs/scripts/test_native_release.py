"""Exercise the native release layout outside the source checkout."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
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
    def probe(self, omit_program=False, implementation=False, omit_implementation=False):
        with tempfile.TemporaryDirectory() as temporary:
            release = Path(temporary) / 'release'
            release.mkdir()
            for relative in json.loads(MANIFEST.read_text()):
                if omit_program and relative.endswith('/program_revision.py'):
                    continue
                if omit_implementation and relative == 'implement-tracker-blocks':
                    continue
                source, destination = SOURCE / relative, release / relative
                if source.is_dir():
                    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__'))
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)
            tracker = Path(temporary) / 'tracker.md'
            tracker.write_text(TRACKER)
            expected = {
                str(path.relative_to(SOURCE)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (SOURCE / 'implement-tracker-blocks').rglob('*')
                if path.is_file() and '__pycache__' not in path.parts
            } if implementation else {}
            implementation_probe = '''
import hashlib
import json
from pathlib import Path
release = Path(sys.argv[1]).parents[1]
for relative, expected in json.loads(sys.argv[3]).items():
    path = release / relative
    assert path.resolve().is_relative_to(release)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative
sys.path.insert(0, str(release / 'implement-tracker-blocks/scripts'))
import target_class_protocol as protocol
import candidate_cutover as cutover
assert protocol.ROOT == release
assert Path(protocol.program_revision.__file__).is_relative_to(release)
assert Path(protocol.supervision.__file__).is_relative_to(release)
assert Path(cutover._supervision_module().__file__).is_relative_to(release)
protocol.program_revision._load_full_verifier()
print("packaged-implementation-owner=pass")
''' if implementation else ''
            return subprocess.run(
                [sys.executable, '-I', '-B', '-c',
                 'import sys; sys.path.insert(0, sys.argv[1]); '
                 'import supervision_log as helper; '
                 'snapshot = helper.implementation_tracker_snapshot(sys.argv[2]); '
                 'assert snapshot[3][0]["status"] == "completed"; '
                 'helper.program_revision_module()._load_full_verifier(); '
                 'print("packaged-range-owner=pass")\n' + implementation_probe,
                 str(release / 'supervise-tracker-runs/scripts'), str(tracker),
                 json.dumps(expected)],
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

    def test_complete_implementation_bytes_and_owner_imports_resolve_outside_checkout(self):
        result = self.probe(implementation=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('packaged-implementation-owner=pass', result.stdout)

    def test_missing_implementation_package_cannot_satisfy_discovery(self):
        result = self.probe(implementation=True, omit_implementation=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FileNotFoundError', result.stderr)
        self.assertNotIn('packaged-implementation-owner=pass', result.stdout)

    def test_git_archive_preserves_reviewed_instructions_and_both_source_substitutions(self):
        if not (SOURCE / '.git').exists():
            self.skipTest('Git export comparison requires the source checkout.')
        paths = [
            'implement-tracker-blocks/SKILL.md',
            'implement-tracker-blocks/references/adaptive-decision-control.md',
            'implement-tracker-blocks/scripts/adaptive_protocol_dogfood.py',
            'supervise-tracker-runs/scripts/factory_evolution_dogfood.py',
        ]
        revision = subprocess.check_output(
            ['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
        archive = subprocess.check_output(
            ['git', '-C', str(SOURCE), 'archive', revision, '--', *paths])
        with tarfile.open(fileobj=io.BytesIO(archive)) as exported:
            for relative in paths:
                expected = (SOURCE / relative).read_bytes()
                if relative.endswith('.py'):
                    expected = expected.replace(b'$Format:%H$', revision.encode())
                with exported.extractfile(relative) as source:
                    self.assertEqual(source.read(), expected, relative)


if __name__ == '__main__':
    unittest.main()

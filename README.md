# Software Factory

Custom Codex skills that author, implement,
and supervise bounded implementation trackers:

- `author-implementation-trackers`
- `implement-tracker-blocks`
- `supervise-tracker-runs`

The repository is rooted at the live Codex skills directory so edits are
immediately usable without copying or symlinking. Codex-managed `.system`
skills, generated Python bytecode, and local supervision runtime state are not
tracked.

## Validation

Validate each skill with the maintained skill validator. The supervision skill
also owns focused helper tests:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  ~/.codex/skills/author-implementation-trackers
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  ~/.codex/skills/implement-tracker-blocks
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  ~/.codex/skills/supervise-tracker-runs
python3 ~/.codex/skills/supervise-tracker-runs/scripts/test_supervision_log.py -v
```

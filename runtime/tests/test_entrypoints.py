from __future__ import annotations

import json
import tempfile
from pathlib import Path

from software_factory.cli import main as cli_main
from software_factory.daemon import main as daemon_main
from software_factory.native_skills import main as skill_main


def test_cli_init_health_and_create_mission(capsys) -> None:
    with tempfile.TemporaryDirectory() as temp:
        home = Path(temp) / "state"
        assert cli_main(["--home", str(home), "init"]) == 0
        initialized = json.loads(capsys.readouterr().out)
        assert initialized["initialized"] is True
        assert Path(initialized["database"]).exists()

        assert cli_main(["--home", str(home), "health"]) == 0
        assert json.loads(capsys.readouterr().out)["ok"] is True

        assert (
            cli_main(
                [
                    "--home",
                    str(home),
                    "create-mission",
                    "Build",
                    "Produce a verified capability",
                ]
            )
            == 0
        )
        mission_id = json.loads(capsys.readouterr().out)["mission_id"]
        assert mission_id.startswith("mis_")

        assert cli_main(["--home", str(home), "tick", mission_id]) == 0
        tick = json.loads(capsys.readouterr().out)
        assert tick["posture"]["action"] in {
            "run_terminal_verification",
            "diagnose_reflect_or_replan",
        }


def test_daemon_once_and_skill_bridge(capsys) -> None:
    with tempfile.TemporaryDirectory() as temp:
        home = Path(temp) / "state"
        cli_main(
            [
                "--home",
                str(home),
                "create-mission",
                "Build",
                "Produce a verified capability",
            ]
        )
        mission_id = json.loads(capsys.readouterr().out)["mission_id"]
        assert daemon_main(["--home", str(home), "--once"]) == 0
        assert (
            skill_main(
                [
                    "author-implementation-trackers",
                    "--home",
                    str(home),
                    "--mission",
                    mission_id,
                    "--payload",
                    '{"source":"request"}',
                ]
            )
            == 0
        )
        output = json.loads(capsys.readouterr().out)
        assert output["mission_id"] == mission_id
        assert output["boundary_type"] == "checkpoint"


def test_all_native_skill_wrappers_dispatch_real_runtime_services(capsys) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        home = root / "state"
        source = root / "migration-source"
        source.mkdir()
        (source / "evidence.json").write_text('{"status":"historical"}\n')
        assert (
            cli_main(
                [
                    "--home",
                    str(home),
                    "create-mission",
                    "Native skills",
                    "Exercise every installed wrapper against the canonical runtime",
                ]
            )
            == 0
        )
        mission_id = json.loads(capsys.readouterr().out)["mission_id"]

        assert (
            skill_main(
                [
                    "implement-tracker-blocks",
                    "--home",
                    str(home),
                    "--mission",
                    mission_id,
                    "--payload",
                    '{"max_dispatch":1}',
                ]
            )
            == 0
        )
        implementation = json.loads(capsys.readouterr().out)
        assert implementation["mission_id"] == mission_id
        assert "controller" in implementation
        assert "continuation" in implementation

        for skill in ("supervise-tracker-runs", "evolve-product-program"):
            assert (
                skill_main(
                    [
                        skill,
                        "--home",
                        str(home),
                        "--mission",
                        mission_id,
                    ]
                )
                == 0
            )
            reconciled = json.loads(capsys.readouterr().out)
            assert reconciled["mission_id"] == mission_id
            assert "evolution_checkpoint" in reconciled

        payload = json.dumps({"action": "migration_inventory", "source_root": str(source)})
        assert (
            skill_main(
                [
                    "clean-software-factory",
                    "--home",
                    str(home),
                    "--mission",
                    mission_id,
                    "--payload",
                    payload,
                ]
            )
            == 0
        )
        cleanup = json.loads(capsys.readouterr().out)
        assert cleanup["source_root"] == str(source.resolve())
        assert cleanup["status"] == "inventoried"
        assert len(cleanup["source_inventory_root"]) == 64

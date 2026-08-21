from __future__ import annotations

import json
import tempfile
from pathlib import Path

from software_factory.cli import main as cli_main
from software_factory.daemon import main as daemon_main
from software_factory.skill_bridge import main as skill_main


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
        assert json.loads(capsys.readouterr().out)["action"] in {
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
        assert output["role"] == "program_author"
        assert output["mission_id"] == mission_id

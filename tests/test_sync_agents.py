from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PLUGIN = Path(__file__).resolve().parents[1]
SYNC = PLUGIN / "scripts" / "sync_agents.py"


def load_sync_module():
    spec = importlib.util.spec_from_file_location("superworkflows_sync_agents", SYNC)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SyncAgentsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="superworkflows-agents-")
        self.root = Path(self.temp.name)
        self.target = self.root / "agents"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_sync(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SYNC), *args, "--target", str(self.target), "--allow-custom-target", "--check-json", "--skip-runtime-model-check"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(expected, result.returncode, msg=f"stdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_transactional_install_semantic_check_and_rollback(self) -> None:
        self.run_sync("--check", expected=2)
        installed = json.loads(self.run_sync("--install").stdout)
        self.assertTrue(installed["check"]["valid"])
        transaction_id = installed["transaction_id"]
        explorer = self.target / "sw-explorer.toml"
        explorer.write_text(explorer.read_text(encoding="utf-8") + "\n# local comment\n", encoding="utf-8")
        checked = json.loads(self.run_sync("--check").stdout)
        explorer_status = next(item for item in checked["agents"] if item["name"] == "sw-explorer.toml")
        self.assertEqual("compatible-local", explorer_status["status"])
        self.run_sync("--rollback", transaction_id, "--force")
        self.assertFalse(explorer.exists())

    def test_symlink_target_is_rejected_without_touching_victim(self) -> None:
        self.target.mkdir()
        victim = self.root / "victim.txt"
        victim.write_text("do not change\n", encoding="utf-8")
        os.symlink(victim, self.target / "sw-explorer.toml")
        self.run_sync("--install", "--force", expected=2)
        self.assertEqual("do not change\n", victim.read_text(encoding="utf-8"))

    def test_symlink_backup_directory_and_rollback_traversal_are_rejected(self) -> None:
        self.target.mkdir()
        victim_dir = self.root / "victim-backups"
        victim_dir.mkdir()
        os.symlink(victim_dir, self.target / ".superworkflows-backups")
        self.run_sync("--install", expected=2)
        self.assertEqual([], list(victim_dir.iterdir()))
        self.run_sync("--rollback", "../../escape", expected=2)

    def test_mid_transaction_failure_rolls_back_all_targets(self) -> None:
        module = load_sync_module()
        sources = module.load_sources()
        original = module.atomic_write
        target = self.target
        calls = {"targets": 0}

        def failing_write(path, data, mode=0o600):
            if path.parent == target and path.suffix == ".toml":
                calls["targets"] += 1
                if calls["targets"] == 2:
                    raise OSError("injected write failure")
            return original(path, data, mode)

        with mock.patch.object(module, "atomic_write", side_effect=failing_write):
            with self.assertRaises(module.SyncError):
                module.install(target, sources, force=False)
        self.assertEqual([], list(target.glob("sw-*.toml")))
        manifests = list((target / ".superworkflows-backups").glob("*/manifest.json"))
        self.assertEqual(1, len(manifests))
        self.assertEqual("ROLLED_BACK", json.loads(manifests[0].read_text())["status"])


if __name__ == "__main__":
    unittest.main()

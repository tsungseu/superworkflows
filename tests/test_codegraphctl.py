from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN = Path(__file__).resolve().parents[1]
CONTROLLER = PLUGIN / "scripts" / "codegraphctl.py"


class CodeGraphctlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="superworkflows-codegraphctl-")
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.state = self.base / "state.json"
        self.log = self.base / "actions.log"
        fake = self.bin / "codegraph"
        fake.write_text(
            f"""#!{sys.executable}
import json
import os
import sys
from pathlib import Path

state_path = Path(os.environ["FAKE_CODEGRAPH_STATE"])
log_path = Path(os.environ["FAKE_CODEGRAPH_LOG"])
command = sys.argv[1]
if os.environ.get("FAKE_CODEGRAPH_FAIL") == command:
    print("forced failure", file=sys.stderr)
    raise SystemExit(7)
state = json.loads(state_path.read_text(encoding="utf-8"))
if command == "status":
    print(json.dumps(state))
    raise SystemExit(0)
with log_path.open("a", encoding="utf-8") as stream:
    stream.write(command + "\\n")
if command in {{"init", "index", "sync"}}:
    state["initialized"] = True
    state["lastIndexed"] = "2099-01-01T00:00:00Z"
    state["pendingChanges"] = {{"added": 0, "modified": 0, "removed": 0}}
    state["worktreeMismatch"] = None
    state["index"] = {{"reindexRecommended": command == "sync" and bool(state.get("reindexAfterSync"))}}
    state_path.write_text(json.dumps(state), encoding="utf-8")
    raise SystemExit(0)
raise SystemExit(9)
""",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        self.write_state(initialized=False)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_state(
        self,
        *,
        initialized: bool,
        pending: dict[str, int] | None = None,
        mismatch: str | None = None,
        reindex: bool = False,
    ) -> None:
        self.state.write_text(
            json.dumps(
                {
                    "initialized": initialized,
                    "version": "test",
                    "projectPath": str(self.root),
                    "lastIndexed": None,
                    "fileCount": 1 if initialized else None,
                    "nodeCount": 1 if initialized else None,
                    "edgeCount": 0 if initialized else None,
                    "pendingChanges": pending or {"added": 0, "modified": 0, "removed": 0},
                    "worktreeMismatch": mismatch,
                    "index": {"reindexRecommended": reindex},
                }
            ),
            encoding="utf-8",
        )

    def run_ctl(
        self,
        command: str,
        *,
        expected: int = 0,
        path: str | None = None,
        fail: str | None = None,
    ) -> dict:
        env = os.environ.copy()
        env["PATH"] = path if path is not None else f"{self.bin}:{env.get('PATH', '')}"
        env["FAKE_CODEGRAPH_STATE"] = str(self.state)
        env["FAKE_CODEGRAPH_LOG"] = str(self.log)
        if fail:
            env["FAKE_CODEGRAPH_FAIL"] = fail
        result = subprocess.run(
            [sys.executable, str(CONTROLLER), command, "--root", str(self.root), "--timeout", "5"],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(expected, result.returncode, msg=f"stdout={result.stdout}\nstderr={result.stderr}")
        return json.loads(result.stdout)

    def actions(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []

    def test_prepare_initializes_missing_index(self) -> None:
        result = self.run_ctl("prepare")
        self.assertEqual(["init"], result["actions"])
        self.assertTrue(result["status"]["healthy"])
        self.assertEqual(["init"], self.actions())

    def test_prepare_synchronizes_pending_changes(self) -> None:
        self.write_state(initialized=True, pending={"added": 1, "modified": 2, "removed": 1})
        result = self.run_ctl("prepare")
        self.assertEqual(["sync"], result["actions"])
        self.assertEqual(["sync"], self.actions())

    def test_prepare_reindexes_mismatched_or_incompatible_index(self) -> None:
        self.write_state(initialized=True, mismatch="other-worktree", reindex=True)
        result = self.run_ctl("prepare")
        self.assertEqual(["index"], result["actions"])
        self.assertEqual(["index"], self.actions())

    def test_prepare_can_sync_then_reindex_until_healthy(self) -> None:
        self.write_state(initialized=True, pending={"added": 1, "modified": 0, "removed": 0})
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["reindexAfterSync"] = True
        self.state.write_text(json.dumps(state), encoding="utf-8")
        result = self.run_ctl("prepare")
        self.assertEqual(["sync", "index"], result["actions"])
        self.assertEqual(["sync", "index"], self.actions())

    def test_status_is_read_only_and_fails_when_stale(self) -> None:
        self.write_state(initialized=True, pending={"added": 0, "modified": 1, "removed": 0})
        result = self.run_ctl("status", expected=2)
        self.assertFalse(result["ok"])
        self.assertIn("pending source changes", result["status"]["reasons"])
        self.assertEqual([], self.actions())

    def test_sync_does_not_initialize_missing_index(self) -> None:
        result = self.run_ctl("sync", expected=2)
        self.assertIn("run prepare first", result["error"])
        self.assertEqual([], self.actions())

    def test_command_failure_and_missing_executable_fail_closed(self) -> None:
        self.write_state(initialized=True, pending={"added": 1, "modified": 0, "removed": 0})
        failed = self.run_ctl("prepare", expected=2, fail="sync")
        self.assertIn("forced failure", failed["error"])
        missing = self.run_ctl("prepare", expected=2, path=str(self.base / "missing-bin"))
        self.assertIn("unavailable on PATH", missing["error"])

    def test_malformed_or_wrong_project_status_fails_closed(self) -> None:
        self.write_state(initialized=True)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["pendingChanges"]["added"] = True
        self.state.write_text(json.dumps(state), encoding="utf-8")
        malformed = self.run_ctl("prepare", expected=2)
        self.assertIn("pendingChanges.added", malformed["error"])
        self.write_state(initialized=True)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["projectPath"] = str(self.base / "other-repo")
        self.state.write_text(json.dumps(state), encoding="utf-8")
        wrong_root = self.run_ctl("prepare", expected=2)
        self.assertIn("projectPath does not match", wrong_root["error"])


if __name__ == "__main__":
    unittest.main()

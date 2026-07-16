# Superworkflows - persistent robotics AI Coding Loop Engineering.
# Copyright (c) 2026 Tsung Xu
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# Dual-licensed: AGPL-3.0-only OR a separate commercial license.

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN = Path(__file__).resolve().parents[1]
LOOPCTL = PLUGIN / "scripts" / "loopctl.py"


class LoopctlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="superworkflows-loopctl-")
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "tests@example.com")
        self.git("config", "user.name", "Superworkflows Tests")
        (self.root / "README.md").write_text("test\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-qm", "initial")
        self.run_loop("bootstrap", "--root", str(self.root))
        profile_path = self.root / ".ai" / "project-profile.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["commands"]["unit_test"] = [sys.executable, "-c", "print('pass')"]
        profile["commands"]["real_robot"] = ["ros2", "run", "robot", "actuate"]
        profile["external_actions"]["release_enabled"] = True
        profile["gates"]["release"] = ["release-check"]
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        self.run_loop("start", "--root", str(self.root), "--task", "run-1", "--title", "Test run")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=self.root, text=True, capture_output=True, check=True)

    def run_loop(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(LOOPCTL), *args], cwd=self.root, text=True, capture_output=True, check=False
        )
        self.assertEqual(expected, result.returncode, msg=f"stdout={result.stdout}\nstderr={result.stderr}")
        return result

    def output_json(self, result: subprocess.CompletedProcess[str]) -> dict:
        return json.loads(result.stdout)

    def transition(self, state: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        return self.run_loop(
            "transition",
            "--root",
            str(self.root),
            "--task",
            "run-1",
            "--state",
            state,
            "--reason",
            "test",
            expected=expected,
        )

    def reach_reviewing(self) -> None:
        for state in ("DISCOVERING", "CONTRACTED", "PLANNED", "PLAN_REVIEW", "IMPLEMENTING", "REVIEWING"):
            self.transition(state)

    def capture_evidence(self, label: str = "unit") -> str:
        current = self.output_json(self.run_loop("status", "--root", str(self.root), "--task", "run-1"))["run"]["state"]
        result = self.run_loop(
            "evidence",
            "--root",
            str(self.root),
            "--task",
            "run-1",
            "--stage",
            current,
            "--label",
            label,
            "--command-key",
            "unit_test",
            "--",
            sys.executable,
            "-c",
            "print('pass')",
        )
        return self.output_json(result)["evidence"]["evidence_id"]

    def test_bootstrap_is_minimal_and_start_is_idempotent(self) -> None:
        profile = self.root / ".ai" / "project-profile.json"
        before = profile.read_text(encoding="utf-8")
        second_bootstrap = self.output_json(self.run_loop("bootstrap", "--root", str(self.root)))
        self.assertIn(str(profile), second_bootstrap["preserved"])
        self.assertEqual(before, profile.read_text(encoding="utf-8"))
        self.assertFalse((self.root / ".ai" / "workflow.md").exists())
        self.assertFalse((self.root / ".ai" / "project-profile.md").exists())
        self.assertFalse((self.root / ".ai" / "templates").exists())

        second_start = self.output_json(
            self.run_loop("start", "--root", str(self.root), "--task", "run-1", "--title", "Test run")
        )
        self.assertTrue(second_start["idempotent"])
        events = (self.root / ".ai" / "runs" / "run-1" / "events.jsonl").read_text().splitlines()
        self.assertEqual(1, len(events))

    def test_legacy_project_workflow_and_codegraph_index_do_not_change_run_freshness(self) -> None:
        (self.root / ".ai" / "workflow.md").write_text("legacy and ignored\n", encoding="utf-8")
        codegraph = self.root / ".codegraph"
        codegraph.mkdir()
        (codegraph / "index.db").write_text("first\n", encoding="utf-8")
        evidence_id = self.capture_evidence("index-independent")
        (codegraph / "index.db").write_text("second\n", encoding="utf-8")
        result = self.output_json(self.run_loop("validate", "--root", str(self.root), "--task", "run-1"))
        self.assertEqual([], result["issues"])
        self.assertTrue(evidence_id)
        self.assertIn("index-independent", result["passing_evidence_labels"])

    def test_pause_resume_and_snapshot_recovery_are_idempotent(self) -> None:
        self.run_loop(
            "transition", "--root", str(self.root), "--task", "run-1", "--status", "PAUSED", "--reason", "interrupt"
        )
        self.transition("DISCOVERING", expected=2)
        run_path = self.root / ".ai" / "runs" / "run-1"
        events = [json.loads(line) for line in (run_path / "events.jsonl").read_text().splitlines()]
        lagging = events[0]["payload"]["post_state"]
        lagging["last_event_seq"] = events[0]["seq"]
        lagging["previous_event_hash"] = events[0]["hash"]
        (run_path / "run.json").write_text(json.dumps(lagging), encoding="utf-8")

        read_only = self.output_json(self.run_loop("status", "--root", str(self.root), "--task", "run-1"))
        self.assertEqual("lagging-recoverable", read_only["run"]["journal"]["snapshot"])
        self.run_loop("resume", "--root", str(self.root), "--task", "run-1")
        before = len((run_path / "events.jsonl").read_text().splitlines())
        duplicate = self.output_json(self.run_loop("resume", "--root", str(self.root), "--task", "run-1"))
        after = len((run_path / "events.jsonl").read_text().splitlines())
        self.assertTrue(duplicate["idempotent"])
        self.assertEqual(before, after)

    def test_p0_blocks_integration_until_independent_verification(self) -> None:
        self.reach_reviewing()
        opened = self.output_json(
            self.run_loop(
                "finding-open", "--root", str(self.root), "--task", "run-1", "--priority", "P0",
                "--title", "unsafe limit", "--owner", "implementer", "--verification-spec", "rerun safety test",
                "--actor", "reviewer",
            )
        )
        finding_id = opened["finding_id"]
        self.transition("READY_TO_INTEGRATE", expected=2)
        evidence_id = self.capture_evidence("safety")
        self.run_loop(
            "finding-update", "--root", str(self.root), "--task", "run-1", "--finding-id", finding_id,
            "--status", "FIXED", "--evidence", evidence_id, "--actor", "implementer",
        )
        self.run_loop(
            "finding-update", "--root", str(self.root), "--task", "run-1", "--finding-id", finding_id,
            "--status", "VERIFIED", "--evidence", evidence_id, "--independent", "--actor", "reviewer-2",
        )
        self.transition("READY_TO_INTEGRATE")

    def test_p2_deferral_requires_owner_reason_and_due_condition(self) -> None:
        finding_id = self.output_json(
            self.run_loop(
                "finding-open", "--root", str(self.root), "--task", "run-1", "--priority", "P2",
                "--title", "cleanup", "--owner", "maintainer", "--verification-spec", "inspect later",
            )
        )["finding_id"]
        self.run_loop(
            "finding-update", "--root", str(self.root), "--task", "run-1", "--finding-id", finding_id,
            "--status", "DEFERRED", "--actor", "reviewer", expected=2,
        )
        self.run_loop(
            "finding-update", "--root", str(self.root), "--task", "run-1", "--finding-id", finding_id,
            "--status", "DEFERRED", "--owner", "maintainer", "--reason", "bounded debt",
            "--due-condition", "before 0.3 release", "--actor", "reviewer",
        )

    def test_evidence_tampering_is_detected(self) -> None:
        evidence_id = self.capture_evidence("tamper")
        stdout = self.root / ".ai" / "runs" / "run-1" / "evidence" / evidence_id / "stdout.log"
        stdout.write_text("modified\n", encoding="utf-8")
        result = self.run_loop("validate", "--root", str(self.root), "--task", "run-1", expected=2)
        self.assertIn("stdout hash mismatch", result.stdout)

    def test_snapshot_tampering_is_detected_even_when_event_pointer_is_preserved(self) -> None:
        path = self.root / ".ai" / "runs" / "run-1" / "run.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["title"] = "forged title"
        path.write_text(json.dumps(state), encoding="utf-8")
        result = self.run_loop("status", "--root", str(self.root), "--task", "run-1", expected=2)
        self.assertIn("snapshot and journal diverge", result.stderr)

    def test_evidence_executor_rejects_unprofiled_and_hardware_commands(self) -> None:
        self.run_loop(
            "evidence", "--root", str(self.root), "--task", "run-1", "--stage", "NEW",
            "--label", "mismatch", "--command-key", "unit_test", "--", "git", "push", expected=2,
        )
        self.run_loop(
            "evidence", "--root", str(self.root), "--task", "run-1", "--stage", "NEW",
            "--label", "robot", "--command-key", "real_robot", expected=2,
        )

    def test_evidence_command_timeout_is_recorded_as_failure(self) -> None:
        profile_path = self.root / ".ai" / "project-profile.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["commands"]["unit_test"] = [sys.executable, "-c", "import time; time.sleep(5)"]
        profile["workflow_budgets"]["evidence_command_timeout_seconds"] = 1
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        self.run_loop("start", "--root", str(self.root), "--task", "timeout-run", "--title", "Timeout run")
        result = self.run_loop(
            "evidence", "--root", str(self.root), "--task", "timeout-run", "--stage", "NEW",
            "--label", "timeout", "--command-key", "unit_test", expected=124,
        )
        evidence = self.output_json(result)["evidence"]
        metadata_path = self.root / ".ai" / "runs" / "timeout-run" / evidence["relative_dir"] / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertTrue(metadata["timed_out"])
        self.assertEqual(124, metadata["exit_code"])

    def test_control_paths_reject_symbolic_links(self) -> None:
        runs = self.root / ".ai" / "runs"
        real = self.root / "moved-run"
        (runs / "run-1").rename(real)
        (runs / "run-1").symlink_to(real, target_is_directory=True)
        self.run_loop("status", "--root", str(self.root), "--task", "run-1", expected=2)

    def test_project_policy_drift_blocks_progress_but_allows_cancel(self) -> None:
        profile_path = self.root / ".ai" / "project-profile.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["gates"]["complete"] = ["new-unreviewed-gate"]
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        self.transition("DISCOVERING", expected=2)
        self.run_loop(
            "evidence", "--root", str(self.root), "--task", "run-1", "--stage", "NEW",
            "--label", "unit", "--command-key", "unit_test", expected=2,
        )
        self.run_loop(
            "transition", "--root", str(self.root), "--task", "run-1", "--status", "CANCELLED",
            "--reason", "policy drift",
        )

    def test_action_authorization_is_bound_and_idempotent(self) -> None:
        self.reach_reviewing()
        self.capture_evidence("implementation")
        self.transition("READY_TO_INTEGRATE")
        self.transition("INTEGRATING")
        self.capture_evidence("integration")
        self.transition("VERIFYING")
        self.capture_evidence("release-check")
        self.transition("AWAITING_EXTERNAL_APPROVAL")
        commit = self.git("rev-parse", "HEAD").stdout.strip()
        self.run_loop(
            "authorize", "--root", str(self.root), "--task", "run-1", "--action", "push",
            "--target", "origin/main", "--commit", commit, "--granted-by", "test-user",
            "--expires", "2099-01-01T00:00:00Z", "--scope-note", "test approval",
        )
        self.run_loop(
            "approval-check", "--root", str(self.root), "--task", "run-1", "--action", "push",
            "--target", "other/main", "--commit", commit, expected=2,
        )
        self.transition("DELIVERING")
        self.run_loop(
            "action-begin", "--root", str(self.root), "--task", "run-1", "--action", "push",
            "--target", "origin/main", "--commit", commit, "--operation-id", "push-test-1",
            "--expected-before-state", "remote main at expected SHA",
        )
        self.run_loop(
            "action-begin", "--root", str(self.root), "--task", "run-1", "--action", "push",
            "--target", "origin/main", "--commit", commit, "--operation-id", "push-test-1",
            "--expected-before-state", "remote main at expected SHA", expected=2,
        )
        self.run_loop(
            "action-complete", "--root", str(self.root), "--task", "run-1", "--operation-id", "push-test-1",
            "--result", "UNKNOWN", "--observed-state", "response lost",
        )
        result = self.run_loop(
            "validate", "--root", str(self.root), "--task", "run-1", "--gate", "complete", expected=2
        )
        self.assertIn("require reconciliation", result.stdout)

    def test_complete_path_requires_fresh_evidence(self) -> None:
        self.reach_reviewing()
        self.capture_evidence("implementation")
        self.transition("READY_TO_INTEGRATE")
        self.transition("INTEGRATING")
        self.capture_evidence("integration")
        self.transition("VERIFYING")
        self.capture_evidence("complete")
        self.transition("LEARNING")
        self.transition("COMPLETE")
        final = self.output_json(self.run_loop("status", "--root", str(self.root), "--task", "run-1"))
        self.assertEqual("COMPLETE", final["run"]["status"])


if __name__ == "__main__":
    unittest.main()

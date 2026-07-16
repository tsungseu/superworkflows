#!/usr/bin/env python3
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

"""Fail-closed CodeGraph lifecycle controller for Superworkflows."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


class CodeGraphError(RuntimeError):
    """A CodeGraph precondition or command failed."""


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def resolve_root(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise CodeGraphError(f"repository root is not a directory: {root}")
    return root


def executable() -> str:
    path = shutil.which("codegraph")
    if not path:
        raise CodeGraphError("codegraph executable is unavailable on PATH")
    return path


def bounded_output(value: str | None, limit: int = 4000) -> str:
    text = (value or "").strip()
    return text if len(text) <= limit else text[-limit:]


def run_codegraph(binary: str, root: Path, arguments: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            [binary, *arguments],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise CodeGraphError(f"codegraph {' '.join(arguments[:1])} timed out after {timeout}s") from exc
    except OSError as exc:
        raise CodeGraphError(f"unable to execute codegraph: {exc}") from exc
    if result.returncode != 0:
        detail = bounded_output(result.stderr) or bounded_output(result.stdout) or "no diagnostic output"
        raise CodeGraphError(f"codegraph {' '.join(arguments[:1])} failed ({result.returncode}): {detail}")
    return result


def read_status(binary: str, root: Path, timeout: int) -> dict[str, Any]:
    result = run_codegraph(binary, root, ["status", "--json", str(root)], timeout)
    try:
        status = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CodeGraphError("codegraph status returned invalid JSON") from exc
    if not isinstance(status, dict) or not isinstance(status.get("initialized"), bool):
        raise CodeGraphError("codegraph status omitted the initialized flag")
    project_path = status.get("projectPath")
    if not isinstance(project_path, str) or Path(project_path).expanduser().resolve() != root:
        raise CodeGraphError("codegraph status projectPath does not match the requested repository")
    return status


def pending_count(status: dict[str, Any]) -> int:
    pending = status.get("pendingChanges")
    if not status.get("initialized"):
        return 0
    if not isinstance(pending, dict):
        raise CodeGraphError("initialized CodeGraph status omitted pendingChanges")
    total = 0
    for key in ("added", "modified", "removed"):
        value = pending.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise CodeGraphError(f"invalid CodeGraph pendingChanges.{key}")
        total += value
    return total


def reindex_recommended(status: dict[str, Any]) -> bool:
    index = status.get("index")
    if status.get("initialized") and not isinstance(index, dict):
        raise CodeGraphError("initialized CodeGraph status omitted index metadata")
    if status.get("initialized") and "worktreeMismatch" not in status:
        raise CodeGraphError("initialized CodeGraph status omitted worktreeMismatch")
    value = (index or {}).get("reindexRecommended")
    if not isinstance(value, bool):
        raise CodeGraphError("invalid CodeGraph index.reindexRecommended")
    return value


def needs_reindex(status: dict[str, Any]) -> bool:
    return status.get("worktreeMismatch") is not None or reindex_recommended(status)


def health(status: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not status.get("initialized"):
        reasons.append("not initialized")
        return False, reasons
    if pending_count(status):
        reasons.append("pending source changes")
    if status.get("worktreeMismatch") is not None:
        reasons.append("worktree mismatch")
    if needs_reindex(status):
        reasons.append("full reindex required")
    return not reasons, reasons


def normalize_status(status: dict[str, Any]) -> dict[str, Any]:
    healthy, reasons = health(status)
    return {
        "initialized": status.get("initialized"),
        "healthy": healthy,
        "reasons": reasons,
        "version": status.get("version"),
        "project_path": status.get("projectPath"),
        "last_indexed": status.get("lastIndexed"),
        "file_count": status.get("fileCount"),
        "node_count": status.get("nodeCount"),
        "edge_count": status.get("edgeCount"),
        "pending_changes": status.get("pendingChanges"),
        "worktree_mismatch": status.get("worktreeMismatch"),
        "reindex_recommended": reindex_recommended(status) if status.get("initialized") else False,
    }


def converge(binary: str, root: Path, timeout: int, allow_init: bool) -> tuple[list[str], dict[str, Any]]:
    actions: list[str] = []
    for _ in range(4):
        status = read_status(binary, root, timeout)
        healthy, _ = health(status)
        if healthy:
            return actions, status
        if not status["initialized"]:
            if not allow_init:
                raise CodeGraphError("CodeGraph is not initialized; run prepare first")
            run_codegraph(binary, root, ["init", str(root)], timeout)
            actions.append("init")
        elif needs_reindex(status):
            run_codegraph(binary, root, ["index", str(root)], timeout)
            actions.append("index")
        elif pending_count(status):
            run_codegraph(binary, root, ["sync", str(root)], timeout)
            actions.append("sync")
        else:
            break
    status = read_status(binary, root, timeout)
    _, reasons = health(status)
    raise CodeGraphError("CodeGraph did not converge after four actions: " + ", ".join(reasons))


def execute(args: argparse.Namespace) -> int:
    root = resolve_root(args.root)
    binary = executable()
    if args.command == "status":
        status = read_status(binary, root, args.timeout)
        healthy, _ = health(status)
        emit({"ok": healthy, "command": "status", "root": str(root), "actions": [], "status": normalize_status(status)})
        return 0 if healthy else 2
    actions, status = converge(binary, root, args.timeout, allow_init=args.command == "prepare")
    emit({"ok": True, "command": args.command, "root": str(root), "actions": actions, "status": normalize_status(status)})
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("prepare", "initialize, rebuild, or incrementally synchronize CodeGraph until healthy"),
        ("sync", "synchronize an already initialized CodeGraph until healthy"),
        ("status", "report CodeGraph health without changing it"),
    ):
        item = commands.add_parser(name, help=help_text)
        item.add_argument("--root", required=True)
        item.add_argument("--timeout", type=int, default=1800)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not 1 <= args.timeout <= 86400:
        emit({"ok": False, "error": "timeout must be between 1 and 86400 seconds"})
        return 2
    try:
        return execute(args)
    except CodeGraphError as exc:
        emit({"ok": False, "command": args.command, "root": str(Path(args.root).expanduser()), "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

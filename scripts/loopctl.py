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

"""Fail-closed local control plane for Superworkflows Loop Engineering runs."""

from __future__ import annotations

import argparse
import contextlib
import copy
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Iterable


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
ASSET_ROOT = PLUGIN_ROOT / "assets" / "loop-engineering"
SPEC_PATH = ASSET_ROOT / "workflow-spec.json"
ZERO_HASH = "0" * 64
TASK_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}")


class LoopError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_time(value: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LoopError(f"invalid ISO-8601 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise LoopError("timestamp must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LoopError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LoopError(f"invalid JSON in {path}: {exc}") from exc


def load_spec() -> dict[str, Any]:
    spec = load_json(SPEC_PATH)
    if spec.get("schema_version") != 1:
        raise LoopError("unsupported workflow spec schema")
    return spec


SPEC = load_spec()


def emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def resolve_root(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise LoopError(f"repository root is not a directory: {root}")
    return root


def validate_task(value: str) -> str:
    if not TASK_RE.fullmatch(value) or value in {".", ".."} or ".." in value:
        raise LoopError("run id must use 1-96 safe letters, numbers, dots, underscores, or dashes")
    return value


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip(".-_").lower()
    return (slug[:48] or "run") + "-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]


def ai_root(root: Path) -> Path:
    return root / ".ai"


def runs_root(root: Path) -> Path:
    return ai_root(root) / "runs"


def run_dir(root: Path, task: str) -> Path:
    return runs_root(root) / validate_task(task)


def assert_no_symlinks(path: Path, boundary: Path) -> None:
    boundary = boundary.resolve()
    candidate = path if path.is_absolute() else boundary / path
    try:
        relative = candidate.relative_to(boundary)
    except ValueError as exc:
        raise LoopError(f"path escapes repository boundary: {candidate}") from exc
    current = boundary
    for part in relative.parts:
        current = current / part
        if current.exists() or current.is_symlink():
            if current.is_symlink():
                raise LoopError(f"refusing symbolic-link path component: {current}")


def fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise LoopError(f"refusing to replace symbolic link: {path}")
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, mode)
    try:
        offset = 0
        while offset < len(data):
            offset += os.write(descriptor, data[offset:])
        os.fsync(descriptor)
    except Exception:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()
        raise
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    fsync_dir(path.parent)


def atomic_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise LoopError(f"refusing symbolic-link journal: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        line = canonical_bytes(value) + b"\n"
        offset = 0
        while offset < len(line):
            offset += os.write(descriptor, line[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextlib.contextmanager
def ledger_lock(root: Path) -> Iterable[None]:
    directory = runs_root(root)
    assert_no_symlinks(directory, root)
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / ".loopctl.lock"
    if lock_path.is_symlink():
        raise LoopError(f"refusing symbolic-link lock: {lock_path}")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def git_output(root: Path, arguments: list[str]) -> bytes | None:
    try:
        result = subprocess.run(
            ["git", *arguments], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False
        )
    except FileNotFoundError:
        return None
    return result.stdout if result.returncode == 0 else None


def hash_command_output(root: Path, arguments: list[str]) -> str | None:
    try:
        process = subprocess.Popen(
            ["git", *arguments], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
    except FileNotFoundError:
        return None
    digest = hashlib.sha256()
    assert process.stdout is not None
    for block in iter(lambda: process.stdout.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest() if process.wait() == 0 else None


def git_head(root: Path) -> str | None:
    value = git_output(root, ["rev-parse", "HEAD"])
    return value.decode("ascii", errors="replace").strip() if value else None


def workspace_snapshot(root: Path) -> dict[str, Any]:
    head = git_head(root)
    if head is None:
        return {
            "vcs": "none",
            "commit": None,
            "workspace_digest": sha256_bytes(str(root).encode("utf-8")),
            "dirty": None,
        }
    pathspec = ["--", ".", ":(exclude).ai", ":(exclude).codegraph"]
    diff_hash = hash_command_output(root, ["diff", "--binary", "HEAD", *pathspec])
    status = git_output(root, ["status", "--porcelain=v2", "-z", "--untracked-files=all", *pathspec]) or b""
    status_hash = sha256_bytes(status)
    digest = sha256_bytes(canonical_bytes({"head": head, "diff": diff_hash, "status": status_hash}))
    return {
        "vcs": "git",
        "commit": head,
        "workspace_digest": digest,
        "dirty": bool(status),
        "diff_hash": diff_hash,
        "status_hash": status_hash,
    }


def repository_fingerprint(root: Path) -> str:
    top = git_output(root, ["rev-parse", "--show-toplevel"])
    remote = git_output(root, ["config", "--get", "remote.origin.url"])
    payload = {
        "root": str(root),
        "git_root": top.decode(errors="replace").strip() if top else None,
        "origin": remote.decode(errors="replace").strip() if remote else None,
    }
    return sha256_bytes(canonical_bytes(payload))


def project_policy_hash(root: Path) -> str:
    entries: dict[str, str | None] = {}
    for relative in (".ai/project-profile.json",):
        path = root / relative
        assert_no_symlinks(path, root)
        entries[relative] = sha256_file(path) if path.is_file() else None
    return sha256_bytes(canonical_bytes(entries))


def hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return ZERO_HASH
    for path in sorted(
        p for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and ".codegraph" not in p.parts
    ):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def read_events(directory: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = directory / "events.jsonl"
    if not path.exists():
        return [], ["missing events.jsonl"]
    if path.is_symlink():
        return [], ["events.jsonl is a symbolic link"]
    events: list[dict[str, Any]] = []
    issues: list[str] = []
    previous = ZERO_HASH
    expected_seq = 1
    with path.open("r", encoding="utf-8") as stream:
        for line_number, raw in enumerate(stream, start=1):
            if not raw.strip():
                issues.append(f"blank journal line {line_number}")
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                issues.append(f"invalid journal JSON at line {line_number}: {exc}")
                continue
            claimed_hash = event.get("hash")
            unhashed = dict(event)
            unhashed.pop("hash", None)
            calculated = sha256_bytes(canonical_bytes(unhashed))
            if event.get("seq") != expected_seq:
                issues.append(f"journal sequence mismatch at line {line_number}")
            if event.get("previous_hash") != previous:
                issues.append(f"journal previous_hash mismatch at line {line_number}")
            if claimed_hash != calculated:
                issues.append(f"journal hash mismatch at line {line_number}")
            events.append(event)
            previous = claimed_hash if isinstance(claimed_hash, str) else previous
            expected_seq += 1
    return events, issues


def load_run(directory: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    state_path = directory / "run.json"
    if state_path.is_symlink():
        raise LoopError(f"run.json is a symbolic link: {state_path}")
    state = load_json(state_path)
    if state.get("run_id") != directory.name:
        raise LoopError("run id does not match its directory name")
    events, issues = read_events(directory)
    if issues:
        raise LoopError("; ".join(issues))
    if not events:
        raise LoopError(f"run has no valid events: {directory}")
    latest = events[-1]
    post_state = latest.get("payload", {}).get("post_state")
    if not isinstance(post_state, dict):
        raise LoopError("latest journal event has no recoverable post_state")
    expected = copy.deepcopy(post_state)
    expected["last_event_seq"] = latest["seq"]
    expected["previous_event_hash"] = latest["hash"]
    snapshot_status = "current"
    if canonical_bytes(state) == canonical_bytes(expected):
        recovered = state
    elif isinstance(state.get("last_event_seq"), int) and state["last_event_seq"] < latest.get("seq", 0):
        recovered = expected
        snapshot_status = "lagging-recoverable"
    else:
        raise LoopError("run snapshot and journal diverge")
    return recovered, {"snapshot": snapshot_status, "events": len(events), "last_hash": latest["hash"]}


def append_event(
    directory: Path,
    state: dict[str, Any],
    event_type: str,
    actor: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    next_state = copy.deepcopy(state)
    next_state["updated_at"] = utc_now()
    post_state = copy.deepcopy(next_state)
    seq = int(state.get("last_event_seq", 0)) + 1
    previous = state.get("previous_event_hash", ZERO_HASH)
    event = {
        "seq": seq,
        "event_id": str(uuid.uuid4()),
        "timestamp": next_state["updated_at"],
        "type": event_type,
        "actor": actor,
        "previous_hash": previous,
        "payload": {"details": details or {}, "post_state": post_state},
    }
    event["hash"] = sha256_bytes(canonical_bytes(event))
    append_jsonl(directory / "events.jsonl", event)
    next_state["last_event_seq"] = seq
    next_state["previous_event_hash"] = event["hash"]
    atomic_json(directory / "run.json", next_state)
    return next_state


def mutate_run(
    root: Path,
    task: str,
    actor: str,
    event_type: str,
    mutate: Callable[[dict[str, Any]], dict[str, Any] | None],
) -> dict[str, Any]:
    directory = run_dir(root, task)
    assert_no_symlinks(directory, root)
    with ledger_lock(root):
        state, journal = load_run(directory)
        if journal["snapshot"] == "lagging-recoverable":
            atomic_json(directory / "run.json", state)
        details = mutate(state) or {}
        return append_event(directory, state, event_type, actor, details)


def profile_path(root: Path) -> Path:
    return ai_root(root) / "project-profile.json"


def load_profile(root: Path) -> dict[str, Any]:
    path = profile_path(root)
    assert_no_symlinks(path, root)
    if not path.exists():
        raise LoopError(f"missing project profile: {path}; run bootstrap or create it explicitly")
    profile = load_json(path)
    if profile.get("schema_version") != 1:
        raise LoopError("unsupported project-profile schema")
    for key in ("artifact_policy", "commands", "gates", "external_actions"):
        if not isinstance(profile.get(key), dict):
            raise LoopError(f"project profile field must be an object: {key}")
    if "workflow_budgets" in profile and not isinstance(profile["workflow_budgets"], dict):
        raise LoopError("project profile field must be an object: workflow_budgets")
    return profile


def bootstrap(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    targets: list[tuple[Path, Path]] = [
        (ASSET_ROOT / "project-profile.json", ai_root(root) / "project-profile.json"),
    ]
    plan = []
    for source, target in targets:
        assert_no_symlinks(target, root)
        plan.append({"target": str(target), "action": "preserve" if target.exists() else "create"})
    if args.dry_run:
        emit({"dry_run": True, "root": str(root), "plan": plan})
        return
    created = []
    with ledger_lock(root):
        for source, target in targets:
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(target, source.read_bytes(), 0o644)
            created.append(str(target))
        for directory in (runs_root(root), ai_root(root) / "improvements" / "pending"):
            assert_no_symlinks(directory, root)
            directory.mkdir(parents=True, exist_ok=True)
    emit({"root": str(root), "created": created, "preserved": [p["target"] for p in plan if p["action"] == "preserve"]})


def artifact_policy(root: Path) -> dict[str, Any]:
    policy = load_profile(root).get("artifact_policy", {})
    probe = ".ai/runs/__superworkflows_probe__"
    ignored = False
    try:
        result = subprocess.run(["git", "check-ignore", "-q", probe], cwd=root, check=False)
        ignored = result.returncode == 0
    except FileNotFoundError:
        pass
    return {"declared": policy, "git_ignored": ignored}


def audit(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    required = [profile_path(root)]
    missing = [str(path) for path in required if not path.exists()]
    issues: list[str] = []
    profile = None
    if not missing:
        try:
            profile = load_profile(root)
        except LoopError as exc:
            issues.append(str(exc))
    for path in [ai_root(root), runs_root(root)]:
        if path.is_symlink():
            issues.append(f"symbolic-link control path: {path}")
    emit(
        {
            "root": str(root),
            "valid": not missing and not issues,
            "missing": missing,
            "issues": issues,
            "artifact_policy": artifact_policy(root) if profile is not None else None,
            "workflow_spec_hash": sha256_file(SPEC_PATH),
        }
    )


def initial_state(root: Path, task: str, title: str, parent_run: str | None) -> dict[str, Any]:
    workspace = workspace_snapshot(root)
    return {
        "schema_version": SPEC["schema_version"],
        "plugin_version": SPEC["plugin_version"],
        "workflow_spec_hash": sha256_file(SPEC_PATH),
        "plugin_runtime_hash": hash_tree(PLUGIN_ROOT),
        "agent_contract_hash": hash_tree(PLUGIN_ROOT / "assets" / "agents"),
        "run_id": task,
        "parent_run_id": parent_run,
        "title": title,
        "repository_root": str(root),
        "repository_fingerprint": repository_fingerprint(root),
        "project_policy_hash": project_policy_hash(root),
        "base_commit": workspace["commit"],
        "base_workspace_digest": workspace["workspace_digest"],
        "state": SPEC["initial_state"],
        "status": "ACTIVE",
        "blocked_from": None,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "resume_count": 0,
        "route_trace": [],
        "findings": [],
        "evidence": [],
        "approvals": [],
        "external_actions": [],
        "last_event_seq": 0,
        "previous_event_hash": ZERO_HASH,
        "artifact_policy": load_profile(root).get("artifact_policy", {}),
        "workflow_budgets": load_profile(root).get("workflow_budgets", {}),
    }


def start(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    load_profile(root)
    task = validate_task(args.task) if args.task else validate_task(slugify(args.title))
    directory = run_dir(root, task)
    assert_no_symlinks(directory, root)
    with ledger_lock(root):
        if directory.exists():
            existing, journal = load_run(directory)
            if existing.get("title") == args.title:
                emit({"created": False, "idempotent": True, "run": summarize_run(existing, journal)})
                return
            raise LoopError(f"run id already exists with a different title: {task}")
        if args.parent_run:
            parent = run_dir(root, args.parent_run)
            assert_no_symlinks(parent, root)
            if not parent.exists():
                raise LoopError(f"parent run does not exist: {args.parent_run}")
            load_run(parent)
        directory.mkdir(parents=True, exist_ok=False)
        try:
            (directory / "evidence").mkdir()
            for template in sorted((ASSET_ROOT / "templates").glob("[0-9][0-9]-*.md")):
                atomic_write(directory / template.name, template.read_bytes(), 0o644)
            state = initial_state(root, task, args.title, args.parent_run)
            state = append_event(directory, state, "RUN_STARTED", args.actor, {"title": args.title})
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            raise
    emit({"created": True, "run": summarize_run(state, {"snapshot": "current", "events": 1})})


def summarize_run(state: dict[str, Any], journal: dict[str, Any]) -> dict[str, Any]:
    finding_counts: dict[str, int] = {"P0": 0, "P1": 0, "P2": 0}
    for finding in state.get("findings", []):
        if finding.get("status") not in {"VERIFIED", "DEFERRED"}:
            finding_counts[finding.get("priority", "P2")] = finding_counts.get(finding.get("priority", "P2"), 0) + 1
    valid_approvals = 0
    expired_approvals = 0
    now = dt.datetime.now(dt.timezone.utc)
    for approval in state.get("approvals", []):
        try:
            valid = not approval.get("revoked_at") and parse_time(approval["expires_at"]) > now
        except (KeyError, LoopError):
            valid = False
        valid_approvals += int(valid)
        expired_approvals += int(not valid)
    return {
        "run_id": state.get("run_id"),
        "parent_run_id": state.get("parent_run_id"),
        "title": state.get("title"),
        "state": state.get("state"),
        "status": state.get("status"),
        "allowed_next_states": SPEC["transitions"].get(state.get("state"), []),
        "updated_at": state.get("updated_at"),
        "resume_count": state.get("resume_count"),
        "open_findings": finding_counts,
        "evidence_count": len(state.get("evidence", [])),
        "approval_count": len(state.get("approvals", [])),
        "valid_approvals": valid_approvals,
        "expired_or_revoked_approvals": expired_approvals,
        "pending_external_actions": sum(1 for item in state.get("external_actions", []) if item.get("status") in {"PENDING", "UNKNOWN"}),
        "last_event_seq": state.get("last_event_seq"),
        "journal": journal,
    }


def status(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    directory = runs_root(root)
    if args.task:
        selected = run_dir(root, args.task)
        assert_no_symlinks(selected, root)
        state, journal = load_run(selected)
        emit({"root": str(root), "run": summarize_run(state, journal)})
        return
    runs = []
    if directory.exists():
        for candidate in sorted(directory.iterdir()):
            if not candidate.is_dir() or candidate.is_symlink() or not (candidate / "run.json").exists():
                continue
            try:
                state, journal = load_run(candidate)
                runs.append(summarize_run(state, journal))
            except LoopError as exc:
                runs.append({"run_id": candidate.name, "corrupt": True, "error": str(exc)})
    active = [item["run_id"] for item in runs if not item.get("corrupt") and item.get("status") in {"ACTIVE", "PAUSED", "BLOCKED"}]
    emit({"root": str(root), "active_runs": active, "runs": runs})


def find_evidence(state: dict[str, Any], evidence_id: str) -> dict[str, Any] | None:
    return next((item for item in state.get("evidence", []) if item.get("evidence_id") == evidence_id), None)


def evidence_integrity(root: Path, state: dict[str, Any], current: dict[str, Any]) -> tuple[list[str], list[str], dict[str, bool]]:
    issues: list[str] = []
    warnings: list[str] = []
    labels: dict[str, bool] = {}
    directory = run_dir(root, state["run_id"])
    for item in state.get("evidence", []):
        evidence_id = item.get("evidence_id", "unknown")
        relative = item.get("relative_dir")
        if not isinstance(relative, str):
            issues.append(f"evidence {evidence_id} has no relative_dir")
            continue
        evidence_dir = directory / relative
        try:
            assert_no_symlinks(evidence_dir, directory)
        except LoopError as exc:
            issues.append(str(exc))
            continue
        metadata_path = evidence_dir / "metadata.json"
        stdout_path = evidence_dir / "stdout.log"
        stderr_path = evidence_dir / "stderr.log"
        if not all(path.is_file() for path in (metadata_path, stdout_path, stderr_path)):
            issues.append(f"evidence {evidence_id} is missing files")
            continue
        if sha256_file(metadata_path) != item.get("metadata_sha256"):
            issues.append(f"evidence {evidence_id} metadata hash mismatch")
            continue
        metadata = load_json(metadata_path)
        if sha256_file(stdout_path) != metadata.get("stdout_sha256"):
            issues.append(f"evidence {evidence_id} stdout hash mismatch")
        if sha256_file(stderr_path) != metadata.get("stderr_sha256"):
            issues.append(f"evidence {evidence_id} stderr hash mismatch")
        fresh = metadata.get("workspace_digest") == current.get("workspace_digest")
        if not fresh:
            warnings.append(f"evidence {evidence_id} is stale for the current workspace")
        labels[metadata.get("label", evidence_id)] = bool(metadata.get("exit_code") == 0 and fresh)
    return issues, warnings, labels


def run_validation(root: Path, state: dict[str, Any], gate: str | None) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    current = workspace_snapshot(root)
    if state.get("schema_version") != SPEC["schema_version"]:
        issues.append("run schema is incompatible")
    if state.get("repository_fingerprint") != repository_fingerprint(root):
        issues.append("repository fingerprint differs from the run")
    if state.get("project_policy_hash") != project_policy_hash(root):
        issues.append("project profile changed; create a child run or migrate explicitly")
    if state.get("workflow_spec_hash") != sha256_file(SPEC_PATH):
        issues.append("workflow specification changed; create a child run or migrate explicitly")
    if state.get("agent_contract_hash") != hash_tree(PLUGIN_ROOT / "assets" / "agents"):
        issues.append("bundled agent contract changed; create a child run or migrate explicitly")
    event_list, event_issues = read_events(run_dir(root, state["run_id"]))
    issues.extend(event_issues)
    if event_list and (state.get("last_event_seq") != event_list[-1].get("seq") or state.get("previous_event_hash") != event_list[-1].get("hash")):
        warnings.append("run.json is behind the recoverable event journal")
    evidence_issues, evidence_warnings, labels = evidence_integrity(root, state, current)
    issues.extend(evidence_issues)
    warnings.extend(evidence_warnings)
    open_p0 = [f for f in state.get("findings", []) if f.get("priority") == "P0" and f.get("status") != "VERIFIED"]
    open_p1 = [f for f in state.get("findings", []) if f.get("priority") == "P1" and f.get("status") not in SPEC["p1_closed_states"]]
    invalid_deferrals = [
        f for f in state.get("findings", [])
        if f.get("status") == "DEFERRED" and (not f.get("owner") or not f.get("deferral_reason") or not f.get("due_condition"))
    ]
    stale_verified = [
        f for f in state.get("findings", [])
        if f.get("status") == "VERIFIED" and f.get("verified_workspace_digest") != current.get("workspace_digest")
    ]
    if open_p0:
        issues.append(f"{len(open_p0)} P0 finding(s) are not independently verified")
    if gate in {"release", "complete"} and open_p1:
        issues.append(f"{len(open_p1)} P1 finding(s) remain open")
    if invalid_deferrals:
        issues.append(f"{len(invalid_deferrals)} finding deferral(s) lack owner/reason/due condition")
    if stale_verified:
        issues.append(f"{len(stale_verified)} verified finding(s) are stale for the current workspace")
    pending = [item for item in state.get("external_actions", []) if item.get("status") in {"PENDING", "UNKNOWN"}]
    if gate in {"release", "complete"} and pending:
        issues.append(f"{len(pending)} external action(s) require reconciliation")
    profile = load_profile(root)
    required: list[str] = []
    if gate:
        required = profile.get("gates", {}).get(gate, [])
        if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
            issues.append(f"project profile gate must be a list of evidence labels: {gate}")
            required = []
        missing = [label for label in required if not labels.get(label)]
        if missing:
            issues.append("missing fresh passing evidence: " + ", ".join(missing))
    if gate == "release" and not profile.get("external_actions", {}).get("release_enabled", False):
        issues.append("release is disabled in the project profile")
    if gate == "complete" and not any(labels.values()):
        issues.append("completion requires at least one fresh passing machine-captured evidence item")
    return {
        "valid": not issues,
        "gate": gate,
        "run_id": state["run_id"],
        "state": state["state"],
        "status": state["status"],
        "current_workspace": current,
        "issues": issues,
        "warnings": warnings,
        "required_evidence": required,
        "passing_evidence_labels": sorted(label for label, passed in labels.items() if passed),
        "open_findings": {"P0": len(open_p0), "P1": len(open_p1)},
        "pending_external_actions": len(pending),
    }


def validate_command(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    directory = run_dir(root, args.task)
    assert_no_symlinks(directory, root)
    state, _ = load_run(directory)
    result = run_validation(root, state, args.gate)
    emit(result)
    if not result["valid"]:
        raise SystemExit(2)


def transition(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    target_state = args.state or args.stage
    if not target_state and not args.status:
        raise LoopError("transition requires --state/--stage or --status")
    if target_state and target_state not in SPEC["states"]:
        raise LoopError(f"unknown state: {target_state}")
    if args.status and args.status not in SPEC["run_statuses"]:
        raise LoopError(f"unknown run status: {args.status}")
    if args.status in {"ACTIVE", "COMPLETE"}:
        raise LoopError(f"status {args.status} is controller-owned; use resume or transition to COMPLETE")

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        if state["status"] in {"COMPLETE", "CANCELLED"}:
            raise LoopError("terminal run cannot transition")
        old_state = state["state"]
        if target_state and target_state != "CANCELLED" and state.get("project_policy_hash") != project_policy_hash(root):
            raise LoopError("project profile changed; cancel or create a child run")
        if target_state and target_state != "CANCELLED" and state.get("workflow_spec_hash") != sha256_file(SPEC_PATH):
            raise LoopError("workflow specification changed; cancel or create a child run")
        if target_state and target_state != "CANCELLED" and state.get("agent_contract_hash") != hash_tree(PLUGIN_ROOT / "assets" / "agents"):
            raise LoopError("agent contract changed; cancel or create a child run")
        if target_state and target_state != "CANCELLED" and state["status"] != "ACTIVE":
            raise LoopError("paused or blocked run must be resumed before changing state")
        if target_state and target_state != old_state:
            max_hops = state.get("workflow_budgets", {}).get("max_route_hops", 64)
            if not isinstance(max_hops, int) or max_hops < 1:
                raise LoopError("invalid max_route_hops workflow budget")
            if len(state.get("route_trace", [])) >= max_hops and target_state != "CANCELLED":
                raise LoopError("workflow route-hop budget exhausted; cancel or create a child run")
            allowed = SPEC["transitions"].get(old_state, [])
            if target_state not in allowed:
                raise LoopError(f"illegal transition: {old_state} -> {target_state}")
            if target_state in SPEC["guarded_states"]:
                validation_gate = (
                    "complete" if target_state == "COMPLETE"
                    else "release" if target_state in {"AWAITING_EXTERNAL_APPROVAL", "DELIVERING"}
                    else None
                )
                check = run_validation(root, state, validation_gate)
                blocking = list(check["issues"])
                required_evidence_stages = {
                    "READY_TO_INTEGRATE": {"IMPLEMENTING", "REVIEWING", "REMEDIATING"},
                    "INTEGRATING": {"IMPLEMENTING", "REVIEWING", "REMEDIATING"},
                    "VERIFYING": {"INTEGRATING", "REMEDIATING"},
                    "AWAITING_EXTERNAL_APPROVAL": {"VERIFYING"},
                    "DELIVERING": {"VERIFYING"},
                    "LEARNING": {"VERIFYING", "DELIVERING"},
                    "COMPLETE": {"VERIFYING", "LEARNING"},
                }.get(target_state, set())
                current_digest = check["current_workspace"]["workspace_digest"]
                stage_evidence = [
                    item for item in state.get("evidence", [])
                    if item.get("stage") in required_evidence_stages
                    and item.get("exit_code") == 0
                    and item.get("workspace_digest") == current_digest
                ]
                if required_evidence_stages and not stage_evidence:
                    blocking.append(
                        "guarded transition requires fresh passing evidence from stage(s): "
                        + ", ".join(sorted(required_evidence_stages))
                    )
                unresolved_p1 = [
                    finding for finding in state.get("findings", [])
                    if finding.get("priority") == "P1" and finding.get("status") not in SPEC["p1_closed_states"]
                ]
                if unresolved_p1:
                    blocking.append(f"{len(unresolved_p1)} P1 finding(s) remain open")
                if target_state in {"LEARNING", "COMPLETE"}:
                    pending_actions = [
                        action for action in state.get("external_actions", [])
                        if action.get("status") in {"PENDING", "UNKNOWN"}
                    ]
                    if pending_actions:
                        blocking.append(f"{len(pending_actions)} external action(s) require reconciliation")
                if target_state == "DELIVERING":
                    current = workspace_snapshot(root)
                    approval_present = any(
                        valid_approval(
                            state,
                            approval.get("action", ""),
                            approval.get("target", ""),
                            current.get("commit"),
                            current.get("workspace_digest"),
                        ) is not None
                        for approval in state.get("approvals", [])
                    )
                    if not approval_present:
                        blocking.append("DELIVERING requires a current action-scoped approval")
                if blocking:
                    raise LoopError("transition guard failed: " + "; ".join(dict.fromkeys(blocking)))
            state["state"] = target_state
            state["route_trace"].append(
                {"from": old_state, "to": target_state, "at": utc_now(), "actor": args.actor, "reason": args.reason}
            )
        if args.status:
            if args.status == "CANCELLED":
                state["state"] = "CANCELLED"
            if args.status in {"PAUSED", "BLOCKED"}:
                state["blocked_from"] = state["state"]
            state["status"] = args.status
        if state["state"] == "COMPLETE":
            state["status"] = "COMPLETE"
        if state["state"] == "CANCELLED":
            state["status"] = "CANCELLED"
        return {"from": old_state, "to": state["state"], "status": state["status"], "reason": args.reason}

    state = mutate_run(root, args.task, args.actor, "STATE_TRANSITION", apply)
    emit({"run": summarize_run(state, {"snapshot": "current", "events": state["last_event_seq"]})})


def resume(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    directory = run_dir(root, args.task)
    assert_no_symlinks(directory, root)
    with ledger_lock(root):
        state, journal = load_run(directory)
        if journal["snapshot"] == "lagging-recoverable":
            atomic_json(directory / "run.json", state)
        if state["status"] in {"COMPLETE", "CANCELLED"}:
            raise LoopError("terminal run cannot resume")
        current_major = str(SPEC["plugin_version"]).split(".", 1)[0]
        run_major = str(state.get("plugin_version", "0")).split(".", 1)[0]
        if current_major != run_major:
            raise LoopError("plugin major version changed; create a child run or migrate explicitly")
        if state.get("repository_fingerprint") != repository_fingerprint(root):
            raise LoopError("repository identity changed; create a child run")
        if state.get("project_policy_hash") != project_policy_hash(root):
            raise LoopError("project profile changed; create a child run")
        if state.get("workflow_spec_hash") != sha256_file(SPEC_PATH):
            raise LoopError("workflow specification changed; create a child run")
        if state.get("agent_contract_hash") != hash_tree(PLUGIN_ROOT / "assets" / "agents"):
            raise LoopError("agent contract changed; create a child run")
        if state["status"] == "ACTIVE":
            emit({"idempotent": True, "run": summarize_run(state, journal)})
            return
        state["status"] = "ACTIVE"
        state["resume_count"] = int(state.get("resume_count", 0)) + 1
        state = append_event(
            directory,
            state,
            "RUN_RESUMED",
            args.actor,
            {"resume_count": state["resume_count"], "workspace": workspace_snapshot(root)},
        )
    emit({"run": summarize_run(state, {"snapshot": "current", "events": state["last_event_seq"]})})


def evidence(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    if args.command_key in {"hil", "real_robot", "rollback"}:
        raise LoopError(f"{args.command_key} cannot run through the local evidence executor; use an authorized action workflow")
    profile = load_profile(root)
    configured = profile.get("commands", {}).get(args.command_key)
    if not isinstance(configured, list) or not configured or not all(isinstance(item, str) and item for item in configured):
        raise LoopError(f"project profile command must be a non-empty argv array: {args.command_key}")
    supplied = list(args.argv)
    if supplied and supplied[0] == "--":
        supplied = supplied[1:]
    if supplied and supplied != configured:
        raise LoopError("supplied argv does not exactly match the project-profile command")
    command = configured
    timeout_seconds = profile.get("workflow_budgets", {}).get("evidence_command_timeout_seconds", 1800)
    if not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 86400:
        raise LoopError("evidence_command_timeout_seconds must be an integer from 1 to 86400")
    task = validate_task(args.task)
    directory = run_dir(root, task)
    assert_no_symlinks(directory, root)
    state, _ = load_run(directory)
    if state["status"] != "ACTIVE":
        raise LoopError("evidence can only be captured for an active run")
    if state.get("project_policy_hash") != project_policy_hash(root):
        raise LoopError("project profile changed; create a child run before capturing evidence")
    if state.get("workflow_spec_hash") != sha256_file(SPEC_PATH):
        raise LoopError("workflow specification changed; create a child run before capturing evidence")
    if state.get("agent_contract_hash") != hash_tree(PLUGIN_ROOT / "assets" / "agents"):
        raise LoopError("agent contract changed; create a child run before capturing evidence")
    if args.stage != state["state"]:
        raise LoopError(f"evidence stage {args.stage} does not match current state {state['state']}")
    before = workspace_snapshot(root)
    evidence_id = re.sub(r"[^A-Za-z0-9._-]+", "-", args.label).strip(".-_")[:40] or "evidence"
    evidence_id += "-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    relative = Path("evidence") / evidence_id
    evidence_dir = directory / relative
    assert_no_symlinks(evidence_dir, directory)
    evidence_dir.mkdir(parents=True, exist_ok=False)
    stdout_path = evidence_dir / "stdout.log"
    stderr_path = evidence_dir / "stderr.log"
    started = utc_now()
    timed_out = False
    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            try:
                process = subprocess.Popen(command, cwd=root, stdout=stdout, stderr=stderr, start_new_session=True)
                try:
                    exit_code = process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    stderr.write(f"command timed out after {timeout_seconds}s\n".encode("utf-8"))
                    stderr.flush()
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        with contextlib.suppress(ProcessLookupError):
                            os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    exit_code = 124
            except FileNotFoundError as exc:
                stderr.write((str(exc) + "\n").encode("utf-8"))
                exit_code = 127
    except Exception:
        shutil.rmtree(evidence_dir, ignore_errors=True)
        raise
    ended = utc_now()
    after = workspace_snapshot(root)
    metadata = {
        "schema_version": 1,
        "evidence_id": evidence_id,
        "run_id": task,
        "stage": args.stage,
        "label": args.label,
        "command_key": args.command_key,
        "command": command,
        "cwd": str(root),
        "started_at": started,
        "ended_at": ended,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "timeout_seconds": timeout_seconds,
        "commit": after["commit"],
        "workspace_digest": after["workspace_digest"],
        "workspace_changed_during_command": before["workspace_digest"] != after["workspace_digest"],
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_sha256": sha256_file(stderr_path),
    }
    atomic_json(evidence_dir / "metadata.json", metadata)
    entry = {
        "evidence_id": evidence_id,
        "label": args.label,
        "stage": args.stage,
        "relative_dir": relative.as_posix(),
        "metadata_sha256": sha256_file(evidence_dir / "metadata.json"),
        "exit_code": exit_code,
        "commit": after["commit"],
        "workspace_digest": after["workspace_digest"],
        "recorded_at": ended,
    }

    def apply(current: dict[str, Any]) -> dict[str, Any]:
        if current["status"] != "ACTIVE":
            raise LoopError("run stopped while evidence command was executing; evidence remains unregistered")
        current["evidence"].append(entry)
        return {"evidence_id": evidence_id, "label": args.label, "exit_code": exit_code}

    updated = mutate_run(root, task, args.actor, "EVIDENCE_RECORDED", apply)
    emit({"evidence": entry, "passed": exit_code == 0, "run_event": updated["last_event_seq"]})
    if exit_code != 0:
        raise SystemExit(exit_code if 0 < exit_code < 126 else 2)


def finding_open(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    if args.priority not in SPEC["finding_priorities"]:
        raise LoopError(f"invalid finding priority: {args.priority}")
    finding_id = args.finding_id or (args.priority.lower() + "-" + uuid.uuid4().hex[:8])
    current_workspace = workspace_snapshot(root)

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        if any(item.get("finding_id") == finding_id for item in state["findings"]):
            raise LoopError(f"finding already exists: {finding_id}")
        finding = {
            "finding_id": finding_id,
            "priority": args.priority,
            "title": args.title,
            "status": "OPEN",
            "owner": args.owner,
            "opened_by": args.actor,
            "opened_at": utc_now(),
            "affected_commit": current_workspace["commit"],
            "affected_workspace_digest": current_workspace["workspace_digest"],
            "evidence_refs": list(args.evidence or []),
            "verification_spec": args.verification_spec,
            "deferral_reason": None,
            "due_condition": None,
            "verifier": None,
            "verified_commit": None,
            "verified_workspace_digest": None,
        }
        state["findings"].append(finding)
        return {"finding": finding}

    state = mutate_run(root, args.task, args.actor, "FINDING_OPENED", apply)
    emit({"finding_id": finding_id, "run_event": state["last_event_seq"]})


def finding_update(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    if args.status not in SPEC["finding_states"]:
        raise LoopError(f"invalid finding status: {args.status}")
    current_workspace = workspace_snapshot(root)

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        finding = next((item for item in state["findings"] if item.get("finding_id") == args.finding_id), None)
        if finding is None:
            raise LoopError(f"finding not found: {args.finding_id}")
        previous = finding["status"]
        allowed = {
            "OPEN": {"FIXED", "DEFERRED"},
            "FIXED": {"OPEN", "VERIFIED", "DEFERRED"},
            "VERIFIED": {"OPEN"},
            "DEFERRED": {"OPEN", "FIXED"},
        }
        if args.status == previous:
            raise LoopError("finding already has that status")
        if args.status not in allowed.get(previous, set()):
            raise LoopError(f"illegal finding transition: {previous} -> {args.status}")
        if args.status == "DEFERRED":
            if finding["priority"] == "P0":
                raise LoopError("P0 findings cannot be deferred")
            if not (args.owner and args.reason and args.due_condition):
                raise LoopError("deferral requires --owner, --reason, and --due-condition")
            finding["owner"] = args.owner
            finding["deferral_reason"] = args.reason
            finding["due_condition"] = args.due_condition
        if args.status == "FIXED":
            if not args.evidence:
                raise LoopError("FIXED requires at least one --evidence reference")
            finding["evidence_refs"] = list(dict.fromkeys([*finding.get("evidence_refs", []), *args.evidence]))
            finding["fixed_by"] = args.actor
            finding["fixed_at"] = utc_now()
        if args.status == "VERIFIED":
            if not args.independent or args.actor == finding.get("owner"):
                raise LoopError("VERIFIED requires an independent actor distinct from the finding owner")
            refs = list(dict.fromkeys([*finding.get("evidence_refs", []), *(args.evidence or [])]))
            if not refs:
                raise LoopError("VERIFIED requires evidence references")
            for ref in refs:
                item = find_evidence(state, ref)
                if item is None or item.get("exit_code") != 0:
                    raise LoopError(f"verification evidence is missing or failed: {ref}")
                if item.get("workspace_digest") != current_workspace["workspace_digest"]:
                    raise LoopError(f"verification evidence is stale: {ref}")
            finding["evidence_refs"] = refs
            finding["verifier"] = args.actor
            finding["verified_at"] = utc_now()
            finding["verified_commit"] = current_workspace["commit"]
            finding["verified_workspace_digest"] = current_workspace["workspace_digest"]
        if args.status == "OPEN":
            finding["verifier"] = None
            finding["verified_at"] = None
            finding["verified_commit"] = None
            finding["verified_workspace_digest"] = None
        finding["status"] = args.status
        finding["updated_at"] = utc_now()
        return {"finding_id": args.finding_id, "from": previous, "to": args.status, "reason": args.reason}

    state = mutate_run(root, args.task, args.actor, "FINDING_UPDATED", apply)
    emit({"finding_id": args.finding_id, "status": args.status, "run_event": state["last_event_seq"]})


def valid_approval(
    state: dict[str, Any], action: str, target: str, commit: str, workspace_digest: str | None = None
) -> dict[str, Any] | None:
    now = dt.datetime.now(dt.timezone.utc)
    candidates = [
        item for item in state.get("approvals", [])
        if item.get("action") == action
        and item.get("target") == target
        and item.get("commit") == commit
        and item.get("project_policy_hash") == state.get("project_policy_hash")
        and (workspace_digest is None or item.get("workspace_digest") == workspace_digest)
        and not item.get("revoked_at")
    ]
    for item in reversed(candidates):
        if parse_time(item["expires_at"]) > now:
            return item
    return None


def authorize(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    if args.action not in SPEC["external_actions"]:
        raise LoopError(f"unsupported external action: {args.action}")
    current = workspace_snapshot(root)
    if args.commit != current["commit"]:
        raise LoopError("approval commit must equal the current repository commit")
    if parse_time(args.expires) <= dt.datetime.now(dt.timezone.utc):
        raise LoopError("approval expiry must be in the future")
    approval_id = "approval-" + uuid.uuid4().hex[:12]

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        if state["state"] != "AWAITING_EXTERNAL_APPROVAL":
            raise LoopError("authorization may only be recorded in AWAITING_EXTERNAL_APPROVAL")
        approval = {
            "approval_id": approval_id,
            "action": args.action,
            "target": args.target,
            "commit": args.commit,
            "workspace_digest": current["workspace_digest"],
            "project_policy_hash": state["project_policy_hash"],
            "granted_by": args.granted_by,
            "granted_at": utc_now(),
            "expires_at": args.expires,
            "scope_note": args.scope_note,
            "revoked_at": None,
        }
        state["approvals"].append(approval)
        return {"approval": approval}

    state = mutate_run(root, args.task, args.actor, "AUTHORIZATION_RECORDED", apply)
    emit({"approval_id": approval_id, "run_event": state["last_event_seq"]})


def approval_check(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    directory = run_dir(root, args.task)
    assert_no_symlinks(directory, root)
    state, _ = load_run(directory)
    current = workspace_snapshot(root)
    approval = valid_approval(state, args.action, args.target, args.commit, current["workspace_digest"])
    emit({"valid": approval is not None, "approval": approval})
    if approval is None:
        raise SystemExit(2)


def action_begin(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    if args.action not in SPEC["external_actions"]:
        raise LoopError(f"unsupported external action: {args.action}")
    current = workspace_snapshot(root)
    if args.commit != current["commit"]:
        raise LoopError("external action commit must equal current repository commit")
    operation_id = args.operation_id or (args.action + "-" + uuid.uuid4().hex[:12])

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        if state["state"] != "DELIVERING":
            raise LoopError("external action intent requires state DELIVERING")
        existing = next((item for item in state["external_actions"] if item.get("operation_id") == operation_id), None)
        if existing:
            requested = (args.action, args.target, args.commit)
            recorded = (existing.get("action"), existing.get("target"), existing.get("commit"))
            if requested != recorded:
                raise LoopError("operation id was already used for a different action")
            raise LoopError(f"operation already recorded with status {existing.get('status')}; reconcile instead of replaying")
        approval = valid_approval(state, args.action, args.target, args.commit, current["workspace_digest"])
        if approval is None:
            raise LoopError("no current action-scoped approval matches action, target, and commit")
        operation = {
            "operation_id": operation_id,
            "idempotency_key": sha256_bytes(canonical_bytes({"run": state["run_id"], "operation": operation_id, "action": args.action, "target": args.target, "commit": args.commit})),
            "approval_id": approval["approval_id"],
            "action": args.action,
            "target": args.target,
            "commit": args.commit,
            "workspace_digest": current["workspace_digest"],
            "expected_before_state": args.expected_before_state,
            "status": "PENDING",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "observed_state": None,
            "evidence_refs": [],
        }
        state["external_actions"].append(operation)
        return {"operation": operation}

    state = mutate_run(root, args.task, args.actor, "EXTERNAL_ACTION_INTENT", apply)
    emit({"operation_id": operation_id, "status": "PENDING", "run_event": state["last_event_seq"]})


def action_complete(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    if args.result not in {"SUCCESS", "FAILED", "UNKNOWN"}:
        raise LoopError("result must be SUCCESS, FAILED, or UNKNOWN")

    def apply(state: dict[str, Any]) -> dict[str, Any]:
        if state["state"] != "DELIVERING":
            raise LoopError("external action reconciliation requires state DELIVERING")
        operation = next((item for item in state["external_actions"] if item.get("operation_id") == args.operation_id), None)
        if operation is None:
            raise LoopError(f"operation not found: {args.operation_id}")
        if operation["status"] not in {"PENDING", "UNKNOWN"}:
            raise LoopError(f"operation is already terminal: {operation['status']}")
        if args.result == "SUCCESS" and not args.observed_state:
            raise LoopError("successful external action requires --observed-state")
        for ref in args.evidence or []:
            if find_evidence(state, ref) is None:
                raise LoopError(f"unknown evidence reference: {ref}")
        operation["status"] = args.result
        operation["observed_state"] = args.observed_state
        operation["evidence_refs"] = list(args.evidence or [])
        operation["updated_at"] = utc_now()
        operation["completed_by"] = args.actor
        return {"operation_id": args.operation_id, "result": args.result, "observed_state": args.observed_state}

    state = mutate_run(root, args.task, args.actor, "EXTERNAL_ACTION_RECONCILED", apply)
    emit({"operation_id": args.operation_id, "status": args.result, "run_event": state["last_event_seq"]})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="subcommand", required=True)

    item = commands.add_parser("bootstrap", help="install the optional project profile and run directories")
    item.add_argument("--root", required=True)
    item.add_argument("--dry-run", action="store_true")
    item.set_defaults(function=bootstrap)

    item = commands.add_parser("audit", help="audit the optional project profile and run directories")
    item.add_argument("--root", required=True)
    item.set_defaults(function=audit)

    item = commands.add_parser("start", help="start an idempotent run")
    item.add_argument("--root", required=True)
    item.add_argument("--task")
    item.add_argument("--title", required=True)
    item.add_argument("--parent-run")
    item.add_argument("--actor", default="main")
    item.set_defaults(function=start)

    item = commands.add_parser("status", help="show runs without changing them")
    item.add_argument("--root", required=True)
    item.add_argument("--task")
    item.set_defaults(function=status)

    item = commands.add_parser("resume", help="resume a paused or blocked run")
    item.add_argument("--root", required=True)
    item.add_argument("--task", required=True)
    item.add_argument("--actor", default="main")
    item.set_defaults(function=resume)

    item = commands.add_parser("transition", help="perform a guarded state/status transition")
    item.add_argument("--root", required=True)
    item.add_argument("--task", required=True)
    item.add_argument("--state")
    item.add_argument("--stage", help="compatibility alias for --state")
    item.add_argument("--status")
    item.add_argument("--reason", required=True)
    item.add_argument("--actor", default="main")
    item.set_defaults(function=transition)

    item = commands.add_parser("evidence", help="run argv directly and record tamper-evident output")
    item.add_argument("--root", required=True)
    item.add_argument("--task", required=True)
    item.add_argument("--stage", required=True)
    item.add_argument("--label", required=True)
    item.add_argument("--command-key", required=True)
    item.add_argument("--actor", default="main")
    item.add_argument("argv", nargs=argparse.REMAINDER)
    item.set_defaults(function=evidence)

    item = commands.add_parser("finding-open", help="open a P0/P1/P2 finding")
    item.add_argument("--root", required=True)
    item.add_argument("--task", required=True)
    item.add_argument("--finding-id")
    item.add_argument("--priority", required=True)
    item.add_argument("--title", required=True)
    item.add_argument("--owner", required=True)
    item.add_argument("--verification-spec", required=True)
    item.add_argument("--evidence", action="append")
    item.add_argument("--actor", default="reviewer")
    item.set_defaults(function=finding_open)

    item = commands.add_parser("finding-update", help="move a finding through remediation states")
    item.add_argument("--root", required=True)
    item.add_argument("--task", required=True)
    item.add_argument("--finding-id", required=True)
    item.add_argument("--status", required=True)
    item.add_argument("--owner")
    item.add_argument("--reason")
    item.add_argument("--due-condition")
    item.add_argument("--evidence", action="append")
    item.add_argument("--independent", action="store_true")
    item.add_argument("--actor", required=True)
    item.set_defaults(function=finding_update)

    item = commands.add_parser("authorize", help="record explicit action-scoped user authorization")
    item.add_argument("--root", required=True)
    item.add_argument("--task", required=True)
    item.add_argument("--action", required=True)
    item.add_argument("--target", required=True)
    item.add_argument("--commit", required=True)
    item.add_argument("--granted-by", required=True)
    item.add_argument("--expires", required=True)
    item.add_argument("--scope-note", required=True)
    item.add_argument("--actor", default="main")
    item.set_defaults(function=authorize)

    item = commands.add_parser("approval-check", help="check an action-scoped approval read-only")
    item.add_argument("--root", required=True)
    item.add_argument("--task", required=True)
    item.add_argument("--action", required=True)
    item.add_argument("--target", required=True)
    item.add_argument("--commit", required=True)
    item.set_defaults(function=approval_check)

    item = commands.add_parser("action-begin", help="record an idempotent external-action intent")
    item.add_argument("--root", required=True)
    item.add_argument("--task", required=True)
    item.add_argument("--action", required=True)
    item.add_argument("--target", required=True)
    item.add_argument("--commit", required=True)
    item.add_argument("--operation-id")
    item.add_argument("--expected-before-state", required=True)
    item.add_argument("--actor", default="main")
    item.set_defaults(function=action_begin)

    item = commands.add_parser("action-complete", help="record reconciliation of an external action")
    item.add_argument("--root", required=True)
    item.add_argument("--task", required=True)
    item.add_argument("--operation-id", required=True)
    item.add_argument("--result", required=True)
    item.add_argument("--observed-state")
    item.add_argument("--evidence", action="append")
    item.add_argument("--actor", default="main")
    item.set_defaults(function=action_complete)

    item = commands.add_parser("validate", help="validate state, evidence, findings, and an optional gate")
    item.add_argument("--root", required=True)
    item.add_argument("--task", required=True)
    item.add_argument("--gate", choices=["complete", "release"])
    item.set_defaults(function=validate_command)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.function(args)
        return 0
    except LoopError as exc:
        print(f"loopctl: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

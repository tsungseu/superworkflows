#!/usr/bin/env python3
"""Validate and transactionally install namespaced Superworkflows agents."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # Python 3.10 compatibility on the current Codex host
    import tomli as tomllib  # type: ignore[no-redef]


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = PLUGIN_ROOT / "assets" / "agents"
READ_ONLY_AGENTS = {
    "sw-explorer",
    "sw-robot-system-architect",
    "sw-robot-safety-reviewer",
    "sw-robot-sim2real-validator",
    "sw-robot-release-engineer",
}
ALLOWED_EFFORT = {"low", "medium", "high", "xhigh", "max", "ultra"}
REQUIRED_MARKERS = ("do not spawn or delegate", ".ai/runs/**", "run_id", "input commit/digest")
TRANSACTION_RE = re.compile(r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}")


class SyncError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    if path.is_symlink():
        raise SyncError(f"refusing symbolic-link target: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
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


def safe_regular_bytes(path: Path) -> bytes:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise SyncError(f"refusing non-regular file: {path}")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        chunks = []
        remaining = info.st_size + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def parse_agent(path: Path, data: bytes | None = None) -> dict[str, Any]:
    if path.is_symlink():
        raise SyncError(f"agent source/target is a symbolic link: {path}")
    raw = data if data is not None else safe_regular_bytes(path)
    try:
        value = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise SyncError(f"invalid TOML: {path}: {exc}") from exc
    name = value.get("name")
    if name != path.stem:
        raise SyncError(f"agent name must equal filename: {path.name} has {name!r}")
    if not isinstance(name, str) or not name.startswith("sw-"):
        raise SyncError(f"agent is not namespaced: {path.name}")
    if not isinstance(value.get("model"), str) or not value["model"]:
        raise SyncError(f"agent has no model: {path.name}")
    if value.get("model_reasoning_effort") not in ALLOWED_EFFORT:
        raise SyncError(f"agent has invalid reasoning effort: {path.name}")
    if name in READ_ONLY_AGENTS and value.get("sandbox_mode") != "read-only":
        raise SyncError(f"review/advisory agent must be read-only: {path.name}")
    instructions = value.get("developer_instructions")
    if not isinstance(instructions, str):
        raise SyncError(f"agent has no developer instructions: {path.name}")
    lowered = instructions.lower()
    missing = [marker for marker in REQUIRED_MARKERS if marker.lower() not in lowered]
    if missing:
        raise SyncError(f"agent child contract is incomplete in {path.name}: {', '.join(missing)}")
    return value


def load_sources() -> dict[str, tuple[bytes, dict[str, Any]]]:
    if SOURCE_DIR.is_symlink() or not SOURCE_DIR.is_dir():
        raise SyncError(f"invalid agent source directory: {SOURCE_DIR}")
    sources: dict[str, tuple[bytes, dict[str, Any]]] = {}
    for path in sorted(SOURCE_DIR.glob("*.toml")):
        raw = safe_regular_bytes(path)
        sources[path.name] = (raw, parse_agent(path, raw))
    if not sources:
        raise SyncError("no bundled agent definitions found")
    return sources


def validate_runtime_models(sources: dict[str, tuple[bytes, dict[str, Any]]]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["codex", "debug", "models", "--bundled"], text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False
        )
    except FileNotFoundError as exc:
        raise SyncError("codex executable is unavailable for runtime model validation") from exc
    if result.returncode != 0:
        raise SyncError("codex model catalog validation failed: " + result.stderr.strip())
    try:
        catalog = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SyncError("codex model catalog returned invalid JSON") from exc
    models = {item.get("slug"): item for item in catalog.get("models", []) if isinstance(item, dict)}
    issues = []
    for filename, (_, agent) in sources.items():
        model = models.get(agent["model"])
        if model is None:
            issues.append(f"{filename}: unavailable model {agent['model']}")
            continue
        efforts = {item.get("effort") for item in model.get("supported_reasoning_levels", []) if isinstance(item, dict)}
        if agent["model_reasoning_effort"] not in efforts:
            issues.append(f"{filename}: unsupported effort {agent['model_reasoning_effort']} for {agent['model']}")
    if issues:
        raise SyncError("runtime agent/model incompatibility: " + "; ".join(issues))
    return {"catalog_source": "codex debug models --bundled", "models_checked": sorted({agent[1]["model"] for agent in sources.values()})}


def contract_view(value: dict[str, Any]) -> dict[str, Any]:
    instructions = str(value.get("developer_instructions", "")).lower()
    return {
        "name": value.get("name"),
        "model": value.get("model"),
        "model_reasoning_effort": value.get("model_reasoning_effort"),
        "sandbox_mode": value.get("sandbox_mode"),
        "child_contract": {marker: marker.lower() in instructions for marker in REQUIRED_MARKERS},
    }


def resolve_target(args: argparse.Namespace) -> Path:
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
    default = codex_home / "agents"
    target = Path(args.target).expanduser() if args.target else default
    if args.target and not args.allow_custom_target:
        raise SyncError("custom --target requires --allow-custom-target")
    if target.exists() and target.is_symlink():
        raise SyncError(f"refusing symbolic-link agent directory: {target}")
    if not args.target:
        expected_parent = codex_home.resolve(strict=False)
        if target.resolve(strict=False).parent != expected_parent:
            raise SyncError("default target escaped CODEX_HOME")
    return target


def check_target_file(path: Path, target_dir: Path) -> None:
    if path.parent.resolve(strict=False) != target_dir.resolve(strict=False):
        raise SyncError(f"target escapes agent directory: {path}")
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise SyncError(f"refusing symbolic-link or non-regular target: {path}")


def safe_directory(path: Path, create: bool = False) -> Path:
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise SyncError(f"refusing symbolic-link or non-directory path: {path}")
    elif create:
        path.mkdir(parents=False, exist_ok=False)
        fsync_dir(path.parent)
    else:
        raise SyncError(f"missing directory: {path}")
    return path


def inspect(target_dir: Path, sources: dict[str, tuple[bytes, dict[str, Any]]]) -> dict[str, Any]:
    results = []
    for filename, (source_raw, source_value) in sources.items():
        target = target_dir / filename
        check_target_file(target, target_dir)
        if not target.exists():
            results.append({"name": filename, "status": "missing", "compatible": False})
            continue
        target_raw = safe_regular_bytes(target)
        try:
            target_value = parse_agent(target, target_raw)
            compatible = contract_view(target_value) == contract_view(source_value)
            error = None
        except SyncError as exc:
            compatible = False
            error = str(exc)
        results.append(
            {
                "name": filename,
                "status": "identical" if target_raw == source_raw else ("compatible-local" if compatible else "conflict"),
                "compatible": compatible,
                "source_sha256": sha256_bytes(source_raw),
                "target_sha256": sha256_bytes(target_raw),
                "error": error,
            }
        )
    return {
        "target": str(target_dir),
        "valid": all(item["compatible"] for item in results),
        "agents": results,
    }


@contextlib.contextmanager
def install_lock(target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    if target_dir.is_symlink():
        raise SyncError(f"refusing symbolic-link agent directory: {target_dir}")
    lock_path = target_dir / ".superworkflows-agents.lock"
    check_target_file(lock_path, target_dir)
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SyncError("another agent installation transaction holds the lock") from exc
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def install(target_dir: Path, sources: dict[str, tuple[bytes, dict[str, Any]]], force: bool) -> dict[str, Any]:
    transaction_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    with install_lock(target_dir):
        backup_base = target_dir / ".superworkflows-backups"
        if not backup_base.exists() and not backup_base.is_symlink():
            safe_directory(backup_base, create=True)
        else:
            safe_directory(backup_base)
        backup_root = backup_base / transaction_id
        manifest_path = backup_root / "manifest.json"
        current = inspect(target_dir, sources)
        conflicts = [item["name"] for item in current["agents"] if item["status"] == "conflict"]
        if conflicts and not force:
            raise SyncError("incompatible agents require --force: " + ", ".join(conflicts))
        operations = []
        for filename, (raw, value) in sources.items():
            target = target_dir / filename
            check_target_file(target, target_dir)
            previous = safe_regular_bytes(target) if target.exists() else None
            if previous == raw or (previous is not None and not force and contract_view(parse_agent(target, previous)) == contract_view(value)):
                continue
            operations.append(
                {
                    "name": filename,
                    "target": str(target),
                    "existed": previous is not None,
                    "previous_sha256": sha256_bytes(previous) if previous is not None else None,
                    "installed_sha256": sha256_bytes(raw),
                }
            )
        backup_root.mkdir(parents=True, exist_ok=False)
        manifest = {
            "schema_version": 1,
            "transaction_id": transaction_id,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "target_dir": str(target_dir.resolve()),
            "status": "PREPARED",
            "operations": operations,
        }
        atomic_json(manifest_path, manifest)
        applied: list[dict[str, Any]] = []
        try:
            for operation in operations:
                filename = operation["name"]
                target = target_dir / filename
                check_target_file(target, target_dir)
                if operation["existed"]:
                    previous = safe_regular_bytes(target)
                    if sha256_bytes(previous) != operation["previous_sha256"]:
                        raise SyncError(f"target changed during transaction: {target}")
                    atomic_write(backup_root / filename, previous, 0o600)
                atomic_write(target, sources[filename][0], 0o644)
                if sha256_file(target) != operation["installed_sha256"]:
                    raise SyncError(f"post-install hash mismatch: {target}")
                applied.append(operation)
        except Exception as exc:
            rollback_errors = []
            for operation in reversed(applied):
                target = target_dir / operation["name"]
                try:
                    if operation["existed"]:
                        atomic_write(target, safe_regular_bytes(backup_root / operation["name"]), 0o644)
                    elif target.exists():
                        target.unlink()
                        fsync_dir(target_dir)
                except Exception as rollback_exc:  # pragma: no cover - catastrophic filesystem failure
                    rollback_errors.append(str(rollback_exc))
            manifest["status"] = "ROLLBACK_FAILED" if rollback_errors else "ROLLED_BACK"
            manifest["error"] = str(exc)
            manifest["rollback_errors"] = rollback_errors
            atomic_json(manifest_path, manifest)
            raise SyncError(f"installation failed and was {'not fully ' if rollback_errors else ''}rolled back: {exc}") from exc
        manifest["status"] = "COMMITTED"
        manifest["committed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        atomic_json(manifest_path, manifest)
    return {"transaction_id": transaction_id, "installed": [item["name"] for item in operations], "manifest": str(manifest_path)}


def rollback(target_dir: Path, transaction_id: str, force: bool) -> dict[str, Any]:
    if not TRANSACTION_RE.fullmatch(transaction_id):
        raise SyncError("invalid transaction id")
    with install_lock(target_dir):
        backup_base = safe_directory(target_dir / ".superworkflows-backups")
        backup_root = safe_directory(backup_base / transaction_id)
        manifest_path = backup_root / "manifest.json"
        manifest = json.loads(safe_regular_bytes(manifest_path).decode("utf-8"))
        if Path(manifest.get("target_dir", "")).resolve() != target_dir.resolve():
            raise SyncError("transaction target directory does not match")
        if manifest.get("status") != "COMMITTED":
            raise SyncError(f"transaction is not committed: {manifest.get('status')}")
        for operation in manifest.get("operations", []):
            target = target_dir / operation["name"]
            check_target_file(target, target_dir)
            if target.exists() and sha256_file(target) != operation["installed_sha256"] and not force:
                raise SyncError(f"target changed after install; use --force to roll back: {target}")
        for operation in reversed(manifest.get("operations", [])):
            target = target_dir / operation["name"]
            if operation["existed"]:
                atomic_write(target, safe_regular_bytes(backup_root / operation["name"]), 0o644)
            elif target.exists():
                target.unlink()
                fsync_dir(target_dir)
        manifest["status"] = "ROLLED_BACK"
        manifest["rolled_back_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        atomic_json(manifest_path, manifest)
    return {"transaction_id": transaction_id, "status": "ROLLED_BACK"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="validate runtime compatibility (default)")
    mode.add_argument("--install", action="store_true", help="transactionally install missing/incompatible agents")
    mode.add_argument("--rollback", metavar="TRANSACTION_ID", help="roll back a committed transaction")
    parser.add_argument("--force", action="store_true", help="replace conflicts or force rollback over later changes")
    parser.add_argument("--target", help="custom agent directory")
    parser.add_argument("--allow-custom-target", action="store_true")
    parser.add_argument("--check-json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--skip-runtime-model-check", action="store_true", help="skip Codex catalog compatibility validation")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        sources = load_sources()
        model_check = {"skipped": True} if args.skip_runtime_model_check else validate_runtime_models(sources)
        target = resolve_target(args)
        if args.rollback:
            result = rollback(target, args.rollback, args.force)
        elif args.install:
            result = install(target, sources, args.force)
            result["check"] = inspect(target, sources)
        else:
            result = inspect(target, sources)
        result["runtime_model_check"] = model_check
        if args.check_json or args.install or args.rollback:
            print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        else:
            for item in result["agents"]:
                print(f"{item['status']:>16}  {item['name']}")
            print("compatible" if result["valid"] else "not compatible")
        if not args.install and not args.rollback and not result.get("valid", True):
            return 2
        return 0
    except (SyncError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"sync_agents: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

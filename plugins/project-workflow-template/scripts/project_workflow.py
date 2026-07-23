#!/usr/bin/env python3
"""Deterministic initializer, migrator, verifier, and restorer for project workspaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_ROOT.parent
TEMPLATE_ROOT = PLUGIN_ROOT / "assets" / "project-template"
MANIFEST_PATH = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
MARKER_REL = Path(".codex/project-workflow.json")

CORE_COMPONENTS = [Path("AGENTS.md"), Path(".agents/skills")]
DOC_COMPONENTS = [Path("README.md"), Path("HUMAN_WORKFLOW_GUIDE.md")]
HOOK_COMPONENTS = [
    Path(".codex/hooks.json"),
    Path(".codex/hooks/check-sot-drift.ps1"),
    Path(".codex/hooks/check-sot-drift.sh"),
]
STANDARD_DIRS = [
    Path("SOT/REVIEW"),
    Path("SOT/HISTORY"),
    Path("01_INBOX"),
    Path("02_SOURCE/COMMUNICATION_LOG"),
    Path("03_WORK"),
    Path("04_OUTPUT"),
    Path("05_MEETING"),
    Path("06_KNOWLEDGE/CANDIDATES"),
]
PROTECTED_PATHS = [
    "SOT",
    "01_INBOX",
    "02_SOURCE",
    "03_WORK",
    "03_WORKS",
    "04_OUTPUT",
    "05_MEETING",
    "06_KNOWLEDGE",
]


class WorkflowError(RuntimeError):
    pass


def plugin_version() -> str:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["version"]


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reject_symlinks(path: Path) -> None:
    if path.is_symlink():
        raise WorkflowError(f"Symbolic links are not supported: {path}")
    if path.is_dir():
        for child in path.rglob("*"):
            if child.is_symlink():
                raise WorkflowError(f"Symbolic links are not supported: {child}")


def hash_path(path: Path) -> str | None:
    if not path.exists():
        return None
    reject_symlinks(path)
    if path.is_file():
        return sha256_file(path)
    digest = hashlib.sha256()
    for child in sorted(path.rglob("*"), key=lambda item: item.as_posix()):
        relative = child.relative_to(path).as_posix()
        if child.is_dir():
            digest.update(f"D\0{relative}\0".encode("utf-8"))
        elif child.is_file():
            digest.update(f"F\0{relative}\0{sha256_file(child)}\0".encode("utf-8"))
    return digest.hexdigest()


def kind_of(path: Path) -> str:
    if not path.exists():
        return "missing"
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return "other"


def stable_fingerprint(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_remove(path: Path, target: Path) -> None:
    absolute = path.absolute()
    root = target.absolute()
    if absolute == root or not is_within(absolute, root):
        raise WorkflowError(f"Refusing destructive operation outside the target: {absolute}")
    if path.is_symlink():
        raise WorkflowError(f"Refusing to remove a symbolic link: {path}")
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def copy_exact(source: Path, destination: Path) -> None:
    reject_symlinks(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def snapshot(paths: list[Path], target: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": relative.as_posix(),
            "kind": kind_of(target / relative),
            "hash": hash_path(target / relative),
        }
        for relative in paths
    ]


def merge_hooks(existing_path: Path, bundled_path: Path) -> dict[str, Any]:
    existing = json.loads(existing_path.read_text(encoding="utf-8")) if existing_path.exists() else {"hooks": {}}
    bundled = json.loads(bundled_path.read_text(encoding="utf-8"))
    if not isinstance(existing.get("hooks"), dict) or not isinstance(bundled.get("hooks"), dict):
        raise WorkflowError("hooks.json must contain a hooks object")

    for event, groups in list(existing["hooks"].items()):
        cleaned_groups = []
        for group in groups if isinstance(groups, list) else []:
            if not isinstance(group, dict):
                cleaned_groups.append(group)
                continue
            hooks = group.get("hooks")
            if not isinstance(hooks, list):
                cleaned_groups.append(group)
                continue
            kept = [
                hook
                for hook in hooks
                if "check-sot-drift" not in str(hook.get("command", ""))
                and "check-sot-drift" not in str(hook.get("commandWindows", ""))
            ]
            if kept:
                updated = dict(group)
                updated["hooks"] = kept
                cleaned_groups.append(updated)
        existing["hooks"][event] = cleaned_groups

    for event, groups in bundled["hooks"].items():
        existing["hooks"].setdefault(event, [])
        existing["hooks"][event].extend(groups)
    return existing


def init_plan(target: Path) -> dict[str, Any]:
    target_exists = target.exists()
    children = sorted(child.name for child in target.iterdir()) if target_exists and target.is_dir() else []
    if target_exists and (not target.is_dir() or children):
        return {
            "status": "requires_migration",
            "target": str(target),
            "reason": "The target is not an empty directory.",
            "existingTopLevelEntries": children,
        }
    state = {"targetExists": target_exists, "children": children}
    files = sorted(
        path.relative_to(TEMPLATE_ROOT).as_posix()
        for path in TEMPLATE_ROOT.rglob("*")
        if path.is_file()
    )
    return {
        "status": "planned",
        "action": "initialize",
        "target": str(target),
        "templateVersion": plugin_version(),
        "files": files + [MARKER_REL.as_posix()],
        "directories": [item.as_posix() for item in STANDARD_DIRS],
        "fingerprint": stable_fingerprint(state),
        "state": state,
    }


def write_marker(target: Path, latest_backup: str | None, managed: dict[str, Any]) -> None:
    write_json(
        target / MARKER_REL,
        {
            "schemaVersion": 1,
            "templateVersion": plugin_version(),
            "installedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
            "sourcePlugin": "project-workflow-template",
            "latestBackup": latest_backup,
            "managedComponents": managed,
        },
    )


def initialize(args: argparse.Namespace) -> None:
    target = Path(args.target).expanduser().absolute()
    plan = init_plan(target)
    if not args.apply or plan["status"] != "planned":
        emit(plan, 2 if plan["status"] == "requires_migration" else 0)
    if not args.expected_fingerprint or args.expected_fingerprint != plan["fingerprint"]:
        emit({"status": "aborted", "reason": "Fingerprint mismatch; request a new initialization plan.", **plan}, 3)

    target.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        for source in sorted(TEMPLATE_ROOT.rglob("*"), key=lambda item: (len(item.parts), item.as_posix())):
            relative = source.relative_to(TEMPLATE_ROOT)
            destination = target / relative
            if source.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                copy_exact(source, destination)
                created.append(destination)
        for relative in STANDARD_DIRS:
            (target / relative).mkdir(parents=True, exist_ok=True)
        managed_paths = CORE_COMPONENTS + DOC_COMPONENTS + HOOK_COMPONENTS + [Path("SOT/SourceOfTruth.md")]
        managed = {
            item.as_posix(): {
                "templateHash": hash_path(TEMPLATE_ROOT / item),
                "installedHash": hash_path(target / item),
            }
            for item in managed_paths
        }
        write_marker(target, None, managed)
    except Exception:
        for path in sorted(created, key=lambda item: len(item.parts), reverse=True):
            if path.exists():
                safe_remove(path, target)
        raise
    emit({"status": "initialized", "target": str(target), "templateVersion": plugin_version(), "createdFiles": plan["files"]})


def selected_components(args: argparse.Namespace) -> list[Path]:
    result = list(CORE_COMPONENTS)
    if args.include_docs:
        result.extend(DOC_COMPONENTS)
    if args.include_hooks:
        result.extend(HOOK_COMPONENTS)
    return result


def migration_plan(args: argparse.Namespace, target: Path) -> dict[str, Any]:
    if not target.is_dir():
        raise WorkflowError(f"Target directory does not exist: {target}")
    components = selected_components(args)
    current = snapshot(components + ([MARKER_REL] if (target / MARKER_REL).exists() else []), target)
    operations = []
    for relative in components:
        current_hash = hash_path(target / relative)
        template_hash = hash_path(TEMPLATE_ROOT / relative)
        if relative == Path(".codex/hooks.json") and args.include_hooks:
            action = "merge" if (target / relative).exists() else "create"
        elif current_hash is None:
            action = "create"
        elif current_hash == template_hash:
            action = "keep"
        else:
            action = "replace"
        operations.append(
            {
                "path": relative.as_posix(),
                "action": action,
                "currentHash": current_hash,
                "templateHash": template_hash,
            }
        )
    if args.create_missing_folders:
        for relative in STANDARD_DIRS:
            operations.append(
                {
                    "path": relative.as_posix(),
                    "action": "keep" if (target / relative).is_dir() else "create-directory",
                    "currentHash": hash_path(target / relative),
                    "templateHash": None,
                }
            )
    fingerprint_payload = {
        "target": str(target),
        "version": plugin_version(),
        "options": {
            "includeDocs": args.include_docs,
            "includeHooks": args.include_hooks,
            "createMissingFolders": args.create_missing_folders,
        },
        "current": current,
    }
    backup_root = Path(args.backup_root).expanduser().absolute() if args.backup_root else target.parent / "_project-workflow-backups"
    return {
        "status": "planned",
        "action": "migrate",
        "target": str(target),
        "templateVersion": plugin_version(),
        "backupRoot": str(backup_root),
        "operations": operations,
        "protectedPaths": PROTECTED_PATHS,
        "fingerprint": stable_fingerprint(fingerprint_payload),
    }


def unique_backup_path(root: Path, target: Path) -> Path:
    if is_within(root, target):
        raise WorkflowError("Backup root must be outside the target workspace")
    project_id = sha256_bytes(str(target.resolve()).encode("utf-8"))[:8]
    base = root / f"{target.name}-{project_id}" / datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = base
    counter = 1
    while candidate.exists():
        candidate = Path(f"{base}-{counter:02d}")
        counter += 1
    return candidate


def backup_entries(target: Path, backup: Path, relative_paths: list[Path]) -> list[dict[str, Any]]:
    entries = []
    for relative in relative_paths:
        source = target / relative
        existed = source.exists()
        before_hash = hash_path(source)
        if existed:
            destination = backup / "files" / relative
            copy_exact(source, destination)
            copied_hash = hash_path(destination)
            if copied_hash != before_hash:
                raise WorkflowError(f"Backup hash verification failed: {relative.as_posix()}")
        entries.append(
            {
                "path": relative.as_posix(),
                "existed": existed,
                "kind": kind_of(source),
                "beforeHash": before_hash,
                "afterHash": None,
            }
        )
    return entries


def restore_entries(target: Path, backup: Path, entries: list[dict[str, Any]]) -> None:
    for entry in sorted(entries, key=lambda item: len(Path(item["path"]).parts), reverse=True):
        relative = Path(entry["path"])
        destination = target / relative
        if destination.exists():
            safe_remove(destination, target)
        if entry["existed"]:
            copy_exact(backup / "files" / relative, destination)


def migrate(args: argparse.Namespace) -> None:
    target = Path(args.target).expanduser().absolute()
    plan = migration_plan(args, target)
    if not args.apply:
        emit(plan)
    if not args.expected_fingerprint or args.expected_fingerprint != plan["fingerprint"]:
        emit({"status": "aborted", "reason": "Fingerprint mismatch; request a new migration plan.", **plan}, 3)

    changed = [item for item in plan["operations"] if item["action"] not in {"keep"}]
    if not changed:
        marker_path = target / MARKER_REL
        marker = json.loads(marker_path.read_text(encoding="utf-8")) if marker_path.exists() else {}
        if marker.get("templateVersion") != plugin_version():
            managed = {
                relative.as_posix(): {
                    "templateHash": hash_path(TEMPLATE_ROOT / relative),
                    "installedHash": hash_path(target / relative),
                }
                for relative in selected_components(args)
            }
            write_marker(target, marker.get("latestBackup"), managed)
        emit(
            {
                "status": "already_current",
                "target": str(target),
                "templateVersion": plugin_version(),
                "backup": None,
                "operations": [],
            }
        )
    replace_paths = [Path(item["path"]) for item in changed]
    backup_paths = list(replace_paths)
    if MARKER_REL not in backup_paths:
        backup_paths.append(MARKER_REL)
    backup_root = Path(plan["backupRoot"]).absolute()
    backup = unique_backup_path(backup_root, target)
    backup.mkdir(parents=True, exist_ok=False)
    entries = backup_entries(target, backup, backup_paths)
    manifest = {
        "schemaVersion": 1,
        "pluginVersion": plugin_version(),
        "createdAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "projectPath": str(target),
        "fingerprint": plan["fingerprint"],
        "restoredAt": None,
        "entries": entries,
    }
    write_json(backup / "manifest.json", manifest)

    try:
        for operation in changed:
            relative = Path(operation["path"])
            destination = target / relative
            action = operation["action"]
            if action == "create-directory":
                destination.mkdir(parents=True, exist_ok=True)
                continue
            if relative == Path(".codex/hooks.json") and args.include_hooks:
                merged = merge_hooks(destination, TEMPLATE_ROOT / relative)
                write_json(destination, merged)
                continue
            if destination.exists():
                safe_remove(destination, target)
            copy_exact(TEMPLATE_ROOT / relative, destination)

        managed = {}
        for relative in selected_components(args):
            managed[relative.as_posix()] = {
                "templateHash": hash_path(TEMPLATE_ROOT / relative),
                "installedHash": hash_path(target / relative),
            }
        write_marker(target, str(backup), managed)
        for entry in entries:
            entry["afterHash"] = hash_path(target / Path(entry["path"]))
        write_json(backup / "manifest.json", manifest)
    except Exception:
        restore_entries(target, backup, entries)
        raise

    emit(
        {
            "status": "migrated",
            "target": str(target),
            "templateVersion": plugin_version(),
            "backup": str(backup),
            "operations": changed,
        }
    )


def locate_backup(target: Path, supplied: str | None) -> Path:
    if supplied:
        return Path(supplied).expanduser().absolute()
    marker = target / MARKER_REL
    if not marker.is_file():
        raise WorkflowError("No marker or backup path was supplied")
    latest = json.loads(marker.read_text(encoding="utf-8")).get("latestBackup")
    if not latest:
        raise WorkflowError("The workspace marker has no latest backup")
    return Path(latest).absolute()


def restore_plan(args: argparse.Namespace, target: Path) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    backup = locate_backup(target, args.backup)
    if is_within(backup, target):
        raise WorkflowError("Backup must be outside the target workspace")
    manifest_path = backup / "manifest.json"
    if not manifest_path.is_file():
        raise WorkflowError(f"Backup manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if Path(manifest["projectPath"]).absolute() != target:
        raise WorkflowError("Backup manifest belongs to a different project path")
    current = []
    conflicts = []
    for entry in manifest["entries"]:
        relative = Path(entry["path"])
        current_hash = hash_path(target / relative)
        current.append({"path": entry["path"], "hash": current_hash})
        if current_hash != entry.get("afterHash"):
            conflicts.append({"path": entry["path"], "expected": entry.get("afterHash"), "current": current_hash})
    fingerprint = stable_fingerprint({"target": str(target), "backup": str(backup), "current": current})
    return (
        {
            "status": "planned",
            "action": "restore",
            "target": str(target),
            "backup": str(backup),
            "conflicts": conflicts,
            "canApply": not conflicts or args.force_conflicts,
            "fingerprint": fingerprint,
        },
        backup,
        manifest,
    )


def restore(args: argparse.Namespace) -> None:
    target = Path(args.target).expanduser().absolute()
    plan, backup, manifest = restore_plan(args, target)
    if not args.apply:
        emit(plan)
    if not args.expected_fingerprint or args.expected_fingerprint != plan["fingerprint"]:
        emit({"status": "aborted", "reason": "Fingerprint mismatch; request a new restore plan.", **plan}, 3)
    if plan["conflicts"] and not args.force_conflicts:
        emit({"status": "aborted", "reason": "Current files differ from the migrated state.", **plan}, 4)

    safety = backup / "restore-safety" / datetime.now().strftime("%Y%m%d-%H%M%S")
    safety.mkdir(parents=True, exist_ok=False)
    safety_entries = backup_entries(target, safety, [Path(entry["path"]) for entry in manifest["entries"]])
    try:
        restore_entries(target, backup, manifest["entries"])
        manifest["restoredAt"] = datetime.now().astimezone().isoformat(timespec="seconds")
        manifest["latestRestoreSafety"] = str(safety)
        write_json(backup / "manifest.json", manifest)
    except Exception:
        restore_entries(target, safety, safety_entries)
        raise
    emit(
        {
            "status": "restored",
            "target": str(target),
            "backup": str(backup),
            "restoreSafetyBackup": str(safety),
            "backupPreserved": True,
        }
    )


def verify(args: argparse.Namespace) -> None:
    target = Path(args.target).expanduser().absolute()
    marker_path = target / MARKER_REL
    if not marker_path.is_file():
        emit({"status": "unmanaged", "target": str(target), "reason": "project-workflow.json was not found"}, 2)
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    results = []
    for relative_text, hashes in marker.get("managedComponents", {}).items():
        current = hash_path(target / Path(relative_text))
        expected = hashes.get("installedHash")
        results.append({"path": relative_text, "currentHash": current, "installedHash": expected, "matches": current == expected})
    clean = all(item["matches"] for item in results)
    emit(
        {
            "status": "verified" if clean else "drifted",
            "target": str(target),
            "templateVersion": marker.get("templateVersion"),
            "latestBackup": marker.get("latestBackup"),
            "components": results,
        },
        0 if clean else 5,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)

    initialize_parser = subparsers.add_parser("initialize")
    initialize_parser.add_argument("--target", required=True)
    initialize_parser.add_argument("--apply", action="store_true")
    initialize_parser.add_argument("--expected-fingerprint")
    initialize_parser.set_defaults(handler=initialize)

    migrate_parser = subparsers.add_parser("migrate")
    migrate_parser.add_argument("--target", required=True)
    migrate_parser.add_argument("--include-docs", action="store_true")
    migrate_parser.add_argument("--include-hooks", action="store_true")
    migrate_parser.add_argument("--create-missing-folders", action="store_true")
    migrate_parser.add_argument("--backup-root")
    migrate_parser.add_argument("--apply", action="store_true")
    migrate_parser.add_argument("--expected-fingerprint")
    migrate_parser.set_defaults(handler=migrate)

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--target", required=True)
    restore_parser.add_argument("--backup")
    restore_parser.add_argument("--force-conflicts", action="store_true")
    restore_parser.add_argument("--apply", action="store_true")
    restore_parser.add_argument("--expected-fingerprint")
    restore_parser.set_defaults(handler=restore)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--target", required=True)
    verify_parser.set_defaults(handler=verify)
    return parser


def main() -> None:
    try:
        args = build_parser().parse_args()
        args.handler(args)
    except WorkflowError as error:
        emit({"status": "error", "message": str(error)}, 1)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        emit({"status": "error", "message": str(error)}, 1)


if __name__ == "__main__":
    main()

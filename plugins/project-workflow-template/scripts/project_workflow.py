#!/usr/bin/env python3
"""Deterministic initializer, migrator, verifier, and restorer for project workspaces."""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import secrets
import stat
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


def stat_identity(metadata: os.stat_result) -> dict[str, int]:
    return {
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "mode": stat.S_IFMT(metadata.st_mode),
    }


def path_identity(path: Path, *, include_ctime: bool = False) -> dict[str, int]:
    """Return identity from lstat so replacements and symlinks are detectable."""
    metadata = path.lstat()
    identity = stat_identity(metadata)
    if include_ctime:
        identity["ctimeNs"] = metadata.st_ctime_ns
    return identity


def reject_path_symlinks(path: Path) -> None:
    """Reject symlinks in every existing component of a target path."""
    for component in (path, *path.parents):
        try:
            metadata = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise WorkflowError(f"Symbolic links are not supported in the target path: {component}")


def canonical_initialization_target(path: Path) -> Path:
    absolute = path.expanduser().absolute()
    try:
        canonical_parent = absolute.parent.resolve(strict=True)
    except FileNotFoundError as error:
        raise WorkflowError(f"Target parent directory does not exist: {absolute.parent}") from error
    return canonical_parent / absolute.name


def initialization_state(target: Path) -> dict[str, Any]:
    reject_path_symlinks(target)
    parent = target.parent
    try:
        parent_metadata = parent.lstat()
    except FileNotFoundError as error:
        raise WorkflowError(f"Target parent directory does not exist: {parent}") from error
    if not stat.S_ISDIR(parent_metadata.st_mode):
        raise WorkflowError(f"Target parent is not a directory: {parent}")

    parent_identity = path_identity(parent)
    try:
        target_metadata = target.lstat()
    except FileNotFoundError:
        return {
            "targetExists": False,
            "children": [],
            "parentIdentity": parent_identity,
            "targetIdentity": None,
        }
    if stat.S_ISLNK(target_metadata.st_mode):
        raise WorkflowError(f"Symbolic links are not supported in the target path: {target}")
    children = sorted(child.name for child in target.iterdir()) if stat.S_ISDIR(target_metadata.st_mode) else []
    return {
        "targetExists": True,
        "children": children,
        "parentIdentity": parent_identity,
        "targetIdentity": path_identity(target, include_ctime=True),
    }


def atomic_rename_no_replace_at(parent_fd: int, source_name: str, destination_name: str) -> None:
    """Rename one leaf within an already-open parent without replacing a target."""
    if os.name == "nt":
        raise WorkflowError("Descriptor-anchored atomic initialization is not supported on Windows")
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source_name)
    destination_bytes = os.fsencode(destination_name)
    if sys.platform == "darwin":
        rename_function = libc.renameatx_np
        rename_function.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename_function.restype = ctypes.c_int
        # RENAME_EXCL | RENAME_NOFOLLOW_ANY. The latter prevents any symbolic
        # link encountered by the kernel during this single commit operation.
        result = rename_function(parent_fd, source_bytes, parent_fd, destination_bytes, 0x04 | 0x10)
    elif sys.platform.startswith("linux"):
        try:
            rename_function = libc.renameat2
        except AttributeError as error:
            raise WorkflowError("This system does not provide atomic no-replace rename support") from error
        rename_function.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename_function.restype = ctypes.c_int
        result = rename_function(parent_fd, source_bytes, parent_fd, destination_bytes, 0x01)
    else:
        raise WorkflowError("This system does not provide descriptor-anchored atomic rename support")
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number), destination_name)


def verify_installed_workspace(
    target: Path,
    expected_identity: dict[str, int],
    *,
    parent_fd: int,
    content_fd: int,
    template_version: str,
    template_digest: str,
    workflow_digest: str,
    template_manifest_snapshot: list[dict[str, str]],
    marker_sha256: str,
) -> None:
    """Verify that the installed leaf is still the directory we staged.

    A sibling path is not a stable security handle: another process can replace
    it between a preflight lstat and rename. Check the installed leaf on both
    sides of content verification so a substituted symlink/directory is never
    reported as a successful initialization.
    """
    anchored_before = stat_identity(
        os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
    )
    visible_before = path_identity(target)
    if (
        anchored_before != expected_identity
        or visible_before != expected_identity
        or anchored_before["mode"] != stat.S_IFDIR
    ):
        raise WorkflowError(
            "Installed target is not the verified staging directory; "
            "external state was preserved for manual recovery"
        )
    verification, clean = workspace_verification_at(
        content_fd,
        installation_target=target,
        expected_template_version=template_version,
        expected_template_digest=template_digest,
        expected_workflow_digest=workflow_digest,
        template_manifest_snapshot=template_manifest_snapshot,
        expected_marker_sha256=marker_sha256,
    )
    anchored_after = stat_identity(
        os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
    )
    visible_after = path_identity(target)
    if anchored_after != expected_identity or visible_after != expected_identity or not clean:
        details = "; ".join(verification.get("errors", []) or [])
        suffix = f": {details}" if details else ""
        raise WorkflowError(
            "Installed target changed or failed verification; "
            f"external state was preserved for manual recovery{suffix}"
        )


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


def template_manifest() -> list[dict[str, str]]:
    reject_symlinks(TEMPLATE_ROOT)
    return [
        {
            "path": path.relative_to(TEMPLATE_ROOT).as_posix(),
            "sha256": sha256_file(path),
        }
        for path in sorted(TEMPLATE_ROOT.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file()
    ]


def current_template_digest(
    manifest: list[dict[str, str]] | None = None,
    *,
    template_version: str | None = None,
) -> str:
    files = manifest if manifest is not None else template_manifest()
    return stable_fingerprint(
        {
            "templateVersion": template_version or plugin_version(),
            "files": files,
            "directories": [item.as_posix() for item in STANDARD_DIRS],
        }
    )


def current_workflow_digest() -> str:
    return stable_fingerprint(
        {
            "script": sha256_file(Path(__file__).resolve()),
            "manifest": sha256_file(MANIFEST_PATH),
        }
    )


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


def safe_relative_parts(relative: Path) -> tuple[str, ...]:
    if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise WorkflowError(f"Unsafe relative staging path: {relative}")
    return relative.parts


def open_tracked_directory_at(
    root_fd: int,
    relative: Path,
    directory_identities: dict[str, dict[str, int]],
) -> int:
    """Open a previously-created staging directory without reinterpreting parent paths."""
    parts = () if relative == Path(".") else safe_relative_parts(relative)
    current_fd = os.dup(root_fd)
    try:
        for index, part in enumerate(parts):
            next_fd = os.open(
                part,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=current_fd,
            )
            os.close(current_fd)
            current_fd = next_fd
            relative_text = Path(*parts[: index + 1]).as_posix()
            expected = directory_identities.get(relative_text)
            actual = stat_identity(os.fstat(current_fd))
            if expected is None or actual != expected:
                raise WorkflowError(
                    f"Staging directory changed or was not created by this run: {relative_text}"
                )
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def ensure_directory_at(
    root_fd: int,
    relative: Path,
    directory_identities: dict[str, dict[str, int]],
) -> None:
    parts = safe_relative_parts(relative)
    for index, part in enumerate(parts):
        prefix = Path(*parts[: index + 1])
        prefix_text = prefix.as_posix()
        if prefix_text in directory_identities:
            opened = open_tracked_directory_at(root_fd, prefix, directory_identities)
            os.close(opened)
            continue
        parent = Path(*parts[:index]) if index else Path(".")
        parent_fd = open_tracked_directory_at(root_fd, parent, directory_identities)
        try:
            try:
                os.mkdir(part, mode=0o700, dir_fd=parent_fd)
            except FileExistsError as error:
                raise WorkflowError(
                    f"Unexpected entry appeared in private staging: {prefix_text}"
                ) from error
            child_fd = os.open(
                part,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent_fd,
            )
            try:
                directory_identities[prefix_text] = stat_identity(os.fstat(child_fd))
            finally:
                os.close(child_fd)
        finally:
            os.close(parent_fd)


def read_approved_source(source: Path, expected_sha256: str) -> tuple[bytes, int]:
    source_fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(source_fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise WorkflowError(f"Template source is not a regular file: {source}")
        chunks: list[bytes] = []
        while True:
            block = os.read(source_fd, 1024 * 1024)
            if not block:
                break
            chunks.append(block)
        payload = b"".join(chunks)
        if sha256_bytes(payload) != expected_sha256:
            raise WorkflowError(f"Template source changed after planning: {source}")
        return payload, stat.S_IMODE(metadata.st_mode)
    finally:
        os.close(source_fd)


def write_new_file_at(
    root_fd: int,
    relative: Path,
    payload: bytes,
    mode: int,
    directory_identities: dict[str, dict[str, int]],
) -> None:
    parts = safe_relative_parts(relative)
    parent = Path(*parts[:-1]) if len(parts) > 1 else Path(".")
    if parent != Path("."):
        ensure_directory_at(root_fd, parent, directory_identities)
    parent_fd = open_tracked_directory_at(root_fd, parent, directory_identities)
    try:
        try:
            file_fd = os.open(
                parts[-1],
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0),
                mode,
                dir_fd=parent_fd,
            )
        except FileExistsError as error:
            raise WorkflowError(
                f"Unexpected file appeared in private staging: {relative.as_posix()}"
            ) from error
        try:
            view = memoryview(payload)
            while view:
                written = os.write(file_fd, view)
                view = view[written:]
            os.fchmod(file_fd, mode)
        finally:
            os.close(file_fd)
    finally:
        os.close(parent_fd)


def read_file_at(root_fd: int, relative: Path) -> bytes:
    parts = safe_relative_parts(relative)
    parent = Path(*parts[:-1]) if len(parts) > 1 else Path(".")
    # Verification does not trust the construction map; every parent is opened
    # one component at a time with O_NOFOLLOW.
    current_fd = os.dup(root_fd)
    try:
        for part in (() if parent == Path(".") else safe_relative_parts(parent)):
            next_fd = os.open(
                part,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=current_fd,
            )
            os.close(current_fd)
            current_fd = next_fd
        file_fd = os.open(
            parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=current_fd
        )
        try:
            metadata = os.fstat(file_fd)
            if not stat.S_ISREG(metadata.st_mode):
                raise WorkflowError(f"Staging path is not a regular file: {relative}")
            chunks: list[bytes] = []
            while True:
                block = os.read(file_fd, 1024 * 1024)
                if not block:
                    break
                chunks.append(block)
            return b"".join(chunks)
        finally:
            os.close(file_fd)
    finally:
        os.close(current_fd)


def open_directory_path_at(root_fd: int, relative: Path) -> int:
    parts = safe_relative_parts(relative)
    current_fd = os.dup(root_fd)
    try:
        for part in parts:
            next_fd = os.open(
                part,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=current_fd,
            )
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def hash_directory_fd(directory_fd: int) -> str:
    digest = hashlib.sha256()

    def visit(current_fd: int, prefix: Path) -> None:
        names = sorted(entry.name for entry in os.scandir(current_fd))
        for name in names:
            metadata = os.stat(name, dir_fd=current_fd, follow_symlinks=False)
            relative = prefix / name
            relative_text = relative.as_posix()
            if stat.S_ISLNK(metadata.st_mode):
                raise WorkflowError(f"Symbolic links are not supported in staging: {relative_text}")
            if stat.S_ISDIR(metadata.st_mode):
                digest.update(f"D\0{relative_text}\0".encode("utf-8"))
                child_fd = os.open(
                    name,
                    os.O_RDONLY
                    | getattr(os, "O_DIRECTORY", 0)
                    | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=current_fd,
                )
                try:
                    visit(child_fd, relative)
                finally:
                    os.close(child_fd)
            elif stat.S_ISREG(metadata.st_mode):
                file_fd = os.open(
                    name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=current_fd
                )
                try:
                    file_digest = hashlib.sha256()
                    while True:
                        block = os.read(file_fd, 1024 * 1024)
                        if not block:
                            break
                        file_digest.update(block)
                finally:
                    os.close(file_fd)
                digest.update(
                    f"F\0{relative_text}\0{file_digest.hexdigest()}\0".encode("utf-8")
                )
            else:
                raise WorkflowError(f"Unsupported staging entry type: {relative_text}")

    visit(directory_fd, Path())
    return digest.hexdigest()


def inventory_directory_fd(directory_fd: int) -> dict[str, dict[str, str]]:
    """Return an exact, descriptor-anchored inventory of a directory tree."""
    inventory: dict[str, dict[str, str]] = {}

    def visit(current_fd: int, prefix: Path) -> None:
        with os.scandir(current_fd) as entries:
            names = sorted(entry.name for entry in entries)
        for name in names:
            metadata = os.stat(name, dir_fd=current_fd, follow_symlinks=False)
            relative = prefix / name
            relative_text = relative.as_posix()
            if stat.S_ISLNK(metadata.st_mode):
                raise WorkflowError(f"Symbolic links are not supported in staging: {relative_text}")
            if stat.S_ISDIR(metadata.st_mode):
                inventory[relative_text] = {"kind": "directory"}
                child_fd = os.open(
                    name,
                    os.O_RDONLY
                    | getattr(os, "O_DIRECTORY", 0)
                    | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=current_fd,
                )
                try:
                    visit(child_fd, relative)
                finally:
                    os.close(child_fd)
            elif stat.S_ISREG(metadata.st_mode):
                file_fd = os.open(
                    name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=current_fd
                )
                try:
                    digest = hashlib.sha256()
                    while True:
                        block = os.read(file_fd, 1024 * 1024)
                        if not block:
                            break
                        digest.update(block)
                finally:
                    os.close(file_fd)
                inventory[relative_text] = {
                    "kind": "file",
                    "sha256": digest.hexdigest(),
                }
            else:
                raise WorkflowError(f"Unsupported staging entry type: {relative_text}")

    visit(directory_fd, Path())
    return inventory


def expected_initialization_inventory(
    template_manifest_snapshot: list[dict[str, str]],
    marker_sha256: str,
) -> dict[str, dict[str, str]]:
    expected: dict[str, dict[str, str]] = {}

    def add_parents(relative: Path) -> None:
        for parent in reversed(relative.parents):
            if parent != Path("."):
                expected.setdefault(parent.as_posix(), {"kind": "directory"})

    for item in template_manifest_snapshot:
        relative = Path(item["path"])
        safe_relative_parts(relative)
        add_parents(relative)
        expected[relative.as_posix()] = {
            "kind": "file",
            "sha256": item["sha256"],
        }
    for relative in STANDARD_DIRS:
        add_parents(relative)
        expected.setdefault(relative.as_posix(), {"kind": "directory"})
    add_parents(MARKER_REL)
    expected[MARKER_REL.as_posix()] = {
        "kind": "file",
        "sha256": marker_sha256,
    }
    return expected


def hash_path_at(root_fd: int, relative: Path) -> str | None:
    parts = safe_relative_parts(relative)
    parent = Path(*parts[:-1]) if len(parts) > 1 else Path(".")
    try:
        current_fd = (
            os.dup(root_fd)
            if parent == Path(".")
            else open_directory_path_at(root_fd, parent)
        )
    except FileNotFoundError:
        return None
    try:
        try:
            metadata = os.stat(parts[-1], dir_fd=current_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        if stat.S_ISLNK(metadata.st_mode):
            raise WorkflowError(f"Symbolic links are not supported in staging: {relative}")
        if stat.S_ISREG(metadata.st_mode):
            return sha256_bytes(read_file_at(root_fd, relative))
        if stat.S_ISDIR(metadata.st_mode):
            directory_fd = os.open(
                parts[-1],
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=current_fd,
            )
            try:
                return hash_directory_fd(directory_fd)
            finally:
                os.close(directory_fd)
        raise WorkflowError(f"Unsupported staging entry type: {relative}")
    finally:
        os.close(current_fd)


def is_directory_at(root_fd: int, relative: Path) -> bool:
    parts = safe_relative_parts(relative)
    parent = Path(*parts[:-1]) if len(parts) > 1 else Path(".")
    try:
        current_fd = (
            os.dup(root_fd)
            if parent == Path(".")
            else open_directory_path_at(root_fd, parent)
        )
    except FileNotFoundError:
        return False
    try:
        try:
            metadata = os.stat(parts[-1], dir_fd=current_fd, follow_symlinks=False)
        except FileNotFoundError:
            return False
        return stat.S_ISDIR(metadata.st_mode)
    finally:
        os.close(current_fd)


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
    target = canonical_initialization_target(target)
    state = initialization_state(target)
    target_exists = state["targetExists"]
    children = state["children"]
    target_is_directory = bool(
        target_exists
        and state["targetIdentity"]
        and state["targetIdentity"]["mode"] == stat.S_IFDIR
    )
    if target_exists and target_is_directory and not children:
        return {
            "status": "requires_empty_target_removal",
            "target": str(target),
            "reason": (
                "Atomic initialization requires a missing target. "
                "Have the operator remove this confirmed empty directory, then request a new plan."
            ),
            "state": state,
        }
    if target_exists:
        return {
            "status": "requires_migration",
            "target": str(target),
            "reason": "The existing target must use the migration workflow.",
            "existingTopLevelEntries": children,
        }
    manifest = template_manifest()
    template_version = plugin_version()
    files = [item["path"] for item in manifest]
    directories = [item.as_posix() for item in STANDARD_DIRS]
    template_digest = current_template_digest(
        manifest, template_version=template_version
    )
    workflow_digest = current_workflow_digest()
    managed_paths = CORE_COMPONENTS + DOC_COMPONENTS + HOOK_COMPONENTS
    managed_template_hashes = {
        item.as_posix(): hash_path(TEMPLATE_ROOT / item) for item in managed_paths
    }
    fingerprint_payload = {
        "action": "initialize",
        "target": str(target.resolve()),
        "templateVersion": template_version,
        "templateDigest": template_digest,
        "workflowDigest": workflow_digest,
        "state": state,
    }
    return {
        "status": "planned",
        "action": "initialize",
        "target": str(target),
        "templateVersion": template_version,
        "templateDigest": template_digest,
        "workflowDigest": workflow_digest,
        "files": files + [MARKER_REL.as_posix()],
        "templateManifest": manifest,
        "managedTemplateHashes": managed_template_hashes,
        "directories": directories,
        "fingerprint": stable_fingerprint(fingerprint_payload),
        "state": state,
    }


def build_marker(
    latest_backup: str | None,
    managed: dict[str, Any],
    initialization: dict[str, Any] | None = None,
    *,
    template_version: str | None = None,
    template_digest: str | None = None,
    workflow_digest: str | None = None,
) -> dict[str, Any]:
    marker = {
        "schemaVersion": 1,
        "templateVersion": template_version or plugin_version(),
        "templateDigest": template_digest or current_template_digest(),
        "workflowDigest": workflow_digest or current_workflow_digest(),
        "installedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sourcePlugin": "project-workflow-template",
        "latestBackup": latest_backup,
        "managedComponents": managed,
    }
    if initialization is not None:
        marker["initialization"] = initialization
    return marker


def write_marker(
    target: Path,
    latest_backup: str | None,
    managed: dict[str, Any],
    initialization: dict[str, Any] | None = None,
    *,
    template_version: str | None = None,
    template_digest: str | None = None,
    workflow_digest: str | None = None,
) -> None:
    marker = build_marker(
        latest_backup,
        managed,
        initialization,
        template_version=template_version,
        template_digest=template_digest,
        workflow_digest=workflow_digest,
    )
    write_json(target / MARKER_REL, marker)


def initialize(args: argparse.Namespace) -> None:
    target = canonical_initialization_target(Path(args.target))
    plan = init_plan(target)
    if not args.apply or plan["status"] != "planned":
        emit(
            plan,
            2
            if plan["status"] in {"requires_migration", "requires_empty_target_removal"}
            else 0,
        )
    if not args.expected_fingerprint or args.expected_fingerprint != plan["fingerprint"]:
        emit({**plan, "status": "aborted", "reason": "Fingerprint mismatch; request a new initialization plan."}, 3)

    open_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    parent_fd = os.open(target.parent, open_flags)
    approved_parent_identity = plan["state"]["parentIdentity"]
    parent_metadata = os.fstat(parent_fd)
    opened_parent_identity = stat_identity(parent_metadata)
    if opened_parent_identity != approved_parent_identity:
        os.close(parent_fd)
        raise WorkflowError("Target parent changed after approval; request a new initialization plan")
    staging_name = f".{target.name}.project-workflow-staging-{secrets.token_hex(8)}"
    staging_fd: int | None = None
    try:
        os.mkdir(staging_name, mode=0o700, dir_fd=parent_fd)
        staging_fd = os.open(
            staging_name,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        staging_identity = stat_identity(os.fstat(staging_fd))
    except Exception:
        if staging_fd is not None:
            os.close(staging_fd)
        os.close(parent_fd)
        raise
    assert staging_fd is not None
    try:
        directory_identities: dict[str, dict[str, int]] = {}
        for item in plan["templateManifest"]:
            relative = Path(item["path"])
            source = TEMPLATE_ROOT / relative
            payload, mode = read_approved_source(source, item["sha256"])
            write_new_file_at(
                staging_fd, relative, payload, mode, directory_identities
            )
        for relative in STANDARD_DIRS:
            ensure_directory_at(staging_fd, relative, directory_identities)
        managed = {
            relative_text: {
                "templateHash": approved_hash,
                "installedHash": approved_hash,
            }
            for relative_text, approved_hash in plan["managedTemplateHashes"].items()
        }
        initialization = {
            "action": "initialize",
            "approvedFingerprint": plan["fingerprint"],
            "target": str(target),
            "approvedState": plan["state"],
        }
        marker = build_marker(
            None,
            managed,
            initialization,
            template_version=plan["templateVersion"],
            template_digest=plan["templateDigest"],
            workflow_digest=plan["workflowDigest"],
        )
        marker_payload = (
            json.dumps(marker, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")
        marker_sha256 = sha256_bytes(marker_payload)
        write_new_file_at(
            staging_fd,
            MARKER_REL,
            marker_payload,
            0o600,
            directory_identities,
        )
        verification, clean = workspace_verification_at(
            staging_fd,
            installation_target=target,
            expected_template_version=plan["templateVersion"],
            expected_template_digest=plan["templateDigest"],
            expected_workflow_digest=plan["workflowDigest"],
            template_manifest_snapshot=plan["templateManifest"],
            expected_marker_sha256=marker_sha256,
        )
        if not clean:
            raise WorkflowError(
                "Staged workspace verification failed: "
                + "; ".join(verification["errors"] or ["generated content did not match its marker"])
            )

        # Creating the sibling staging directory changes the parent timestamp,
        # but neither approved target state nor directory identity may change.
        current_plan = init_plan(target)
        if current_plan.get("fingerprint") != plan["fingerprint"]:
            raise WorkflowError("Target changed after approval; request a new initialization plan")
        if stat_identity(
            os.stat(staging_name, dir_fd=parent_fd, follow_symlinks=False)
        ) != staging_identity or stat_identity(os.fstat(staging_fd)) != staging_identity:
            raise WorkflowError(
                "Staging directory changed before installation; "
                "external state was preserved for manual recovery"
            )

        try:
            atomic_rename_no_replace_at(parent_fd, staging_name, target.name)
            verify_installed_workspace(
                target,
                staging_identity,
                parent_fd=parent_fd,
                content_fd=staging_fd,
                template_version=plan["templateVersion"],
                template_digest=plan["templateDigest"],
                workflow_digest=plan["workflowDigest"],
                template_manifest_snapshot=plan["templateManifest"],
                marker_sha256=marker_sha256,
            )
        except OSError as error:
            if error.errno == errno.EXDEV:
                raise WorkflowError("Atomic installation cannot cross filesystems") from error
            if error.errno in {errno.EEXIST, errno.ENOTEMPTY}:
                raise WorkflowError("Target changed during atomic installation") from error
            raise
    except Exception:
        # Deliberately do not recursively clean a path in a shared parent. Even
        # lstat followed immediately by rmtree has a replacement race. A failed
        # run leaves its randomized private staging/recovery path for inspection.
        # A successful missing-target commit consumes the staging leaf.
        raise
    finally:
        os.close(staging_fd)
        os.close(parent_fd)
    emit(
        {
            "status": "initialized",
            "target": str(target),
            "templateVersion": plan["templateVersion"],
            "createdFiles": plan["files"],
        }
    )


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
    marker_path = target / MARKER_REL
    marker_action = "keep"
    marker_data: dict[str, Any] = {}
    if marker_path.exists():
        try:
            loaded_marker = json.loads(marker_path.read_text(encoding="utf-8"))
            if isinstance(loaded_marker, dict):
                marker_data = loaded_marker
            else:
                marker_action = "update-marker"
        except (OSError, UnicodeError, json.JSONDecodeError):
            marker_action = "update-marker"
    else:
        marker_action = "create-marker"
    if marker_data.get("templateVersion") != plugin_version():
        marker_action = "update-marker" if marker_path.exists() else "create-marker"
    if any(item["action"] != "keep" for item in operations):
        marker_action = "update-marker" if marker_path.exists() else "create-marker"
    operations.append(
        {
            "path": MARKER_REL.as_posix(),
            "action": marker_action,
            "currentHash": hash_path(marker_path),
            "templateHash": None,
        }
    )
    backup_root = Path(args.backup_root).expanduser().absolute() if args.backup_root else target.parent / "_project-workflow-backups"
    template_digest = current_template_digest()
    workflow_digest = current_workflow_digest()
    fingerprint_payload = {
        "action": "migrate",
        "target": str(target),
        "templateVersion": plugin_version(),
        "templateDigest": template_digest,
        "workflowDigest": workflow_digest,
        "backupRoot": str(backup_root.resolve()),
        "options": {
            "includeDocs": args.include_docs,
            "includeHooks": args.include_hooks,
            "createMissingFolders": args.create_missing_folders,
        },
        "current": current,
        "operations": operations,
    }
    return {
        "status": "planned",
        "action": "migrate",
        "target": str(target),
        "templateVersion": plugin_version(),
        "templateDigest": template_digest,
        "workflowDigest": workflow_digest,
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
        emit({**plan, "status": "aborted", "reason": "Fingerprint mismatch; request a new migration plan."}, 3)

    changed = [item for item in plan["operations"] if item["action"] not in {"keep"}]
    if not changed:
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
    backup_paths = list(dict.fromkeys(replace_paths))
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
            if relative == MARKER_REL:
                continue
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
        emit({**plan, "status": "aborted", "reason": "Fingerprint mismatch; request a new restore plan."}, 3)
    if plan["conflicts"] and not args.force_conflicts:
        emit({**plan, "status": "aborted", "reason": "Current files differ from the migrated state."}, 4)

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


def workspace_verification(
    content_root: Path,
    *,
    installation_target: Path | None = None,
    expected_template_version: str | None = None,
    expected_template_digest: str | None = None,
    expected_workflow_digest: str | None = None,
) -> tuple[dict[str, Any], bool]:
    reported_target = installation_target or content_root
    marker_path = content_root / MARKER_REL
    if not marker_path.is_file():
        return (
            {
                "status": "unmanaged",
                "target": str(reported_target),
                "reason": "project-workflow.json was not found",
            },
            False,
        )
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if not isinstance(marker, dict):
        return (
            {
                "status": "invalid-marker",
                "target": str(reported_target),
                "reason": "Marker must be a JSON object.",
            },
            False,
        )
    errors = []
    if marker.get("schemaVersion") != 1:
        errors.append("Marker schemaVersion must be 1.")
    if marker.get("sourcePlugin") != "project-workflow-template":
        errors.append("Marker sourcePlugin must be project-workflow-template.")
    verified_template_version = expected_template_version or plugin_version()
    if marker.get("templateVersion") != verified_template_version:
        errors.append(
            f"Marker templateVersion {marker.get('templateVersion') or '<missing>'} "
            f"does not match expected version {verified_template_version}."
        )
    verified_template_digest = expected_template_digest or current_template_digest()
    verified_workflow_digest = expected_workflow_digest or current_workflow_digest()
    if marker.get("templateDigest") != verified_template_digest:
        errors.append("Marker templateDigest does not match the current template.")
    if marker.get("workflowDigest") != verified_workflow_digest:
        errors.append("Marker workflowDigest does not match the current workflow implementation.")
    initialization = marker.get("initialization")
    if initialization is not None:
        if not isinstance(initialization, dict):
            errors.append("Marker initialization must be an object.")
        else:
            approved_state = initialization.get("approvedState")
            approved_target = initialization.get("target")
            if initialization.get("action") != "initialize":
                errors.append("Marker initialization action must be initialize.")
            if approved_target != str(reported_target):
                errors.append("Marker initialization target does not match this workspace path.")
            if not isinstance(approved_state, dict):
                errors.append("Marker initialization approvedState must be an object.")
            else:
                fingerprint_payload = {
                    "action": "initialize",
                    "target": approved_target,
                    "templateVersion": marker.get("templateVersion"),
                    "templateDigest": marker.get("templateDigest"),
                    "workflowDigest": marker.get("workflowDigest"),
                    "state": approved_state,
                }
                if initialization.get("approvedFingerprint") != stable_fingerprint(fingerprint_payload):
                    errors.append("Marker initialization approval evidence is inconsistent.")
    managed_components = marker.get("managedComponents")
    if not isinstance(managed_components, dict) or not managed_components:
        errors.append("Marker managedComponents must be a non-empty object.")
        managed_components = {}
    for required in CORE_COMPONENTS:
        if required.as_posix() not in managed_components:
            errors.append(f"Marker is missing required managed component: {required.as_posix()}.")
    results = []
    for relative_text, hashes in managed_components.items():
        if not isinstance(hashes, dict):
            errors.append(f"Managed component metadata must be an object: {relative_text}.")
            continue
        current = hash_path(content_root / Path(relative_text))
        expected = hashes.get("installedHash")
        results.append({"path": relative_text, "currentHash": current, "installedHash": expected, "matches": current == expected})
    structure = []
    required_files = [Path("SOT/SourceOfTruth.md")]
    for relative in required_files:
        path = content_root / relative
        readable_utf8 = False
        if path.is_file():
            try:
                path.read_text(encoding="utf-8", errors="strict")
                readable_utf8 = True
            except (OSError, UnicodeError):
                pass
        structure.append(
            {
                "path": relative.as_posix(),
                "expectedKind": "file",
                "matches": path.is_file() and readable_utf8,
            }
        )
    for relative in STANDARD_DIRS:
        path = content_root / relative
        structure.append(
            {
                "path": relative.as_posix(),
                "expectedKind": "directory",
                "matches": path.is_dir(),
            }
        )
    clean = not errors and all(item["matches"] for item in results) and all(item["matches"] for item in structure)
    return (
        {
            "status": "verified" if clean else "drifted",
            "target": str(reported_target),
            "templateVersion": marker.get("templateVersion"),
            "pluginVersion": plugin_version(),
            "templateDigest": marker.get("templateDigest"),
            "pluginTemplateDigest": verified_template_digest,
            "workflowDigest": marker.get("workflowDigest"),
            "pluginWorkflowDigest": verified_workflow_digest,
            "latestBackup": marker.get("latestBackup"),
            "components": results,
            "structure": structure,
            "errors": errors,
        },
        clean,
    )


def workspace_verification_at(
    content_fd: int,
    *,
    installation_target: Path,
    expected_template_version: str,
    expected_template_digest: str,
    expected_workflow_digest: str,
    template_manifest_snapshot: list[dict[str, str]],
    expected_marker_sha256: str,
) -> tuple[dict[str, Any], bool]:
    """Verify staged/installed content exclusively through an open directory FD."""
    try:
        marker_bytes = read_file_at(content_fd, MARKER_REL)
    except FileNotFoundError:
        return (
            {
                "status": "unmanaged",
                "target": str(installation_target),
                "reason": "project-workflow.json was not found",
            },
            False,
        )
    try:
        marker = json.loads(marker_bytes.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError):
        return (
            {
                "status": "invalid-marker",
                "target": str(installation_target),
                "reason": "Marker must be valid UTF-8 JSON.",
            },
            False,
        )
    if not isinstance(marker, dict):
        return (
            {
                "status": "invalid-marker",
                "target": str(installation_target),
                "reason": "Marker must be a JSON object.",
            },
            False,
        )

    errors: list[str] = []
    expected_inventory = expected_initialization_inventory(
        template_manifest_snapshot, expected_marker_sha256
    )
    actual_inventory = inventory_directory_fd(content_fd)
    for relative_text, expected_entry in expected_inventory.items():
        actual_entry = actual_inventory.get(relative_text)
        expected_kind = expected_entry["kind"]
        if actual_entry is None:
            errors.append(f"Approved snapshot entry is missing: {relative_text}.")
            continue
        if actual_entry.get("kind") != expected_kind:
            errors.append(f"Approved snapshot entry kind changed: {relative_text}.")
        elif expected_kind == "file" and actual_entry.get("sha256") != expected_entry.get("sha256"):
            errors.append(f"Approved snapshot file hash changed: {relative_text}.")
    for relative_text in sorted(set(actual_inventory) - set(expected_inventory)):
        errors.append(f"Unexpected staged entry is not in the approved snapshot: {relative_text}.")
    if marker.get("schemaVersion") != 1:
        errors.append("Marker schemaVersion must be 1.")
    if marker.get("sourcePlugin") != "project-workflow-template":
        errors.append("Marker sourcePlugin must be project-workflow-template.")
    if marker.get("templateVersion") != expected_template_version:
        errors.append(
            f"Marker templateVersion {marker.get('templateVersion') or '<missing>'} "
            f"does not match expected version {expected_template_version}."
        )
    if marker.get("templateDigest") != expected_template_digest:
        errors.append("Marker templateDigest does not match the approved template snapshot.")
    if marker.get("workflowDigest") != expected_workflow_digest:
        errors.append("Marker workflowDigest does not match the approved workflow snapshot.")

    initialization = marker.get("initialization")
    if not isinstance(initialization, dict):
        errors.append("Marker initialization must be an object.")
    else:
        approved_state = initialization.get("approvedState")
        approved_target = initialization.get("target")
        if initialization.get("action") != "initialize":
            errors.append("Marker initialization action must be initialize.")
        if approved_target != str(installation_target):
            errors.append("Marker initialization target does not match this workspace path.")
        if not isinstance(approved_state, dict):
            errors.append("Marker initialization approvedState must be an object.")
        else:
            fingerprint_payload = {
                "action": "initialize",
                "target": approved_target,
                "templateVersion": marker.get("templateVersion"),
                "templateDigest": marker.get("templateDigest"),
                "workflowDigest": marker.get("workflowDigest"),
                "state": approved_state,
            }
            if initialization.get("approvedFingerprint") != stable_fingerprint(fingerprint_payload):
                errors.append("Marker initialization approval evidence is inconsistent.")

    managed_components = marker.get("managedComponents")
    if not isinstance(managed_components, dict) or not managed_components:
        errors.append("Marker managedComponents must be a non-empty object.")
        managed_components = {}
    for required in CORE_COMPONENTS:
        if required.as_posix() not in managed_components:
            errors.append(f"Marker is missing required managed component: {required.as_posix()}.")
    results = []
    for relative_text, hashes in managed_components.items():
        if not isinstance(hashes, dict):
            errors.append(f"Managed component metadata must be an object: {relative_text}.")
            continue
        current = hash_path_at(content_fd, Path(relative_text))
        expected = hashes.get("installedHash")
        results.append(
            {
                "path": relative_text,
                "currentHash": current,
                "installedHash": expected,
                "matches": current == expected,
            }
        )

    structure = []
    required_sot = Path("SOT/SourceOfTruth.md")
    readable_utf8 = False
    try:
        read_file_at(content_fd, required_sot).decode("utf-8", errors="strict")
        readable_utf8 = True
    except (FileNotFoundError, WorkflowError, UnicodeError):
        pass
    structure.append(
        {
            "path": required_sot.as_posix(),
            "expectedKind": "file",
            "matches": readable_utf8,
        }
    )
    for relative in STANDARD_DIRS:
        structure.append(
            {
                "path": relative.as_posix(),
                "expectedKind": "directory",
                "matches": is_directory_at(content_fd, relative),
            }
        )
    clean = not errors and all(item["matches"] for item in results) and all(
        item["matches"] for item in structure
    )
    return (
        {
            "status": "verified" if clean else "drifted",
            "target": str(installation_target),
            "templateVersion": marker.get("templateVersion"),
            "pluginVersion": expected_template_version,
            "templateDigest": marker.get("templateDigest"),
            "pluginTemplateDigest": expected_template_digest,
            "workflowDigest": marker.get("workflowDigest"),
            "pluginWorkflowDigest": expected_workflow_digest,
            "latestBackup": marker.get("latestBackup"),
            "components": results,
            "structure": structure,
            "errors": errors,
        },
        clean,
    )


def verify(args: argparse.Namespace) -> None:
    target = canonical_initialization_target(Path(args.target))
    payload, clean = workspace_verification(target)
    emit(payload, 0 if clean else (2 if payload["status"] == "unmanaged" else 5))


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

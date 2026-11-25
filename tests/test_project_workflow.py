from __future__ import annotations

import argparse
import contextlib
import errno
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT
    / "plugins"
    / "project-workflow-template"
    / "scripts"
    / "project_workflow.py"
)
SPEC = importlib.util.spec_from_file_location("project_workflow", SCRIPT_PATH)
assert SPEC and SPEC.loader
workflow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workflow)


class WorkflowTestCase(unittest.TestCase):
    def run_emitting(self, callback) -> tuple[int, dict]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            callback()
        return int(raised.exception.code), json.loads(output.getvalue())

    @staticmethod
    def initialize_args(target: Path, *, apply: bool, fingerprint: str | None = None) -> argparse.Namespace:
        return argparse.Namespace(
            target=str(target),
            apply=apply,
            expected_fingerprint=fingerprint,
        )

    @staticmethod
    def migrate_args(
        target: Path,
        backup_root: Path,
        *,
        apply: bool,
        fingerprint: str | None = None,
    ) -> argparse.Namespace:
        return argparse.Namespace(
            target=str(target),
            include_docs=False,
            include_hooks=False,
            create_missing_folders=False,
            backup_root=str(backup_root),
            apply=apply,
            expected_fingerprint=fingerprint,
        )

    def initialize_project(self, target: Path) -> dict:
        plan = workflow.init_plan(target)
        code, payload = self.run_emitting(
            lambda: workflow.initialize(
                self.initialize_args(target, apply=True, fingerprint=plan["fingerprint"])
            )
        )
        self.assertEqual(0, code)
        self.assertEqual("initialized", payload["status"])
        return payload

    @staticmethod
    def staging_paths(target: Path) -> list[Path]:
        return list(target.parent.glob(f".{target.name}.project-workflow-staging-*"))

    def assert_workspace_verifies(self, target: Path) -> None:
        canonical = workflow.canonical_initialization_target(target)
        payload, clean = workflow.workspace_verification(canonical)
        self.assertTrue(clean, payload)

    def test_project_template_defaults_deliverables_to_markdown(self) -> None:
        template_agents = workflow.TEMPLATE_ROOT / "AGENTS.md"
        content = template_agents.read_text(encoding="utf-8")
        self.assertIn("산출물은 Markdown을 기본으로 작성한다.", content)
        self.assertIn("사용자가 그 형식을 명시적으로 요청", content)
        self.assertIn("단지 보기 좋게 만들기 위해 PDF로 다시 내보내지 않는다.", content)

    def test_initialization_fingerprint_binds_target_and_template_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            temp = Path(temp_text)
            template = temp / "template"
            template.mkdir()
            (template / "AGENTS.md").write_text("version one\n", encoding="utf-8")
            manifest = temp / "plugin.json"
            manifest.write_text('{"version":"0.2.0"}\n', encoding="utf-8")
            target_a = temp / "target-a"
            target_b = temp / "target-b"

            with (
                mock.patch.object(workflow, "TEMPLATE_ROOT", template),
                mock.patch.object(workflow, "MANIFEST_PATH", manifest),
            ):
                plan_a = workflow.init_plan(target_a)
                plan_b = workflow.init_plan(target_b)
                self.assertNotEqual(plan_a["fingerprint"], plan_b["fingerprint"])

                (template / "AGENTS.md").write_text("version two\n", encoding="utf-8")
                changed = workflow.init_plan(target_a)
                self.assertNotEqual(plan_a["templateDigest"], changed["templateDigest"])
                self.assertNotEqual(plan_a["fingerprint"], changed["fingerprint"])

    def test_existing_empty_target_requires_operator_removal_and_replan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            target = Path(temp_text) / "project"
            missing = workflow.init_plan(target)
            self.assertEqual("planned", missing["status"])
            self.assertFalse(missing["state"]["targetExists"])
            self.assertIsNone(missing["state"]["targetIdentity"])

            target.mkdir()
            empty = workflow.init_plan(target)
            self.assertEqual("requires_empty_target_removal", empty["status"])
            self.assertTrue(empty["state"]["targetExists"])
            self.assertIsNotNone(empty["state"]["targetIdentity"])

            code, payload = self.run_emitting(
                lambda: workflow.initialize(
                    self.initialize_args(target, apply=True, fingerprint=missing["fingerprint"])
                )
            )

            self.assertEqual(2, code)
            self.assertEqual("requires_empty_target_removal", payload["status"])
            self.assertEqual([], list(target.iterdir()))
            self.assertEqual([], self.staging_paths(target))

    def test_stale_initialization_fingerprint_aborts_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            temp = Path(temp_text)
            template = temp / "template"
            template.mkdir()
            (template / "AGENTS.md").write_text("version one\n", encoding="utf-8")
            manifest = temp / "plugin.json"
            manifest.write_text('{"version":"0.2.0"}\n', encoding="utf-8")
            target = temp / "project"

            with (
                mock.patch.object(workflow, "TEMPLATE_ROOT", template),
                mock.patch.object(workflow, "MANIFEST_PATH", manifest),
            ):
                stale = workflow.init_plan(target)["fingerprint"]
                (template / "AGENTS.md").write_text("version two\n", encoding="utf-8")
                code, payload = self.run_emitting(
                    lambda: workflow.initialize(
                        self.initialize_args(target, apply=True, fingerprint=stale)
                    )
                )

            self.assertEqual(3, code)
            self.assertEqual("aborted", payload["status"])
            self.assertFalse(target.exists())

    def test_copy_failure_leaves_missing_target_retryable_with_staging_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            target = Path(temp_text) / "project"
            approved = workflow.init_plan(target)

            with (
                mock.patch.object(
                    workflow,
                    "read_approved_source",
                    side_effect=RuntimeError("injected copy failure"),
                ),
                self.assertRaisesRegex(RuntimeError, "injected copy failure"),
            ):
                workflow.initialize(
                    self.initialize_args(target, apply=True, fingerprint=approved["fingerprint"])
                )

            self.assertFalse(target.exists())
            self.assertEqual(1, len(self.staging_paths(target)))
            retry = workflow.init_plan(target)
            self.assertEqual(approved["fingerprint"], retry["fingerprint"])

    def test_staged_verification_failure_leaves_missing_target_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            target = Path(temp_text) / "project"
            approved = workflow.init_plan(target)

            with (
                mock.patch.object(
                    workflow,
                    "workspace_verification_at",
                    return_value=({"errors": ["injected verification failure"]}, False),
                ),
                self.assertRaisesRegex(workflow.WorkflowError, "injected verification failure"),
            ):
                workflow.initialize(
                    self.initialize_args(target, apply=True, fingerprint=approved["fingerprint"])
                )

            self.assertFalse(target.exists())
            self.assertEqual(1, len(self.staging_paths(target)))

    def test_sot_mutation_after_marker_is_rejected_by_exact_snapshot_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            target = Path(temp_text) / "project"
            approved = workflow.init_plan(target)
            real_verify = workflow.workspace_verification_at
            injected = False

            def mutate_sot_then_verify(content_fd: int, **kwargs):
                nonlocal injected
                if not injected:
                    injected = True
                    file_fd = os.open(
                        "SOT/SourceOfTruth.md",
                        os.O_WRONLY | os.O_TRUNC,
                        dir_fd=content_fd,
                    )
                    try:
                        os.write(file_fd, "valid UTF-8 but unapproved\n".encode("utf-8"))
                    finally:
                        os.close(file_fd)
                return real_verify(content_fd, **kwargs)

            with (
                mock.patch.object(
                    workflow, "workspace_verification_at", side_effect=mutate_sot_then_verify
                ),
                self.assertRaisesRegex(
                    workflow.WorkflowError, "Approved snapshot file hash changed"
                ),
            ):
                workflow.initialize(
                    self.initialize_args(target, apply=True, fingerprint=approved["fingerprint"])
                )

            self.assertFalse(target.exists())
            self.assertEqual(1, len(self.staging_paths(target)))

    def test_marker_mutation_after_write_is_rejected_by_exact_snapshot_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            target = Path(temp_text) / "project"
            approved = workflow.init_plan(target)
            real_verify = workflow.workspace_verification_at
            injected = False

            def mutate_marker_then_verify(content_fd: int, **kwargs):
                nonlocal injected
                if not injected:
                    injected = True
                    marker = json.loads(
                        workflow.read_file_at(content_fd, workflow.MARKER_REL).decode("utf-8")
                    )
                    marker["latestBackup"] = "/external/unapproved-backup"
                    marker["managedComponents"] = {
                        "AGENTS.md": marker["managedComponents"]["AGENTS.md"]
                    }
                    mutated = (
                        json.dumps(marker, ensure_ascii=False, indent=2) + "\n"
                    ).encode("utf-8")
                    file_fd = os.open(
                        workflow.MARKER_REL.as_posix(),
                        os.O_WRONLY | os.O_TRUNC,
                        dir_fd=content_fd,
                    )
                    try:
                        os.write(file_fd, mutated)
                    finally:
                        os.close(file_fd)
                return real_verify(content_fd, **kwargs)

            with (
                mock.patch.object(
                    workflow,
                    "workspace_verification_at",
                    side_effect=mutate_marker_then_verify,
                ),
                self.assertRaisesRegex(
                    workflow.WorkflowError, "Approved snapshot file hash changed"
                ),
            ):
                workflow.initialize(
                    self.initialize_args(target, apply=True, fingerprint=approved["fingerprint"])
                )

            self.assertFalse(target.exists())
            self.assertEqual(1, len(self.staging_paths(target)))

    def test_unexpected_standard_directory_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            target = Path(temp_text) / "project"
            approved = workflow.init_plan(target)
            real_verify = workflow.workspace_verification_at
            injected = False

            def inject_unexpected_then_verify(content_fd: int, **kwargs):
                nonlocal injected
                if not injected:
                    injected = True
                    file_fd = os.open(
                        "01_INBOX/unexpected.txt",
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                        0o600,
                        dir_fd=content_fd,
                    )
                    try:
                        os.write(file_fd, b"not approved\n")
                    finally:
                        os.close(file_fd)
                return real_verify(content_fd, **kwargs)

            with (
                mock.patch.object(
                    workflow,
                    "workspace_verification_at",
                    side_effect=inject_unexpected_then_verify,
                ),
                self.assertRaisesRegex(workflow.WorkflowError, "Unexpected staged entry"),
            ):
                workflow.initialize(
                    self.initialize_args(target, apply=True, fingerprint=approved["fingerprint"])
                )

            self.assertFalse(target.exists())
            self.assertEqual(1, len(self.staging_paths(target)))

    def test_missing_target_concurrent_creation_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            target = Path(temp_text) / "project"
            approved = workflow.init_plan(target)

            def concurrent_create(_parent_fd: int, _source_name: str, _destination_name: str) -> None:
                target.mkdir()
                (target / "external.txt").write_text("keep me\n", encoding="utf-8")
                raise OSError(errno.EEXIST, "injected concurrent creation")

            with (
                mock.patch.object(
                    workflow, "atomic_rename_no_replace_at", side_effect=concurrent_create
                ),
                self.assertRaisesRegex(workflow.WorkflowError, "Target changed during atomic installation"),
            ):
                workflow.initialize(
                    self.initialize_args(target, apply=True, fingerprint=approved["fingerprint"])
                )

            self.assertEqual("keep me\n", (target / "external.txt").read_text(encoding="utf-8"))
            self.assertEqual(1, len(self.staging_paths(target)))

    def test_recreated_parent_and_staging_path_never_touch_external_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            temp = Path(temp_text)
            parent = temp / "approved-parent"
            parent.mkdir()
            target = parent / "project"
            approved = workflow.init_plan(target)
            displaced_parent = temp / "displaced-approved-parent"
            real_read = workflow.read_approved_source
            external_file: Path | None = None

            def replace_parent_then_read(source: Path, expected_hash: str) -> tuple[bytes, int]:
                nonlocal external_file
                if external_file is None:
                    staging = self.staging_paths(target)[0]
                    staging_name = staging.name
                    parent.rename(displaced_parent)
                    parent.mkdir()
                    recreated_staging = parent / staging_name
                    relative = source.relative_to(workflow.TEMPLATE_ROOT)
                    external_file = recreated_staging / relative
                    external_file.parent.mkdir(parents=True)
                    external_file.write_text("external bytes must survive\n", encoding="utf-8")
                return real_read(source, expected_hash)

            with (
                mock.patch.object(
                    workflow, "read_approved_source", side_effect=replace_parent_then_read
                ),
                mock.patch.object(
                    workflow.shutil,
                    "rmtree",
                    side_effect=AssertionError("recursive cleanup must not run"),
                ) as recursive_remove,
                self.assertRaisesRegex(workflow.WorkflowError, "Target changed after approval"),
            ):
                workflow.initialize(
                    self.initialize_args(target, apply=True, fingerprint=approved["fingerprint"])
                )

            recursive_remove.assert_not_called()
            self.assertIsNotNone(external_file)
            self.assertEqual(
                "external bytes must survive\n",
                external_file.read_text(encoding="utf-8"),
            )
            original_staging = list(
                displaced_parent.glob(f".{target.name}.project-workflow-staging-*")
            )
            self.assertEqual(1, len(original_staging))
            self.assertTrue((original_staging[0] / "AGENTS.md").is_file())

    def test_external_file_in_open_staging_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            target = Path(temp_text) / "project"
            approved = workflow.init_plan(target)
            real_read = workflow.read_approved_source
            external_file: Path | None = None

            def inject_external_file(source: Path, expected_hash: str) -> tuple[bytes, int]:
                nonlocal external_file
                if external_file is None:
                    staging = self.staging_paths(target)[0]
                    relative = source.relative_to(workflow.TEMPLATE_ROOT)
                    external_file = staging / relative
                    external_file.parent.mkdir(parents=True)
                    external_file.write_text("never overwrite\n", encoding="utf-8")
                return real_read(source, expected_hash)

            with (
                mock.patch.object(
                    workflow, "read_approved_source", side_effect=inject_external_file
                ),
                self.assertRaisesRegex(
                    workflow.WorkflowError,
                    "Unexpected entry appeared|Unexpected file appeared",
                ),
            ):
                workflow.initialize(
                    self.initialize_args(target, apply=True, fingerprint=approved["fingerprint"])
                )

            self.assertIsNotNone(external_file)
            self.assertEqual("never overwrite\n", external_file.read_text(encoding="utf-8"))
            self.assertFalse(target.exists())

    def test_staging_symlink_substitution_is_never_reported_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            temp = Path(temp_text)
            target = temp / "project"
            external = temp / "external"
            external.mkdir()
            (external / "external.txt").write_text("never touch\n", encoding="utf-8")
            preserved_workspace = temp / "preserved-verified-staging"
            approved = workflow.init_plan(target)

            def substitute_symlink(parent_fd: int, source_name: str, destination_name: str) -> None:
                os.rename(
                    source_name,
                    preserved_workspace.name,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                )
                os.symlink(
                    external,
                    source_name,
                    target_is_directory=True,
                    dir_fd=parent_fd,
                )
                # Simulate a platform primitive without NOFOLLOW_ANY. The
                # post-commit identity check must still reject this leaf.
                os.rename(
                    source_name,
                    destination_name,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                )

            with (
                mock.patch.object(
                    workflow, "atomic_rename_no_replace_at", side_effect=substitute_symlink
                ),
                self.assertRaisesRegex(
                    workflow.WorkflowError, "is not the verified staging directory"
                ),
            ):
                workflow.initialize(
                    self.initialize_args(target, apply=True, fingerprint=approved["fingerprint"])
                )

            self.assertTrue(target.is_symlink())
            self.assertEqual(
                "never touch\n", (external / "external.txt").read_text(encoding="utf-8")
            )
            verification, clean = workflow.workspace_verification(
                preserved_workspace, installation_target=Path(approved["target"])
            )
            self.assertTrue(clean, verification)

    def test_parent_path_replacement_cannot_redirect_descriptor_anchored_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            temp = Path(temp_text)
            parent = temp / "approved-parent"
            parent.mkdir()
            target = parent / "project"
            approved = workflow.init_plan(target)
            displaced_parent = temp / "displaced-approved-parent"
            real_rename = workflow.atomic_rename_no_replace_at

            def replace_parent_then_commit(
                parent_fd: int, source_name: str, destination_name: str
            ) -> None:
                parent.rename(displaced_parent)
                parent.mkdir()
                target.mkdir()
                (target / "external.txt").write_text("never replace\n", encoding="utf-8")
                real_rename(parent_fd, source_name, destination_name)

            with (
                mock.patch.object(
                    workflow,
                    "atomic_rename_no_replace_at",
                    side_effect=replace_parent_then_commit,
                ),
                self.assertRaisesRegex(
                    workflow.WorkflowError, "is not the verified staging directory"
                ),
            ):
                workflow.initialize(
                    self.initialize_args(target, apply=True, fingerprint=approved["fingerprint"])
                )

            self.assertEqual(
                "never replace\n", (target / "external.txt").read_text(encoding="utf-8")
            )
            verification, clean = workflow.workspace_verification(
                displaced_parent / target.name,
                installation_target=Path(approved["target"]),
            )
            self.assertTrue(clean, verification)

    def test_template_source_replacement_after_plan_never_reaches_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            temp = Path(temp_text)
            template = temp / "template"
            template.mkdir()
            source_file = template / "AGENTS.md"
            source_file.write_text("approved bytes\n", encoding="utf-8")
            manifest = temp / "plugin.json"
            manifest.write_text('{"version":"0.3.0"}\n', encoding="utf-8")
            target = temp / "project"

            with (
                mock.patch.object(workflow, "TEMPLATE_ROOT", template),
                mock.patch.object(workflow, "MANIFEST_PATH", manifest),
            ):
                approved = workflow.init_plan(target)
                real_read = workflow.read_approved_source

                def replace_source_then_read(
                    source: Path, expected_hash: str
                ) -> tuple[bytes, int]:
                    source.write_text("unapproved bytes\n", encoding="utf-8")
                    return real_read(source, expected_hash)

                with (
                    mock.patch.object(
                        workflow,
                        "read_approved_source",
                        side_effect=replace_source_then_read,
                    ),
                    self.assertRaisesRegex(workflow.WorkflowError, "source changed after planning"),
                ):
                    workflow.initialize(
                        self.initialize_args(
                            target, apply=True, fingerprint=approved["fingerprint"]
                        )
                    )

            self.assertFalse(target.exists())
            self.assertEqual(1, len(self.staging_paths(target)))

    def test_commit_uses_approved_plan_snapshot_if_manifest_changes_after_final_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            temp = Path(temp_text)
            target = temp / "project"
            manifest = temp / "plugin.json"
            manifest.write_text('{"version":"0.3.0"}\n', encoding="utf-8")
            real_rename = workflow.atomic_rename_no_replace_at

            with mock.patch.object(workflow, "MANIFEST_PATH", manifest):
                approved = workflow.init_plan(target)

                def update_manifest_then_commit(
                    parent_fd: int, source_name: str, destination_name: str
                ) -> None:
                    manifest.write_text('{"version":"9.9.9"}\n', encoding="utf-8")
                    real_rename(parent_fd, source_name, destination_name)

                with mock.patch.object(
                    workflow,
                    "atomic_rename_no_replace_at",
                    side_effect=update_manifest_then_commit,
                ):
                    code, payload = self.run_emitting(
                        lambda: workflow.initialize(
                            self.initialize_args(
                                target, apply=True, fingerprint=approved["fingerprint"]
                            )
                        )
                    )

            self.assertEqual(0, code)
            self.assertEqual("0.3.0", payload["templateVersion"])
            marker = json.loads(
                (target / workflow.MARKER_REL).read_text(encoding="utf-8")
            )
            self.assertEqual("0.3.0", marker["templateVersion"])
            self.assertEqual(approved["templateDigest"], marker["templateDigest"])
            self.assertEqual(approved["workflowDigest"], marker["workflowDigest"])

    def test_cross_device_atomic_failure_leaves_target_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            target = Path(temp_text) / "project"
            approved = workflow.init_plan(target)

            with (
                mock.patch.object(
                    workflow,
                    "atomic_rename_no_replace_at",
                    side_effect=OSError(errno.EXDEV, "injected cross-device failure"),
                ),
                self.assertRaisesRegex(workflow.WorkflowError, "cannot cross filesystems"),
            ):
                workflow.initialize(
                    self.initialize_args(target, apply=True, fingerprint=approved["fingerprint"])
                )

            self.assertFalse(target.exists())
            self.assertEqual(1, len(self.staging_paths(target)))

    def test_exception_immediately_after_atomic_rename_leaves_complete_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            target = Path(temp_text) / "project"
            approved = workflow.init_plan(target)
            real_rename = workflow.atomic_rename_no_replace_at

            def rename_then_crash(parent_fd: int, source_name: str, destination_name: str) -> None:
                real_rename(parent_fd, source_name, destination_name)
                raise RuntimeError("injected post-rename crash")

            with (
                mock.patch.object(
                    workflow, "atomic_rename_no_replace_at", side_effect=rename_then_crash
                ),
                self.assertRaisesRegex(RuntimeError, "post-rename crash"),
            ):
                workflow.initialize(
                    self.initialize_args(target, apply=True, fingerprint=approved["fingerprint"])
                )

            self.assert_workspace_verifies(target)
            self.assertEqual([], self.staging_paths(target))

    def test_initialization_marker_binds_approval_and_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            target = Path(temp_text) / "project"
            approved = workflow.init_plan(target)
            self.initialize_project(target)
            marker_path = target / workflow.MARKER_REL
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            evidence = marker["initialization"]

            self.assertEqual(approved["fingerprint"], evidence["approvedFingerprint"])
            self.assertEqual(str(workflow.canonical_initialization_target(target)), evidence["target"])
            self.assertEqual(approved["state"], evidence["approvedState"])
            self.assert_workspace_verifies(target)

            evidence["approvedFingerprint"] = "0" * 64
            marker_path.write_text(json.dumps(marker), encoding="utf-8")
            payload, clean = workflow.workspace_verification(
                workflow.canonical_initialization_target(target)
            )
            self.assertFalse(clean)
            self.assertIn("Marker initialization approval evidence is inconsistent.", payload["errors"])

    def test_normal_verify_reports_resolved_plugin_digests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            target = Path(temp_text) / "project"
            self.initialize_project(target)

            code, payload = self.run_emitting(
                lambda: workflow.verify(argparse.Namespace(target=str(target)))
            )

            self.assertEqual(0, code)
            self.assertEqual("verified", payload["status"])
            self.assertIsNotNone(payload["pluginTemplateDigest"])
            self.assertIsNotNone(payload["pluginWorkflowDigest"])
            self.assertEqual(payload["templateDigest"], payload["pluginTemplateDigest"])
            self.assertEqual(payload["workflowDigest"], payload["pluginWorkflowDigest"])

    def test_symlink_target_is_rejected_without_touching_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            temp = Path(temp_text)
            destination = temp / "destination"
            destination.mkdir()
            target = temp / "project"
            target.symlink_to(destination, target_is_directory=True)

            with self.assertRaisesRegex(workflow.WorkflowError, "Symbolic links are not supported"):
                workflow.init_plan(target)

            self.assertEqual([], list(destination.iterdir()))

    def test_approved_initial_sot_change_still_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            target = Path(temp_text) / "project"
            self.initialize_project(target)
            (target / "SOT/SourceOfTruth.md").write_text(
                """# Source of Truth — Test

Project ID: P-0003
Project name: Test
Workspace type: standard-project
Company workspace ID: peter-co-2
Status: planned
Owner: Founder
Last updated: 2026-07-31
""",
                encoding="utf-8",
            )

            code, payload = self.run_emitting(
                lambda: workflow.verify(argparse.Namespace(target=str(target)))
            )

            self.assertEqual(0, code)
            self.assertEqual("verified", payload["status"])
            self.assertNotIn(
                "SOT/SourceOfTruth.md",
                json.loads(
                    (target / ".codex/project-workflow.json").read_text(encoding="utf-8")
                )["managedComponents"],
            )

    def test_migration_fingerprint_binds_backup_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            temp = Path(temp_text)
            target = temp / "project"
            self.initialize_project(target)
            first = workflow.migration_plan(
                self.migrate_args(target, temp / "backup-a", apply=False),
                target,
            )
            second = workflow.migration_plan(
                self.migrate_args(target, temp / "backup-b", apply=False),
                target,
            )
            self.assertNotEqual(first["fingerprint"], second["fingerprint"])

    def test_stale_migration_fingerprint_aborts_without_backup_or_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            temp = Path(temp_text)
            target = temp / "project"
            backup_root = temp / "backups"
            self.initialize_project(target)
            plan = workflow.migration_plan(
                self.migrate_args(target, backup_root, apply=False),
                target,
            )
            changed_text = "changed after approval\n"
            (target / "AGENTS.md").write_text(changed_text, encoding="utf-8")

            code, payload = self.run_emitting(
                lambda: workflow.migrate(
                    self.migrate_args(
                        target,
                        backup_root,
                        apply=True,
                        fingerprint=plan["fingerprint"],
                    )
                )
            )

            self.assertEqual(3, code)
            self.assertEqual("aborted", payload["status"])
            self.assertEqual(
                changed_text,
                (target / "AGENTS.md").read_text(encoding="utf-8"),
            )
            self.assertFalse(backup_root.exists())

    def test_marker_update_is_planned_and_hash_verified_in_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_text:
            temp = Path(temp_text)
            target = temp / "project"
            backup_root = temp / "backups"
            self.initialize_project(target)
            marker_path = target / ".codex/project-workflow.json"
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            marker["templateVersion"] = "0.1.0"
            marker_path.write_text(
                json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            before_hash = hashlib.sha256(marker_path.read_bytes()).hexdigest()
            args = self.migrate_args(target, backup_root, apply=False)
            plan = workflow.migration_plan(args, target)
            marker_operation = next(
                item for item in plan["operations"] if item["path"] == ".codex/project-workflow.json"
            )
            self.assertEqual("update-marker", marker_operation["action"])

            code, payload = self.run_emitting(
                lambda: workflow.migrate(
                    self.migrate_args(
                        target,
                        backup_root,
                        apply=True,
                        fingerprint=plan["fingerprint"],
                    )
                )
            )

            self.assertEqual(0, code)
            self.assertEqual("migrated", payload["status"])
            backup = Path(payload["backup"])
            backup_marker = backup / "files/.codex/project-workflow.json"
            self.assertEqual(before_hash, hashlib.sha256(backup_marker.read_bytes()).hexdigest())
            manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
            entry = next(
                item for item in manifest["entries"] if item["path"] == ".codex/project-workflow.json"
            )
            self.assertEqual(before_hash, entry["beforeHash"])
            self.assertEqual(
                workflow.plugin_version(),
                json.loads(marker_path.read_text(encoding="utf-8"))["templateVersion"],
            )


if __name__ == "__main__":
    unittest.main()

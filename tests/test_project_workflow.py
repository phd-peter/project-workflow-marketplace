from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
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
                "0.2.0",
                json.loads(marker_path.read_text(encoding="utf-8"))["templateVersion"],
            )


if __name__ == "__main__":
    unittest.main()

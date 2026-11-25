from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PureWindowsPath
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins/project-workflow-template"
SCRIPT = PLUGIN_ROOT / "scripts/project_workflow.py"
SOT = "SOT/SourceOfTruth.md"
HANDOFF_SKILL = ".agents/skills/record-work-handoff/SKILL.md"
V040_TEAM_SECTION = (
    "<!-- project-workflow:team-smb:start -->\n"
    "## 공유폴더 팀 작업\n"
    "\n"
    "- 팀원은 각자 Codex에서 같은 프로젝트 루트를 열고 배정받은 `03_WORK/WNN_날짜_주제`에서 작업한다. 기존 `03_WORKS`도 같은 의미로 사용한다. 통합자가 작업 번호와 담당자를 배정한다.\n"
    "- 기존 파일은 원래 위치를 근거로 인용한다. 새 수신물은 `01_INBOX`, 분류한 원본과 소통 증빙은 `02_SOURCE`, 실제 송부·공식 공유한 산출물은 `04_OUTPUT`에 둔다.\n"
    "- 산출물·계산·판단을 인계할 때 `.agents/skills/record-work-handoff/SKILL.md`를 따른다. 입력, 처리 방법, 결과 파일, 검증과 다음 행동을 담당 작업폴더에 남긴다. 팀 시트에서 프로젝트명과 작업 ID로 기존 행을 찾아 갱신한다.\n"
    "- 작업 종료 시 프로젝트 상태·마감·결정·대기 사항의 변경을 확인하고 해당 근거를 작업폴더에 남긴다. 통합자 한 명이 `.agents/skills/update-project-sot/SKILL.md`에 따라 반영안을 모은다. 사람이 완성된 반영안을 별도 메시지로 승인한 뒤 공식 `SOT/SourceOfTruth.md`를 갱신한다.\n"
    "- 프로젝트 기존 승인·발행 절차와 충돌하는 지침은 통합자가 검토한다. 공용 위치는 지정된 작성자 한 명이 변경한다.\n"
    "<!-- project-workflow:team-smb:end -->"
).encode("utf-8")


class TeamSMBTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.target = self.root / "팀 공동 업무"
        self.target.mkdir()
        self.backup_root = self.root / "backups"

    def command(self, *arguments: str, code: int = 0) -> dict:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *arguments, "--target", str(self.target)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            check=False,
            timeout=30,
        )
        self.assertEqual(code, result.returncode, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def migrate(self, *arguments: str, code: int = 0) -> dict:
        return self.command(
            "migrate", "--team-smb", "--backup-root", str(self.backup_root), *arguments, code=code
        )

    def apply_migration(self) -> Path:
        plan = self.migrate()
        self.assertEqual("planned", plan["status"])
        applied = self.migrate("--apply", "--expected-fingerprint", plan["fingerprint"])
        self.assertEqual("migrated", applied["status"])
        return Path(applied["backup"])

    def write(self, relative: str, content: bytes) -> Path:
        path = self.target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    @staticmethod
    def load_workflow():
        spec = importlib.util.spec_from_file_location("project_workflow_team_test", SCRIPT)
        assert spec is not None and spec.loader is not None
        workflow = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(workflow)
        return workflow

    @staticmethod
    def snapshot(root: Path) -> dict[str, tuple[str, bytes | str | None]]:
        state = {}
        for path in root.rglob("*"):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                state[relative] = ("symlink", os.readlink(path))
            elif path.is_dir():
                state[relative] = ("directory", None)
            else:
                state[relative] = ("file", path.read_bytes())
        return state

    def test_existing_project_plan_apply_rerun_and_restore_preserve_work(self) -> None:
        old_agents = "# 팀 운영 절차\r\n\r\n원래 결재 절차를 유지한다.\r\n".encode()
        self.write("AGENTS.md", old_agents)
        self.write("README.md", b"Project-specific index\n")
        self.write("HUMAN_WORKFLOW_GUIDE.md", b"Team-specific human workflow\n")
        self.write(SOT, "# 승인된 프로젝트 정본\n".encode())
        self.write("SOT/REVIEW/reference.md", b"Current review\n")
        self.write("02_SOURCE/original.bin", b"\x00\xff\x80")
        self.write("03_WORKS/W01/measurement.csv", b"item,reading\r\n1,2\r\n")
        self.write("04_OUTPUT/delivered.pdf", b"\x25PDF-existing")
        self.write(".agents/skills/local-team-command/SKILL.md", b"Original custom skill\n")
        self.write(".agents/skills/local-team-command/tools/tool.py", b"print('keep')\n")
        existing_skill = ".agents/skills/continue-project-work/SKILL.md"
        self.write(existing_skill, b"Existing customized workflow\n")
        original = self.snapshot(self.target)

        first_plan = self.migrate()
        self.assertEqual("planned", first_plan["status"])
        self.assertTrue(first_plan["teamSmb"])
        self.assertEqual(first_plan["fingerprint"], self.migrate()["fingerprint"])
        self.assertEqual(original, self.snapshot(self.target))
        self.assertFalse(self.backup_root.exists())
        self.assertTrue(
            any(
                collision["path"] == ".agents/skills/continue-project-work"
                and not collision["blocking"]
                for collision in first_plan["collisions"]
            ),
            first_plan,
        )

        applied = self.migrate("--apply", "--expected-fingerprint", first_plan["fingerprint"])
        self.assertEqual("migrated", applied["status"])
        backup = Path(applied["backup"])
        self.assertTrue(backup.is_relative_to(self.backup_root))
        self.assertEqual(old_agents, (backup / "files/AGENTS.md").read_bytes())
        manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
        agents_entry = next(entry for entry in manifest["entries"] if entry["path"] == "AGENTS.md")
        self.assertEqual(hashlib.sha256(old_agents).hexdigest(), agents_entry["beforeHash"])
        self.assertTrue((self.target / "AGENTS.md").read_bytes().startswith(old_agents))
        self.assertTrue((self.target / HANDOFF_SKILL).is_file())
        self.assertFalse((self.target / "03_WORK").exists())
        installed = self.snapshot(self.target)
        for path, content in original.items():
            if path != "AGENTS.md":
                self.assertEqual(content, installed[path], path)
        self.command("verify")

        previous_backups = self.snapshot(self.backup_root)
        rerun_plan = self.migrate()
        rerun = self.migrate("--apply", "--expected-fingerprint", rerun_plan["fingerprint"])
        self.assertEqual("already_current", rerun["status"])
        self.assertEqual(installed, self.snapshot(self.target))
        self.assertEqual(previous_backups, self.snapshot(self.backup_root))

        new_evidence = b"New work in a pre-existing work directory\n"
        new_evidence_path = "03_WORKS/W01/follow-up.md"
        self.write(new_evidence_path, new_evidence)
        original[new_evidence_path] = ("file", new_evidence)
        installed[new_evidence_path] = ("file", new_evidence)
        restore_plan = self.command("restore")
        self.assertTrue(restore_plan["canApply"], restore_plan)
        self.assertEqual(installed, self.snapshot(self.target))
        self.assertEqual(previous_backups, self.snapshot(self.backup_root))
        restored = self.command("restore", "--apply", "--expected-fingerprint", restore_plan["fingerprint"])
        self.assertEqual("restored", restored["status"])
        self.assertEqual(original, self.snapshot(self.target))
        self.assertEqual(old_agents, (backup / "files/AGENTS.md").read_bytes())

    def test_fingerprint_binds_backup_destination_and_preserves_post_plan_edits(self) -> None:
        agents = self.write("AGENTS.md", b"# Team workflow\n")
        original_plan = self.migrate()
        alternate_plan = self.command(
            "migrate", "--team-smb", "--backup-root", str(self.root / "other-backups")
        )
        self.assertNotEqual(original_plan["fingerprint"], alternate_plan["fingerprint"])
        agents.write_bytes(b"# Operator updated workflow after planning\n")
        edited = self.snapshot(self.target)

        result = self.migrate("--apply", "--expected-fingerprint", original_plan["fingerprint"], code=3)

        self.assertEqual("aborted", result["status"])
        self.assertEqual(edited, self.snapshot(self.target))
        self.assertFalse(self.backup_root.exists())

    def test_upgrade_replaces_only_the_released_v040_section_and_can_be_restored(self) -> None:
        prefix = "\ufeff# 프로젝트 승인 규칙\r\n\r\n".encode("utf-8")
        suffix = "\r\n\r\n## 프로젝트별 인계\n\n공식 절차 유지  ".encode("utf-8")
        old_crlf = V040_TEAM_SECTION.replace(b"\n", b"\r\n")
        agents_before = prefix + old_crlf + suffix
        agents = self.write("AGENTS.md", agents_before)
        marker_before = {
            "schemaVersion": 1,
            "sourcePlugin": "project-workflow-template",
            "templateVersion": "0.4.0",
            "teamSmb": {"sectionSha256": hashlib.sha256(old_crlf).hexdigest()},
        }
        self.write(".codex/project-workflow.json", json.dumps(marker_before).encode("utf-8"))
        original = self.snapshot(self.target)

        plan = self.migrate()
        agents_operation = next(item for item in plan["operations"] if item["path"] == "AGENTS.md")
        self.assertEqual("replace-team-section", agents_operation["action"])
        self.assertEqual(original, self.snapshot(self.target))
        self.assertFalse(self.backup_root.exists())
        result = self.migrate("--apply", "--expected-fingerprint", plan["fingerprint"])
        current = (PLUGIN_ROOT / "assets/team-smb/AGENTS.section.md").read_bytes().strip(b"\r\n")
        current_crlf = current.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        self.assertEqual(prefix + current_crlf + suffix, agents.read_bytes())
        self.assertEqual(agents_before, (Path(result["backup"]) / "files/AGENTS.md").read_bytes())
        self.command("verify")
        rerun = self.migrate()
        self.assertEqual(
            "already_current",
            self.migrate("--apply", "--expected-fingerprint", rerun["fingerprint"])["status"],
        )

        restore = self.command("restore")
        self.assertTrue(restore["canApply"], restore)
        self.command("restore", "--apply", "--expected-fingerprint", restore["fingerprint"])
        self.assertEqual(original, self.snapshot(self.target))

    def test_upgrade_blocks_custom_or_ambiguous_sections_even_with_a_matching_old_marker(self) -> None:
        changed = V040_TEAM_SECTION.replace(b"\n## ", b"\n## Local ", 1)
        start, end = V040_TEAM_SECTION.splitlines()[0], V040_TEAM_SECTION.splitlines()[-1]
        released_digest = hashlib.sha256(V040_TEAM_SECTION).hexdigest()
        cases = {
            "locally edited": (changed, released_digest),
            "forged marker hash": (changed, hashlib.sha256(changed).hexdigest()),
            "duplicate": (V040_TEAM_SECTION + b"\n" + start, released_digest),
            "partial": (V040_TEAM_SECTION.removesuffix(end), released_digest),
            "missing installation proof": (V040_TEAM_SECTION, None),
        }
        for case, (section, digest) in cases.items():
            with self.subTest(case=case):
                self.write("AGENTS.md", b"# Local instructions\n\n" + section)
                marker = {
                    "schemaVersion": 1,
                    "sourcePlugin": "project-workflow-template",
                    "templateVersion": "0.4.0",
                    "teamSmb": {"sectionSha256": digest},
                }
                self.write(".codex/project-workflow.json", json.dumps(marker).encode("utf-8"))
                original = self.snapshot(self.target)

                plan = self.migrate(code=2)
                self.assertTrue(any(
                    collision["path"] == "AGENTS.md" and collision["blocking"]
                    for collision in plan["collisions"]
                ), plan)
                self.migrate("--apply", "--expected-fingerprint", plan["fingerprint"], code=2)
                self.assertEqual(original, self.snapshot(self.target))
                self.assertFalse(self.backup_root.exists())

    def test_critical_skill_collision_blocks_without_replacing_existing_skill(self) -> None:
        self.write(HANDOFF_SKILL, b"# Team's existing handoff command\n")
        self.write("03_WORK/W01/note.md", b"Preserve this evidence\n")
        original = self.snapshot(self.target)

        plan = self.migrate(code=2)

        self.assertEqual("blocked", plan["status"])
        self.assertTrue(
            any(
                collision["path"] == ".agents/skills/record-work-handoff" and collision["blocking"]
                for collision in plan["collisions"]
            ),
            plan,
        )
        blocked = self.migrate("--apply", "--expected-fingerprint", plan["fingerprint"], code=2)
        self.assertEqual("blocked", blocked["status"])
        self.assertEqual(original, self.snapshot(self.target))
        self.assertFalse(self.backup_root.exists())

    def test_restore_refuses_to_remove_activated_sot_and_new_evidence(self) -> None:
        self.write("AGENTS.md", b"# Original team workflow\n")
        self.apply_migration()
        self.assertTrue((self.target / SOT).is_file())
        original_restore_plan = self.command("restore")
        self.assertTrue(original_restore_plan["canApply"], original_restore_plan)
        self.write(SOT, "# 팀이 검토해 승인한 정본\n".encode())
        self.write("04_OUTPUT/new-evidence.bin", b"\x00\xff")
        after_edits = self.snapshot(self.target)

        stale = self.command(
            "restore", "--apply", "--expected-fingerprint", original_restore_plan["fingerprint"], code=3
        )
        self.assertEqual("aborted", stale["status"])
        plan = self.command("restore", "--force-conflicts")
        self.assertFalse(plan["canApply"], plan)
        result = self.command(
            "restore", "--force-conflicts", "--apply", "--expected-fingerprint", plan["fingerprint"], code=4
        )
        self.assertEqual("aborted", result["status"])
        self.assertEqual(after_edits, self.snapshot(self.target))

    def test_failed_apply_rolls_back_its_changes_and_preserves_an_intervening_edit(self) -> None:
        agents = self.write("AGENTS.md", b"# Original instructions\n")
        self.write("03_WORK/W01/evidence.md", b"Original evidence\n")
        expected = self.snapshot(self.target)
        plan = self.migrate()
        workflow = self.load_workflow()
        real_set_path = workflow.team_set_path
        intervening_edit = b"# Operator updated instructions while apply was running\n"

        def fail_after_edit(target, relative, current, desired) -> None:
            if relative == Path("HUMAN_WORKFLOW_GUIDE.md"):
                self.assertNotEqual(expected["AGENTS.md"][1], agents.read_bytes())
                agents.write_bytes(intervening_edit)
                raise OSError("Injected publish failure")
            real_set_path(target, relative, current, desired)

        arguments = [
            str(SCRIPT), "migrate", "--team-smb", "--target", str(self.target),
            "--backup-root", str(self.backup_root), "--apply", "--expected-fingerprint",
            plan["fingerprint"],
        ]
        output = io.StringIO()
        with (
            mock.patch.object(workflow, "team_set_path", side_effect=fail_after_edit),
            mock.patch.object(sys, "argv", arguments),
            contextlib.redirect_stdout(output),
            self.assertRaises(SystemExit) as raised,
        ):
            workflow.main()

        self.assertEqual(1, raised.exception.code, output.getvalue())
        expected["AGENTS.md"] = ("file", intervening_edit)
        self.assertEqual(expected, self.snapshot(self.target))
        manifest_path, = self.backup_root.glob("*/*/manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual("needs-recovery", manifest["state"])
        self.assertTrue(any("AGENTS.md" in error for error in manifest["rollbackErrors"]))

    def test_cross_project_backup_cannot_restore_to_another_target(self) -> None:
        self.write("AGENTS.md", b"# First project\n")
        backup = self.apply_migration()
        first_target = self.target
        first_snapshot = self.snapshot(first_target)
        self.target = self.root / "another-project"
        self.write("AGENTS.md", b"# Second project\n")
        other_snapshot = self.snapshot(self.target)

        result = self.command("restore", "--backup", str(backup), code=1)

        self.assertEqual("error", result["status"])
        self.assertEqual(first_snapshot, self.snapshot(first_target))
        self.assertEqual(other_snapshot, self.snapshot(self.target))

    def test_backup_root_inside_target_is_rejected_in_plan(self) -> None:
        self.write("AGENTS.md", b"# Team workflow\n")
        before = self.snapshot(self.target)
        self.backup_root = self.target / "backups"

        result = self.migrate(code=1)

        self.assertEqual("error", result["status"])
        self.assertEqual(before, self.snapshot(self.target))

    def test_migration_cannot_create_a_nested_workspace_under_a_project_root(self) -> None:
        self.write("AGENTS.md", b"# Existing parent project\n")
        self.write(SOT, b"# Parent project source of truth\n")
        parent_project = self.target
        self.target = parent_project / "03_WORKS/W01"
        self.write("evidence.md", b"# One work item in the parent project\n")
        before = self.snapshot(parent_project)

        plan = self.migrate(code=2)

        self.assertEqual("blocked", plan["status"])
        self.assertEqual(before, self.snapshot(parent_project))
        self.assertFalse(self.backup_root.exists())

    def test_windows_maintenance_accepts_fixed_drives_and_rejects_network_paths(self) -> None:
        workflow = self.load_workflow()
        windows_dlls = mock.Mock()
        get_drive_type = windows_dlls.kernel32.GetDriveTypeW
        get_drive_type.side_effect = [3, 4]  # DRIVE_FIXED and DRIVE_REMOTE

        with (
            mock.patch.object(workflow.os, "name", "nt"),
            mock.patch.object(workflow.ctypes, "windll", windows_dlls, create=True),
        ):
            workflow.require_local_team_filesystem(PureWindowsPath(r"C:\Projects\Team"))
            with self.assertRaises(workflow.WorkflowError):
                workflow.require_local_team_filesystem(PureWindowsPath(r"Z:\Team"))
            with self.assertRaises(workflow.WorkflowError):
                workflow.require_local_team_filesystem(PureWindowsPath(r"\\host\share\Team"))

        self.assertEqual([mock.call("C:\\"), mock.call("Z:\\")], get_drive_type.call_args_list)

    @unittest.skipIf(os.name == "nt", "Creating a symlink can require Windows privileges")
    def test_symlink_on_managed_path_cannot_redirect_migration_outside_workspace(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        original = b"External file must be preserved\n"
        (outside / "SourceOfTruth.md").write_bytes(original)
        (self.target / "SOT").symlink_to(outside, target_is_directory=True)
        before = self.snapshot(self.target)

        plan = self.migrate(code=2)

        self.assertEqual("blocked", plan["status"])
        self.assertEqual(before, self.snapshot(self.target))
        self.assertEqual({"SourceOfTruth.md": ("file", original)}, self.snapshot(outside))
        self.assertFalse(self.backup_root.exists())


if __name__ == "__main__":
    unittest.main()

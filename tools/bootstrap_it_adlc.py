#!/usr/bin/env python3
"""Status, dry-run, and additive install helper for the project ADLC overlay.

This script never deletes or overwrites skills. The additive install mode only
copies missing Salesforce consolidated skills. Legacy adlc-* standard skills are
reported if still present so they can be archived explicitly.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SALESFORCE_UPSTREAM_REPO = "https://github.com/SalesforceAIResearch/agentforce-adlc"
DEFAULT_ARTIFACT_REPO = "https://github.com/YOUR_ORG/YOUR_ADLC_ARTIFACT_REPO"

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
CURSOR_SKILLS_DIR = Path.home() / ".cursor" / "skills"
UPSTREAM_CLONE = Path.home() / "agentforce-adlc-salesforce"

CONSOLIDATED_SKILLS = [
    "developing-agentforce",
    "testing-agentforce",
    "observing-agentforce",
]

LOCAL_WRAPPER_SKILLS = [
    "adlc-drive",
    "adlc-execute",
    "adlc-ticket",
]

LEGACY_STANDARD_SKILLS = [
    "adlc-author",
    "adlc-discover",
    "adlc-scaffold",
    "adlc-deploy",
    "adlc-feedback",
    "adlc-test",
    "adlc-run",
    "adlc-optimize",
]

OVERLAY_DOCS = [
    "adlc/playbooks/agentforce-architecture-playbook.md",
    "adlc/docs/core-process-overlay.md",
    "adlc/docs/acceptance-eval-hitl-governance.md",
    "adlc/docs/artifact-repo-workflow.md",
    "adlc/docs/developer-onboarding.md",
]

SF_COMMANDS = ["agent", "project", "data", "apex", "api", "org"]


def run_command(args: list[str]) -> dict[str, Any]:
    """Run a command and return structured status without raising."""
    executable = shutil.which(args[0])
    if executable is None:
        return {
            "command": " ".join(args),
            "available": False,
            "exit_code": None,
            "stdout": "",
            "stderr": f"{args[0]} not found on PATH",
        }

    completed = subprocess.run(
        args,
        check=False,
        text=True,
        capture_output=True,
    )
    return {
        "command": " ".join(args),
        "available": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def git_remote(path: Path) -> str | None:
    if not path.exists():
        return None
    result = run_command(["git", "-C", str(path), "remote", "get-url", "origin"])
    if result["available"]:
        return result["stdout"]
    return None


def git_commit(path: Path) -> str | None:
    if not path.exists():
        return None
    result = run_command(["git", "-C", str(path), "rev-parse", "HEAD"])
    if result["available"]:
        return result["stdout"]
    return None


def path_status(base: Path, names: list[str]) -> dict[str, bool]:
    return {name: (base / name).exists() for name in names}


def build_report() -> dict[str, Any]:
    sf_version = run_command(["sf", "--version"])
    sf_surfaces = {
        name: run_command(["sf", name, "--help"])["available"]
        for name in SF_COMMANDS
    }

    consolidated_installed = path_status(CURSOR_SKILLS_DIR, CONSOLIDATED_SKILLS)
    wrappers_installed = path_status(CURSOR_SKILLS_DIR, LOCAL_WRAPPER_SKILLS)
    legacy_installed = path_status(CURSOR_SKILLS_DIR, LEGACY_STANDARD_SKILLS)
    overlay_docs = {
        doc: (WORKSPACE_ROOT / doc).exists()
        for doc in OVERLAY_DOCS
    }

    upstream_skills_available = {
        skill: (UPSTREAM_CLONE / "skills" / skill).exists()
        for skill in CONSOLIDATED_SKILLS
    }

    blockers: list[str] = []
    warnings: list[str] = []
    actions: list[dict[str, str]] = []

    if not CURSOR_SKILLS_DIR.exists():
        blockers.append(f"Cursor skills directory missing: {CURSOR_SKILLS_DIR}")

    if not UPSTREAM_CLONE.exists():
        blockers.append(f"Salesforce upstream clone missing: {UPSTREAM_CLONE}")

    missing_upstream_skills = [
        skill for skill, exists in upstream_skills_available.items() if not exists
    ]
    if missing_upstream_skills:
        blockers.append(
            "Salesforce upstream clone is missing consolidated skill dirs: "
            + ", ".join(missing_upstream_skills)
        )

    missing_wrappers = [
        skill for skill, exists in wrappers_installed.items() if not exists
    ]
    if missing_wrappers:
        blockers.append(
            "Local wrapper skills missing from Cursor install: "
            + ", ".join(missing_wrappers)
        )

    missing_overlay_docs = [doc for doc, exists in overlay_docs.items() if not exists]
    if missing_overlay_docs:
        blockers.append("Overlay docs missing: " + ", ".join(missing_overlay_docs))

    missing_sf = [name for name, ok in sf_surfaces.items() if not ok]
    if not sf_version["available"] or missing_sf:
        blockers.append(
            "Salesforce CLI command surfaces missing: " + ", ".join(missing_sf)
        )

    installed_legacy = [skill for skill, exists in legacy_installed.items() if exists]
    missing_consolidated = [
        skill for skill, exists in consolidated_installed.items() if not exists
    ]
    if missing_consolidated:
        warnings.append(
            "Consolidated Salesforce skills are not installed in Cursor: "
            + ", ".join(missing_consolidated)
        )
        for skill in missing_consolidated:
            actions.append(
                {
                    "type": "copy-additive",
                    "from": str(UPSTREAM_CLONE / "skills" / skill),
                    "to": str(CURSOR_SKILLS_DIR / skill),
                    "approval_required": "yes",
                }
            )

    if installed_legacy:
        warnings.append(
            "Legacy adlc-* standard skills are still installed: "
            + ", ".join(installed_legacy)
        )
        actions.append(
            {
                "type": "defer-cleanup",
                "from": str(CURSOR_SKILLS_DIR),
                "to": "legacy adlc-* standard skill dirs",
                "approval_required": "yes; archive explicitly after delegation strategy is approved",
            }
        )

    artifact_remote = git_remote(WORKSPACE_ROOT)
    if artifact_remote != DEFAULT_ARTIFACT_REPO:
        warnings.append(
            "Current workspace is not the shared ADLC artifact repo; "
            "artifact push/PR workflow should be run from a clone of "
            f"{DEFAULT_ARTIFACT_REPO}."
        )

    ready = not blockers and not missing_consolidated

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target": "cursor",
        "workspace": str(WORKSPACE_ROOT),
        "salesforce_cli": {
            "version": sf_version["stdout"] if sf_version["available"] else None,
            "commands_available": sf_surfaces,
        },
        "salesforce_upstream": {
            "repo": SALESFORCE_UPSTREAM_REPO,
            "local_clone": str(UPSTREAM_CLONE),
            "remote": git_remote(UPSTREAM_CLONE),
            "commit": git_commit(UPSTREAM_CLONE),
            "skills_available": upstream_skills_available,
        },
        "cursor_install": {
            "skills_dir": str(CURSOR_SKILLS_DIR),
            "consolidated_skills": consolidated_installed,
            "local_wrappers": wrappers_installed,
            "legacy_standard_skills": legacy_installed,
        },
        "local_overlay": {
            "docs": overlay_docs,
            "artifact_repo": DEFAULT_ARTIFACT_REPO,
            "current_workspace_remote": artifact_remote,
        },
        "planned_actions": actions,
        "warnings": warnings,
        "blockers": blockers,
        "status": "ready" if ready else "not-ready",
    }


def install_additive() -> dict[str, Any]:
    """Copy missing consolidated skills without deleting or overwriting."""
    before = build_report()
    if before["blockers"]:
        return {
            "installed": [],
            "skipped": [],
            "errors": before["blockers"],
            "before": before,
            "after": before,
        }

    installed: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    errors: list[str] = []

    CURSOR_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    for skill in CONSOLIDATED_SKILLS:
        source = UPSTREAM_CLONE / "skills" / skill
        destination = CURSOR_SKILLS_DIR / skill
        if destination.exists():
            skipped.append(
                {
                    "skill": skill,
                    "reason": "destination already exists",
                    "path": str(destination),
                }
            )
            continue
        if not source.exists():
            errors.append(f"Source skill missing: {source}")
            continue
        shutil.copytree(source, destination)
        installed.append(
            {
                "skill": skill,
                "from": str(source),
                "to": str(destination),
            }
        )

    after = build_report()
    return {
        "installed": installed,
        "skipped": skipped,
        "errors": errors,
        "before": before,
        "after": after,
    }


def print_human(report: dict[str, Any], dry_run: bool) -> None:
    label = "DRY RUN" if dry_run else "STATUS"
    print(f"ADLC bootstrap {label}")
    print("=" * (16 + len(label)))
    print(f"Workspace: {report['workspace']}")
    print(f"Status: {report['status']}")
    print()

    print("Salesforce CLI:")
    print(f"  Version: {report['salesforce_cli']['version']}")
    for command, ok in report["salesforce_cli"]["commands_available"].items():
        print(f"  sf {command}: {'ok' if ok else 'missing'}")
    print()

    print("Cursor skills:")
    for group in ("consolidated_skills", "local_wrappers", "legacy_standard_skills"):
        print(f"  {group}:")
        for name, exists in report["cursor_install"][group].items():
            print(f"    {name}: {'present' if exists else 'missing'}")
    print()

    print("Overlay docs:")
    for doc, exists in report["local_overlay"]["docs"].items():
        print(f"  {doc}: {'present' if exists else 'missing'}")
    print()

    print("Planned actions:")
    if report["planned_actions"]:
        for action in report["planned_actions"]:
            print(
                f"  - {action['type']}: {action['from']} -> {action['to']} "
                f"(approval: {action['approval_required']})"
            )
    else:
        print("  none")
    print()

    if report["warnings"]:
        print("Warnings:")
        for warning in report["warnings"]:
            print(f"  - {warning}")
        print()

    if report["blockers"]:
        print("Blockers:")
        for blocker in report["blockers"]:
            print(f"  - {blocker}")
        print()

    if dry_run:
        print("No files were changed.")


def print_install_result(result: dict[str, Any]) -> None:
    print("ADLC bootstrap ADDITIVE INSTALL")
    print("===============================")

    if result["installed"]:
        print("Installed:")
        for item in result["installed"]:
            print(f"  - {item['skill']}: {item['from']} -> {item['to']}")
    else:
        print("Installed: none")
    print()

    if result["skipped"]:
        print("Skipped:")
        for item in result["skipped"]:
            print(f"  - {item['skill']}: {item['reason']} ({item['path']})")
        print()

    if result["errors"]:
        print("Errors:")
        for error in result["errors"]:
            print(f"  - {error}")
        print()

    print(f"Final status: {result['after']['status']}")
    print("Legacy adlc-* skills were not deleted or modified.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--dry-run", action="store_true", help="Preview migration")
    parser.add_argument(
        "--install-additive",
        action="store_true",
        help="Copy missing consolidated skills without deleting or overwriting",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    parser.add_argument(
        "--write-report",
        type=Path,
        help="Optional path to write the JSON report",
    )
    args = parser.parse_args()

    if args.install_additive:
        result = install_additive()
        if args.write_report:
            args.write_report.parent.mkdir(parents=True, exist_ok=True)
            args.write_report.write_text(json.dumps(result, indent=2) + "\n")
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_install_result(result)
        return 0 if not result["errors"] else 2

    dry_run = args.dry_run or not args.status
    report = build_report()

    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(json.dumps(report, indent=2) + "\n")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_human(report, dry_run=dry_run)

    return 0 if not report["blockers"] else 2


if __name__ == "__main__":
    sys.exit(main())

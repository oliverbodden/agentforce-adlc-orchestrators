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

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
CURSOR_SKILLS_DIR = Path.home() / ".cursor" / "skills"
# Cache for the upstream Salesforce ADLC repo. Bootstrap clones/pulls here,
# then vendors the relevant skill subfolders into LOCAL_UPSTREAM_SKILLS_DIR.
UPSTREAM_CLONE = Path.home() / "agentforce-adlc-salesforce"
# Custom skills are vendored in this repo at adlc/skills/ and installed from there.
LOCAL_CUSTOM_SKILLS_SOURCE = WORKSPACE_ROOT / "adlc" / "skills"
# Vendored upstream skill folders live alongside custom skills under one root.
# Their content is gitignored; only README.md and .gitkeep are committed.
# Bootstrap populates this folder by copying from the UPSTREAM_CLONE cache.
LOCAL_UPSTREAM_SKILLS_DIR = LOCAL_CUSTOM_SKILLS_SOURCE / "upstream"

CONSOLIDATED_SKILLS = [
    "developing-agentforce",
    "testing-agentforce",
    "observing-agentforce",
]

# Custom skills shipped at adlc/skills/ — installed to ~/.cursor/skills/ by
# --install-additive.
LOCAL_CUSTOM_SKILLS = [
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
    "adlc/playbooks/prompt-engineering-playbook.md",
    "adlc/playbooks/eval-report-playbook.md",
    "adlc/docs/core-process-overlay.md",
    "adlc/docs/acceptance-eval-hitl-governance.md",
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
    custom_installed = path_status(CURSOR_SKILLS_DIR, LOCAL_CUSTOM_SKILLS)
    legacy_installed = path_status(CURSOR_SKILLS_DIR, LEGACY_STANDARD_SKILLS)
    overlay_docs = {
        doc: (WORKSPACE_ROOT / doc).exists()
        for doc in OVERLAY_DOCS
    }

    upstream_cache_available = {
        skill: (UPSTREAM_CLONE / "skills" / skill).exists()
        for skill in CONSOLIDATED_SKILLS
    }
    # Vendored upstream skills under this repo's adlc/skills/upstream/. This
    # is the install source — bootstrap copies from here to ~/.cursor/skills/.
    upstream_vendored = {
        skill: (LOCAL_UPSTREAM_SKILLS_DIR / skill).exists()
        for skill in CONSOLIDATED_SKILLS
    }
    # Custom skills shipped in this repo — source for additive install.
    custom_skills_available = {
        skill: (LOCAL_CUSTOM_SKILLS_SOURCE / skill).exists()
        for skill in LOCAL_CUSTOM_SKILLS
    }

    blockers: list[str] = []
    warnings: list[str] = []
    actions: list[dict[str, str]] = []

    if not CURSOR_SKILLS_DIR.exists():
        blockers.append(f"Cursor skills directory missing: {CURSOR_SKILLS_DIR}")

    # Missing vendored upstream skills are not blockers — bootstrap auto-vendors
    # on --install-additive. They're a warning so devs know what will happen.
    missing_vendored = [
        skill for skill, exists in upstream_vendored.items() if not exists
    ]
    if missing_vendored:
        warnings.append(
            "Upstream skills not vendored at adlc/skills/upstream/: "
            + ", ".join(missing_vendored)
            + " (run --install-additive or --update-upstream-skills to populate)"
        )

    missing_custom = [
        skill for skill, exists in custom_installed.items() if not exists
    ]
    custom_in_repo_but_not_installed = [
        skill for skill in missing_custom
        if custom_skills_available.get(skill, False)
    ]
    if custom_in_repo_but_not_installed:
        warnings.append(
            "Custom skills present in adlc/skills/ but not installed to Cursor: "
            + ", ".join(custom_in_repo_but_not_installed)
            + " (run --install-additive to install)"
        )
        for skill in custom_in_repo_but_not_installed:
            actions.append(
                {
                    "type": "copy-additive",
                    "from": str(LOCAL_CUSTOM_SKILLS_SOURCE / skill),
                    "to": str(CURSOR_SKILLS_DIR / skill),
                    "approval_required": "yes",
                }
            )
    custom_missing_from_repo = [
        skill for skill in missing_custom
        if not custom_skills_available.get(skill, False)
    ]
    if custom_missing_from_repo:
        blockers.append(
            "Custom skills missing from BOTH Cursor install AND adlc/skills/: "
            + ", ".join(custom_missing_from_repo)
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
                    "from": str(LOCAL_UPSTREAM_SKILLS_DIR / skill),
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

    ready = (
        not blockers
        and not missing_consolidated
        and not custom_in_repo_but_not_installed
        and not missing_vendored
    )

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
            "cache_clone": str(UPSTREAM_CLONE),
            "cache_present": UPSTREAM_CLONE.exists(),
            "cache_remote": git_remote(UPSTREAM_CLONE),
            "cache_commit": git_commit(UPSTREAM_CLONE),
            "cache_skills_available": upstream_cache_available,
            "vendored_dir": str(LOCAL_UPSTREAM_SKILLS_DIR),
            "vendored_skills_available": upstream_vendored,
        },
        "cursor_install": {
            "skills_dir": str(CURSOR_SKILLS_DIR),
            "consolidated_skills": consolidated_installed,
            "local_custom_skills": custom_installed,
            "local_custom_skills_source": str(LOCAL_CUSTOM_SKILLS_SOURCE),
            "custom_skills_available_in_repo": custom_skills_available,
            "legacy_standard_skills": legacy_installed,
        },
        "local_overlay": {
            "docs": overlay_docs,
            "current_workspace_remote": git_remote(WORKSPACE_ROOT),
        },
        "planned_actions": actions,
        "warnings": warnings,
        "blockers": blockers,
        "status": "ready" if ready else "not-ready",
    }


def install_additive() -> dict[str, Any]:
    """Copy missing skills (custom + vendored upstream) without deleting or overwriting.

    Single source: adlc/skills/. Custom skills are committed; upstream skills
    are vendored into adlc/skills/upstream/ by this function (auto-fetched if
    missing). Both are then copied to ~/.cursor/skills/.
    """
    before = build_report()
    # Only block on hard blockers — missing custom skills in repo, missing CLI, etc.
    # Custom-skills-not-installed-yet is the very condition this function fixes.
    hard_blockers = [b for b in before["blockers"] if "Custom skills" not in b or "BOTH" in b]
    if hard_blockers and any("salesforce cli" in b.lower() for b in hard_blockers):
        return {
            "installed": [],
            "skipped": [],
            "errors": hard_blockers,
            "vendor_result": None,
            "before": before,
            "after": before,
        }

    installed: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    errors: list[str] = []

    CURSOR_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: ensure upstream skills are vendored. Auto-vendor if any are missing.
    missing_vendored = [
        skill for skill in CONSOLIDATED_SKILLS
        if not (LOCAL_UPSTREAM_SKILLS_DIR / skill).exists()
    ]
    vendor_result: dict[str, Any] | None = None
    if missing_vendored:
        vendor_result = vendor_upstream_skills()
        if not vendor_result["success"]:
            errors.extend(vendor_result.get("errors", []))
            errors.append(
                "Auto-vendor failed; consolidated skill install will be skipped."
            )

    # Step 2: install consolidated upstream skills from the vendored folder.
    for skill in CONSOLIDATED_SKILLS:
        source = LOCAL_UPSTREAM_SKILLS_DIR / skill
        destination = CURSOR_SKILLS_DIR / skill
        if destination.exists():
            skipped.append(
                {
                    "skill": skill,
                    "kind": "consolidated",
                    "reason": "destination already exists",
                    "path": str(destination),
                }
            )
            continue
        if not source.exists():
            errors.append(
                f"Vendored upstream skill missing: {source}. "
                "Run --update-upstream-skills to populate."
            )
            continue
        shutil.copytree(source, destination)
        installed.append(
            {
                "skill": skill,
                "kind": "consolidated",
                "from": str(source),
                "to": str(destination),
            }
        )

    # Step 3: install custom skills from this repo's adlc/skills/.
    for skill in LOCAL_CUSTOM_SKILLS:
        source = LOCAL_CUSTOM_SKILLS_SOURCE / skill
        destination = CURSOR_SKILLS_DIR / skill
        if destination.exists():
            skipped.append(
                {
                    "skill": skill,
                    "kind": "custom",
                    "reason": "destination already exists",
                    "path": str(destination),
                }
            )
            continue
        if not source.exists():
            errors.append(
                f"Custom source skill missing from repo: {source}. "
                "Vendor the skill into adlc/skills/ first."
            )
            continue
        shutil.copytree(source, destination)
        installed.append(
            {
                "skill": skill,
                "kind": "custom",
                "from": str(source),
                "to": str(destination),
            }
        )

    after = build_report()
    return {
        "installed": installed,
        "skipped": skipped,
        "errors": errors,
        "vendor_result": vendor_result,
        "before": before,
        "after": after,
    }


def fetch_upstream_clone() -> dict[str, Any]:
    """Clone or pull the upstream Salesforce ADLC repo into UPSTREAM_CLONE.

    UPSTREAM_CLONE is a cache. Subsequent runs do `git pull --ff-only` to
    update it without disturbing local edits (there should be none).
    """
    if not UPSTREAM_CLONE.exists():
        UPSTREAM_CLONE.parent.mkdir(parents=True, exist_ok=True)
        result = run_command(
            ["git", "clone", SALESFORCE_UPSTREAM_REPO, str(UPSTREAM_CLONE)]
        )
        if not result["available"]:
            return {
                "success": False,
                "action": "clone",
                "error": f"git clone failed: {result['stderr']}",
            }
        return {"success": True, "action": "cloned"}

    result = run_command(
        ["git", "-C", str(UPSTREAM_CLONE), "pull", "--ff-only"]
    )
    if not result["available"]:
        return {
            "success": False,
            "action": "pull",
            "error": f"git pull failed: {result['stderr']}",
        }
    return {"success": True, "action": "pulled"}


def vendor_upstream_skills() -> dict[str, Any]:
    """Copy the upstream Salesforce skill folders into LOCAL_UPSTREAM_SKILLS_DIR.

    Always replaces existing vendored copies with fresh ones. Writes SOURCE.md
    with the upstream commit hash and timestamp so devs can see what was vendored.
    """
    LOCAL_UPSTREAM_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    fetch = fetch_upstream_clone()
    if not fetch["success"]:
        return {
            "success": False,
            "vendored": [],
            "fetch": fetch,
            "errors": [fetch["error"]],
        }

    vendored: list[dict[str, str]] = []
    errors: list[str] = []
    for skill in CONSOLIDATED_SKILLS:
        source = UPSTREAM_CLONE / "skills" / skill
        destination = LOCAL_UPSTREAM_SKILLS_DIR / skill
        if not source.exists():
            errors.append(
                f"Upstream skill missing in cache: {source}. "
                "Cache may be partial; try removing it and re-running."
            )
            continue
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        vendored.append(
            {
                "skill": skill,
                "from": str(source),
                "to": str(destination),
            }
        )

    commit = git_commit(UPSTREAM_CLONE) or "unknown"
    remote = git_remote(UPSTREAM_CLONE) or SALESFORCE_UPSTREAM_REPO
    fetched_at = datetime.now(timezone.utc).isoformat()
    source_md = (
        "# Upstream Source (runtime state — not committed)\n\n"
        "This file is rewritten by `bootstrap_it_adlc.py --update-upstream-skills`\n"
        "(and by `--install-additive` when it auto-vendors). Do not edit by hand.\n\n"
        "## Vendored from\n\n"
        f"- **Repo:** {remote}\n"
        f"- **Commit:** `{commit}`\n"
        f"- **Fetched at:** {fetched_at}\n"
        f"- **Cache location:** `{UPSTREAM_CLONE}`\n\n"
        "## Vendored skills\n\n"
        + "\n".join(f"- `{item['skill']}/`" for item in vendored)
        + "\n\n## Re-vendor\n\n"
        "```bash\n"
        "python3 tools/bootstrap_it_adlc.py --update-upstream-skills\n"
        "```\n"
    )
    (LOCAL_UPSTREAM_SKILLS_DIR / "SOURCE.md").write_text(source_md)

    return {
        "success": not errors,
        "vendored": vendored,
        "errors": errors,
        "fetch": fetch,
        "commit": commit,
        "fetched_at": fetched_at,
    }


def configure_remotes(
    canonical_url: str | None = None,
    mirror_url: str | None = None,
    interactive: bool = True,
) -> dict[str, Any]:
    """Configure git remotes for the workspace.

    If --canonical-url and --mirror-url are not provided and interactive=True,
    prompts the user. Initializes git if no .git/ exists. Idempotent — won't
    overwrite existing remotes; reports them instead.
    """
    result: dict[str, Any] = {
        "git_init_run": False,
        "remotes_added": [],
        "remotes_existing": [],
        "errors": [],
    }

    if not (WORKSPACE_ROOT / ".git").exists():
        if not interactive:
            result["errors"].append(
                "No .git/ found. Run `git init` first or use interactive mode."
            )
            return result
        confirm = input(
            f"No git repo found at {WORKSPACE_ROOT}. Run `git init`? [y/N] "
        ).strip().lower()
        if confirm == "y":
            init_result = run_command(["git", "-C", str(WORKSPACE_ROOT), "init"])
            if not init_result["available"]:
                result["errors"].append(f"git init failed: {init_result['stderr']}")
                return result
            result["git_init_run"] = True
        else:
            result["errors"].append("git init declined; cannot configure remotes.")
            return result

    if canonical_url is None and interactive:
        canonical_url = input(
            "Canonical remote URL (e.g., GitLab) [skip with empty]: "
        ).strip() or None
    if mirror_url is None and interactive:
        mirror_url = input(
            "Mirror remote URL (e.g., GitHub) [skip with empty]: "
        ).strip() or None

    for name, url in (("origin", canonical_url), ("github", mirror_url)):
        if not url:
            continue
        existing = run_command(
            ["git", "-C", str(WORKSPACE_ROOT), "remote", "get-url", name]
        )
        if existing["available"]:
            result["remotes_existing"].append(
                {"name": name, "url": existing["stdout"], "requested": url}
            )
            continue
        add = run_command(
            ["git", "-C", str(WORKSPACE_ROOT), "remote", "add", name, url]
        )
        if add["available"]:
            result["remotes_added"].append({"name": name, "url": url})
        else:
            result["errors"].append(
                f"Failed to add remote {name}={url}: {add['stderr']}"
            )

    return result


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

    print("Cursor skills (installed at ~/.cursor/skills/):")
    for group in (
        "consolidated_skills",
        "local_custom_skills",
        "legacy_standard_skills",
    ):
        print(f"  {group}:")
        for name, exists in report["cursor_install"][group].items():
            print(f"    {name}: {'present' if exists else 'missing'}")
    print()

    print("Upstream Salesforce skills:")
    print(
        f"  Cache present at {report['salesforce_upstream']['cache_clone']}: "
        f"{'yes' if report['salesforce_upstream']['cache_present'] else 'no'}"
    )
    if report['salesforce_upstream']['cache_present']:
        print(f"  Cache commit: {report['salesforce_upstream']['cache_commit']}")
    print(
        f"  Vendored at {report['salesforce_upstream']['vendored_dir']}:"
    )
    for name, exists in report['salesforce_upstream']['vendored_skills_available'].items():
        print(f"    {name}: {'vendored' if exists else 'NOT vendored (run --update-upstream-skills)'}")
    print()

    print(
        "Custom skills available in repo (adlc/skills/): "
        f"{report['cursor_install']['local_custom_skills_source']}"
    )
    for name, exists in report["cursor_install"]["custom_skills_available_in_repo"].items():
        print(f"  {name}: {'present in repo' if exists else 'MISSING from repo'}")
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

    vendor = result.get("vendor_result")
    if vendor:
        print("Auto-vendor of upstream skills:")
        if vendor.get("success"):
            print(
                f"  - Fetch: {vendor['fetch']['action']} "
                f"(commit {vendor.get('commit', 'unknown')[:12]})"
            )
            for item in vendor.get("vendored", []):
                print(f"  - Vendored: {item['skill']} -> {item['to']}")
        else:
            print(f"  - FAILED: {vendor.get('errors', ['unknown'])}")
        print()

    if result["installed"]:
        print("Installed:")
        for item in result["installed"]:
            kind = item.get("kind", "skill")
            print(f"  - [{kind}] {item['skill']}: {item['from']} -> {item['to']}")
    else:
        print("Installed: none")
    print()

    if result["skipped"]:
        print("Skipped:")
        for item in result["skipped"]:
            kind = item.get("kind", "skill")
            print(f"  - [{kind}] {item['skill']}: {item['reason']} ({item['path']})")
        print()

    if result["errors"]:
        print("Errors:")
        for error in result["errors"]:
            print(f"  - {error}")
        print()

    print(f"Final status: {result['after']['status']}")
    print("Legacy adlc-* skills were not deleted or modified.")


def print_vendor_result(result: dict[str, Any]) -> None:
    print("ADLC bootstrap UPDATE UPSTREAM SKILLS")
    print("=====================================")
    fetch = result.get("fetch", {})
    if fetch:
        action = fetch.get("action", "unknown")
        if fetch.get("success"):
            print(f"Cache fetch: {action} ({UPSTREAM_CLONE})")
        else:
            print(f"Cache fetch FAILED ({action}): {fetch.get('error', 'unknown')}")
    print()

    if result.get("vendored"):
        print(f"Vendored to {LOCAL_UPSTREAM_SKILLS_DIR}:")
        for item in result["vendored"]:
            print(f"  - {item['skill']}: {item['from']} -> {item['to']}")
    else:
        print("Vendored: none")
    print()

    if result.get("commit"):
        print(f"Pinned commit: {result['commit']}")
        print(f"Fetched at:    {result.get('fetched_at', 'unknown')}")
        print(f"SOURCE.md updated at: {LOCAL_UPSTREAM_SKILLS_DIR / 'SOURCE.md'}")
        print()

    if result.get("errors"):
        print("Errors:")
        for error in result["errors"]:
            print(f"  - {error}")
        print()

    print(
        "Next: run --install-additive to copy these into ~/.cursor/skills/."
    )


def print_configure_remotes_result(result: dict[str, Any]) -> None:
    print("ADLC bootstrap CONFIGURE REMOTES")
    print("================================")
    if result["git_init_run"]:
        print(f"git init: ran in {WORKSPACE_ROOT}")
    if result["remotes_added"]:
        print("Remotes added:")
        for item in result["remotes_added"]:
            print(f"  - {item['name']}: {item['url']}")
    if result["remotes_existing"]:
        print("Remotes already configured (left unchanged):")
        for item in result["remotes_existing"]:
            print(f"  - {item['name']}: {item['url']} (you requested: {item['requested']})")
    if result["errors"]:
        print("Errors:")
        for err in result["errors"]:
            print(f"  - {err}")
    if not (
        result["git_init_run"]
        or result["remotes_added"]
        or result["remotes_existing"]
        or result["errors"]
    ):
        print("Nothing changed (no URLs provided).")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--dry-run", action="store_true", help="Preview migration")
    parser.add_argument(
        "--install-additive",
        action="store_true",
        help=(
            "Copy missing skills (custom + vendored upstream from adlc/skills/) "
            "to ~/.cursor/skills/ without deleting or overwriting. "
            "Auto-vendors upstream skills if missing from adlc/skills/upstream/."
        ),
    )
    parser.add_argument(
        "--update-upstream-skills",
        action="store_true",
        help=(
            "Fetch upstream Salesforce ADLC repo (clone or git pull) and "
            "re-vendor the consolidated skills into adlc/skills/upstream/. "
            "Run this to upgrade pinned upstream skill versions."
        ),
    )
    parser.add_argument(
        "--configure-remotes",
        action="store_true",
        help=(
            "Configure git remotes (canonical + mirror) for this workspace. "
            "Prompts interactively if --canonical-url and --mirror-url not provided. "
            "Initializes git if no .git/ exists."
        ),
    )
    parser.add_argument(
        "--canonical-url",
        type=str,
        help="Canonical remote URL (used by --configure-remotes; e.g., GitLab)",
    )
    parser.add_argument(
        "--mirror-url",
        type=str,
        help="Mirror remote URL (used by --configure-remotes; e.g., GitHub)",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    parser.add_argument(
        "--write-report",
        type=Path,
        help="Optional path to write the JSON report",
    )
    args = parser.parse_args()

    if args.configure_remotes:
        result = configure_remotes(
            canonical_url=args.canonical_url,
            mirror_url=args.mirror_url,
            interactive=True,
        )
        if args.write_report:
            args.write_report.parent.mkdir(parents=True, exist_ok=True)
            args.write_report.write_text(json.dumps(result, indent=2) + "\n")
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_configure_remotes_result(result)
        return 0 if not result["errors"] else 2

    if args.update_upstream_skills:
        result = vendor_upstream_skills()
        if args.write_report:
            args.write_report.parent.mkdir(parents=True, exist_ok=True)
            args.write_report.write_text(json.dumps(result, indent=2) + "\n")
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_vendor_result(result)
        return 0 if result.get("success") else 2

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

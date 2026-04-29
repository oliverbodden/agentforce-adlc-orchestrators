#!/usr/bin/env python3
"""Update a GenAiPluginInstructionDef record via Tooling API.

Usage:
    python3 update_instruction.py --org <alias> --record-id <id> --file <path>
    python3 update_instruction.py --org <alias> --record-id <id> --rollback <backup-path>

Backs up the current instruction before updating.
"""
import argparse
import json
import subprocess
import sys


def get_org_credentials(org_alias):
    result = subprocess.run(
        ["sf", "org", "display", "-o", org_alias, "--json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    return data["result"]["accessToken"], data["result"]["instanceUrl"]


def get_current_instruction(token, instance, record_id):
    import urllib.request
    url = f"{instance}/services/data/v63.0/tooling/sobjects/GenAiPluginInstructionDef/{record_id}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data.get("Description", "")


def update_instruction(token, instance, record_id, new_text):
    import urllib.request
    url = f"{instance}/services/data/v63.0/tooling/sobjects/GenAiPluginInstructionDef/{record_id}"
    body = json.dumps({"Description": new_text}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="PATCH", headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    with urllib.request.urlopen(req) as resp:
        return resp.status


def main():
    parser = argparse.ArgumentParser(description="Update GenAiPluginInstructionDef")
    parser.add_argument("--org", required=True, help="Org alias")
    parser.add_argument("--record-id", required=True, help="GenAiPluginInstructionDef ID")
    parser.add_argument("--file", help="Path to new instruction text file")
    parser.add_argument("--rollback", help="Path to backup file to restore")
    parser.add_argument("--backup-dir", default=".", help="Where to save backup")
    args = parser.parse_args()

    token, instance = get_org_credentials(args.org)

    source = args.rollback or args.file
    if not source:
        print("Error: provide --file or --rollback", file=sys.stderr)
        sys.exit(1)

    # Backup current instruction
    if not args.rollback:
        current = get_current_instruction(token, instance, args.record_id)
        backup_path = f"{args.backup_dir}/backup-{args.record_id}.txt"
        with open(backup_path, "w") as f:
            f.write(current)
        print(f"Backed up current instruction: {len(current.split())} words → {backup_path}")

    # Load new instruction
    new_text = open(source).read()
    print(f"Deploying: {len(new_text.split())} words from {source}")

    status = update_instruction(token, instance, args.record_id, new_text)
    print(f"HTTP {status} — {'Success' if status == 204 else 'Failed'}")


if __name__ == "__main__":
    main()

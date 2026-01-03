#!/usr/bin/env python3
"""
Set up CAAL workflows in n8n.

Replaces placeholders in workflow JSONs and creates them in n8n.

Usage:
    1. Copy config.env.example to config.env
    2. Fill in your IP addresses and API key
    3. Run: python setup.py
"""

import re
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path


def load_config():
    """Load configuration from config.env file."""
    config = {}
    config_file = Path(__file__).parent / "config.env"

    if not config_file.exists():
        print("Error: config.env not found.")
        print("Run: cp config.env.example config.env")
        print("Then edit config.env with your values.")
        sys.exit(1)

    with open(config_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()

    # Validate required fields
    missing = []
    if not config.get("N8N_HOST"):
        missing.append("N8N_HOST")
    if not config.get("N8N_API_KEY") or config.get("N8N_API_KEY") == "your_n8n_api_key_here":
        missing.append("N8N_API_KEY")

    if missing:
        print(f"Error: Missing required config: {', '.join(missing)}")
        print("Edit config.env and fill in your values.")
        sys.exit(1)

    return config


def replace_placeholders(content: str, config: dict) -> str:
    """Replace {{PLACEHOLDER}} with values from config."""
    def replacer(match):
        key = match.group(1)
        value = config.get(key)
        if value and not value.startswith("your_"):
            return value
        return match.group(0)  # Keep placeholder if no value

    return re.sub(r"\{\{(\w+)\}\}", replacer, content)


def http_request(url: str, headers: dict, method: str = "GET", data: bytes = None) -> tuple:
    """Make HTTP request using urllib. Returns (status_code, response_body)."""
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except urllib.error.URLError as e:
        raise ConnectionError(f"Could not connect: {e.reason}")


def create_workflow(n8n_api: str, headers: dict, workflow: dict, n8n_host: str) -> bool:
    """Create and activate a workflow in n8n."""
    name = workflow.get("name", "unknown")

    # Check if workflow already exists (skip archived workflows)
    status, body = http_request(f"{n8n_api}/workflows", headers)
    if status == 200:
        for wf in json.loads(body).get("data", []):
            if wf["name"] == name and not wf.get("isArchived", False):
                print(f"  Skipped: {name} (already exists)")
                return True

    # Create workflow
    post_headers = {**headers, "Content-Type": "application/json"}
    data = json.dumps(workflow).encode("utf-8")
    status, body = http_request(f"{n8n_api}/workflows", post_headers, "POST", data)
    if status not in (200, 201):
        print(f"  Error creating {name}: {body}")
        return False

    resp_data = json.loads(body)
    workflow_id = resp_data["id"]

    # Activate workflow
    status, body = http_request(f"{n8n_api}/workflows/{workflow_id}/activate", post_headers, "POST")
    if status != 200:
        print(f"  Warning: Created {name} but could not activate")
        return True

    # Get webhook path
    webhook_path = None
    for node in workflow.get("nodes", []):
        if node.get("type") == "n8n-nodes-base.webhook":
            webhook_path = node.get("parameters", {}).get("path")
            break

    if webhook_path:
        print(f"  Created: {name}")
        print(f"           http://{n8n_host}/webhook/{webhook_path}")
    else:
        print(f"  Created: {name}")

    return True


def process_seed_file(config: dict):
    """Replace placeholders in the workflow builder seed file."""
    workflow_dir = Path(__file__).parent
    seed_file = workflow_dir / "caal-workflow-builder-seed.md"

    if not seed_file.exists():
        return

    content = seed_file.read_text()
    original = content
    content = replace_placeholders(content, config)

    if content != original:
        seed_file.write_text(content)
        print("Updated caal-workflow-builder-seed.md with config values\n")


def main():
    print("CAAL n8n Workflow Setup")
    print("=" * 40)
    print()

    config = load_config()
    n8n_host = config["N8N_HOST"]
    api_key = config["N8N_API_KEY"]
    n8n_api = f"http://{n8n_host}/api/v1"
    headers = {"X-N8N-API-KEY": api_key}

    # Process seed file with config values
    process_seed_file(config)

    # Test n8n connection
    print(f"Connecting to n8n at {n8n_host}...")
    try:
        status, _ = http_request(f"{n8n_api}/workflows", headers)
        if status != 200:
            print(f"Error: Could not connect to n8n (HTTP {status})")
            print("Check N8N_HOST and N8N_API_KEY in config.env")
            sys.exit(1)
    except ConnectionError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("Connected!\n")

    # Find all workflow JSON files
    workflow_dir = Path(__file__).parent
    json_files = sorted(workflow_dir.glob("*.json"))

    if not json_files:
        print("No workflow JSON files found.")
        sys.exit(1)

    print(f"Found {len(json_files)} workflow(s):\n")

    success = 0
    failed = 0

    for json_file in json_files:
        content = json_file.read_text()

        # Replace placeholders
        content = replace_placeholders(content, config)

        # Check for remaining placeholders
        remaining = re.findall(r"\{\{(\w+)\}\}", content)
        if remaining:
            print(f"  Skipped: {json_file.name}")
            print(f"           Missing config: {', '.join(set(remaining))}")
            failed += 1
            continue

        # Parse and create
        try:
            workflow = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"  Error: {json_file.name} - Invalid JSON: {e}")
            failed += 1
            continue

        if create_workflow(n8n_api, headers, workflow, n8n_host):
            success += 1
        else:
            failed += 1

    print()
    print("=" * 40)
    print(f"Done! {success} created, {failed} skipped/failed")

    if success > 0:
        print()
        print("Next steps:")
        print("1. Restart CAAL or call /reload-tools to discover new tools")
        print("2. Test with voice: 'What are the NFL scores?'")


if __name__ == "__main__":
    main()

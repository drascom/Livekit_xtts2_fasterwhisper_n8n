#!/usr/bin/env python3
"""Update an existing n8n workflow from a JSON file."""

import sys
import json
import requests
from pathlib import Path


def load_config():
    """Load configuration from config.env file."""
    config = {}
    config_file = Path(__file__).parent / "config.env"

    if not config_file.exists():
        print("Error: config.env not found. Copy config.env.example to config.env and fill in your values.")
        sys.exit(1)

    with open(config_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()

    return config


def get_workflow_id(n8n_api: str, headers: dict, name: str) -> str | None:
    """Find workflow ID by name."""
    resp = requests.get(f"{n8n_api}/workflows", headers=headers)
    if resp.status_code != 200:
        return None
    for wf in resp.json().get("data", []):
        if wf["name"] == name:
            return wf["id"]
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: update_workflow.py <workflow.json> [workflow_id]")
        sys.exit(1)

    config = load_config()
    n8n_host = config.get("N8N_HOST")
    api_key = config.get("N8N_API_KEY")

    if not n8n_host:
        print("Error: N8N_HOST not set in config.env")
        sys.exit(1)
    if not api_key:
        print("Error: N8N_API_KEY not set in config.env")
        sys.exit(1)

    n8n_api = f"http://{n8n_host}/api/v1"
    headers = {"Content-Type": "application/json", "X-N8N-API-KEY": api_key}

    workflow_file = Path(sys.argv[1])
    if not workflow_file.exists():
        print(f"Error: {workflow_file} not found")
        sys.exit(1)

    with open(workflow_file) as f:
        workflow = json.load(f)

    # Get workflow ID from arg or lookup by name
    if len(sys.argv) >= 3:
        workflow_id = sys.argv[2]
    else:
        workflow_id = get_workflow_id(n8n_api, headers, workflow["name"])
        if not workflow_id:
            print(f"Error: Workflow '{workflow['name']}' not found. Use create_workflow.py instead.")
            sys.exit(1)

    # Update workflow
    resp = requests.put(f"{n8n_api}/workflows/{workflow_id}", headers=headers, json=workflow)
    if resp.status_code != 200:
        print(f"Error updating workflow: {resp.text}")
        sys.exit(1)

    data = resp.json()
    print(f"Updated: {data['name']} (ID: {workflow_id})")
    print(f"Active: {data.get('active', False)}")

    # Show webhook path
    webhook_path = None
    for node in workflow.get("nodes", []):
        if node.get("type") == "n8n-nodes-base.webhook":
            webhook_path = node.get("parameters", {}).get("path")
            break

    if webhook_path:
        print(f"Webhook: http://{n8n_host}/webhook/{webhook_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Detect Azure DevOps process template via REST API.

Cross-platform, stdlib-only. Reads AZURE_DEVOPS_EXT_PAT from environment.
Outputs JSON to stdout: {"processTemplate": "Scrum", "workItemTypes": [...]}
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error


def get_pat():
    pat = os.environ.get("AZURE_DEVOPS_EXT_PAT", "")
    if not pat:
        print(json.dumps({"error": "AZURE_DEVOPS_EXT_PAT environment variable not set"}))
        sys.exit(1)
    return pat


def build_auth_header(pat):
    token = base64.b64encode(f":{pat}".encode("utf-8")).decode("utf-8")
    return f"Basic {token}"


def fetch_work_item_types(org_url, project, pat):
    org_url = org_url.rstrip("/")
    url = f"{org_url}/{urllib.request.quote(project)}/_apis/wit/workitemtypes?api-version=7.0"

    req = urllib.request.Request(url)
    req.add_header("Authorization", build_auth_header(pat))
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        print(json.dumps({
            "error": f"HTTP {e.code}: {e.reason}",
            "detail": body
        }))
        sys.exit(1)
    except urllib.error.URLError as e:
        print(json.dumps({"error": f"Connection failed: {e.reason}"}))
        sys.exit(1)


def detect_template(type_names):
    names = set(type_names)
    if "User Story" in names:
        return "Agile"
    if "Product Backlog Item" in names:
        return "Scrum"
    if "Requirement" in names:
        return "CMMI"
    if "Issue" in names:
        return "Basic"
    return "Unknown"


def main():
    parser = argparse.ArgumentParser(
        description="Detect Azure DevOps process template via REST API"
    )
    parser.add_argument("--org", required=True, help="Organization URL (e.g. https://dev.azure.com/myorg)")
    parser.add_argument("--project", required=True, help="Project name")
    args = parser.parse_args()

    pat = get_pat()
    data = fetch_work_item_types(args.org, args.project, pat)

    type_names = []
    for item in data.get("value", []):
        name = item.get("name", "")
        if name:
            type_names.append(name)

    template = detect_template(type_names)

    result = {
        "processTemplate": template,
        "workItemTypes": sorted(type_names)
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

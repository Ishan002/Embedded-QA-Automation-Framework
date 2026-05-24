#!/usr/bin/env python3
"""Post JUnit XML test results to the QA portal API."""
import argparse
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import requests


def parse_junit_xml(xml_path: str) -> list:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    results = []
    for suite in root.iter("testsuite"):
        for case in suite.iter("testcase"):
            classname = case.get("classname", "")
            name = case.get("name", "")
            time_s = float(case.get("time", "0"))

            failure = case.find("failure")
            error = case.find("error")
            skipped = case.find("skipped")

            if failure is not None:
                status = "failed"
                error_message = failure.get("message", failure.text or "")
            elif error is not None:
                status = "error"
                error_message = error.get("message", error.text or "")
            elif skipped is not None:
                status = "skipped"
                error_message = ""
            else:
                status = "passed"
                error_message = ""

            module = classname.replace(".", "/").rsplit("/", 1)[0] if "." in classname else classname
            category = "other"
            if "boot" in module:
                category = "boot"
            elif "sensor_io" in module or "sensor" in module:
                category = "sensor_io"
            elif "data_integrity" in module or "data" in module:
                category = "data_integrity"

            results.append({
                "test_name": name,
                "module": module,
                "category": category,
                "status": status,
                "duration_ms": int(time_s * 1000),
                "error_message": error_message,
                "stdout": "",
                "started_at": datetime.now(timezone.utc).isoformat(),
            })

    return results


def main():
    parser = argparse.ArgumentParser(description="Post test results to QA portal")
    parser.add_argument("--xml", required=True, help="Path to JUnit XML file")
    parser.add_argument("--firmware", default="", help="Firmware version under test")
    args = parser.parse_args()

    portal_url = os.environ.get("PORTAL_URL", "").rstrip("/")
    token = os.environ.get("PORTAL_TOKEN", "")
    commit_sha = os.environ.get("GIT_COMMIT", "0" * 40)
    branch = os.environ.get("GIT_BRANCH", "unknown")
    pr_number = os.environ.get("PR_NUMBER")

    if not portal_url or not token:
        print("PORTAL_URL or PORTAL_TOKEN not set — skipping portal upload")
        sys.exit(0)

    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}

    run_payload = {
        "commit_sha": commit_sha[:40],
        "branch": branch,
        "pr_number": int(pr_number) if pr_number and pr_number.isdigit() else None,
        "triggered_by": "pull_request" if pr_number else "push",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "device_firmware": args.firmware,
    }

    resp = requests.post(f"{portal_url}/api/runs/", json=run_payload, headers=headers, timeout=10)
    resp.raise_for_status()
    run_id = resp.json()["run_id"]
    print(f"Created run: {run_id}")

    results = parse_junit_xml(args.xml)
    resp = requests.post(
        f"{portal_url}/api/runs/{run_id}/results/",
        json=results,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    print(f"Uploaded {len(results)} results")

    failed_count = sum(1 for r in results if r["status"] in ("failed", "error"))
    final_status = "failed" if failed_count > 0 else "passed"
    resp = requests.patch(
        f"{portal_url}/api/runs/{run_id}/complete/",
        json={"status": final_status},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    print(f"Run completed with status: {final_status}")


if __name__ == "__main__":
    main()

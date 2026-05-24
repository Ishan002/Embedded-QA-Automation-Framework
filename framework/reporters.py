import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime


@dataclass
class TestResult:
    test_name: str
    module: str
    status: str  # passed, failed, skipped, error
    duration_ms: int
    error_message: str = ""
    stdout: str = ""
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class JSONReporter:
    def __init__(self, output_path: str = "test_results.json"):
        self.output_path = output_path
        self.results: List[TestResult] = []

    def add(self, result: TestResult):
        self.results.append(result)

    def write(self):
        with open(self.output_path, "w") as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)


class PortalReporter:
    def __init__(self, portal_url: str, token: str):
        self.portal_url = portal_url.rstrip("/")
        self.token = token
        self._run_id: Optional[str] = None

    def _headers(self):
        return {"Authorization": f"Token {self.token}", "Content-Type": "application/json"}

    def create_run(self, commit_sha: str, branch: str, pr_number: Optional[int] = None) -> str:
        import requests
        payload = {
            "commit_sha": commit_sha,
            "branch": branch,
            "pr_number": pr_number,
            "triggered_by": "pull_request" if pr_number else "push",
            "started_at": datetime.utcnow().isoformat(),
            "status": "running",
        }
        resp = requests.post(
            f"{self.portal_url}/api/runs/",
            json=payload,
            headers=self._headers(),
            timeout=10,
        )
        resp.raise_for_status()
        self._run_id = resp.json()["run_id"]
        return self._run_id

    def post_results(self, results: List[TestResult]):
        if not self._run_id:
            raise RuntimeError("No active run — call create_run() first")
        import requests
        payload = [asdict(r) for r in results]
        resp = requests.post(
            f"{self.portal_url}/api/runs/{self._run_id}/results/",
            json=payload,
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()

    def complete_run(self, status: str = "passed"):
        if not self._run_id:
            return
        import requests
        resp = requests.patch(
            f"{self.portal_url}/api/runs/{self._run_id}/complete/",
            json={"status": status, "completed_at": datetime.utcnow().isoformat()},
            headers=self._headers(),
            timeout=10,
        )
        resp.raise_for_status()

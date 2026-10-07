"""Exercise the running API against representative records from all four states."""

from __future__ import annotations

import time

import httpx

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"X-User-Email": "smoke@portercap.net", "X-User-Role": "sales"}
TERMINAL = {"completed", "failed", "source_unavailable"}
CASES = (
    ("CO", "KYLDERON MIST VALLEY LLC", "verified"),
    ("CT", "AAABON PEST CONTROL, INC.", "verified"),
    ("OR", "UNITED METHODIST CHURCH, OREGON CITY, OREGON", "verified"),
    ("OH", "PORTER LIVE SMOKE TEST LLC", "insufficient_evidence"),
)


def main() -> None:
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=30) as client:
        for state, name, expected in CASES:
            started = client.post("/verify", json={"name": name, "state": state})
            started.raise_for_status()
            run_id = started.json()["run_id"]

            for _ in range(60):
                response = client.get(f"/runs/{run_id}")
                response.raise_for_status()
                run = response.json()["run"]
                if run["status"] in TERMINAL:
                    break
                time.sleep(0.5)
            else:
                raise TimeoutError(f"{state} verification did not finish")

            actual = run["verification_status"]
            print(
                f"{state}: {actual} (run={run['status']}, "
                f"confidence={run['match_confidence']})"
            )
            if actual != expected:
                raise AssertionError(f"{state}: expected {expected}, got {actual}")


if __name__ == "__main__":
    main()

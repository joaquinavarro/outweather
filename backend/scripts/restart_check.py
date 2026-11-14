"""Prove persistence across a real process restart."""

import json
import subprocess
import time
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8000/api/v1"
BACKEND = Path(__file__).resolve().parents[1]


def call(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        API + path, data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
        try:
            return r.status, json.loads(body)
        except Exception:
            return r.status, body


status, created = call("/farms", {"demo_farm_id": "demo_finney"})
farm_id = created["data"]["farm_id"]
print("1. farm created:", farm_id, "|", created["data"]["county"])

status, job = call(f"/farms/{farm_id}/rotation:optimize", {})
job_id = job["data"]["job_id"]
for _ in range(200):
    _, j = call(f"/jobs/{job_id}")
    if j["data"]["status"] in ("done", "failed"):
        break
    time.sleep(0.2)
rot_id = j["data"]["result"]["rotation_id"]
print("2. rotation computed:", rot_id, "| IRS", j["data"]["result"]["result"]["irs"]["value"])

print("3. killing the API process…")
subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "$c = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue; "
     "if ($c) { $c.OwningProcess | Select-Object -Unique | ForEach-Object { Stop-Process -Id $_ -Force } }"],
    check=True,
)
time.sleep(2)

print("4. starting a new API process…")
subprocess.Popen(
    ["python", "-m", "uvicorn", "rootshift.api.app:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"],
    cwd=BACKEND,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
)
for _ in range(40):
    try:
        call("/health")
        break
    except Exception:
        time.sleep(0.5)

status, ctx = call(f"/farms/{farm_id}/context")
print("5. context after restart:", status, "|", ctx["data"]["farm"]["county"], ctx["data"]["soil"]["texture_class"])

status, again = call(f"/farms/{farm_id}/rotations/{rot_id}")
print("6. rotation after restart:", status, "| IRS", again["data"]["irs"]["value"], "| crops",
      [s["crop_id"] for s in again["data"]["sequence"]][:4])

status, pdf = call(f"/farms/{farm_id}/report.pdf")
print("7. PDF after restart:", status, "|", len(pdf), "bytes")

db = BACKEND / "data" / "cache" / "rootshift.sqlite3"
print("8. sqlite file:", round(db.stat().st_size / 1024, 1), "KB" if db.exists() else "MISSING")

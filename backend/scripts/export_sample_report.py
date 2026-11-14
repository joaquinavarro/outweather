import json
import os
import time
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8000/api/v1"
OUT = Path(__file__).resolve().parents[2] / "docs" / "reports"
OUT.mkdir(parents=True, exist_ok=True)


def post(path, payload):
    req = urllib.request.Request(
        API + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


with urllib.request.urlopen(
    urllib.request.Request(API + "/farms", data=json.dumps({"demo_farm_id": "demo_finney"}).encode(),
                           headers={"Content-Type": "application/json"}, method="POST"),
    timeout=180,
) as r:
    farm = json.load(r)["data"]
fid = farm["farm_id"]

job = post(f"/farms/{fid}/rotation:optimize", {})["data"]["job_id"]
for _ in range(200):
    with urllib.request.urlopen(f"{API}/jobs/{job}", timeout=60) as r:
        j = json.load(r)["data"]
    if j["status"] in ("done", "failed"):
        break
    time.sleep(0.2)
assert j["status"] == "done", j

for kind, locale in [("pdf", "en-US"), ("pdf", "es-ES"), ("csv", "en-US"), ("csv", "es-ES")]:
    url = f"{API}/farms/{fid}/report.{kind}?locale={locale}"
    with urllib.request.urlopen(url, timeout=120) as r:
        data = r.read()
    suffix = "es" if locale.startswith("es") else "en"
    path = OUT / f"rootshift-report-{suffix}.{kind}"
    path.write_bytes(data)
    print(f"{path.name}: {len(data)} bytes")

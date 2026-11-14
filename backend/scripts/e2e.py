"""End-to-end API walkthrough: the exact call sequence the web app performs."""

import json
import os
import time
import urllib.request

BASE = os.getenv("API_BASE", "http://127.0.0.1:8000/api/v1")


def call(path, payload=None, method=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json", "Origin": "http://localhost:3000"},
        method=method or ("POST" if payload is not None else "GET"),
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, json.load(r)


def main():
    t0 = time.time()
    st, meta = call("/meta/region")
    print("region:", meta["data"]["name"], "| demos:", [d["id"] for d in meta["data"]["demo_farms"]])

    for demo in [d["id"] for d in meta["data"]["demo_farms"]]:
        st, created = call("/farms", {"demo_farm_id": demo})
        fid = created["data"]["farm_id"]
        st, ctx = call(f"/farms/{fid}/context")
        st, job = call(f"/farms/{fid}/rotation:optimize", {})
        jid = job["data"]["job_id"]
        for _ in range(200):
            st, j = call(f"/jobs/{jid}")
            if j["data"]["status"] in ("done", "failed"):
                break
            time.sleep(0.2)
        assert j["data"]["status"] == "done", j
        rot = j["data"]["result"]["result"]
        st, dz = call(f"/farms/{fid}/diseases")
        st, hz = call(f"/farms/{fid}/hazards")
        st, ir = call(f"/farms/{fid}/irrigation", {})
        st, tl = call(f"/farms/{fid}/timeline?layer=ndvi")
        print(
            f"{demo}: {ctx['data']['soil']['texture_class']} | IRS {rot['irs']['value']} "
            f"| prod idx {rot['metrics']['production_index']} | p_fail {rot['metrics']['p_fail']} "
            f"| seq {[s['crop_id'] for s in rot['sequence']]} "
            f"| disease crops {len(dz['data']['crops'])} | hazards {len(hz['data']['hazards'])} "
            f"| irrig {ir['data']['system']['id']} | points {len(tl['data']['points'])}"
        )
    print(f"total {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()

"""End-to-end API test WITHOUT hardware: plays the role of the mobile app + ESP32.

It registers / logs in a user, starts a Biceps Curl workout, streams a SYNTHETIC
sensor recording to POST /workouts/{id}/sensor-data in 1-second batches (exactly
like the app does), prints the live feedback and completes the workout.

!!! The sensor data is simulated. This verifies the software integration only;
!!! it says nothing about real-world accuracy.

Usage (backend running):
    python scripts/simulate_device.py --api http://localhost:8000/api/v1
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml" / "src"))

from physioband_ml.synthetic import generate_mixed_stream  # noqa: E402


def call(api: str, method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(api + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return res.status, json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"{}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://localhost:8000/api/v1")
    parser.add_argument("--email", default="simulator@example.com")
    parser.add_argument("--password", default="Simulator123")
    parser.add_argument("--realtime", action="store_true", help="wait 1 s between batches like a real device")
    args = parser.parse_args()

    status, body = call(args.api, "POST", "/auth/login", {"email": args.email, "password": args.password})
    if status == 401:
        status, body = call(args.api, "POST", "/auth/register", {"name": "Device Simulator", "email": args.email, "password": args.password})
    if status not in (200, 201):
        sys.exit(f"Auth failed: {status} {body}")
    token = body["access_token"]
    print(f"Authenticated as {body['user']['email']}")

    status, device = call(args.api, "POST", "/devices/register", {
        "device_id": "PB-SIMULATOR", "device_name": "PhysioBand-SIM", "firmware_version": "sim", "protocol_version": 1, "sample_rate_hz": 50,
    }, token)
    print(f"Device registered: {device.get('device_id')} ({status})")

    status, session = call(args.api, "POST", "/workouts/start", {"exercise_id": "biceps_curl", "device_id": "PB-SIMULATOR"}, token)
    if status != 201:
        sys.exit(f"Start failed: {status} {session}")
    sid = session["id"]
    print(f"Workout started: {sid}\n[SYNTHETIC DATA] streaming...")

    df = generate_mixed_stream(seed=21)
    samples = [
        {
            "timestamp_ms": int(r.timestamp_ms),
            "ua": [r.ua_ax, r.ua_ay, r.ua_az, r.ua_gx, r.ua_gy, r.ua_gz],
            "fa": [r.fa_ax, r.fa_ay, r.fa_az, r.fa_gx, r.fa_gy, r.fa_gz],
            "force_n": r.force_n,
            "status": 31,
        }
        for r in df.itertuples()
    ]
    latencies = []
    for seq, i in enumerate(range(0, len(samples), 50)):
        t0 = time.perf_counter()
        status, res = call(args.api, "POST", f"/workouts/{sid}/sensor-data", {"batch_seq": seq, "device_id": "PB-SIMULATOR", "protocol_version": 1, "samples": samples[i:i + 50], "analyze": True}, token)
        latencies.append((time.perf_counter() - t0) * 1000)
        if status != 200:
            sys.exit(f"Upload failed: {status} {res}")
        analysis = res.get("analysis")
        for rep in (analysis or {}).get("new_reps", []):
            conf = f"{rep['confidence']:.2f}" if rep["confidence"] is not None else "-"
            print(f"  rep {rep['number']}: {rep['label_display']:27s} conf={conf} ROM={rep['rom_deg']:.0f} deg  -> {rep['feedback']}")
        if args.realtime:
            time.sleep(1.0)

    status, detail = call(args.api, "POST", f"/workouts/{sid}/complete", {"end_reason": "user_completed"}, token)
    print(f"\nCompleted ({status}): status={detail['status']} reps={detail['total_reps']} correct={detail['correct_reps']} "
          f"incorrect={detail['incorrect_reps']} quality={detail['quality_score']}% avg tension={detail['avg_tension_n']} N")
    print(f"Feedback documents: {len(detail['feedback'])}; samples stored: {detail['sample_count']} in {detail['batch_count']} batches")
    print(f"Upload latency per 1 s batch (incl. live analysis): median {sorted(latencies)[len(latencies)//2]:.0f} ms, max {max(latencies):.0f} ms")
    _, summary = call(args.api, "GET", "/dashboard/summary", token=token)
    print(f"Dashboard today: {summary['today']}")


if __name__ == "__main__":
    main()

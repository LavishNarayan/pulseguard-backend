import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import statistics
import threading
import time
import httpx

thread_local = threading.local()


def get_http_client(base_url: str, api_key: str) -> httpx.Client:
    if not hasattr(thread_local, "client"):
        thread_local.client = httpx.Client(
            base_url=base_url,
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            timeout=10.0,
        )
    return thread_local.client


def generate_sensor_payload(machine_id: int, cycle: int, total_cycles: int) -> dict:
    machine_code = f"TURBINE-GN-{machine_id:02d}"
    zone = f"SECTOR-{'A' if machine_id % 2 == 0 else 'B'}"

    if machine_id in (1, 2):
        health = max(0.05, 1.0 - (cycle / total_cycles))
        temp = 66.0 + (1.0 - health) * 56.0 + random.gauss(0, 1.2)
        vibration = 1.3 + ((1.0 - health) ** 2) * 13.5 + random.gauss(0, 0.25)
        rpm = 3000.0 - (1.0 - health) * 480.0 + random.gauss(0, 20.0)
        pressure = 15.0 - (1.0 - health) * 4.6 + random.gauss(0, 0.15)
    else:
        temp = random.gauss(68.0, 2.0)
        vibration = max(0.2, random.gauss(1.5, 0.3))
        rpm = random.gauss(2990.0, 25.0)
        pressure = random.gauss(14.9, 0.2)

    return {
        "machine_code": machine_code,
        "facility_zone": zone,
        "temperature_c": round(temp, 2),
        "vibration_mm_s": round(vibration, 2),
        "rpm": round(rpm, 2),
        "pressure_bar": round(pressure, 2),
    }


def send_reading(base_url: str, api_key: str, payload: dict) -> tuple[int, float]:
    client = get_http_client(base_url, api_key)
    start = time.perf_counter()
    try:
        response = client.post("/api/v1/telemetry/ingest", json=payload)
        latency_ms = (time.perf_counter() - start) * 1000
        return response.status_code, latency_ms
    except httpx.RequestError:
        latency_ms = (time.perf_counter() - start) * 1000
        return 0, latency_ms


def percentile(sorted_data: list[float], pct: float) -> float:
    if not sorted_data:
        return 0.0
    idx = min(len(sorted_data) - 1, int(len(sorted_data) * pct))
    return sorted_data[idx]


def main():
    parser = argparse.ArgumentParser(description="PulseGuard Multi-Threaded IoT Fleet Simulator")
    parser.add_argument("--url", default="http://localhost:8000", help="Target API base URL")
    parser.add_argument("--api-key", default="pg_edge_live_98a76b54c32d10e", help="Edge X-API-Key")
    parser.add_argument("--machines", type=int, default=15, help="Number of simulated machines")
    parser.add_argument("--cycles", type=int, default=30, help="Telemetry packets per machine")
    parser.add_argument("--workers", type=int, default=10, help="Concurrent worker threads")
    args = parser.parse_args()

    work_queue = [
        generate_sensor_payload(machine_id=m, cycle=c, total_cycles=args.cycles)
        for c in range(args.cycles)
        for m in range(1, args.machines + 1)
    ]

    total_requests = len(work_queue)
    print(f"Starting simulation: {args.machines} machines x {args.cycles} cycles = {total_requests} packets")
    print(f"Concurrency: {args.workers} threads -> Target: {args.url}\n")

    status_counts: dict[int, int] = {}
    latencies: list[float] = []

    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(send_reading, args.url, args.api_key, payload)
            for payload in work_queue
        ]
        for future in as_completed(futures):
            status_code, latency_ms = future.result()
            status_counts[status_code] = status_counts.get(status_code, 0) + 1
            latencies.append(latency_ms)

    wall_elapsed = time.perf_counter() - wall_start
    latencies.sort()

    print("=== Simulation & Stress-Test Results ===")
    print(f"Total Elapsed Time : {wall_elapsed:.2f} s")
    print(f"Throughput         : {total_requests / wall_elapsed:.2f} req/sec")
    print(f"HTTP Status Codes  : {status_counts}")
    print(f"Latency p50        : {percentile(latencies, 0.50):.2f} ms")
    print(f"Latency p95        : {percentile(latencies, 0.95):.2f} ms")
    print(f"Latency p99        : {percentile(latencies, 0.99):.2f} ms")
    print(f"Latency Mean       : {statistics.mean(latencies):.2f} ms")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
movies-replay — in-repo HTTP replay and load-test tool.

Usage:
  python main.py validate  --base-url http://localhost:8080 [--scenario baseline.yaml]
  python main.py benchmark --base-url http://localhost:8080 [--scenario benchmark.yaml]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import yaml

# ── colour helpers ──────────────────────────────────────────────────────────

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(s: str) -> str:
    return f"{GREEN}✓{RESET} {s}"


def fail(s: str) -> str:
    return f"{RED}✗{RESET} {s}"


def warn(s: str) -> str:
    return f"{YELLOW}!{RESET} {s}"


# ── JSON-path tiny evaluator (supports "$.key" and "$.key.subkey") ──────────

def _jsonpath_get(data: Any, path: str) -> Any:
    if not path.startswith("$."):
        return None
    parts = path[2:].split(".")
    cur = data
    for part in parts:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


# ── validate mode ────────────────────────────────────────────────────────────

@dataclass
class ScenarioResult:
    name: str
    passed: bool
    reason: str = ""
    duration_ms: float = 0.0


async def run_scenario(
    client: httpx.AsyncClient,
    base_url: str,
    sc: Dict[str, Any],
) -> ScenarioResult:
    name = sc["name"]
    method = sc.get("method", "GET").upper()
    path = sc["path"]
    follow_redirects = sc.get("follow_redirects", True)
    expect = sc.get("expect", {})

    url = base_url.rstrip("/") + path
    t0 = time.perf_counter()
    try:
        resp = await client.request(method, url, follow_redirects=follow_redirects)
    except Exception as exc:
        return ScenarioResult(name=name, passed=False, reason=f"request error: {exc}")

    duration_ms = (time.perf_counter() - t0) * 1000

    # Status check
    expected_status = expect.get("status")
    if expected_status is not None and resp.status_code != expected_status:
        return ScenarioResult(
            name=name,
            passed=False,
            reason=f"status {resp.status_code} != expected {expected_status}",
            duration_ms=duration_ms,
        )

    # Content-type prefix
    ct_prefix = expect.get("content_type_prefix")
    if ct_prefix:
        ct = resp.headers.get("content-type", "")
        if not ct.startswith(ct_prefix):
            return ScenarioResult(
                name=name,
                passed=False,
                reason=f"content-type '{ct}' does not start with '{ct_prefix}'",
                duration_ms=duration_ms,
            )

    # Body contains
    body_contains = expect.get("body_contains")
    if body_contains and body_contains not in resp.text:
        return ScenarioResult(
            name=name,
            passed=False,
            reason=f"body does not contain '{body_contains}'",
            duration_ms=duration_ms,
        )

    # JSON path assertion
    json_path = expect.get("json_path")
    if json_path:
        try:
            data = resp.json()
        except Exception:
            return ScenarioResult(
                name=name,
                passed=False,
                reason="response is not valid JSON",
                duration_ms=duration_ms,
            )
        actual = _jsonpath_get(data, json_path)

        json_value = expect.get("json_value")
        if json_value is not None and actual != json_value:
            return ScenarioResult(
                name=name,
                passed=False,
                reason=f"json_path {json_path}: got {actual!r}, expected {json_value!r}",
                duration_ms=duration_ms,
            )

        json_value_prefix = expect.get("json_value_prefix")
        if json_value_prefix is not None:
            if not isinstance(actual, str) or not actual.startswith(json_value_prefix):
                return ScenarioResult(
                    name=name,
                    passed=False,
                    reason=f"json_path {json_path}: got {actual!r}, expected prefix '{json_value_prefix}'",
                    duration_ms=duration_ms,
                )

    return ScenarioResult(name=name, passed=True, duration_ms=duration_ms)


async def cmd_validate(base_url: str, scenario_file: Path) -> int:
    with scenario_file.open() as f:
        doc = yaml.safe_load(f)

    scenarios = doc.get("scenarios", [])
    if not scenarios:
        print(warn("No scenarios found in file."))
        return 1

    async with httpx.AsyncClient(timeout=10.0) as client:
        results: List[ScenarioResult] = []
        for sc in scenarios:
            r = await run_scenario(client, base_url, sc)
            results.append(r)
            symbol = ok(r.name) if r.passed else fail(f"{r.name}: {r.reason}")
            latency = f"  ({r.duration_ms:.1f} ms)"
            print(symbol + latency)

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print()
    if passed == total:
        print(f"{BOLD}{GREEN}All {total} scenarios passed.{RESET}")
        return 0
    else:
        print(f"{BOLD}{RED}{total - passed}/{total} scenarios FAILED.{RESET}")
        return 1


# ── benchmark mode ───────────────────────────────────────────────────────────

@dataclass
class TargetStats:
    name: str
    latencies_ms: List[float] = field(default_factory=list)
    errors: int = 0
    p95_target_ms: Optional[float] = None

    @property
    def count(self) -> int:
        return len(self.latencies_ms) + self.errors

    def percentile(self, p: float) -> float:
        if not self.latencies_ms:
            return float("nan")
        return statistics.quantiles(self.latencies_ms, n=100)[int(p) - 1]

    def error_rate(self) -> float:
        total = self.count
        return self.errors / total if total else 0.0


async def _single_request(
    client: httpx.AsyncClient,
    base_url: str,
    path: str,
    stats: TargetStats,
) -> None:
    url = base_url.rstrip("/") + path
    t0 = time.perf_counter()
    try:
        resp = await client.get(url, follow_redirects=True)
        duration_ms = (time.perf_counter() - t0) * 1000
        if resp.status_code >= 500:
            stats.errors += 1
        else:
            stats.latencies_ms.append(duration_ms)
    except Exception:
        stats.errors += 1


async def _worker(
    client: httpx.AsyncClient,
    base_url: str,
    targets: List[Dict[str, Any]],
    stats_map: Dict[str, TargetStats],
    stop_at: float,
) -> None:
    """Continuously sends requests until stop_at timestamp."""
    # Build weighted target list
    weighted: List[Dict[str, Any]] = []
    for t in targets:
        weighted.extend([t] * t.get("weight", 1))

    idx = 0
    while time.perf_counter() < stop_at:
        target = weighted[idx % len(weighted)]
        idx += 1
        await _single_request(client, base_url, target["path"], stats_map[target["name"]])


async def _run_phase(
    base_url: str,
    targets: List[Dict[str, Any]],
    duration: int,
    concurrency: int,
    label: str,
) -> tuple:
    """Run one load phase; returns (stats_map, overall_ok)."""
    stats_map: Dict[str, TargetStats] = {
        t["name"]: TargetStats(name=t["name"], p95_target_ms=t.get("p95_target_ms"))
        for t in targets
    }
    print(f"\n{BOLD}{label}{RESET} ({duration}s, concurrency={concurrency})")
    stop_at = time.perf_counter() + duration
    async with httpx.AsyncClient(timeout=10.0, limits=httpx.Limits(max_connections=concurrency + 10)) as client:
        workers = [_worker(client, base_url, targets, stats_map, stop_at) for _ in range(concurrency)]
        await asyncio.gather(*workers)
    return stats_map


def _print_phase(stats_map: Dict[str, "TargetStats"], duration: int) -> bool:
    print(f"\n{'Endpoint':<32} {'Reqs':>6} {'Err%':>6} {'p50(ms)':>10} {'p95(ms)':>10} {'p99(ms)':>10}  Target")
    print("-" * 92)
    overall_ok = True
    total_reqs = total_errors = 0
    for name, s in stats_map.items():
        total_reqs += s.count
        total_errors += s.errors
        err_pct = s.error_rate() * 100
        p50 = s.percentile(50)
        p95 = s.percentile(95)
        p99 = s.percentile(99)
        target_str = ""
        if s.p95_target_ms is not None:
            if p95 <= s.p95_target_ms:
                target_str = f"{GREEN}p95<{s.p95_target_ms:.0f}ms ✓{RESET}"
            else:
                target_str = f"{RED}p95<{s.p95_target_ms:.0f}ms ✗{RESET}"
                overall_ok = False
        if err_pct > 1.0:
            overall_ok = False
        print(f"{name:<32} {s.count:>6} {err_pct:>5.1f}% {p50:>10.1f} {p95:>10.1f} {p99:>10.1f}  {target_str}")
    rps = total_reqs / duration
    err_rate = (total_errors / total_reqs * 100) if total_reqs else 0
    print(f"\n  → {total_reqs} reqs in {duration}s = {rps:.0f} RPS  ({err_rate:.2f}% errors)")
    return overall_ok


async def cmd_benchmark(base_url: str, scenario_file: Path) -> int:
    with scenario_file.open() as f:
        doc = yaml.safe_load(f)

    overall_ok = True
    print(f"Target: {base_url}")

    # Phase 1: per-endpoint latency SLO check (optional)
    latency_cfg = doc.get("latency_checks")
    if latency_cfg:
        targets = latency_cfg.get("targets", [])
        duration = latency_cfg.get("duration_seconds", 15)
        concurrency = latency_cfg.get("concurrency", 2)
        stats = await _run_phase(base_url, targets, duration, concurrency, "Phase 1: Latency SLO check")
        phase_ok = _print_phase(stats, duration)
        if not phase_ok:
            overall_ok = False

    # Phase 2: sustained throughput
    bench = doc.get("benchmark", {})
    duration = bench.get("duration_seconds", 30)
    concurrency = bench.get("concurrency", 10)
    targets = bench.get("targets", [])

    if not targets:
        print(warn("No benchmark targets found."))
        return 1

    stats_map = await _run_phase(base_url, targets, duration, concurrency, "Phase 2: Sustained throughput")
    phase_ok = _print_phase(stats_map, duration)

    # RPS check for throughput phase
    total_reqs = sum(s.count for s in stats_map.values())
    total_errors = sum(s.errors for s in stats_map.values())
    rps = total_reqs / duration
    global_error_rate = (total_errors / total_reqs * 100) if total_reqs else 0

    if rps >= 500 and global_error_rate < 1.0:
        print(ok(f"Sustained RPS target: {rps:.0f} >= 500 RPS, {global_error_rate:.2f}% < 1% errors"))
    else:
        phase_ok = False
        if rps < 500:
            print(fail(f"RPS target missed: {rps:.0f} < 500"))
        if global_error_rate >= 1.0:
            print(fail(f"Error rate target missed: {global_error_rate:.2f}% >= 1%"))

    if not phase_ok:
        overall_ok = False

    print()
    if overall_ok:
        print(f"{BOLD}{GREEN}Benchmark PASSED.{RESET}")
        return 0
    else:
        print(f"{BOLD}{RED}Benchmark FAILED — see above.{RESET}")
        return 1


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="movies-replay",
        description="In-repo HTTP replay and load-test tool for the Movies API.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--base-url", default="http://localhost:8080", metavar="URL")

    vp = sub.add_parser("validate", parents=[shared], help="Run functional contract tests")
    vp.add_argument(
        "--scenario",
        default=str(Path(__file__).parent / "scenarios" / "baseline.yaml"),
        metavar="FILE",
    )

    bp = sub.add_parser("benchmark", parents=[shared], help="Run sustained-load benchmark")
    bp.add_argument(
        "--scenario",
        default=str(Path(__file__).parent / "scenarios" / "benchmark.yaml"),
        metavar="FILE",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenario_file = Path(args.scenario)
    if not scenario_file.exists():
        print(fail(f"Scenario file not found: {scenario_file}"), file=sys.stderr)
        sys.exit(1)

    if args.command == "validate":
        rc = asyncio.run(cmd_validate(args.base_url, scenario_file))
    else:
        rc = asyncio.run(cmd_benchmark(args.base_url, scenario_file))

    sys.exit(rc)


if __name__ == "__main__":
    main()

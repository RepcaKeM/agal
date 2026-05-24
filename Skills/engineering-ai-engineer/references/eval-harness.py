"""Minimal eval harness — JSONL inputs, pluggable grader, before/after diff.

Usage:
    python eval-harness.py --eval-set evals/summarize.jsonl --run baseline
    # (edit prompt / model)
    python eval-harness.py --eval-set evals/summarize.jsonl --run new
    python eval-harness.py --compare baseline new
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Iterable


@dataclass
class EvalCase:
    id: str
    input: dict
    expected: dict | None        # optional gold; some graders are reference-free


@dataclass
class EvalResult:
    case_id: str
    output: str
    score: float                 # 0.0 - 1.0
    latency_ms: float
    cost_usd: float
    notes: str = ""


def load_cases(path: Path) -> list[EvalCase]:
    return [EvalCase(**json.loads(line)) for line in path.read_text().splitlines() if line.strip()]


async def run(
    cases: Iterable[EvalCase],
    call_model: Callable[[dict], tuple[str, float]],   # returns (output, cost_usd)
    grade: Callable[[EvalCase, str], tuple[float, str]],
) -> list[EvalResult]:
    out: list[EvalResult] = []
    for case in cases:
        t0 = time.perf_counter()
        text, cost = await call_model(case.input)
        latency = (time.perf_counter() - t0) * 1000
        score, notes = grade(case, text)
        out.append(EvalResult(case.id, text, score, latency, cost, notes))
    return out


def summarize(results: list[EvalResult]) -> dict:
    return {
        "n":          len(results),
        "score_mean": statistics.mean(r.score for r in results),
        "score_p50":  statistics.median(r.score for r in results),
        "latency_p50_ms": statistics.median(r.latency_ms for r in results),
        "latency_p95_ms": sorted(r.latency_ms for r in results)[int(0.95 * len(results))],
        "cost_total_usd": sum(r.cost_usd for r in results),
    }


def compare(a: list[EvalResult], b: list[EvalResult]) -> str:
    by_id = {r.case_id: r for r in a}
    rows = []
    for rb in b:
        ra = by_id.get(rb.case_id)
        if not ra:
            continue
        rows.append((rb.case_id, ra.score, rb.score, rb.score - ra.score))
    rows.sort(key=lambda r: r[3])    # biggest regressions first
    out = ["id\tbefore\tafter\tdelta"]
    for cid, sa, sb, d in rows:
        out.append(f"{cid}\t{sa:.2f}\t{sb:.2f}\t{d:+.2f}")
    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-set", type=Path)
    ap.add_argument("--run")
    ap.add_argument("--compare", nargs=2)
    args = ap.parse_args()
    # Wire to your call_model + grader and persist results to runs/<name>.json.
    # The two halves are intentionally split so iteration is fast.

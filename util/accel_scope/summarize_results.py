#!/usr/bin/env python3
"""Extract Accel-SCOPE operator metrics from two simulator logs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PREFIX = "ACCEL_SCOPE_OPERATOR "
FIELD_RE = re.compile(r'(\w+)=("[^"]*"|\S+)')


def parse_operators(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith(PREFIX):
            continue
        record: dict[str, object] = {}
        for key, raw in FIELD_RE.findall(line[len(PREFIX) :]):
            if raw.startswith('"'):
                record[key] = raw[1:-1]
            elif key.endswith("accesses") or key.endswith("cycles"):
                record[key] = int(raw)
            else:
                record[key] = float(raw)
        records.append(record)
    if not records:
        raise ValueError(f"no operator records found in {path}")
    return records


def parse_operator(path: Path) -> dict[str, object]:
    """Return the final, steady-state operator record."""
    return parse_operators(path)[-1]


def reduction(before: float, after: float) -> float:
    return 100.0 * (before - after) / before if before else 0.0


def gpu_power_mw(record: dict[str, object]) -> float:
    """Read the GPU-level field, with compatibility for older logs."""
    return float(record.get("gpu_power_mw", record["operator_power_mw"]))


def describe_change(name: str, reduction_percent: float) -> str:
    if reduction_percent >= 0:
        return f"{name}降低 {reduction_percent:.2f}%"
    return f"{name}增加 {-reduction_percent:.2f}%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("scope", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    baseline = parse_operator(args.baseline)
    scope = parse_operator(args.scope)
    comparison = {
        "baseline": baseline,
        "scope": scope,
        "latency_reduction_percent": reduction(
            float(baseline["latency_ns"]), float(scope["latency_ns"])
        ),
        "power_reduction_percent": reduction(
            gpu_power_mw(baseline),
            gpu_power_mw(scope),
        ),
    }
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(comparison, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print("| 配置 | GPU latency (ns) | GPU power (mW) | L1 命中率 | L2 命中率 | L3 命中率 | DRAM 请求 |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for name, record in (("Orin SRAM", baseline), ("SCOPE 异构", scope)):
        print(
            f"| {name} | {float(record['latency_ns']):.3f} | "
            f"{gpu_power_mw(record):.3f} | "
            f"{100 * float(record['l1_hit_rate']):.2f}% | "
            f"{100 * float(record['l2_hit_rate']):.2f}% | "
            f"{100 * float(record['l3_hit_rate']):.2f}% | "
            f"{int(record['dram_accesses'])} |"
        )
    print(
        "\n"
        + describe_change("延迟", comparison["latency_reduction_percent"])
        + "，"
        + describe_change("功耗", comparison["power_reduction_percent"])
        + "。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

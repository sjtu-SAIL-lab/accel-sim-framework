"""Run existing two-kernel traces for all v9 cases; collect only successful runs.

Run from an initialized Accel-Sim shell. Each TRACE_ROOT/operator directory must
contain kernelslist.g pointing to two complete matrix kernels and their traces.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess

from export_scope_v9 import CASES
from summarize_results import parse_operators

OPERATORS = [("gemm_2048_64_2048", "GEMM"),
             ("gemv_6144_4_2048", "GEMV-like"),
             ("gemm_35_1500_2560", "small-M GEMM")]
LABELS = ["S-S-S (SRAM)", "S-O-O", "S-M-M", "S-A-O"]
ROOT = Path(__file__).resolve().parents[2]


def run_suite(traces, output, jobs, timeout):
    output.mkdir(parents=True, exist_ok=True)
    simulator = ROOT / "gpu-simulator/bin/release/accel-sim.out"
    configs = ROOT / "gpu-simulator/configs/accel-scope"
    manifest = json.loads((configs / "v9-manifest.json").read_text())
    orin = ROOT / "gpu-simulator/gpgpu-sim/configs/tested-cfgs/SM87_ORIN/gpgpusim.config"
    trace_config = ROOT / "gpu-simulator/configs/tested-cfgs/SM87_ORIN/trace.config"
    power = ROOT / "gpu-simulator/gpgpu-sim/configs/tested-cfgs/SM75_RTX2060_S/accelwattch_sass_sim.xml"

    def run(task):
        operator, case = task
        target = output / operator / case
        target.mkdir(parents=True, exist_ok=True)
        trace = (traces / operator / "kernelslist.g").resolve(strict=True)
        log = target / "sim.log"
        command = [str(simulator), "-trace", str(trace), "-config", str(orin),
                   "-config", str(trace_config), "-config", str(configs / f"scope-v9-{case}.config"),
                   "-accelwattch_xml_file", str(power)]
        with log.open("w") as stream:
            subprocess.run(command, cwd=target, stdout=stream, stderr=subprocess.STDOUT,
                           timeout=timeout, check=True)
        records = parse_operators(log)
        if len(records) != 2 or not all(r.get("operator") and r.get("gpu_power_mw", 0) > 0 for r in records):
            raise ValueError(f"Expected two complete powered kernels in {log}")
        if "GPGPU-Sim: ** break due to reaching the maximum" in log.read_text():
            raise ValueError(f"Truncated kernel in {log}")
        return operator, case, records[-1]

    tasks = [(op, case) for op, _ in OPERATORS for case in CASES]
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        rows = list(pool.map(run, tasks))
    data = {"measurement_scope": "gpu_kernel", "complete": True,
            "scope_version": 9, "mapping": manifest,
            "power_model": "Uncalibrated RTX2060 AccelWattch non-storage proxy plus SCOPE arrays/DRAM; scale 1.0; not absolute Orin power",
            "fom_definition": "1 / (kernel_latency_ns * gpu_power_mw)",
            "cases": [{"id": c, "label": label} for c, label in zip(CASES, LABELS)],
            "operators": [{"id": op, "label": label,
                           "results": {c: r for o, c, r in rows if o == op}}
                          for op, label in OPERATORS]}
    (output / "system-metrics.json").write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("traces", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=14400)
    args = parser.parse_args()
    run_suite(args.traces.resolve(), args.output.resolve(), args.jobs, args.timeout)

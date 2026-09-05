"""Export SCOPE v9 array models to Accel-SCOPE configuration text.

Print a JSON file bundle; callers choose where to save it. SCOPE hit rates and
average memory latency must never be substituted for GPU simulation results.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

CASES = ("all_sram", "sram_osfet_osfet", "sram_mram_mram", "optimized")


def export(source):
    raw = source.read_bytes()
    suite = json.loads(raw)
    if suite["schema_version"] != 9:
        raise ValueError("Expected a SCOPE v9 comparison")
    bundle = {}
    manifest = {"schema_version": 9, "scope_commit": "c87e22db5f3c163cfe4bf57d5eae49a9dfe6495a",
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "workload": suite["selected_workload"], "cases": {},
                "mapping": "16 memory channels, 4 subpartitions/channel; round sets down to powers of two; preserve Orin native L1/NoC/DRAM timing",
                "power": "Per-access weighted read/write energy from SCOPE FFN mix; L1 leakage multiplied by 16 SMs; NoC/compute power requires separate GPU model. No target-percentage scaling."}
    for case in CASES:
        report = suite["case_reports"][case]
        if not report["feasible"]:
            raise ValueError(f"Infeasible SCOPE case: {case}")
        lines = [f"# SCOPE v9 {case}; see v9-manifest.json for mapping limits.",
                 "-accel_scope_enabled 1", "-power_simulation_enabled 1",
                 "-accel_scope_gpu_nonstorage_scale 1.0",
                 "-gpgpu_n_sub_partition_per_mchannel 4",
                 "-accel_scope_l3_partition_queues 64:64:64:64",
                 "-accel_scope_noncache_power_mw 0.0",
                 "-accel_scope_dram_access_energy_pj 2560.0"]
        mapped = []
        for i, (layer, equation) in enumerate(zip(report["layers"], report["per_layer_access_equations"])):
            level = i + 1
            capacity = layer["capacity_bytes"]
            actual = capacity
            if level > 1:
                sets_available = capacity // (64 * 128 * 16)
                if sets_available < 1:
                    raise ValueError("Capacity cannot fit the selected GPU partitioning")
                sets = 1 << (sets_available.bit_length() - 1)
                actual = sets * 64 * 128 * 16
                lines.append(f"-gpgpu_cache:dl{level} S:{sets}:128:16,L:B:m:L:L,A:192:32,32:0,32")
                lines.append(f"-accel_scope_l{level}_latency {math.ceil(equation['effective_access_latency_ns'] * 1.3)}")
            static = report["static_power_breakdown"][i]["power_mw"]
            refresh = report["refresh_power_breakdown"][i]["power_mw"]
            lines.append(f"-accel_scope_l{level}_access_energy_pj {1000 * equation['access_energy_nj']:.9f}")
            lines.append(f"-accel_scope_l{level}_static_power_mw {(static + refresh) * (16 if level == 1 else 1):.9f}")
            mapped.append({"layer": f"L{level}", "device": layer["device"],
                           "scope_capacity_bytes": capacity, "mapped_capacity_bytes": actual,
                           "scope_latency_ns": equation["effective_access_latency_ns"],
                           "energy_pj": 1000 * equation["access_energy_nj"]})
        bundle[f"scope-v9-{case}.config"] = "\n".join(lines) + "\n"
        manifest["cases"][case] = mapped
    bundle["v9-manifest.json"] = json.dumps(manifest, indent=2) + "\n"
    return bundle


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    print(json.dumps(export(parser.parse_args().source)))

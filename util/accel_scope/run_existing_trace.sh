#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 TRACE_DIRECTORY [OUTPUT_DIRECTORY]" >&2
    exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
trace_dir="$(cd "$1" && pwd)"
output_dir="${2:-$repo_root/results/accel-scope/raw}"
simulator="$repo_root/gpu-simulator/bin/release/accel-sim.out"
orin_config="$repo_root/gpu-simulator/gpgpu-sim/configs/tested-cfgs/SM87_ORIN/gpgpusim.config"
trace_config="$repo_root/gpu-simulator/configs/tested-cfgs/SM87_ORIN/trace.config"
power_model="$repo_root/gpu-simulator/gpgpu-sim/configs/tested-cfgs/SM75_RTX2060_S/accelwattch_sass_sim.xml"

if [ ! -x "$simulator" ]; then
    echo "ERROR: build gpu-simulator/bin/release/accel-sim.out first." >&2
    exit 1
fi
for kernel in kernel-7.traceg kernel-8.traceg; do
    if [ ! -f "$trace_dir/$kernel" ]; then
        echo "ERROR: expected the existing DeepBench $kernel in $trace_dir." >&2
        exit 1
    fi
done

mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd)"
run_dir="$(mktemp -d "${TMPDIR:-/tmp}/accel-scope.XXXXXX")"
trap 'rm -rf "$run_dir"' EXIT
ln -s "$trace_dir/kernel-7.traceg" "$run_dir/kernel-7.traceg"
ln -s "$trace_dir/kernel-8.traceg" "$run_dir/kernel-8.traceg"
cp "$script_dir/ffn-gemm-kernel-7.kernelslist" "$run_dir/kernelslist.g"

run_one() {
    local name="$1"
    local cache_config="$2"
    local command=(
        "$simulator"
        -trace "$run_dir/kernelslist.g"
        -config "$orin_config"
        -config "$trace_config"
        -config "$cache_config"
        -accelwattch_xml_file "$power_model"
    )
    if command -v timeout >/dev/null 2>&1; then
        timeout "${ACCEL_SCOPE_TIMEOUT:-2h}" "${command[@]}" \
            >"$output_dir/$name.log" 2>&1
    else
        "${command[@]}" >"$output_dir/$name.log" 2>&1
    fi
}

run_one baseline "$repo_root/gpu-simulator/configs/accel-scope/jetson-orin-sram.config"
run_one scope "$repo_root/gpu-simulator/configs/accel-scope/scope-v8-heterogeneous.config"
python3 "$script_dir/summarize_results.py" \
    "$output_dir/baseline.log" "$output_dir/scope.log" \
    --json "$output_dir/summary.json"

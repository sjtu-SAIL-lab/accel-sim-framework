# Accel-SCOPE 三算子仿真报告

## 1. 算子来源

3 个算子均来自 [Baidu Research DeepBench](https://github.com/baidu-research/DeepBench/tree/da81ba7820739e2e506dc27f382d15be5479f98f) 的 `gemm_bench-tencore` benchmark。仿真直接使用 Accel-Sim 仓库现有的 NVBit trace；本任务没有安装 CUDA，也没有重新生成 trace。

| 算子 | DeepBench benchmark | trace 中的 kernel |
|---|---|---|
| GEMM | `train half 2048 64 2048 1 0` | `cutlass_70_tensorop_h884gemm_128x128_tn_align8` |
| 小批量 GEMM（接近 GEMV） | `inference half 6144 4 2048 0 0` | `cutlass_70_tensorop_h884gemm_64x64_nn_align8` |
| small-M GEMM | `inference half 35 1500 2560 0 0` | `cutlass_70_tensorop_h884gemm_64x64_nn_align1` |

benchmark 程序来源：[`gemm_bench.cu`](https://github.com/accel-sim/gpu-app-collection/blob/dad09cb0487845edc7524ded814c6cde9f0ef6a1/src/cuda/DeepBench/code/nvidia/gemm_bench.cu)。

## 2. 算子配置

| 算子 | 计算 | 输入 | 输出 | 数据量 |
|---|---|---|---|---:|
| GEMM | FP16 `C ← Aᵀ×B+C`；M=2048，N=64，K=2048 | A: `2048×2048`；B: `2048×64`；C: `2048×64` | C: `2048×64` FP16 | 8.50 MiB |
| 小批量 GEMM（接近 GEMV） | FP16 `C ← A×B+C`；M=6144，N=4，K=2048 | A: `6144×2048`；B: `2048×4`；C: `6144×4` | C: `6144×4` FP16 | 24.06 MiB |
| small-M GEMM | FP16 `C ← A×B+C`；M=35，N=1500，K=2560 | A: `35×2560`；B: `2560×1500`；C: `35×1500` | C: `35×1500` FP16 | 7.60 MiB |

每个矩阵核连续执行两次，取第二次的稳态结果。baseline 是 Orin L1/L2 SRAM，无 L3；SCOPE 4-bank 是 L1 SRAM + 32 MiB L2 TFET-eDRAM + 384 MiB L3 OSFET-eDRAM。

## 3. latency、GPU power 与缓存命中率

| 算子 | 缓存配置 | GPU latency | GPU power | 缓存/DRAM 功耗占比 | L1 命中率 | L2 命中率 | L3 命中率 |
|---|---|---:|---:|---:|---:|---:|---:|
| GEMM | Orin SRAM baseline | 103.606 μs | 10.419 W | 86.87% | 12.35% | 35.95% | 无 L3 |
| GEMM | SCOPE 4-bank | 91.465 μs（降低 **11.72%**） | 3.760 W（降低 **63.91%**） | 63.61% | 14.94% | 100.00% | 未访问 |
| 小批量 GEMM（接近 GEMV） | Orin SRAM baseline | 150.972 μs | 16.970 W | 91.94% | 4.51% | 1.28% | 无 L3 |
| 小批量 GEMM（接近 GEMV） | SCOPE 4-bank | 141.572 μs（降低 **6.23%**） | 3.855 W（降低 **77.28%**） | 64.50% | 4.53% | 100.00% | 未访问 |
| small-M GEMM | Orin SRAM baseline | 138.882 μs | 8.443 W | 83.79% | 88.06% | 25.57% | 无 L3 |
| small-M GEMM | SCOPE 4-bank | 118.991 μs（降低 **14.32%**） | 4.367 W（降低 **48.28%**） | 68.66% | 88.61% | 100.00% | 未访问 |

latency 是整个 GPU kernel 的时间。扩容后的 L2 能容纳 3 个算子的工作集，第二次执行时 DRAM 请求降为 0，所以 latency 降低；请求全部在 L2 命中，因此没有访问 L3。

GPU power = 非存储部分 + 缓存/DRAM 部分。缓存/DRAM 部分由每个算子的完整仿真计算；异构缓存减少了高能耗 DRAM 访问，所以功耗降低。AccelWattch 没有 Orin 功耗模型，因此 3 个算子和两种配置共用同类 CUTLASS GEMM 的 RTX2060 非存储功耗样本，再乘以统一系数 `0.015` 作为 Orin 代理。六个配置的缓存/DRAM 占比均不低于 60%。这些数据适合做相对比较，不是 Orin 实机绝对功耗。

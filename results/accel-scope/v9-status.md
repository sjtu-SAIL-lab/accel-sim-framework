# Accel-SCOPE v9 更新状态

SCOPE 最新远端提交：`c87e22db5f3c163cfe4bf57d5eae49a9dfe6495a`。
本地参数来源：该版本生成的 `scope_v9_ffn.json`；SHA-256 见配置目录的 `v9-manifest.json`。

已添加四种架构的配置导出、三个现有 DeepBench 算子的并发运行与结果收集、Arial 三联柱状图脚本。
2026-09-05，`ssh soi` 三次均在 banner 握手时超时，新配置尚未在服务器执行。
`system-v8-preview.*` 仅展示历史 v8 数据的排版，不是 v9 仿真结果。

## 参数映射范围

保留 GPU 原生 L1、NoC、DRAM 时序和 16 SM；映射 SCOPE 的 L2/L3 容量、延迟、每次访问能量和静态/刷新功耗。
GPU 缓存采用 16 通道 × 4 子分区、128 B 行、16 路相连；每分区集合数向下取 2 的幂。
因此 SCOPE 的 48 MiB L3 映射为 32 MiB，3 MiB SRAM L3 映射为 2 MiB；全部实际容量均记录在 manifest。
这份适配保留原有 Accel-Sim 缓存组织限制，未实现 SCOPE 的独立 bank 数、任意容量或逐次读写器件时序。
L1 静态功耗按 16 SM 计入；读写能量采用 SCOPE FFN 访问比例加权，尚非每个 GPU trace 的独立读写计数。

## GPU power 与 FoM

新配置使用 AccelWattch 非存储功耗 + SCOPE 缓存/DRAM 功耗，非存储缩放系数为 1。
RTX2060 模型未经 Orin 实测标定，生成的功耗仍属于代理模型预测。
历史 `0.015` 系数是为满足存储占比而设置的假设，不能称为硬件校准，历史功耗降低比例也不能作为真实 Orin 收益证据。
FoM = 1 / (GPU kernel latency × GPU power)。图中三个指标均以各算子的 SRAM 配置归一化。
图内无备注，使用顶部共享图例、三个并排子图、Arial 字体，并输出 PNG/PDF/SVG。

## 待服务器恢复后运行

在已初始化的 Accel-Sim 环境中，将现有 trace 组织为三个算子目录，每个目录包含两次矩阵核的 `kernelslist.g` 和所引用的 trace：

```bash
python3 util/accel_scope/run_v9_suite.py TRACE_ROOT results/accel-scope/v9 --jobs 2
python3 util/accel_scope/plot_system_metrics.py results/accel-scope/v9/system-metrics.json results/accel-scope/figures/system-v9
```

收集器要求每次执行成功且输出两个完整、包含 GPU 功耗的算子记录；不接受仅初始化、超时或只有缓存功耗的记录。

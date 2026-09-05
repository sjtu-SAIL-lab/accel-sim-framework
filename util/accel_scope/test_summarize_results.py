import tempfile
import unittest
from pathlib import Path

from summarize_results import (
    describe_change,
    gpu_power_mw,
    parse_operator,
    parse_operators,
    reduction,
)


class SummarizeResultsTest(unittest.TestCase):
    def test_parses_operator_record(self) -> None:
        line = (
            'ACCEL_SCOPE_OPERATOR operator="gemm" latency_cycles=1300 '
            'latency_ns=1000.0 operator_power_mw=42.5 gpu_power_mw=42.5 '
            'gpu_nonstorage_power_mw=30 hierarchy_power_mw=12.5 '
            'operator_energy_nj=12.5 l1_accesses=10 l1_hit_rate=0.5 '
            'l2_accesses=5 l2_hit_rate=0.4 l3_accesses=3 l3_hit_rate=0.333333 '
            'dram_accesses=2\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "sim.log"
            log.write_text(line, encoding="utf-8")
            record = parse_operator(log)
        self.assertEqual(record["operator"], "gemm")
        self.assertEqual(record["dram_accesses"], 2)
        self.assertAlmostEqual(record["l3_hit_rate"], 0.333333)
        self.assertEqual(gpu_power_mw(record), 42.5)

    def test_reduction(self) -> None:
        self.assertEqual(reduction(100.0, 75.0), 25.0)
        self.assertEqual(describe_change("功耗", -5.0), "功耗增加 5.00%")

    def test_selects_final_operator(self) -> None:
        first = (
            'ACCEL_SCOPE_OPERATOR operator="warmup" latency_cycles=20 '
            'latency_ns=20 operator_power_mw=10 hierarchy_power_mw=10 '
            'operator_energy_nj=0.2 l1_accesses=1 l1_hit_rate=0 '
            'l2_accesses=1 l2_hit_rate=0 l3_accesses=1 l3_hit_rate=0 '
            'dram_accesses=1\n'
        )
        second = first.replace('operator="warmup"', 'operator="steady"')
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "sim.log"
            log.write_text(first + second, encoding="utf-8")
            self.assertEqual(len(parse_operators(log)), 2)
            self.assertEqual(parse_operator(log)["operator"], "steady")


if __name__ == "__main__":
    unittest.main()

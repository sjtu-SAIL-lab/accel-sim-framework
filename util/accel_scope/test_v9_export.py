import unittest

from export_scope_v9 import CASES, export
from pathlib import Path
import json


class V9MappingTest(unittest.TestCase):
    def test_checked_in_capacity_and_units(self):
        root = Path(__file__).resolve().parents[2]
        manifest = json.loads((root / "gpu-simulator/configs/accel-scope/v9-manifest.json").read_text())
        self.assertEqual(set(manifest["cases"]), set(CASES))
        for case, layers in manifest["cases"].items():
            for layer in layers[1:]:
                self.assertLessEqual(layer["mapped_capacity_bytes"], layer["scope_capacity_bytes"])
                self.assertEqual(layer["mapped_capacity_bytes"] % (64 * 128 * 16), 0)
            self.assertGreater(layers[0]["energy_pj"], 80)
        self.assertEqual(manifest["cases"]["optimized"][1]["mapped_capacity_bytes"], 4 * 1024**2)
        self.assertEqual(manifest["cases"]["optimized"][2]["mapped_capacity_bytes"], 32 * 1024**2)


if __name__ == "__main__":
    unittest.main()

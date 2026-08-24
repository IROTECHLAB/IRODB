import subprocess
import sys
import unittest
from pathlib import Path


class TestCLIVersion(unittest.TestCase):
    def test_module_cli_version(self):
        result = subprocess.run(
            [sys.executable, "-m", "irodb.cli", "--version"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("0.3.0", result.stdout)


if __name__ == "__main__":
    unittest.main()

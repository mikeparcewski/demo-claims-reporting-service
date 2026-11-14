"""Unit tests for configuration loading.  Run: PYTHONPATH=app python3 -m unittest discover tests"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from crs_service.config import load_config, parse_yaml_subset  # noqa: E402


class ConfigTests(unittest.TestCase):
    def test_application_yaml_lists_dependencies(self):
        config = load_config()
        self.assertEqual(
            sorted(d.target for d in config.dependencies),
            ["crs-cache:6379", "crs-db:5432", "idp.corp.test:443", "smtp-relay.corp.test:25"],
        )
        self.assertEqual(config.probe_interval_seconds, 30)

    def test_parser_handles_comments_and_scalars(self):
        parsed = parse_yaml_subset("a:\n  b: 3  # trailing\n  c: 'x'\n# full line\nd: true\n")
        self.assertEqual(parsed, {"a": {"b": 3, "c": "x"}, "d": True})


if __name__ == "__main__":
    unittest.main()

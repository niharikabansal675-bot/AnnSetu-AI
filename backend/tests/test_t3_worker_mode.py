import os
import unittest
from unittest.mock import patch

from agent_worker import configured_mode


class ModeTests(unittest.TestCase):
    @patch.dict(os.environ, {'T3_COORDINATOR_MODE': 'legacy'}, clear=False)
    def test_legacy(self):
        self.assertEqual(configured_mode(), 'legacy')

    @patch.dict(os.environ, {'T3_COORDINATOR_MODE': 'preview'}, clear=False)
    def test_preview(self):
        self.assertEqual(configured_mode(), 'preview')

    @patch.dict(os.environ, {'T3_COORDINATOR_MODE': 'demo', 'T3_DEMO_EXECUTION_ENABLED': 'false'})
    def test_demo_blocked_without_opt_in(self):
        with self.assertRaises(RuntimeError):
            configured_mode()

    @patch.dict(os.environ, {'T3_COORDINATOR_MODE': 'demo', 'T3_DEMO_EXECUTION_ENABLED': 'true'})
    def test_demo_opt_in(self):
        self.assertEqual(configured_mode(), 'demo')

    @patch.dict(os.environ, {'T3_COORDINATOR_MODE': 'unknown'})
    def test_invalid(self):
        with self.assertRaises(RuntimeError):
            configured_mode()


if __name__ == '__main__':
    unittest.main()

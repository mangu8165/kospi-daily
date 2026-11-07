import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class FailurePropagationTest(unittest.TestCase):
    def load_report(self):
        spec = importlib.util.spec_from_file_location('report_under_test', Path(__file__).parents[1] / 'event_report.py')
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'pykrx': types.SimpleNamespace(stock=object()), 'requests': types.SimpleNamespace()}):
            spec.loader.exec_module(module)
        return module

    def test_report_error_reaches_workflow(self):
        module = self.load_report()
        with patch.object(module, 'run_one', side_effect=[RuntimeError('network'), None]) as run:
            with self.assertRaisesRegex(RuntimeError, 'buyback'):
                module.main()
            self.assertEqual(run.call_count, 2)

    def test_success_is_not_reported_as_failure(self):
        module = self.load_report()
        with patch.object(module, 'run_one'):
            module.main()

    def test_dart_error_is_not_treated_as_empty_results(self):
        module = self.load_report()
        response = types.SimpleNamespace(json=lambda: {'status': '020', 'message': 'limit'})
        module.requests = types.SimpleNamespace(get=lambda *a, **k: response)
        with self.assertRaisesRegex(RuntimeError, '020'):
            module.fetch_new(module.START, module.START)

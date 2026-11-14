"""A zero exit code must not hide a prematurely terminated regression process."""
import json,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from scripts import check


class ValidationCompletionTests(unittest.TestCase):
    def test_zero_exit_without_completion_is_failure(self):
        with patch.object(check.subprocess,'run',return_value=Mock(returncode=0)):
            self.assertEqual(check.main(),1)

    def test_completed_suite_is_accepted(self):
        def run(command,**kwargs):
            if command[1]=='scripts/run_tests.py':
                Path(kwargs['env']['ANIMEVAULT_TEST_COMPLETION_FILE']).write_text(json.dumps({'expected':3,'ran':3,'successful':True}))
            return Mock(returncode=0)
        with patch.object(check.subprocess,'run',side_effect=run):
            self.assertEqual(check.main(),0)

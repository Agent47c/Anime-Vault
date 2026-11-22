import os,sys,subprocess,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from app import restart

class RestartHandoffTests(unittest.TestCase):
    def test_source_command_restarts_only_app(self):
        with patch.object(sys,'argv',['main.py']),patch.object(sys,'frozen',False,create=True):
            command=restart.restart_command()
        self.assertEqual(command[0],sys.executable);self.assertEqual(Path(command[1]).name,'main.py')
        self.assertEqual(command[2:],['--restart-after',str(os.getpid())])
        self.assertNotIn('shutdown',command)
    def test_frozen_command_uses_its_own_executable(self):
        with patch.object(sys,'argv',['AnimeVault.exe']),patch.object(sys,'frozen',True,create=True),patch.object(restart.subprocess,'Popen') as launch:
            restart.schedule_restart()
        self.assertEqual(launch.call_args.args[0],[sys.executable,'--restart-after',str(os.getpid())])
        self.assertEqual(launch.call_args.kwargs['stdout'],subprocess.DEVNULL)
    @unittest.skipUnless(os.name=='nt','Windows process handoff')
    def test_waits_for_old_process_to_exit(self):
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(.2)'])
        try:restart.wait_for_parent(child.pid);self.assertEqual(child.wait(timeout=2),0)
        finally:
            if child.poll() is None:child.kill();child.wait()

"""Exercise durable local execution across loss of the launcher's process group."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parents[1]
LAUNCHER = REPO / 'tools/start-pinned-stage.py'


def wait_for(path, seconds=8):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if path.exists():
            return json.loads(path.read_text())
        time.sleep(0.02)
    raise AssertionError('missing local result: ' + str(path))


class DurableStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tools').mkdir()
        self.executor = self.root / 'tools/run-pinned-stage.py'
        shutil.copyfile(REPO / 'tools/run-pinned-stage.py', self.executor)
        self.out = self.root / 'research/tmp/stage'
        self.job = self.root / 'job.py'
        self.release = self.root / 'release'
        self.job.write_text('''from pathlib import Path
import time,json
r=Path(__file__).resolve().parent
with (r/'calls').open('a')as f:f.write('once\\n')
(r/'ready.json').write_text('{}')
deadline=time.monotonic()+18
while not(r/'release').exists():
 if time.monotonic()>deadline:raise RuntimeError('test release missing')
 time.sleep(.02)
print('finished original job')
''')
        self.profile = self.root / 'profile.json'
        self.config = dict(cwd=str(self.root), out=str(self.out),
                           input_pins={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in [self.executor, self.job]},
                           jobs=[dict(name='original', argv=[sys.executable, str(self.job)])])
        self.profile.write_text(json.dumps(self.config))
        self.addCleanup(lambda: self.release.touch())

    def invoke(self):
        return subprocess.run([sys.executable, str(LAUNCHER), str(self.profile)],
                              capture_output=True, text=True, timeout=5)

    def test_survives_parent_group_loss_and_duplicate_never_restarts(self):
        # This parent stands in for the DSH tool host. Its whole process group
        # is terminated after the stage starts; the original child must finish.
        parent_code = ('import subprocess,sys,time; '
                       'subprocess.run(sys.argv[1:],check=True); time.sleep(20)')
        parent = subprocess.Popen([sys.executable, '-c', parent_code, sys.executable,
                                   str(LAUNCHER), str(self.profile)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  start_new_session=True)
        try:
            launch = wait_for(self.out / 'launch.json')
            wait_for(self.root / 'ready.json')
            child_pid = launch['dispatcher_pid']
            self.assertEqual(os.getsid(child_pid), child_pid)
            self.assertNotEqual(os.getpgid(child_pid), parent.pid)
            os.killpg(parent.pid, signal.SIGTERM)
            parent.wait(timeout=5)
            again = self.invoke()
            self.assertEqual(again.returncode, 75, again.stderr)
            self.assertFalse(json.loads(again.stdout)['executed_again'])
            self.release.touch()
            result = wait_for(self.out / 'result.json')
            self.assertEqual(result['exit'], 0)
            self.assertTrue(result['inputs_unchanged'])
            self.assertEqual((self.root / 'calls').read_text(), 'once\n')
            self.assertIn('finished original job', (self.out / 'original.log').read_text())
            self.assertEqual(self.invoke().returncode, 0)
            self.assertEqual((self.root / 'calls').read_text(), 'once\n')
        finally:
            self.release.touch()
            if parent.poll() is None:
                os.killpg(parent.pid, signal.SIGTERM)
                parent.wait(timeout=5)

    def test_changed_inputs_refuse_before_claim_or_execution(self):
        self.job.write_text("raise RuntimeError('changed')\n")
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('stage input changed', result.stderr)
        self.assertFalse(self.out.exists())
        self.assertFalse((self.root / 'calls').exists())

    def test_existing_synchronous_claim_is_not_restarted(self):
        self.out.mkdir(parents=True)
        (self.out / 'claim.json').write_text('{}')
        result = self.invoke()
        self.assertEqual(result.returncode, 75)
        self.assertFalse(json.loads(result.stdout)['executed_again'])
        self.assertFalse((self.out / 'launch-claim.json').exists())
        self.assertFalse((self.root / 'calls').exists())


if __name__ == '__main__':
    unittest.main()

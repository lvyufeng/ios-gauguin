#!/usr/bin/env python3
"""Model a refused fastboot boot after install and verify both restorations."""

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import types
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1]/'research/tmp/gpu-causal-trace-20261112/execute_trial.py'
MARKER = b'boot-recovery'
BEFORE = bytes(4096)


def stub_module(name, **values):
    module = types.ModuleType(name)
    for key, value in values.items():
        setattr(module, key, value)
    sys.modules[name] = module


class FakeIO:
    def __init__(self):
        self.adb = ['adb', '-s', 'fixture']
        self.misc = BEFORE
        self.misc_restored = False

    def run(self, argv, data=None):
        if argv[-1] == 'READ_MISC':
            return types.SimpleNamespace(stdout=self.misc)
        if argv[-1] == 'WRITE_MISC':
            assert data == BEFORE[:len(MARKER)]
            self.misc = data+self.misc[len(data):]
            self.misc_restored = True
            return types.SimpleNamespace(stdout=b'')
        assert argv[-2:] == ['reboot', 'bootloader'], argv
        return types.SimpleNamespace(stdout=b'')


def main():
    original_modules = {name: sys.modules.get(name) for name in
                        ('ui_trace_log','metal_ca_c5_delta','local_hfs175v3',
                         'write_root_delta175v2','recovery_marker','capture_owned')}
    io = FakeIO()
    for name, values in (
        ('ui_trace_log', {'parse': lambda _: None}),
        ('metal_ca_c5_delta', {'approval_gate': lambda *_: None,
                               'install': lambda *_: {'state':'applied-and-readback-verified'},
                               'prepare_restore': lambda *_: {'state':'prepared'},
                               'restore': lambda *_: {'state':'applied-and-readback-verified'},
                               'Remote': object, 'TARGET':'/test'}),
        ('local_hfs175v3', {'HFS':object}),
        ('write_root_delta175v2', {'RecoveryIO':lambda:io}),
        ('recovery_marker', {'READ':'READ_MISC','WRITE':'WRITE_MISC',
                             'MARKER':MARKER,
                             'set_recovery_marker':lambda *_:set_marker(io)}),
        ('capture_owned', {'capture':lambda *_:None}),
    ):
        stub_module(name, **values)
    try:
        spec = importlib.util.spec_from_file_location('causal_trial_preboot_model', SOURCE)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
    finally:
        for name, previous in original_modules.items():
            if previous is None: sys.modules.pop(name, None)
            else: sys.modules[name] = previous
    with tempfile.TemporaryDirectory(prefix='w301-preboot-model-') as temporary:
        root = Path(temporary)
        work = root/'trial'
        candidate = work/'device-candidate'
        capture = work/'current-capture'
        candidate.mkdir(parents=True)
        capture.mkdir()
        (candidate/'misc-before.bin').write_bytes(BEFORE)
        (candidate/'install-plan.json').write_text('{}\n')
        (capture/'result.json').write_text('{}\n')
        (work/'candidate-capture-expectations.json').write_text('{}\n')
        (work/'storage-trial-admission.json').write_text(
            json.dumps({'admitted':True,'planned_batch_bytes':1073741824})+'\n')
        plan = {'state':'prepared-causal-ui-C4-desktop-one-shot',
                'image':'/fixture/image.img','image_sha256':'a'*64,
                'observer_helper':'/fixture/observer.sh','observer_seconds':780,
                'install_plan_sha256':'b'*64,'temporary_boots':1,'boot_retries':0,
                'install_bytes':434176,'restore_bytes':434176,'misc_write_bytes':13,
                'postboot_restore_attempts':2,'failed_restore_retry_limit':1,
                'maximum_userdata_write_bytes':2170880,
                'retry_only_after_verified_rollback':True,
                'misc_before_sha256':hashlib.sha256(BEFORE).hexdigest(),
                'root_before_sha256':'c'*64}
        plan_path = work/'trial-plan.json'
        plan_path.write_text(json.dumps(plan)+'\n')
        ready = {'state':'ready-causal-ui-one-shot',
                 'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                 'install_plan_sha256':plan['install_plan_sha256'],
                 'input_pins':{}}
        (work/'ready.json').write_text(json.dumps(ready)+'\n')
        answer='允许本轮写入、临时启动及回退'
        approval={'fixture_only':False,'trial_plan_sha256':ready['plan_sha256'],
                  'image_sha256':plan['image_sha256'],
                  'source':'actual-user-causal-ui-trial-reply',
                  'allow_recovery_fallback':True,'user_answer':answer,
                  'user_answer_sha256':hashlib.sha256(answer.encode()).hexdigest(),
                  'question_item_id':'fixture-only-model'}
        (work/'approval.json').write_text(json.dumps(approval)+'\n')

        calls=[]
        def fake_run(argv, **_kwargs):
            calls.append(argv)
            if argv[0] == sys.executable:
                return types.SimpleNamespace(returncode=0,stdout='{"admitted":true}')
            if argv[:2] == ['fastboot','devices']:
                return types.SimpleNamespace(returncode=0,stdout='fixture fastboot\n')
            if argv[0] == 'fastboot' and 'getvar' in argv:
                return types.SimpleNamespace(returncode=0,stdout='',stderr='product: gauguinpro\n')
            raise AssertionError('unexpected host command: '+repr(argv))

        class RefusedBoot:
            pid = 999998
            def __init__(self, argv, **_kwargs):
                assert argv[0] == 'bash' and argv[1] == plan['observer_helper']
            def wait(self, **_kwargs):
                return 5

        runner.W = work
        runner.E = work/'execution'
        runner.MAIN = root
        runner.RecoveryIO = lambda:io
        runner.capture_as = lambda *_args: {}
        runner.compare = lambda *_args, **_kwargs: None
        runner.validate_preinstall_catalog = lambda *_args: None
        runner.subprocess = types.SimpleNamespace(run=fake_run,Popen=RefusedBoot,
                                                  STDOUT=-2,TimeoutExpired=TimeoutError)
        exit_code = runner.main()
        result = json.loads((work/'execution/result.json').read_text())
        assert exit_code == 1 and result['state'] == 'trial-incomplete-or-failed'
        assert result['observer_exit'] == 5 and result['boot_attempts'] == 1
        assert result['restored'] and result['partition_write_phase'] == 'desktop-restored-after-failure'
        assert result['boot_started'] is False and result['preboot_marker_restore']['bytes'] == 13
        assert io.misc_restored and io.misc == BEFORE
        assert all(command[0] != 'adb' for command in calls)
    print('W301 refused-boot model restored desktop and misc marker without device IO')


def set_marker(io):
    io.misc = MARKER+io.misc[len(MARKER):]
    return {'state':'misc-marker-readback-verified'}


if __name__ == '__main__':
    main()

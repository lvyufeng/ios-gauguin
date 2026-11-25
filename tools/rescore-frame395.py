#!/usr/bin/env python3
"""Score the preserved 0395 capture without changing its frozen executor output."""

from importlib import import_module
import json

from frame366_scope import load, require, sha

stock = import_module('run-frame392-trial')
scope = import_module('prepare-frame393')
EXEC = scope.LAST
COMPARISON = EXEC/'scanout-comparison-0391-0395.json'
RECEIPT = EXEC/'score-replay-0395.json'


def check_restore():
    terminal, independent, readback, activation = (load(EXEC/name) for name in (
        'result.json', 'independent-restore.json', 'restored-capture/result.json', 'edr-activation.json'))
    plan = load(scope.P395/'trial-plan.json')
    require(terminal['state'] == '0395-comparison-incomplete-root-restored' and terminal['comparison_error'] == "'0391'" and
            terminal['boot_attempts'] == 1 and terminal['observer_exit'] == 0 and terminal['restored'] and
            terminal['independent_restore_verified'] and terminal['static_root_comparison_passed'] and
            independent['install_plan_sha256'] == plan['install_plan_sha256'] and independent['journal_empty'] and
            independent['all_original_slot_bits_allocated'] and independent['misc_original_4096_bytes_match'] and
            independent['root_header_sha256'] == readback['root_header_sha256'] and terminal['hardware_CRC_pairs'] == 2704 and
            activation['active'] and activation['code_checks_qualified'] and activation['once_abi_qualified'],
            '0395 source did not complete activation, independent restoration and physical collection')
    return plan, activation


def replay():
    plan, activation = check_restore()
    report = stock.score(EXEC, plan, trial='0395')
    report.update(state='0391-0395-compared-after-independent-restore', EDR_activation=activation)
    if COMPARISON.exists():
        require(load(COMPARISON) == report, '0395 preserved score differs on replay')
    else:
        stock.stage.save_bounded(COMPARISON, report, 3_300_000)
    sources = [scope.P395/'ready.json', scope.P395/'trial-plan.json', COMPARISON,
               *(EXEC/name for name in ('result.json', 'independent-restore.json', 'restored-capture/result.json',
                                        'edr-activation.json', 'kernel.log', 'kernel.log.bin', 'page-flip-latches.json'))]
    result = dict(state='0395-physical-score-replayed-after-independent-restore', device_commands=0,
        DPU_independent_physical_FPS_qualified=True, compiled_EDR_activation=True,
        stable_60_fps_observed=report['stable_60_fps_observed'], input_pins={str(p):sha(p) for p in sources})
    if RECEIPT.exists():
        require(load(RECEIPT) == result, '0395 replay receipt differs')
    else:
        scope.save(RECEIPT, result)
    return result


if __name__ == '__main__':
    print(json.dumps(replay(), indent=2))

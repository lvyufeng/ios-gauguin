#!/usr/bin/env python3
"""Parser controls using actual Mac rows inside explicitly synthetic phone envelopes."""
from pathlib import Path
import importlib.util, os, struct, unittest
R = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('task_reader', R/'tools/metal_task_surface_log.py')
reader = importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)
BUILD = '0123456789abcdef01234567'
P = reader.PREFIX

def hash_bytes(data):
    v = 0xcbf29ce484222325
    for byte in data:
        v ^= byte; v *= 0x100000001b3; v &= 0xffffffffffffffff
    return f'{v:016x}'

def synthetic_envelope(mac, seed):
    """Only the rows are actual GPU output; permission/lifetime records are models."""
    oracle_rows = [r.split('GAUGUIN TASK ORACLE ',1)[1] for r in mac.splitlines() if ' ORACLE row ' in r]
    rows = [f'begin build={BUILD} seed={seed} cases=5']
    for index, (name,bpe,bias) in enumerate(reader.CASES):
        pitch = 64*bpe+64; size = pitch*64+13; early = int(index >= 3)
        source = bytearray((seed+29*(i+bias)+17*index) % 256 for i in range(size))
        for y in range(64):
            for x in range(64):
                bits = seed ^ 13*x ^ 7*y ^ 5*index
                color = [(255 if bits & (1<<c) else 0) for c in range(4)]
                if bpe < 4: data = bytes(color[:bpe])
                elif bpe == 4: data = bytes([color[2],color[1],color[0],color[3]])
                elif bpe == 8: data = struct.pack('<HHHH', *(15360 if c else 0 for c in color))
                else: data = struct.pack('<ffff', *(float(bool(c)) for c in color))
                pos = pitch*y+bpe*x; source[pos:pos+bpe] = data
        selected = [r for r in oracle_rows if r.startswith(f'row case={name} ')]
        raw = b''.join(bytes.fromhex(r.split('rgba=')[1]) for r in selected)
        rows.extend([f'permissions case={name} handle={index+1} gpu_bias={bias%4096} bytes={size} flags=131074 cpu_write=22 gpu_write=22 fence=0 close=0 uncertain=0 phase=passed',
                     f'case name={name} index={index} id={index+1} bpe={bpe} bias={bias} pitch={pitch} bytes={size} early={early}',
                     *selected, f'pixels case={name} pixels=4096 hash={hash_bytes(raw)} source_before={hash_bytes(source)} source_after={hash_bytes(source)} early={early} full_guard={1-early} PASS'])
    rows.extend(['memory phase=task-surfaces-completed active=128 inactive=128 hard=1 footprint=16000000',
                 'end cases=5 pixels=20480 jobs=5 direct=1 immutable=1 PASS'])
    return '\n'.join(P+r for r in rows)+'\n'

class Reader(unittest.TestCase):
    def test_actual_mac_rows_with_synthetic_permission_envelopes(self):
        directory = Path(os.environ['GAUGUIN_TASK_MAC_ORACLE'])
        controls = 0
        for seed in [0,0xffffffff,0xdeadbeef,0x12345678]:
            text = synthetic_envelope((directory/f'{seed:08x}.stdout').read_text(),seed)
            result = reader.qualify_task_surface_log(text,'',build=BUILD,seed=seed)
            self.assertEqual(result['compared_pixels'],20480); self.assertFalse(result['hardware_qualified'])
            bad = [text.replace('gpu_write=22','gpu_write=0',1),text.replace('cpu_write=22','cpu_write=0',1),
                   text.replace('gpu_bias=64','gpu_bias=0',1),text.replace('flags=131074','flags=131072',1),
                   text.replace('uncertain=0','uncertain=1',1),text.replace('fence=0','fence=1',1),
                   text.replace('close=0','close=5',1),text.replace('id=2 ','id=1 ',1),
                   text.replace('early=1','early=0',1),text.replace('full_guard=1','full_guard=0',1),
                   text.replace('y=0 ','y=1 ',1),text.replace('bytes=8205','bytes=8206',1),
                   text.replace('footprint=16000000','footprint=134217729'),text.replace(BUILD,'f'*24,1),
                   text+P+'unexpected=1\n', '\n'.join(text.splitlines()[:-1])]
            # Corrupt a genuine sampler channel and update the aggregate hash:
            # the independent expected pixels must still reject it.
            lines = text.splitlines(); index = next(i for i,r in enumerate(lines) if 'row case=R8 y=0 ' in r)
            prefix,raw = lines[index].split('rgba='); lines[index] = prefix+'rgba='+f'{int(raw[:2],16)^1:02x}'+raw[2:]
            changed_raw = b''.join(bytes.fromhex(r.split('rgba=')[1]) for r in lines if ' row case=R8 ' in r)
            old = next(r for r in lines if ' pixels case=R8 ' in r).split('hash=')[1][:16]
            bad.append('\n'.join(lines).replace('hash='+old,'hash='+hash_bytes(changed_raw),1))
            for changed in bad:
                with self.assertRaises(ValueError): reader.qualify_task_surface_log(changed,'',build=BUILD,seed=seed)
                controls += 1
            with self.assertRaises(ValueError): reader.qualify_task_surface_log(text,P+'FAIL phase=task\n',build=BUILD,seed=seed)
            controls += 1
        self.assertEqual(controls,72)
        print('Parser-only permission/lifetime models: 4 actual-Mac pixel sets and 72 bad envelopes rejected; no phone proof')
if __name__ == '__main__': unittest.main()

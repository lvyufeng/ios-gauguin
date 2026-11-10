#!/usr/bin/env python3
"""Exercise the real payload ABI with every supported trace selector."""
from pathlib import Path
import importlib.util,os,struct,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import mkpayload,adt
from test_payload_nvt_asset import kernel,tree
spec=importlib.util.spec_from_file_location('trace_profile',ROOT/'tools/prepare-ui-trace-profile.py')
profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)
BASE=('debug=0x8 serial=3 cpus=8 keepsyms=1 -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1 '
 'ignition_level=1 ufsrw=1 rootrw=1 launchd_unsecure_cache=1 sweetlog=1 sweetlogms=500 '
 'sweetfb_noconsole=1 sweetufsquiet=1 sweetsample=- sweetwdtpet=0 sweettzsample=1 sweettouchmode=0 '
 'sweetnvt=1 sweetpasprobe=1 sweetpasstage=1 sweetbusvote=1 sweetgpuzap=12 sweetpasmem=0 '
 'sweetcxpower=1 sweetgmuclk=1 sweetgmufw=1 sweetgmuperf=1 sweetgmubw=1 sweetgmudcvs=1 '
 'sweetgpucontext=1 sweetgpustart=1 sweetreboot=0 sweettrial=gwrt-0175-a1 sweetgpuservice=1 '
 'sweetgpuservicesecs=600 sweet_dyld_probe=1 sweeteagl=2 gmt=2 sweetfb_hz=60')
class TraceProfile(unittest.TestCase):
    def test_actual_payload_roundtrip_and_only_metadata_changes(self):
        self.assertEqual(len(BASE.encode()),607)
        with tempfile.TemporaryDirectory()as tmp:
            k=Path(tmp)/'kernel';d=Path(tmp)/'adt';k.write_bytes(kernel());d.write_bytes(adt.serialize(tree()))
            before,_=mkpayload.build(k,d,BASE)
            for gesture in range(1,17):
                command=profile.trace_command(BASE,gesture);self.assertEqual(len(command.encode()),596+(gesture>=10))
                self.assertEqual(command.replace('sweettrace='+str(gesture),profile.OLD),BASE)
                after,_=mkpayload.build(k,d,command);field=after[0x48:0x2a8]
                self.assertEqual(field,command.encode()+bytes(608-len(command.encode())) )
                self.assertEqual(before[:0x48],after[:0x48]);self.assertEqual(before[0x2a8:],after[0x2a8:])
                self.assertGreater(struct.unpack_from('<I',after,12)[0],0)
    def test_oversized_append_is_rejected_by_actual_packer(self):
        with self.assertRaisesRegex(ValueError,'607 UTF-8 bytes'):
            mkpayload.build(Path('missing-kernel'),Path('missing-adt'),BASE+' sweettrace=2')
    def test_refuse_other_modes_duplicates_spacing_and_bad_selectors(self):
        for gesture in [False,True,0,-1,17,'2',None,1.5]:
            with self.subTest(gesture=gesture),self.assertRaises(ValueError):profile.trace_command(BASE,gesture)
        for command in [BASE.replace('gmt=2','gmt=1'),BASE.replace('sweeteagl=2','sweeteagl=1'),
             BASE.replace(profile.OLD,'sweettrial=other'),BASE.replace(profile.OLD,'sweettrace=2'),
             BASE.replace('cpus=8','cpus=8 cpus=8'),BASE.replace('cpus=8','cpus=8  '),BASE+'\0']:
            with self.subTest(command=command),self.assertRaises(ValueError):profile.trace_command(command,2)
    def test_current_tree_has_no_trial_consumer(self):
        if 'XNU_SOURCE'not in os.environ:self.skipTest('full source check belongs to staged-source/CI lane')
        root=Path(os.environ['XNU_SOURCE']);self.assertTrue((root/'bsd/conf/files').is_file())
        for p in root.rglob('*'):
            if p.is_file()and '.git'not in p.parts:self.assertNotIn(b'sweettrial',p.read_bytes(),str(p))
        self.assertIn('PE_parse_boot_argn("sweettrace"',(root/'bsd/dev/gauguin_ui_trace_board.c').read_text())
if __name__=='__main__':unittest.main()

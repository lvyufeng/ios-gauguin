#!/usr/bin/env python3
"""Exercise the real payload ABI and reject commands that cannot round-trip."""
from pathlib import Path
import importlib.util,json,os,struct,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests'))
import mkpayload
import adt
from test_payload_nvt_asset import kernel,tree
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
package=module('desktop_package_command',ROOT/'tools/prepare-metal-desktop-package.py')

class Commands(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='boot-command-');self.path=Path(self.tmp.name)
        self.kernel=self.path/'kernel';self.kernel.write_bytes(kernel())
        self.adt=self.path/'adt';self.adt.write_bytes(adt.serialize(tree()))
    def tearDown(self):self.tmp.cleanup()
    def test_boundary_round_trips_and_segment_table_stays_intact(self):
        for command in ['', 'a', 'a'*606, 'a'*607, 'é'*303+'a']:
            with self.subTest(bytes=len(command.encode())):
                blob,info=mkpayload.build(self.kernel,self.adt,command)
                field=blob[0x48:0x2a8];self.assertEqual(len(field),608)
                self.assertEqual(field.split(b'\0',1)[0],command.encode())
                self.assertEqual(field[len(command.encode()):],bytes(608-len(command.encode())))
                count=struct.unpack_from('<I',blob,12)[0];self.assertGreater(count,0)
                for index in range(count):
                    va,vm,off,size=struct.unpack_from('<4Q',blob,0x2a8+32*index)
                    self.assertGreater(vm,0);self.assertGreaterEqual(vm,size)
                    self.assertLessEqual(off+size,len(blob));self.assertGreaterEqual(off,0x2a8+32*count)
                self.assertEqual(info['size'],len(blob))
    def test_overflow_and_nul_refused_before_any_input_read(self):
        for command in ['a'*608,'a'*638,'a'*800,'é'*304,'a\0b','\0','a\0']:
            with self.subTest(command_bytes=len(command.encode())):
                with self.assertRaises(ValueError):
                    mkpayload.build(self.path/'missing-kernel',self.path/'missing-adt',command)
    def test_cli_failure_preserves_existing_output(self):
        output=self.path/'existing';output.write_bytes(b'preserve existing payload')
        result=subprocess.run([sys.executable,str(ROOT/'tools/mkpayload.py'),str(self.kernel),str(self.adt),
            str(output),'--cmdline','a'*608],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('boot command exceeds 607 UTF-8 bytes',result.stderr)
        self.assertEqual(output.read_bytes(),b'preserve existing payload')
    def test_actual_board_profile_keeps_every_other_token_and_round_trips(self):
        base=json.loads(Path(os.environ['BOOT_COMMAND_BASE']).read_text())
        command,overrides=package.boot_profile(base)
        self.assertEqual(len(command.encode()),607)
        self.assertEqual(overrides,dict(sweet_dyld_probe=1,sweeteagl=2,gmt=2,sweetfb_hz=60))
        key=lambda word:word.split('=',1)[0]
        self.assertEqual([w for w in command.split()if key(w)not in overrides],
                         [w for w in base['command'].split()if key(w)not in overrides])
        for name,value in overrides.items():self.assertEqual(command.split().count(name+'='+str(value)),1)
        blob,_=mkpayload.build(self.kernel,self.adt,command)
        self.assertEqual(blob[0x48:0x2a8],command.encode()+b'\0')
        old=module('old_payload_command',Path(os.environ['BOOT_COMMAND_REFERENCE']))
        oldpkg=module('old_package_command',Path(os.environ['BOOT_PACKAGE_REFERENCE']))
        oldcommand,_=oldpkg.boot_profile(base);self.assertEqual(len(oldcommand.encode()),638)
        oldblob,_=old.build(self.kernel,self.adt,oldcommand)
        field=oldblob[0x48:0x2a8].split(b'\0',1)[0]
        self.assertNotEqual(field,oldcommand.encode());self.assertTrue(field.endswith(b'sweetfb_hold='))
        self.assertEqual(oldcommand.encode()[len(field):],b'1 sweetfb_phase=1 sweetfb_hz=60')
        print('Baseline functional RED: real old packer silently loses phase/copy flags; new607B profile round-trips')

if __name__=='__main__':unittest.main()

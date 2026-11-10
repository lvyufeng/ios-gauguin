"""Fresh read is mandatory even when the local clone is already identical."""
import hashlib,io
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'tools'))
from stream_clone_backup import copy_verified_stream

class CloneBackup(unittest.TestCase):
    def test_equal_and_changed_streams(self):
        base=bytes(range(251))*17
        for changed in [[],[0],[2048],[len(base)-1],[0,2048,len(base)-1]]:
            fresh=bytearray(base)
            for i in changed:fresh[i]^=0xff
            target=io.BytesIO(base);stream=io.BytesIO(fresh)
            result=copy_verified_stream(stream,target,len(base),1024)
            self.assertEqual(target.getvalue(),fresh)
            self.assertEqual(result['sha256'],hashlib.sha256(fresh).hexdigest())
            self.assertEqual(result['fresh_bytes'],len(fresh))
            self.assertEqual(stream.tell(),len(fresh))
            self.assertEqual(result['changed_chunks'],len({i//1024 for i in changed}))

    def test_incomplete_extra_and_bad_geometry_never_pass(self):
        for stream,target,size,chunk in [
            (b'a'*15,b'b'*16,16,8),(b'a'*17,b'b'*16,16,8),
            (b'a'*16,b'b'*15,16,8),(b'a'*16,b'b'*16,0,8),
            (b'a'*16,b'b'*16,16,0),(b'a'*16,b'b'*16,True,8)]:
            with self.assertRaises(ValueError):copy_verified_stream(io.BytesIO(stream),io.BytesIO(target),size,chunk)

    def test_partial_host_write_rejected(self):
        class ShortWrite(io.BytesIO):
            def write(self,data):return super().write(data[:-1])
        with self.assertRaisesRegex(ValueError,'short clone write'):
            copy_verified_stream(io.BytesIO(b'a'*16),ShortWrite(b'b'*16),16,8)

if __name__=='__main__':unittest.main(verbosity=2)

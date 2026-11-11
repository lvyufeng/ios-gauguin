#!/usr/bin/env python3
"""Execute real emitters beside an unfinished caller line; keep strict parsing."""
from pathlib import Path
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from gpu_service_log import records
TREE=Path(os.environ['XNU_SOURCE'])
REFERENCE=Path(os.environ['LOG_FRAMING_REFERENCE'])
PREFIX='SWEET GPU USER: submit '
PATTERN=(r'SWEET GPU USER: submit rc=(\d+) ibs=(\d+) submitted=(\d+) '
         r'completed=(\d+) shadow=(\d+) polls=(\d+)')
LINE='SWEET GPU USER: submit rc=0 ibs=1 submitted=1 completed=1 shadow=32 polls=1'


def function(text,name):
    start=re.search(r'static\s+void\s+'+re.escape(name)+r'\s*\([^)]*\)\s*\{',text).start()
    brace=text.index('{',start);depth=0
    for end in range(brace,len(text)):
        depth+=(text[end]=='{')-(text[end]=='}')
        if depth==0:return text[start:end+1]
    raise ValueError('incomplete emitter')


HOST=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static bool in_thread;
static unsigned marks,flushes,console_calls;
static const char *original;
static bool gmb_thread(void){return in_thread;}
static void sweet_log_mark_sync(const char *line){assert(strcmp(line,original)==0);marks++;}
static void sweet_log_flush_now(void){flushes++;}
static void console_write(char *text,int bytes){
    assert(bytes>0&&bytes<=193&&bytes==(int)strlen(original)+2);
    assert(text[0]=='\n'&&text[bytes-1]=='\n');
    assert(memcmp(text+1,original,strlen(original))==0);
    console_calls++;assert(fwrite(text,1,(size_t)bytes,stdout)==(size_t)bytes);
}
@EMITTER@
int main(int argc,char **argv){
    assert(argc==4);in_thread=atoi(argv[1])!=0;
    original=argv[2];unsigned expected=(unsigned)atoi(argv[3]);
    fputs("IOK unfinished multi-call message: ",stdout);
    @FUNCTION@(original);
    assert(marks==unsigned_unused); /* substituted below */
    assert(flushes==marks&&console_calls==expected);
    return 0;
}
'''.replace('marks==unsigned_unused','marks==(unsigned)in_thread')


class FramingTests(unittest.TestCase):
    def test_actual_baseline_fails_and_candidate_keeps_one_bounded_console_record(self):
        paths=[Path(__file__),ROOT/'tools/gpu_service_log.py']+[tree/'bsd/dev/gauguin_gmu_board.c'for tree in [REFERENCE,TREE]]
        pins={p:hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
        before=(REFERENCE/'bsd/dev/gauguin_gmu_board.c').read_text()
        after=(TREE/'bsd/dev/gauguin_gmu_board.c').read_text()
        self.assertIn('gmb_record_submission(line);',after)
        self.assertEqual(after.count('gmb_record_submission(line);'),1)
        self.assertEqual(function(before,'gmb_record'),function(after,'gmb_record'))
        with tempfile.TemporaryDirectory(prefix='submit-framing-') as directory:
            for name,source,emitter in [('baseline',before,'gmb_record'),('candidate',after,'gmb_record_submission')]:
                code=HOST.replace('@EMITTER@',function(source,emitter)).replace('@FUNCTION@',emitter)
                cpp=Path(directory)/(name+'.c');exe=cpp.with_suffix('');cpp.write_text(code)
                subprocess.run(['clang','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-pedantic',str(cpp),'-o',str(exe)],check=True)
                for in_thread in ['0','1']:
                    result=subprocess.run([str(exe),in_thread,LINE,'0'if name=='baseline'else'1'],capture_output=True,text=True,check=True)
                    if name=='baseline':
                        with self.assertRaisesRegex(ValueError,'malformed/interleaved'):
                            records(result.stdout,PREFIX,PATTERN)
                    else:
                        self.assertEqual([row[2]for row in records(result.stdout,PREFIX,PATTERN)],[(0,1,1,1,32,1)])
                if name=='candidate':
                    # The formatter's maximum legal payload fits one ring reservation.
                    for payload,expected in [('x'*191,'1'),('x'*192,'0')]:
                        result=subprocess.run([str(exe),'1',payload,expected],capture_output=True,text=True,check=True)
                        self.assertEqual(result.stdout,'IOK unfinished multi-call message: \n'+payload+'\n')
        self.assertEqual(pins,{p:hashlib.sha256(p.read_bytes()).hexdigest()for p in paths})


if __name__=='__main__':unittest.main()

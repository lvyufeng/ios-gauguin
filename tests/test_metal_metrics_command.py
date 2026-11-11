#!/usr/bin/env python3
"""Run all nine actual reboot consumers and the installed frontend flag reader."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from metal_metrics_command import with_metal_metrics
from mkpayload import encode_cmdline
TREE=Path(os.environ['XNU_SOURCE'])
BASE=Path(os.environ['METRICS_BASE_PACKAGE'])
FRONT=Path(os.environ['METRICS_FRONTEND_SOURCE'])
SPECS=[('gauguin_pas_init.c','gpi_flags'),('gauguin_bcm_transport.c','gt_conflicts'),
       ('gauguin_bcm_coordinator.c','bcm_flags'),('gauguin_gmu_board.c','gpzb_flags'),
       ('gauguin_wdt_test.c','wdt_conflict'),('gauguin_wdt_test.c','wdt_bus_conflict'),
       ('gauguin_cx_power.c','gcx_flags'),('sweet_ufs.c','sweet_reboot_thread'),('sweet_ufs.c','sweet_reboot_start')]


def function(text,name):
    match=re.search(r'(?:static\s+)?(?:void|bool|BOOL)\s+'+re.escape(name)+r'\s*\([^)]*\)\s*\{',text)
    if match is None:raise ValueError('function missing '+name)
    brace=text.index('{',match.start());depth=0
    for end in range(brace,len(text)):
        depth+=(text[end]=='{')-(text[end]=='}')
        if depth==0:return text[match.start():end+1]
    raise ValueError('incomplete '+name)


HOST=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef __unused
#define __unused __attribute__((unused))
#endif
#define PZERO 0
#define KERN_SUCCESS 0
#define RB_AUTOBOOT 1
static const char *command;
static unsigned starts,deallocs,sleeps,panics,reboots,reboot_queries;
static int sweet_log_chan,hz=100;
typedef int wait_result_t;
typedef int thread_t;
typedef int BOOL;
static bool PE_parse_boot_argn(const char *key,void *out,int size){
    assert(size==(int)sizeof(int));if(strcmp(key,"sweetreboot")==0)reboot_queries++;
    const size_t k=strlen(key);
    for(const char *p=command;*p;){
        const char *end=strchr(p,' ');if(end==NULL)end=p+strlen(p);
        if((size_t)(end-p)>k&&memcmp(p,key,k)==0&&p[k]=='='){
            int value=(int)strtol(p+k+1,NULL,0);memcpy(out,&value,sizeof(value));return true;
        }
        p=*end?end+1:end;
    }
    return false; /* missing arguments leave the real caller's initial value */
}
static int sysctlbyname(const char *key,void *out,size_t *size,void *newp,size_t len){
    assert(strcmp(key,"kern.bootargs")==0&&newp==NULL&&len==0);
    assert(*size>strlen(command));strcpy(out,command);*size=strlen(command)+1;return 0;
}
static void wdt_record(const char *line){assert(line!=NULL);}
static int kernel_thread_start(void (*fn)(void *,wait_result_t),void *arg,thread_t *thread){
    assert(fn!=NULL&&arg==NULL);starts++;*thread=123;return KERN_SUCCESS;
}
static void thread_deallocate(thread_t thread){assert(thread==123);deallocs++;}
static int tsleep(void *channel,int priority,const char *message,int ticks){
    assert(channel==&sweet_log_chan&&priority==PZERO&&strcmp(message,"sweetreboot")==0&&ticks==100);sleeps++;return 0;
}
static void panic(const char *format,int seconds){assert(format!=NULL&&seconds==1);panics++;}
static int reboot_kernel(int flags,void *message){assert(flags==RB_AUTOBOOT&&message==NULL);reboots++;return 0;}
@METHODS@
int main(int argc,char **argv){
    assert(argc==2);command=argv[1];
    int answers[]={gpi_flags(),gt_conflicts(),bcm_flags(),gpzb_flags(),wdt_conflict(),wdt_bus_conflict(),gcx_flags()};
    sweet_reboot_start();sweet_reboot_thread(NULL,0);
    printf("RESULT %d %d %d %d %d %d %d %u %u %u %u %u %d %u\n",
           answers[0],answers[1],answers[2],answers[3],answers[4],answers[5],answers[6],
           starts,deallocs,sleeps,panics,reboots,hm_fps_on(),reboot_queries);
    return 0;
}
'''


class MetricsCommandTests(unittest.TestCase):
    def test_actual_nine_consumers_preserve_disabled_reboot_and_enable_real_frontend_flag(self):
        old=json.loads(BASE.read_text())['command'];new=with_metal_metrics(old)
        self.assertEqual((len(encode_cmdline(old)),len(encode_cmdline(new))),(607,603))
        self.assertEqual(new.split(' '),[token for token in old.split(' ')if token!='sweetreboot=0']+['metal_fps'])
        paths=[Path(__file__),ROOT/'tools/metal_metrics_command.py',ROOT/'tools/mkpayload.py',BASE,FRONT]+[TREE/'bsd/dev'/file for file,_ in SPECS]
        pins={path:hashlib.sha256(path.read_bytes()).hexdigest()for path in paths}
        methods=[function((TREE/'bsd/dev'/file).read_text(),name)for file,name in SPECS]
        methods.append(function(FRONT.read_text(),'hm_fps_on'))
        with tempfile.TemporaryDirectory(prefix='metrics-command-') as directory:
            cpp=Path(directory)/'readers.c';exe=cpp.with_suffix('');cpp.write_text(HOST.replace('@METHODS@','\n'.join(methods)))
            subprocess.run(['clang','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-pedantic',str(cpp),'-o',str(exe)],check=True)
            values=[]
            for command in [old,new,old.replace('sweetreboot=0','sweetreboot=1')]:
                result=subprocess.run([str(exe),command],capture_output=True,text=True,check=True)
                rows=[line for line in result.stdout.splitlines()if line.startswith('RESULT ')]
                self.assertEqual(len(rows),1);values.append(tuple(map(int,rows[0].split()[1:])))
        # Seven real conflict/permission decisions and both real timer bodies.
        self.assertEqual(values[0][:12],values[1][:12]);self.assertEqual(values[0][7:12],(0,0,0,0,0))
        self.assertEqual((values[0][12],values[1][12]),(0,1))
        self.assertGreaterEqual(values[0][13],9);self.assertGreaterEqual(values[1][13],9)
        self.assertEqual(values[2][7:12],(1,1,1,1,0));self.assertNotEqual(values[0][:7],values[2][:7])
        self.assertEqual(pins,{path:hashlib.sha256(path.read_bytes()).hexdigest()for path in paths})

    def test_unreviewed_or_ambiguous_command_changes_are_rejected(self):
        old=json.loads(BASE.read_text())['command']
        for bad in [old+' sweetreboot=0',old.replace('sweetreboot=0','sweetreboot=1'),old.replace('sweetreboot=0','sweetrebootnormal=1'),old+' metal_fps',old+' metal_fps=timeline',old.replace('-noprogress ','')]:
            with self.subTest(command=bad),self.assertRaises(ValueError):with_metal_metrics(bad)


if __name__=='__main__':unittest.main()

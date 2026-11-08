#!/usr/bin/env python3
"""Exercise the production read-only memory admission against the actual XNU ABI.

These are mocked syscall boundary cases, not proof of launchd policy or GPU work.
"""
from pathlib import Path
import argparse,hashlib,json,re,subprocess

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kernel-source',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();repo=Path(__file__).resolve().parents[1]
    source=repo/'tools/gauguin-gles-probe.c'
    header=a.kernel_source/'bsd/sys/kern_memorystatus.h'
    text=source.read_text();native=header.read_text()
    declaration=re.search(r'struct probe_memlimit \{.*?\n\};',text,re.S).group()
    actual=re.search(r'typedef struct memorystatus_memlimit_properties \{.*?\n\} memorystatus_memlimit_properties_t;',native,re.S).group()
    command=re.search(r'^#define MEMORYSTATUS_CMD_GET_MEMLIMIT_PROPERTIES[^\n]+',native,re.M).group()
    function=text[text.index('static int memory_checkpoint('):text.index('static void number(')]
    fields=list(zip(['active','active_attr','inactive','inactive_attr'],['memlimit_active','memlimit_active_attr','memlimit_inactive','memlimit_inactive_attr']))
    abi='\n'.join('_Static_assert(offsetof(struct probe_memlimit,%s)==offsetof(memorystatus_memlimit_properties_t,%s),"wire field");'%x for x in fields)
    unit=r'''#include <mach/mach.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <assert.h>
''' + actual+'\n'+command+'\n'+declaration+'\n'+abi+r'''
_Static_assert(sizeof(struct probe_memlimit)==sizeof(memorystatus_memlimit_properties_t),"wire size");
_Static_assert(MEMORYSTATUS_CMD_GET_MEMLIMIT_PROPERTIES==8,"actual read command");
static int scenario,queries,vmqueries,failures;
static int fail(const char *why){(void)why;failures++;return 1;}
static int memorystatus_control(uint32_t cmd,int32_t pid,uint32_t flags,void *buf,size_t n)
{
    assert(cmd==MEMORYSTATUS_CMD_GET_MEMLIMIT_PROPERTIES&&pid==getpid()&&flags==0);
    assert(n==sizeof(memorystatus_memlimit_properties_t));queries++;
    if(scenario==1)return -1;
    memorystatus_memlimit_properties_t p={128,1,128,1};
    if(scenario==4)p.memlimit_active=6;
    if(scenario==5)p.memlimit_inactive=6;
    if(scenario==6)p.memlimit_active=0;
    if(scenario==7)p.memlimit_inactive=-1;
    if(scenario==8)p.memlimit_active_attr=0;
    if(scenario==9)p.memlimit_inactive_attr=0;
    if(scenario==10)p.memlimit_active_attr=3;
    memcpy(buf,&p,n);return 0;
}
static kern_return_t query_vm(task_name_t task,task_flavor_t flavor,task_info_t data,mach_msg_type_number_t *count)
{
    assert(task==mach_task_self()&&flavor==TASK_VM_INFO&&*count==TASK_VM_INFO_REV1_COUNT);vmqueries++;
    if(scenario==2)return KERN_FAILURE;
    ((task_vm_info_t)data)->phys_footprint=8*1024*1024;
    if(scenario==3)*count=TASK_VM_INFO_REV0_COUNT;
    if(scenario==11)((task_vm_info_t)data)->phys_footprint=0;
    if(scenario==12)((task_vm_info_t)data)->phys_footprint=UINT64_C(128)*1024*1024+1;
    if(scenario==13)((task_vm_info_t)data)->phys_footprint=UINT64_C(128)*1024*1024;
    return KERN_SUCCESS;
}
#define task_info query_vm
''' + function + r'''
int main(void)
{
    for(scenario=0;scenario<14;scenario++) {
        queries=vmqueries=failures=0;int rc=memory_checkpoint("boundary-test");
        assert((rc==0)==(scenario==0||scenario==13));
        assert(queries==1&&vmqueries==(scenario==1?0:1));
        assert(failures==(rc?1:0));
    }
    puts("PASS14 mocked memory-boundary cases; actual kernel ABI size/offsets/GET command");
    return 0;
}
'''
    a.out.mkdir(parents=True,exist_ok=False);tu=a.out/'memory-host.c';tu.write_text(unit)
    results=[]
    for name,argv in [('compile',['xcrun','clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(tu),'-o',str(a.out/'memory-host')]),('run',[str(a.out/'memory-host')])]:
        with (a.out/(name+'.log')).open('x') as f:p=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT)
        results.append({'name':name,'exit':p.returncode});assert p.returncode==0,(name,p.returncode)
    result={'state':'passed14-mocked-readonly-memory-boundary-cases','physical_qualified':False,'device_commands':0,'results':results,'input_pins':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),source,header]}}
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS14 memory admission cases; actual ABI; no device memory query or policy acceptance')
if __name__=='__main__':main()

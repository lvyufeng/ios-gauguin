#!/usr/bin/env python3
"""Exercise the actual singleton publisher and accelerator start/stop with typed seams."""
from pathlib import Path
import argparse,os,subprocess

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    text=(a.source/'iokit/Kernel/arm/SweetFramebuffer.cpp').read_text()
    start=text.index('\n',text.index('/* SWEET_METAL_PUBLICATION_BEGIN:'))+1
    helper=text[start:text.index('/* SWEET_METAL_PUBLICATION_END */',start)]
    def method(signature):
        start=text.index(signature);return text[start:text.index('\n}\n',start)+3]
    code=r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <thread>
#include <vector>
static bool mode;
static bool sweet_metal_desktop_enabled(){return mode;}
static const char *kIOUserClientClassKey="IOUserClientClass";
#define IOLog(...) ((void)0)
struct IOService {
    virtual ~IOService()=default;
    std::map<std::string,std::string> props;unsigned registered=0,stopped=0,metal_calls=0,fail_at=0;
    virtual bool start(IOService *){return true;}virtual void stop(IOService *){stopped++;}
    bool setProperty(const char *k,const char *v){if(!strncmp(k,"MetalPlugin",11)&&++metal_calls==fail_at)return false;props[k]=v;return true;}
    bool setProperty(const char *k,bool v){props[k]=v?"true":"false";return true;}
    void removeProperty(const char *k){props.erase(k);}void registerService(){registered++;}
};
struct IOAcceleratorES:IOService{bool start(IOService *)override;void stop(IOService *)override;};
struct AGXAccelerator:IOAcceleratorES{bool start(IOService *)override;};
HELPER
START
STOP
AGX
static unsigned checks;
#define CHECK(x) do{checks++;assert(x);}while(0)
int main(){
    IOService parent;IOAcceleratorES legacy;mode=false;CHECK(legacy.start(&parent));
    CHECK(legacy.props.count("MetalPluginName")==0&&legacy.registered==1&&!sweet_metal_publisher);
    legacy.stop(&parent);CHECK(legacy.stopped==1);
    mode=true;
    for(unsigned fail=1;fail<=2;fail++) {
        IOAcceleratorES bad;bad.fail_at=fail;CHECK(bad.start(&parent));
        CHECK(!sweet_metal_publisher&&!bad.props.count("MetalPluginName")&&!bad.props.count("MetalPluginClassName"));
        bad.stop(&parent);
    }
    for(unsigned round=0;round<100;round++) {
        std::vector<AGXAccelerator> nodes(16);std::vector<std::thread> workers;
        for(auto &node:nodes)workers.emplace_back([&node,&parent]{assert(node.start(&parent));});
        for(auto &worker:workers)worker.join();unsigned count=0;
        for(auto &node:nodes)if(node.props.count("MetalPluginName")){
            count++;CHECK(node.props["MetalPluginName"]=="GauguinMetalDesktop");
            CHECK(node.props["MetalPluginClassName"]=="GauguinDesktopMetalDevice");
            CHECK(sweet_metal_publisher==&node);
        }
        CHECK(count==1);
        for(auto &node:nodes)node.stop(&parent);CHECK(!sweet_metal_publisher);
    }
    printf("%u actual singleton publication checks passed; typed services, no real registry\n",checks);
}
'''.replace('HELPER',helper).replace('START',method('bool\nIOAcceleratorES::start(')).replace('STOP',method('void\nIOAcceleratorES::stop(')).replace('AGX\n',method('bool\nAGXAccelerator::start(')+'\n')
    unit=a.out/'publication.cpp';unit.write_text(code)
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1')
    with(a.out/'compile.log').open('x')as f:subprocess.run(['xcrun','clang++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(unit),'-o',str(a.out/'publication')],stdout=f,stderr=subprocess.STDOUT,env=env,check=True)
    subprocess.run([str(a.out/'publication')],env=env,check=True)
if __name__=='__main__':main()

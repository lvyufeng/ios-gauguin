// SPDX-License-Identifier: MIT
// Real Metal-produced library through the unchanged A619 AIR/NIR/IR3 compiler.
// Compile/link qualification only: no GPU execution or fake rasterization.
#include <cstdio>
#include <fstream>
#include <iterator>
#include <map>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include "hakios-metal/compiler.hpp"
#include "hakios-metal/device_profile.hpp"
#include "hakios-metal/metallib.hpp"
using namespace hakios::metal;
static unsigned checks;
static void require(bool ok,const std::string& why) { ++checks;if (!ok) throw std::runtime_error(why); }

int main(int argc,char** argv) try {
    require(argc==2,"one library path required");
    std::ifstream file(argv[1],std::ios::binary);
    std::vector<uint8_t> data((std::istreambuf_iterator<char>(file)),{});
    require(data.size()>=88 && data.size()<1048576,"bounded generated library");
    MetalLibrary library;require(library.parse(data.data(),data.size()),library.why());
    require(hasCompiler() && device::kTarget.chipId==0x06010900,"real A619 compiler profile");
    const std::map<std::string,uint8_t> want={{"gauguin_fill",2},{"gauguin_vertex",0},
        {"gauguin_fragment",1},{"gauguin_uniform_fragment",1},{"gauguin_texture_fragment",1}};
    require(library.functions().size()==want.size(),"exact function count");
    std::map<std::string,std::shared_ptr<CompiledStage>> stages;
    std::unique_ptr<CompiledKernel> kernel;
    std::set<std::string> seen;
    for (const auto& function:library.functions()) {
        auto row=want.find(function.name);
        require(row!=want.end() && function.type==row->second && seen.insert(function.name).second,"unexpected function/type");
        const uint8_t* code=nullptr;uint64_t size=0;std::string why;
        require(library.bitcode(function,&code,&size) && code && size>16,"function AIR bitcode");
        if (function.type==2) {
            kernel=compileAir(code,size,&why);require(bool(kernel),function.name+": "+why);
            require(!kernel->words.empty(),"nonempty compute program");
        } else {
            auto stage=compileStage(code,size,&why);require(bool(stage),function.name+": "+why);
            require(!stage->words.empty(),"nonempty vertex/fragment program");
            stages[function.name]=std::shared_ptr<CompiledStage>(std::move(stage));
        }
        std::printf("COMPILED %s type=%u AIR_bytes=%llu\n",function.name.c_str(),function.type,(unsigned long long)size);
    }
    require(bool(kernel),"compute stage present");
    bool output=false,seed=false;
    for (const auto& resource:kernel->resources) {
        if (resource.kind==Resource::kDeviceBuffer && resource.index==0 && resource.irWrite) output=true;
        if (resource.kind==Resource::kConstantBuffer && resource.index==1 && resource.read && resource.sizeBytes==4) seed=true;
    }
    require(output && seed,"compute public buffer0/output and buffer1/constant-seed bindings");
    const PixelFormat formats[]={PixelFormat::kRGBA8Unorm,PixelFormat::kBGRA8Unorm,
        PixelFormat::kRGBA8UnormSrgb,PixelFormat::kBGRA8UnormSrgb,PixelFormat::kRGBA16Float};
    unsigned linked=0;
    for (auto format:formats) for (const char* fragment:{"gauguin_fragment","gauguin_uniform_fragment","gauguin_texture_fragment"}) {
        std::string why;auto program=linkProgram(stages.at("gauguin_vertex"),stages.at(fragment),format,&why);
        require(bool(program),std::string(fragment)+": "+why);++linked;
    }
    std::printf("PASS %u generated-library/A619 compiler checks; functions=5 linked_programs=%u; no hardware/pixel/API-runtime claim\n",checks,linked);
    return 0;
} catch (const std::exception& error) {
    std::fprintf(stderr,"FAIL generated Metal library: %s\n",error.what());return 1;
}

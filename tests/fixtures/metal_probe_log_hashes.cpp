// SPDX-License-Identifier: MIT
// CPU-only bridge between the compiled probe's expectations and log verifier.
#include <cstdio>
#include <vector>
#include "probe_pixels.hpp"
namespace p=gauguin::metal_probe;
template<class T,class E> static void emit(uint32_t seed,const char* phase,size_t count,E expected) {
    std::vector<T> data(count);
    for(size_t i=0;i<count;i++) data[i]=expected(i);
    auto result=p::compare(data.data(),count,expected);
    std::printf("%u %s %016llx\n",seed,phase,(unsigned long long)result.hash);
}
int main() {
    for(uint32_t seed:{0u,1u,0xffffffffu,0x6a09e667u}) {
        emit<uint32_t>(seed,"clear-A",4096,[=](size_t){return p::binaryColor(seed&7);});
        emit<uint32_t>(seed,"clear-B",4096,[=](size_t){return p::binaryColor((seed&7)^7);});
        emit<uint32_t>(seed,"compute",256,[=](size_t i){return p::computeWord(seed,uint32_t(i));});
        emit<uint32_t>(seed,"triangle",4096,[](size_t i){return p::triangle(uint32_t(i%64),uint32_t(i/64));});
        emit<uint32_t>(seed,"texture-A",4096,[=](size_t i){return p::checker(seed,uint32_t(i%64),uint32_t(i/64));});
        emit<uint32_t>(seed,"texture-B",4096,[=](size_t i){return p::checker(seed^8,uint32_t(i%64),uint32_t(i/64));});
        emit<uint32_t>(seed,"additive",4096,[](size_t){return p::rgba(255,255,0);});
        emit<uint64_t>(seed,"premultiplied-half",4096,[](size_t){return p::kPremultipliedHalf;});
    }
}

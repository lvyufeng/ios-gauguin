// SPDX-License-Identifier: MIT
#include <cstdio>
#include <cstdlib>
#include <vector>
#include "probe_pixels.hpp"
namespace p=gauguin::metal_probe;
static unsigned checks;
#define CHECK(c) do {++checks;if (!(c)) {std::fprintf(stderr,"FAIL %s:%d %s\n",__FILE__,__LINE__,#c);return 1;}} while(0)
static double edge(double ax,double ay,double bx,double by,double x,double y) {
    return (bx-ax)*(y-ay)-(by-ay)*(x-ax);
}
int main() {
    CHECK(p::rgba(255,0,0)==0xff0000ffu);
    CHECK(p::rgba(0,0,255)==0xffff0000u);
    CHECK(p::computeWord(0xffffffffu,1)==0x9e3779b0u);
    CHECK(p::checker(0,0,0)==0xff000000u);
    CHECK(p::checker(0,8,0)==0xffffffffu);
    CHECK(p::checker(8,0,0)==0xffffffffu);
    unsigned covered=0;
    // Independent geometric reference: transform the exact uploaded vertices
    // through the Metal viewport, then use oriented double-precision edges.
    double xy[3][2];
    for (unsigned v=0;v<3;v++) {
        xy[v][0]=(double(p::kTriangle[v].x)+1)*32;
        xy[v][1]=(1-double(p::kTriangle[v].y))*32;
    }
    for (unsigned y=0;y<64;y++) for (unsigned x=0;x<64;x++) {
        bool inside=true;
        for (unsigned v=0;v<3;v++) {
            double e=edge(xy[v][0],xy[v][1],xy[(v+1)%3][0],xy[(v+1)%3][1],x+0.5,y+0.5);
            CHECK(e!=0);inside&=e>0;
        }
        CHECK(p::inTriangle(x,y)==inside);covered+=inside;
        CHECK(p::triangle(x,y)==(inside?0xff0000ffu:0xffff0000u));
    }
    CHECK(covered>1900 && covered<2100);
    std::vector<uint32_t> data(4096,0xff00ff00u);
    auto good=p::compare(data.data(),data.size(),[](size_t){return 0xff00ff00u;});
    CHECK(good.equal && good.checked==4096);
    data[43]^=1;
    auto bad=p::compare(data.data(),data.size(),[](size_t){return 0xff00ff00u;});
    CHECK(!bad.equal && bad.firstBad==43 && bad.actual==0xff00ff01u && bad.expected==0xff00ff00u && bad.checked==4096 && bad.hash!=good.hash);
    std::vector<uint64_t> half(4096,0x3c00000038003800ull);
    auto hg=p::compare(half.data(),half.size(),[](size_t){return p::kPremultipliedHalf;});
    CHECK(hg.equal && hg.checked==4096);
    half[4095]^=uint64_t(1)<<48;
    auto hb=p::compare(half.data(),half.size(),[](size_t){return p::kPremultipliedHalf;});
    CHECK(!hb.equal && hb.firstBad==4095 && hb.checked==4096);
    std::printf("%u independent pixel-oracle and corruption checks; triangle_pixels=%u\n",checks,covered);
}

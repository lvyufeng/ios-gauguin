#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <compression.h>
int main(int c, char **v) {
    FILE *f = fopen(v[1], "rb"); fseek(f,0,SEEK_END); long n=ftell(f); fseek(f,0,SEEK_SET);
    char *in = malloc(n); fread(in,1,n,f); fclose(f);
    size_t cap = 1<<22; char *out = malloc(cap); size_t outsz = cap;
    compression_stream s = {0};
    if (compression_stream_init(&s, COMPRESSION_STREAM_DECODE, COMPRESSION_LZFSE) != 0) return 2;
    s.src_ptr = (uint8_t*)in; s.src_size = n;
    s.dst_ptr = (uint8_t*)out; s.dst_size = outsz;
    int r = compression_stream_process(&s, COMPRESSION_STREAM_FINALIZE);
    printf("result=%d out=%zu\n", r, outsz - s.dst_size);
    FILE *g = fopen(v[2], "wb"); fwrite(out,1,outsz - s.dst_size,g); fclose(g);
    return 0;
}

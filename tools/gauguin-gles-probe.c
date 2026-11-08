/* Compile real GLES shaders with Mesa, render a dynamic checker, sample it into
 * an imported IOSurface and compare every pixel. No software renderer may pass.
 * This is a separate future root probe; never part of the frozen175 image/job.
 */
#define GL_GLEXT_PROTOTYPES 1
#include <GLES3/gl3.h>
#include <GL/osmesa.h>
#include <IOKit/IOKitLib.h>
#include <IOSurface/IOSurfaceRef.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <errno.h>
#include <spawn.h>
#include <sys/wait.h>
#include <mach/mach.h>
extern char **environ;
/* Read-only XNU SPI, also imported by this root's own launchd. Wire layout and
 * command8 are checked against the kernel which runs the probe. No SET command
 * or global memory policy change is made by this executable. */
extern int memorystatus_control(uint32_t,int32_t,uint32_t,void *,size_t);
struct probe_memlimit {
    int32_t active;
    uint32_t active_attr;
    int32_t inactive;
    uint32_t inactive_attr;
};
_Static_assert(sizeof(struct probe_memlimit)==16,"XNU memlimit query wire size");

enum { WIDTH=32, HEIGHT=32, PIXELS=WIDTH*HEIGHT };
struct param {uint32_t pipe,param;uint64_t value;uint32_t len,pad;};
_Static_assert(sizeof(struct param)==24,"msm GET_PARAM wire layout");
static int fail(const char *where)
{fprintf(stderr,"GAUGUIN GLES FAIL: %s\n",where);fflush(stderr);return 1;}
static int memory_checkpoint(const char *phase)
{
    struct probe_memlimit limits={0};
    if(memorystatus_control(8,getpid(),0,&limits,sizeof(limits)))return fail("read actual probe memory limits");
    task_vm_info_data_t vm={0};mach_msg_type_number_t count=TASK_VM_INFO_REV1_COUNT;
    if(task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&vm,&count)!=KERN_SUCCESS||count<TASK_VM_INFO_REV1_COUNT)return fail("read actual probe physical footprint");
    printf("GAUGUIN GLES memory phase=%s active_mb=%d active_attr=%u inactive_mb=%d inactive_attr=%u footprint_bytes=%llu\n",phase,limits.active,limits.active_attr,limits.inactive,limits.inactive_attr,(unsigned long long)vm.phys_footprint);fflush(stdout);
    if(limits.active!=128||limits.inactive!=128||limits.active_attr!=1||limits.inactive_attr!=1)return fail("expected finite128MiB active/inactive hard limits");
    if(!vm.phys_footprint||vm.phys_footprint>UINT64_C(128)*1024*1024)return fail("invalid probe physical footprint for configured limit");
    return 0;
}
static void number(CFMutableDictionaryRef p,CFStringRef key,int32_t value)
{CFNumberRef n=CFNumberCreate(NULL,kCFNumberSInt32Type,&value);CFDictionarySetValue(p,key,n);CFRelease(n);}
static int query_identity(void)
{
    io_service_t service=IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("HakiosGPU"));
    if(!service)return fail("no real HakiosGPU service");
    io_connect_t c=0;kern_return_t rc=IOServiceOpen(service,mach_task_self(),0,&c);IOObjectRelease(service);
    if(rc)return fail("GPU user client open");
    const uint32_t ids[]={1,2,3,6};uint64_t values[4]={0};
    for(unsigned i=0;i<4;i++) {
        struct param p={0x10,ids[i],0,0,0};size_t size=sizeof(p);
        rc=IOConnectCallStructMethod(c,0x40,&p,sizeof(p),&p,&size);
        if(rc||size!=sizeof(p)){IOServiceClose(c);return fail(ids[i]==6?"kernel must implement actual GMEM-base parameter6 before GLES":"hardware query");}
        values[i]=p.value;
    }
    rc=IOServiceClose(c);
    if(rc||values[0]!=619||values[1]!=512*1024||values[2]!=0x06010900||values[3]!=0x100000)return fail("actual A619 identity/configured GMEM differs");
    printf("GAUGUIN GLES identity gpu=%llu chip=%llx gmem=%llu base=%llx\n",(unsigned long long)values[0],(unsigned long long)values[2],(unsigned long long)values[1],(unsigned long long)values[3]);fflush(stdout);return 0;
}
static GLuint shader(GLenum type,const char *source)
{
    GLuint s=glCreateShader(type);glShaderSource(s,1,&source,NULL);glCompileShader(s);GLint ok=0;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);
    if(!ok){char log[2048];GLsizei n=0;glGetShaderInfoLog(s,sizeof(log),&n,log);fprintf(stderr,"GLSL compile: %.*s\n",(int)n,log);glDeleteShader(s);return 0;}return s;
}
static GLuint program(const char *fs)
{
    const char *vs="#version 300 es\nout vec2 uv;\nvoid main(){vec2 p=vec2((gl_VertexID==1)?3.0:-1.0,(gl_VertexID==2)?3.0:-1.0);uv=(p+1.0)*0.5;gl_Position=vec4(p,0.0,1.0);}\n";
    GLuint v=shader(GL_VERTEX_SHADER,vs),f=shader(GL_FRAGMENT_SHADER,fs);if(!v||!f)return 0;
    GLuint p=glCreateProgram();glAttachShader(p,v);glAttachShader(p,f);glLinkProgram(p);glDeleteShader(v);glDeleteShader(f);GLint ok=0;glGetProgramiv(p,GL_LINK_STATUS,&ok);
    if(!ok){char log[2048];GLsizei n=0;glGetProgramInfoLog(p,sizeof(log),&n,log);fprintf(stderr,"GLSL link: %.*s\n",(int)n,log);glDeleteProgram(p);return 0;}return p;
}
static uint32_t expected(uint32_t seed,unsigned x,unsigned y)
{
    unsigned cell=((x/4)+(y/4)+(seed&1))&1;
    unsigned bits=((seed>>1)&7)^(cell?7:0);
    return 0xff000000u|((bits&1)?0x000000ffu:0)|((bits&2)?0x0000ff00u:0)|((bits&4)?0x00ff0000u:0);
}
static int api_then_late_workload(void)
{
    /* One launchd job owns the ordering: the unchanged signed API probe closes
     * its client before Mesa opens one. No simultaneous privileged owners. */
    char *args[]={"/usr/libexec/gauguin-gpu-probe","gwrt-0175-a1",NULL};
    pid_t child=0;
    int rc=posix_spawn(&child,args[0],NULL,NULL,args,environ);
    if(rc)return fail("GPU API child spawn");
    int status=0;pid_t reaped;
    do{reaped=waitpid(child,&status,0);}while(reaped<0&&errno==EINTR);
    if(reaped!=child||!WIFEXITED(status)||WEXITSTATUS(status)!=0)return fail("GPU API child did not pass");
    struct timespec before,after,remaining={90,0};
    if(clock_gettime(CLOCK_MONOTONIC_RAW,&before))return fail("late-workload start clock");
    puts("GAUGUIN GLES preflight=GPU-API-child-PASS idle_seconds=90");fflush(stdout);
    while(nanosleep(&remaining,&remaining))if(errno!=EINTR)return fail("late-workload delay");
    if(clock_gettime(CLOCK_MONOTONIC_RAW,&after))return fail("late-workload end clock");
    int64_t elapsed=((int64_t)after.tv_sec-before.tv_sec)*INT64_C(1000000000)+after.tv_nsec-before.tv_nsec;
    if(elapsed<INT64_C(90000000000))return fail("late-workload delay too short");
    printf("GAUGUIN GLES late-start waited_ns=%llu\n",(unsigned long long)elapsed);fflush(stdout);
    return 0;
}
int main(int argc,char **argv)
{
    if(getuid()!=0)return fail("root-only GPU prototype");
    if(argc==2&&!strcmp(argv[1],"--after-gpu-api")) {
        if(api_then_late_workload())return 1;
    } else if(argc!=1)return fail("unsupported probe arguments");
    if(memory_checkpoint("before-context"))return 1;
    if(query_identity())return 1;
    const int attribs[]={OSMESA_FORMAT,OSMESA_BGRA,OSMESA_DEPTH_BITS,0,OSMESA_STENCIL_BITS,0,OSMESA_PROFILE,OSMESA_ES_PROFILE,OSMESA_CONTEXT_MAJOR_VERSION,3,OSMESA_CONTEXT_MINOR_VERSION,0,0};
    OSMesaContext context=OSMesaCreateContextAttribs(attribs,NULL);uint32_t memory[PIXELS];memset(memory,0x5a,sizeof(memory));
    if(!context)return fail("real ES3 context creation");
    if(memory_checkpoint("context-created"))return 1;
    if(!OSMesaMakeCurrent(context,memory,GL_UNSIGNED_BYTE,WIDTH,HEIGHT))return fail("real ES3 context current");
    if(memory_checkpoint("context-current"))return 1;
    const char *renderer=(const char *)glGetString(GL_RENDERER),*version=(const char *)glGetString(GL_VERSION);
    printf("GAUGUIN GLES renderer=%s version=%s\n",renderer?renderer:"null",version?version:"null");fflush(stdout);
    if(!renderer||!version||(!strstr(renderer,"FD619")&&!strstr(renderer,"Adreno (TM) 619"))||strstr(renderer,"softpipe")||strstr(renderer,"llvmpipe")||!strstr(version,"OpenGL ES 3"))return fail("hardware renderer identity");
    GLuint draw=program("#version 300 es\nprecision highp float;\nuniform vec4 tint;uniform int phase;out vec4 color;void main(){ivec2 p=ivec2(gl_FragCoord.xy);bool odd=((p.x/4+p.y/4+phase)&1)!=0;color=vec4(odd?vec3(1.0)-tint.rgb:tint.rgb,1.0);}\n");
    GLuint sample=program("#version 300 es\nprecision highp float;in vec2 uv;uniform sampler2D src;out vec4 color;void main(){color=texture(src,uv);}\n");
    if(!draw||!sample)return fail("runtime GLSL programs");
    if(memory_checkpoint("programs-linked"))return 1;
    struct timespec t;clock_gettime(CLOCK_MONOTONIC_RAW,&t);uint32_t seed=(uint32_t)t.tv_nsec^((uint32_t)getpid()*0x9e3779b9u);
    GLuint texture=0,framebuffer=0,vao=0;glGenVertexArrays(1,&vao);glBindVertexArray(vao);
    glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,WIDTH,HEIGHT);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
    glGenFramebuffers(1,&framebuffer);glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)return fail("normal framebuffer");
    glViewport(0,0,WIDTH,HEIGHT);glUseProgram(draw);unsigned bits=(seed>>1)&7;
    glUniform4f(glGetUniformLocation(draw,"tint"),(bits&1)?1:0,(bits&2)?1:0,(bits&4)?1:0,1);
    glUniform1i(glGetUniformLocation(draw,"phase"),seed&1);glDrawArrays(GL_TRIANGLES,0,3);glFinish();
    uint32_t result[PIXELS];glReadPixels(0,0,WIDTH,HEIGHT,GL_RGBA,GL_UNSIGNED_BYTE,result);
    if(glGetError()!=GL_NO_ERROR)return fail("normal shader draw/readback GL error");
    uint32_t hash=2166136261u;
    for(unsigned i=0;i<PIXELS;i++) {
        if(result[i]!=expected(seed,i%WIDTH,i/WIDTH)){fprintf(stderr,"normal mismatch pixel=%u actual=%08x expected=%08x\n",i,result[i],expected(seed,i%WIDTH,i/WIDTH));return 1;}
        hash=(hash^result[i])*16777619u;
    }
    printf("GAUGUIN GLES normal seed=%u pixels=%u hash=%08x\n",seed,PIXELS,hash);fflush(stdout);
    if(memory_checkpoint("normal-readback"))return 1;
    CFMutableDictionaryRef props=CFDictionaryCreateMutable(NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
    number(props,kIOSurfaceWidth,WIDTH);number(props,kIOSurfaceHeight,HEIGHT);number(props,kIOSurfaceBytesPerRow,4*WIDTH);number(props,kIOSurfaceBytesPerElement,4);number(props,kIOSurfacePixelFormat,0x42475241);
    number(props,CFSTR("IOSurfaceOffset"),64);number(props,kIOSurfaceAllocSize,16384);
    IOSurfaceRef surface=IOSurfaceCreate(props);CFRelease(props);if(!surface)return fail("IOSurface create");
    if(IOSurfaceLock(surface,0,NULL))return fail("surface init lock");
    void *base=IOSurfaceGetBaseAddress(surface);if(!base)return fail("surface base");memset(base,0xa5,PIXELS*4);
    if(IOSurfaceUnlock(surface,0,NULL))return fail("surface init unlock");
    typedef void (*ImportImage)(GLenum,void *);
    ImportImage import=(ImportImage)OSMesaGetProcAddress("glEGLImageTargetTexture2DOES");if(!import)return fail("IOSurface import entry");
    GLuint shared=0;glGenTextures(1,&shared);glBindTexture(GL_TEXTURE_2D,shared);import(GL_TEXTURE_2D,(void *)(uintptr_t)IOSurfaceGetID(surface));
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,shared,0);
    if(glGetError()!=GL_NO_ERROR||glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)return fail("IOSurface framebuffer/import");
    glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,texture);glUseProgram(sample);glUniform1i(glGetUniformLocation(sample,"src"),0);glDrawArrays(GL_TRIANGLES,0,3);glFinish();
    if(glGetError()!=GL_NO_ERROR)return fail("IOSurface sampled draw/fence");
    if(IOSurfaceLock(surface,kIOSurfaceLockReadOnly,NULL))return fail("surface result lock");
    volatile uint32_t *pixels=(volatile uint32_t *)IOSurfaceGetBaseAddress(surface);if(!pixels)return fail("surface result base");hash=2166136261u;
    for(unsigned i=0;i<PIXELS;i++) {
        uint32_t rgba=expected(seed,i%WIDTH,i/WIDTH);uint32_t bgra=(rgba&0xff00ff00u)|((rgba&0xffu)<<16)|((rgba>>16)&0xffu);uint32_t have=pixels[i];
        if(have!=bgra){fprintf(stderr,"surface mismatch pixel=%u actual=%08x expected=%08x\n",i,have,bgra);return 1;}
        hash=(hash^have)*16777619u;
    }
    if(IOSurfaceUnlock(surface,kIOSurfaceLockReadOnly,NULL))return fail("surface result unlock");
    printf("GAUGUIN GLES surface seed=%u pixels=%u hash=%08x\n",seed,PIXELS,hash);fflush(stdout);
    if(memory_checkpoint("surface-readback"))return 1;
    glBindFramebuffer(GL_FRAMEBUFFER,0);glDeleteFramebuffers(1,&framebuffer);glDeleteTextures(1,&shared);glDeleteTextures(1,&texture);glDeleteVertexArrays(1,&vao);glDeleteProgram(sample);glDeleteProgram(draw);CFRelease(surface);OSMesaDestroyContext(context);
    puts("GAUGUIN GLES PASS real-GLSL-draw-texture-IOSurface");return 0;
}

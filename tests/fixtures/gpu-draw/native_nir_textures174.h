/* SPDX-License-Identifier: MIT
 * Authored texture NIR. Unchanged Mesa NIR/IR3 produces all ISA/program state.
 * Same173 full-screen triangle and smooth UV. Sampler0, 2D normalized nearest,
 * LOD0 and clamp-to-edge: RG UV, GR UV, then U+1 clamp control. No fragcoord,
 * UBO/SSBO/image store, CPU sampling implementation, or hand-written ISA.
 */
#ifndef GAUGUIN_NATIVE_NIR_TEXTURES174_H
#define GAUGUIN_NATIVE_NIR_TEXTURES174_H
#include "native_nir_varyings173.h"
static nir_shader *draw174_fragment_nir(const nir_shader_compiler_options *options,
                                      unsigned profile)
{
   assert(profile<3);
   nir_builder b=nir_builder_init_simple_shader(MESA_SHADER_FRAGMENT,options,
                                               "gauguin 2D nearest texture FS");
   nir_variable *uv=nir_variable_create(b.shader,nir_var_shader_in,glsl_vec2_type(),"vertexUV");
   uv->data.location=VARYING_SLOT_VAR0;uv->data.interpolation=INTERP_MODE_SMOOTH;
   nir_variable *sampler=nir_variable_create(b.shader,nir_var_uniform,
      glsl_sampler_type(GLSL_SAMPLER_DIM_2D,false,false,GLSL_TYPE_FLOAT),"texture0");
   sampler->data.binding=0;sampler->data.descriptor_set=0;
   sampler->data.explicit_binding=true;
   /* Mandatory authored opaque-resource usage, as in native nir_draw_helpers. */
   BITSET_SET(b.shader->info.textures_used,0);
   BITSET_SET(b.shader->info.samplers_used,0);
   nir_variable *color=nir_variable_create(b.shader,nir_var_shader_out,glsl_vec4_type(),"fragColor");
   color->data.location=FRAG_RESULT_DATA0;
   nir_def *rg=nir_load_var(&b,uv),*r=nir_channel(&b,rg,0),*g=nir_channel(&b,rg,1);
   if(profile==1){nir_def *tmp=r;r=g;g=tmp;}
   if(profile==2)r=nir_fadd_imm(&b,r,1.0f);
   nir_deref_instr *deref=nir_build_deref_var(&b,sampler);
   nir_tex_instr *tex=nir_tex_instr_create(b.shader,4);
   tex->op=nir_texop_txl;tex->sampler_dim=GLSL_SAMPLER_DIM_2D;
   tex->dest_type=nir_type_float32;tex->coord_components=2;
   tex->src[0].src_type=nir_tex_src_texture_deref;tex->src[0].src=nir_src_for_ssa(&deref->def);
   tex->src[1].src_type=nir_tex_src_sampler_deref;tex->src[1].src=nir_src_for_ssa(&deref->def);
   tex->src[2].src_type=nir_tex_src_coord;tex->src[2].src=nir_src_for_ssa(nir_vec2(&b,r,g));
   tex->src[3].src_type=nir_tex_src_lod;tex->src[3].src=nir_src_for_ssa(nir_imm_float(&b,0));
   nir_def_init(&tex->instr,&tex->def,4,32);nir_builder_instr_insert(&b,&tex->instr);
   nir_store_var(&b,color,&tex->def,15);
   return b.shader;
}
#endif

/* SPDX-License-Identifier: MIT
 * Authored NIR inputs for unchanged Mesa24.3.4 NIR/IR3/A619 emitters.
 * Vertex IDs0,1,2: clip(-1,-1),(3,-1),(-1,3), all W1; varying
 * (0,0),(2,0),(0,2). Scale8/translate8 yields window(0,0),(32,0),(0,32).
 * On the16x16 target a pixel center(x+.5,y+.5) has smooth varying
 * ((2*x+1)/32,(2*y+1)/32). Equal W makes perspective interpolation affine.
 * FS writes varying RG or GR, blue1/4, alpha1 to RGBA8_UNORM.
 * Flat control uses the first provoking vertex(0,0). No resource reads,
 * fragment-coordinate substitution, hand ISA or framebuffer emulation.
 * Pixel values are source expectations, never evidence of hardware output.
 */
#ifndef GAUGUIN_NATIVE_NIR_VARYINGS173_H
#define GAUGUIN_NATIVE_NIR_VARYINGS173_H
#include "native_nir_programs.h"

static nir_shader *
draw173_vertex_nir(const nir_shader_compiler_options *options)
{
   nir_builder b = nir_builder_init_simple_shader(MESA_SHADER_VERTEX, options,
                                                 "gauguin varying RG VS");
   nir_variable *position = nir_variable_create(b.shader, nir_var_shader_out,
                                               glsl_vec4_type(), "gl_Position");
   position->data.location = VARYING_SLOT_POS;
   nir_variable *varying = nir_variable_create(b.shader, nir_var_shader_out,
                                              glsl_vec2_type(), "vertexRG");
   varying->data.location = VARYING_SLOT_VAR0;
   varying->data.interpolation = INTERP_MODE_SMOOTH;
   nir_def *id = nir_load_vertex_id(&b);
   nir_def *r = nir_u2f32(&b, nir_iand_imm(&b, nir_ishl_imm(&b, id, 1), 2));
   nir_def *g = nir_u2f32(&b, nir_iand_imm(&b, id, 2));
   nir_def *x = nir_fadd_imm(&b, nir_fmul_imm(&b, r, 2.0f), -1.0f);
   nir_def *y = nir_fadd_imm(&b, nir_fmul_imm(&b, g, 2.0f), -1.0f);
   nir_store_var(&b, position, nir_vec4(&b, x, y, nir_imm_float(&b, 0.0f),
                                      nir_imm_float(&b, 1.0f)), 0xf);
   nir_store_var(&b, varying, nir_vec2(&b, r, g), 3);
   return b.shader;
}

static nir_shader *
draw173_fragment_nir(const nir_shader_compiler_options *options,
                     bool swap, bool flat)
{
   nir_builder b = nir_builder_init_simple_shader(MESA_SHADER_FRAGMENT, options,
                         flat ? "gauguin flat RG FS" :
                         swap ? "gauguin smooth GR FS" : "gauguin smooth RG FS");
   nir_variable *varying = nir_variable_create(b.shader, nir_var_shader_in,
                                              glsl_vec2_type(), "vertexRG");
   varying->data.location = VARYING_SLOT_VAR0;
   varying->data.interpolation = flat ? INTERP_MODE_FLAT : INTERP_MODE_SMOOTH;
   nir_variable *color = nir_variable_create(b.shader, nir_var_shader_out,
                                            glsl_vec4_type(), "fragColor");
   color->data.location = FRAG_RESULT_DATA0;
   nir_def *rg = nir_load_var(&b, varying);
   nir_def *r = nir_channel(&b, rg, swap ? 1 : 0);
   nir_def *g = nir_channel(&b, rg, swap ? 0 : 1);
   nir_store_var(&b, color, nir_vec4(&b, r, g, nir_imm_float(&b, 0.25f),
                                   nir_imm_float(&b, 1.0f)), 0xf);
   return b.shader;
}
#endif

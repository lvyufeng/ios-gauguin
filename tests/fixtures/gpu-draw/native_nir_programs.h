/* SPDX-License-Identifier: MIT
 * Input programs for the unmodified Mesa24.3.4 NIR/IR3 compiler.
 * These are authored NIR inputs, not hand-written shader ISA or GPU emulation.
 * With scale1 and vertex IDs0,1,2 the positions are (-1,-1), (3,-1), (-1,3).
 * Future rasterization needs separate physical evidence and a pixel oracle.
 */
#ifndef GAUGGUIN_NATIVE_NIR_PROGRAMS_H
#define GAUGGUIN_NATIVE_NIR_PROGRAMS_H
#include "nir_builder.h"

static nir_shader *
draw171_vertex_nir(const nir_shader_compiler_options *options, float scale)
{
   nir_builder b = nir_builder_init_simple_shader(MESA_SHADER_VERTEX, options,
                                                 "gauguin triangle VS");
   nir_variable *position = nir_variable_create(b.shader, nir_var_shader_out,
                                               glsl_vec4_type(), "gl_Position");
   position->data.location = VARYING_SLOT_POS;
   nir_def *id = nir_load_vertex_id(&b);
   nir_def *x = nir_u2f32(&b, nir_iand_imm(&b, nir_ishl_imm(&b, id, 1), 2));
   nir_def *y = nir_u2f32(&b, nir_iand_imm(&b, id, 2));
   x = nir_fadd_imm(&b, nir_fmul_imm(&b, x, 2.0f * scale), -scale);
   y = nir_fadd_imm(&b, nir_fmul_imm(&b, y, 2.0f * scale), -scale);
   nir_store_var(&b, position, nir_vec4(&b, x, y, nir_imm_float(&b, 0.0f),
                                      nir_imm_float(&b, 1.0f)), 0xf);
   return b.shader;
}

static nir_shader *
draw171_fragment_nir(const nir_shader_compiler_options *options, bool red)
{
   nir_builder b = nir_builder_init_simple_shader(MESA_SHADER_FRAGMENT, options,
                                                 "gauguin constant FS");
   nir_variable *color = nir_variable_create(b.shader, nir_var_shader_out,
                                            glsl_vec4_type(), "fragColor");
   color->data.location = FRAG_RESULT_DATA0;
   nir_store_var(&b, color, nir_imm_vec4(&b, red ? 1.0f : 0.0f,
                                      red ? 0.0f : 1.0f, 0.0f, 1.0f), 0xf);
   return b.shader;
}
#endif

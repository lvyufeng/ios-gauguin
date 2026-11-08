/* SPDX-License-Identifier: MIT
 * Authored NIR input for the unchanged Mesa24.3.4 A619 compiler.
 * Vertex IDs0,1,2 produce (-15/32,-15/32), (49/32,-15/32),
 * (-15/32,49/32), with z0/w1. Viewport scale8/translate8 gives
 * (4.25,4.25), (20.25,4.25), (4.25,20.25). Every single-sample
 * pixel center is strictly on one side of each edge: no tie-rule oracle.
 * The 16x16 target has116 interior green centers and140 blue background
 * centers. These are geometric expected values, NOT observed GPU pixels.
 * Keep the original171 input programs and full-green shader bytes intact.
 */
#ifndef GAUGUIN_NATIVE_NIR_CONTROLS_H
#define GAUGUIN_NATIVE_NIR_CONTROLS_H
#include "native_nir_programs.h"

static nir_shader *
draw172_inset_vertex_nir(const nir_shader_compiler_options *options)
{
   nir_builder b = nir_builder_init_simple_shader(MESA_SHADER_VERTEX, options,
                                                 "gauguin inset coverage VS");
   nir_variable *position = nir_variable_create(b.shader, nir_var_shader_out,
                                               glsl_vec4_type(), "gl_Position");
   position->data.location = VARYING_SLOT_POS;
   nir_def *id = nir_load_vertex_id(&b);
   nir_def *x = nir_u2f32(&b, nir_iand_imm(&b, nir_ishl_imm(&b, id, 1), 2));
   nir_def *y = nir_u2f32(&b, nir_iand_imm(&b, id, 2));
   x = nir_fadd_imm(&b, x, -15.0f / 32.0f);
   y = nir_fadd_imm(&b, y, -15.0f / 32.0f);
   nir_store_var(&b, position, nir_vec4(&b, x, y, nir_imm_float(&b, 0.0f),
                                      nir_imm_float(&b, 1.0f)), 0xf);
   return b.shader;
}
#endif

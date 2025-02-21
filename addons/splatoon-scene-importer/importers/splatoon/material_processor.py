import os
import bpy
import re

class MaterialProcessor:
    def __init__(self, material, file_path):
        self.material = material
        self.file_path = file_path
        self.base_name = self._find_base_texture() or self._find_base_from_material()
        self.principled_node = self._init_principled_node()
        self.base_x_position = self.principled_node.location.x - 900

        # 2nd texture의 영향을 받지않은 node보관용 emission에서 사용한다
        self.base_color_node = self._init_base_color_node()

    def _init_principled_node(self):
        principled = None
        for node in self.material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break

        if principled is None:
            principled = self.material.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')

        principled.inputs['Base Color'].default_value = (0, 0, 0, 1)

        return principled

    def _init_base_color_node(self):
        ao_node = self.import_texture('_ao', non_color=True, location_y=self.principled_node.location.y + 50)
        tcl_node = self.import_texture('_tcl', non_color=True, location_y=self.principled_node.location.y + 100)

        if not self.principled_node.inputs['Base Color'].is_linked:
            return None

        base_color_node = self.principled_node.inputs['Base Color'].links[0].from_node
        base_color_node.location = (self.base_x_position, self.principled_node.location.y)
        base_color_node.hide = True

        alb_multiple_node = self.material.node_tree.nodes.new('ShaderNodeMixRGB')
        alb_multiple_node.location = (base_color_node.location.x + 300, base_color_node.location.y + 100)
        alb_multiple_node.label = 'Alb Multiply'
        alb_multiple_node.blend_type = 'MULTIPLY'
        alb_multiple_node.inputs['Fac'].default_value = 1.0
        alb_multiple_node.inputs[2].default_value = (1, 1, 1, 1)
        self.material.node_tree.links.new(base_color_node.outputs['Color'], alb_multiple_node.inputs[1])
        final_base_node = alb_multiple_node

        if ao_node:
            ao_multiple_color_node = self.material.node_tree.nodes.new('ShaderNodeMixRGB')
            ao_multiple_color_node.blend_type = 'MULTIPLY'
            ao_multiple_color_node.inputs['Fac'].default_value = 1.0
            ao_multiple_color_node.inputs[2].default_value = (1, 1, 1, 1)
            ao_multiple_color_node.location = (final_base_node.location.x + 200, final_base_node.location.y)
            ao_multiple_color_node.hide = True
            self.material.node_tree.links.new(final_base_node.outputs['Color'], ao_multiple_color_node.inputs[1])
            self.material.node_tree.links.new(ao_node.outputs['Color'], ao_multiple_color_node.inputs[2])
            final_base_node = ao_multiple_color_node

        if tcl_node:
            mix_color_node = self.material.node_tree.nodes.new('ShaderNodeMixRGB')
            mix_color_node.label = 'Tcl Mix'
            mix_color_node.blend_type = 'MIX'
            mix_color_node.inputs[2].default_value = (1, 1, 1, 1)
            mix_color_node.location = (final_base_node.location.x + 200, final_base_node.location.y)
            self.material.node_tree.links.new(final_base_node.outputs['Color'], mix_color_node.inputs[1])
            self.material.node_tree.links.new(tcl_node.outputs['Color'], mix_color_node.inputs['Fac'])
            final_base_node = mix_color_node

        self.material.node_tree.links.new(final_base_node.outputs['Color'], self.principled_node.inputs['Base Color'])

        return final_base_node

    def _find_base_texture(self):
        # Define base suffixes
        suffixes = ['_alb', '_emm', '_emi']

        # 각 suffix를 정규표현식 패턴으로 변환
        # re.escape()를 사용하여 특수문자가 있을 경우 처리
        patterns = [re.compile(re.escape(suffix), re.IGNORECASE) for suffix in suffixes]

        for node in self.material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                image_path = bpy.path.abspath(node.image.filepath)
                basename = os.path.basename(image_path)

                # 각 패턴에 대해 검사
                for pattern, original_suffix in zip(patterns, suffixes):
                    match = pattern.search(basename)
                    if match:
                        # 실제 찾은 suffix를 사용
                        # found_suffix = basename[match.start():match.end()]
                        base_name = basename[:match.start()]
                        return base_name

        return None

    def _find_base_from_material(self):
        """Extract base_name from the material name."""
        if not self.material:
            return None  # If no material is provided, return None

        # Remove suffixes like '.001', '.002', etc.
        return self.material.name.split('.')[0]

    def import_texture(self, suffix, non_color=False, location_x=None, location_y=0):
        if not location_x:
            location_x = self.base_x_position

        # Find the actual texture file with case-insensitive suffix
        def find_texture_file(dir_path, base, sfx):
            # Get all files in the directory
            try:
                files = os.listdir(dir_path)
                expected_filename = f"{base}{sfx}.png"

                # Case-insensitive search for the file
                for file in files:
                    if file.lower() == expected_filename.lower():
                        return os.path.join(dir_path, file)
            except (OSError, FileNotFoundError):
                return None
            return None

        texture_path = find_texture_file(self.file_path, self.base_name, suffix)
        if not texture_path:
            return False

        # Create a new image texture node
        tex_image_node = self.material.node_tree.nodes.new('ShaderNodeTexImage')
        tex_image_node.image = bpy.data.images.load(texture_path)
        tex_image_node.hide = True
        tex_image_node.location = (location_x, location_y)

        if non_color:
            tex_image_node.image.colorspace_settings.name = 'Non-Color'

        return tex_image_node

    def link_texture_principled_node(self, input_name, suffix, non_color=False, location_x=None, location_y=0):
        if not location_x:
            location_x = self.base_x_position

        # 블랜더가 자동으로 import한것은 신뢰한다
        if self.principled_node.inputs[input_name].is_linked:
            already_node = self.principled_node.inputs[input_name].links[0].from_node
            already_node.location = (location_x, location_y)
            already_node.hide = True
            return

        tex_image_node = self.import_texture(suffix, non_color, location_x, location_y)
        if tex_image_node:
            self.material.node_tree.links.new(tex_image_node.outputs['Color'], self.principled_node.inputs[input_name])

    def import_alpha(self):
        if self.principled_node.inputs['Alpha'].is_linked:
            imported_alpha_node = self.principled_node.inputs['Alpha'].links[0].from_node
            self.material.node_tree.links.remove(self.principled_node.inputs['Alpha'].links[0])
            self.material.node_tree.nodes.remove(imported_alpha_node)

        alpha_node = self.import_texture('_opa', non_color=True)

        if alpha_node:
            alpha_node.hide = True
            alpha_node.location = (self.base_x_position, self.principled_node.location.y - 135)
            math_node = self.material.node_tree.nodes.new('ShaderNodeMath')
            math_node.hide = True
            math_node.location = (alpha_node.location.x + 700, alpha_node.location.y)
            math_node.operation = 'GREATER_THAN'
            self.material.node_tree.links.new(alpha_node.outputs['Color'], math_node.inputs['Value'])
            self.material.node_tree.links.new(math_node.outputs['Value'], self.principled_node.inputs['Alpha'])

    def import_normal(self):
        tex_image_node = self.import_texture('_nrm', non_color=True)
        if not tex_image_node:
            return

        for link in self.material.node_tree.links:
            if (link.to_node == self.principled_node and link.to_socket.name == 'Normal'):
                normal_map_node = link.from_node

        if not normal_map_node:
            normal_map_node = self.material.node_tree.nodes.new('ShaderNodeNormalMap')
            self.material.node_tree.links.new(normal_map_node.outputs['Normal'], self.principled_node.inputs['Normal'])
        normal_map_node.hide = True

        tex_image_node.location = (self.base_x_position, self.principled_node.location.y - 180)
        normal_map_node.location = (tex_image_node.location.x + 300, tex_image_node.location.y)

        self.material.node_tree.links.new(tex_image_node.outputs['Color'], normal_map_node.inputs['Color'])

    def import_second_color(self):
        trm_node = self.import_texture('_trm', location_y=self.principled_node.location.y + 300)
        mai_node = self.import_texture('_mai', non_color=True, location_y=self.principled_node.location.y + 500)
        thc_node = self.import_texture('_thc', non_color=True, location_y=self.principled_node.location.y + 600)
        if not self.principled_node.inputs['Base Color'].is_linked or (not trm_node and not mai_node and not thc_node):
            return
        base_color_node = self.principled_node.inputs['Base Color'].links[0].from_node
        nodes = self.material.node_tree.nodes
        links = self.material.node_tree.links

        # Create and setup screen node
        screen_node = nodes.new('ShaderNodeMixRGB')
        screen_node.blend_type = 'SCREEN'
        screen_node.inputs['Fac'].default_value = 1.0
        screen_node.inputs[2].default_value = (0, 0, 0, 1)
        screen_node.hide = True
        screen_node.location = (self.principled_node.location.x, self.principled_node.location.y + 200)
        links.new(base_color_node.outputs['Color'], screen_node.inputs[1])
        second_texture_node = screen_node

        # trm process
        if trm_node:
            trm_multiple_node = nodes.new('ShaderNodeMixRGB')
            trm_multiple_node.label = 'Trm Multiply'
            trm_multiple_node.blend_type = 'MULTIPLY'
            trm_multiple_node.inputs['Fac'].default_value = 1.0
            trm_multiple_node.inputs[2].default_value = (0, 0, 0, 1)
            trm_multiple_node.location = (trm_node.location.x + 300, trm_node.location.y)
            links.new(trm_node.outputs['Color'], trm_multiple_node.inputs[1])

            trm_second_screen_node = nodes.new('ShaderNodeMixRGB')
            trm_second_screen_node.label = 'Trm Second Screen'
            trm_second_screen_node.blend_type = 'SCREEN'
            trm_second_screen_node.inputs['Fac'].default_value = 1.0
            trm_second_screen_node.inputs[2].default_value = (0, 0, 0, 1)
            links.new(trm_multiple_node.outputs['Color'], trm_second_screen_node.inputs[1])
            trm_second_screen_node.location = (trm_node.location.x + 500, trm_node.location.y)
            second_texture_node = trm_second_screen_node

        # mai process
        if mai_node:
            mai_multiple_node = nodes.new('ShaderNodeMixRGB')
            mai_multiple_node.blend_type = 'MULTIPLY'
            mai_multiple_node.hide = True
            mai_multiple_node.location = (mai_node.location.x + 700, mai_node.location.y)
            mai_multiple_node.inputs['Fac'].default_value = 1.0
            links.new(mai_node.outputs['Color'], mai_multiple_node.inputs[2])
            links.new(second_texture_node.outputs['Color'], mai_multiple_node.inputs[1])
            second_texture_node = mai_multiple_node

        # connect second_texture_node
        if second_texture_node != screen_node:
            links.new(second_texture_node.outputs['Color'], screen_node.inputs[2])

        # thc process
        if thc_node:
            invert_node = nodes.new('ShaderNodeInvert')
            invert_node.hide = True
            invert_node.location = (thc_node.location.x + 300, thc_node.location.y)
            links.new(thc_node.outputs['Color'], invert_node.inputs['Color'])
            links.new(invert_node.outputs['Color'], screen_node.inputs[0])

        # final connect base color
        links.new(screen_node.outputs['Color'], self.principled_node.inputs['Base Color'])

    def import_second_shader(self):
        """
        Import and setup shader-related textures (_trm and _thc).
        Sets up complex shader mixing with translucent BSDF when _trm exists,
        and optionally connects _thc as a factor if present.
        """
        trm_node = self.import_texture('_trm', location_y=self.principled_node.location.y + 300)
        thc_node = self.import_texture('_thc', non_color=True, location_y=self.principled_node.location.y + 600)
        mai_node = self.import_texture('_mai', non_color=True, location_y=self.principled_node.location.y + 800)

        if trm_node:
            nodes = self.material.node_tree.nodes
            links = self.material.node_tree.links

            # Create and setup multiply mix node
            multiple_color_node = nodes.new('ShaderNodeMixRGB')
            multiple_color_node.label = 'Trm Multiply'
            multiple_color_node.blend_type = 'MULTIPLY'
            multiple_color_node.inputs['Fac'].default_value = 1.0
            multiple_color_node.inputs[2].default_value = (0, 0, 0, 1)
            multiple_color_node.location = (trm_node.location.x + 300, trm_node.location.y)

            # Connect _trm to mix color
            links.new(trm_node.outputs['Color'], multiple_color_node.inputs[1])  # A input

            # Create and setup toBSDF
            to_shade_node = nodes.new('ShaderNodeBsdfDiffuse')
            to_shade_node.location = (multiple_color_node.location.x + 200, multiple_color_node.location.y)
            to_shade_node.hide = True
            links.new(multiple_color_node.outputs['Color'], to_shade_node.inputs['Color'])

            # Create 2nd trm RGB node
            second_trm_rgb_node = nodes.new('ShaderNodeRGB')
            second_trm_rgb_node.outputs[0].default_value = (0, 0, 0, 1)
            second_trm_rgb_node.label = 'Trm Second Color'
            second_trm_rgb_node.location = (multiple_color_node.location.x, multiple_color_node.location.y + 200)

            # Create and set 2nd toBSDF
            second_to_shade_node = nodes.new('ShaderNodeBsdfDiffuse')
            second_to_shade_node.location = (to_shade_node.location.x, to_shade_node.location.y + 200)
            second_to_shade_node.hide = True
            links.new(second_trm_rgb_node.outputs['Color'], second_to_shade_node.inputs['Color'])

            # Connect normal to toBSDF
            if self.principled_node.inputs['Normal'].is_linked:
                links.new(self.principled_node.inputs['Normal'].links[0].from_node.outputs[0], to_shade_node.inputs['Normal'])
                links.new(self.principled_node.inputs['Normal'].links[0].from_node.outputs[0], second_to_shade_node.inputs['Normal'])

            # Connect rgh to toBSDF
            if self.principled_node.inputs['Roughness'].is_linked:
                links.new(self.principled_node.inputs['Roughness'].links[0].from_node.outputs[0], to_shade_node.inputs['Roughness'])
                links.new(self.principled_node.inputs['Roughness'].links[0].from_node.outputs[0], second_to_shade_node.inputs['Roughness'])

            # 200% mix shade
            trm_add_shader_node = nodes.new('ShaderNodeAddShader')
            trm_add_shader_node.hide = True
            trm_add_shader_node.location = (to_shade_node.location.x + 200, to_shade_node.location.y)
            links.new(to_shade_node.outputs['BSDF'], trm_add_shader_node.inputs[0])
            links.new(second_to_shade_node.outputs['BSDF'], trm_add_shader_node.inputs[1])

            # knob shade
            knob_mix_shader_node = nodes.new('ShaderNodeMixShader')
            knob_mix_shader_node.location = (trm_add_shader_node.location.x + 200, trm_add_shader_node.location.y)
            knob_mix_shader_node.inputs['Fac'].default_value = 0.5 # default to 100%
            links.new(trm_add_shader_node.outputs['Shader'], knob_mix_shader_node.inputs[2])

            final_shade = knob_mix_shader_node

            if thc_node:
                thc_mix_shader_node = nodes.new('ShaderNodeMixShader')
                thc_mix_shader_node.hide = True
                thc_mix_shader_node.location = (final_shade.location.x + 200, final_shade.location.y)
                links.new(thc_node.outputs['Color'], thc_mix_shader_node.inputs['Fac'])
                links.new(final_shade.outputs['Shader'], thc_mix_shader_node.inputs[1])
                final_shade = thc_mix_shader_node

            if mai_node:
                mai_mix_shader_node = nodes.new('ShaderNodeMixShader')
                mai_mix_shader_node.hide = True
                mai_mix_shader_node.location = (final_shade.location.x + 200, final_shade.location.y)
                links.new(mai_node.outputs['Color'], mai_mix_shader_node.inputs['Fac'])
                links.new(final_shade.outputs['Shader'], mai_mix_shader_node.inputs[2])
                final_shade = mai_mix_shader_node

            # Create Final add shader
            add_shader_node = nodes.new('ShaderNodeAddShader')
            add_shader_node.location = (self.principled_node.location.x + 400, self.principled_node.location.y)
            links.new(final_shade.outputs['Shader'], add_shader_node.inputs[0])
            links.new(self.principled_node.outputs['BSDF'], add_shader_node.inputs[1])

            # Connect to material output
            output_node = self.principled_node.outputs['BSDF'].links[0].to_node
            if not output_node:
                output_node = nodes.new('ShaderNodeOutputMaterial')

            output_node.location = (add_shader_node.location.x + 200, add_shader_node.location.y)

            links.new(add_shader_node.outputs['Shader'], output_node.inputs['Surface'])

    def _is_grayscale_image(self, image):
        """흑백 이미지 여부 확인"""
        pixels = image.pixels[:]
        for i in range(0, len(pixels), 4):  # RGBA -> 4개씩 묶음
            r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
            if r != g or g != b or b != r:
                return False  # 색상이 다르면 컬러
        return True  # 모두 동일하면 흑백

    def import_emission(self):
        emission_node = None
        if self.principled_node.inputs['Emission Color'].is_linked:
            emission_node = self.principled_node.inputs['Emission Color'].links[0].from_node
        else:
            emission_node = self.import_texture('_emm')
            if not emission_node:
                emission_node = self.import_texture('_emi')

        if emission_node and emission_node.image:
            emission_node.hide = True
            emission_node.location = (self.base_x_position, self.principled_node.location.y - 250)
            mix_node = self.material.node_tree.nodes.new('ShaderNodeMixRGB')
            mix_node.blend_type = 'MULTIPLY'
            mix_node.inputs['Fac'].default_value = 1.0
            mix_node.location = (emission_node.location.x + 300, emission_node.location.y)
            mix_node.hide = True

            if self.base_color_node:
                self.material.node_tree.links.new(self.base_color_node.outputs['Color'], mix_node.inputs[1])
            self.material.node_tree.links.new(emission_node.outputs['Color'], mix_node.inputs[2])

            final_output_node = mix_node

            if self._is_grayscale_image(emission_node.image):
                emission_node.image.colorspace_settings.name = 'Non-Color'

                multiply_node = self.material.node_tree.nodes.new('ShaderNodeMixRGB')
                multiply_node.label = 'Emm Multiply'
                multiply_node.blend_type = 'MULTIPLY'
                multiply_node.inputs['Fac'].default_value = 1.0
                multiply_node.inputs[2].default_value = (1, 1, 1, 1)
                multiply_node.location = (mix_node.location.x + 200, mix_node.location.y)

                self.material.node_tree.links.new(mix_node.outputs['Color'], multiply_node.inputs[1])
                final_output_node = multiply_node

            # 최종 출력 연결
            self.material.node_tree.links.new(final_output_node.outputs['Color'], self.principled_node.inputs['Emission Color'])
            self.principled_node.inputs['Emission Strength'].default_value = 1.0

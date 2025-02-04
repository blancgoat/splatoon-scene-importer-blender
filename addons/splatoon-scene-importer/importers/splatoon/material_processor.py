import os
import bpy
import re

class MaterialProcessor:
    def __init__(self, material, file_path):
        self.material = material
        self.file_path = file_path
        self.base_name = self._find_base_texture() or self._find_base_from_material()
        self.principled_node = self._find_principled_node()
        self.base_color_node = self._find_base_color_node()
        self.base_x_position = self.principled_node.location.x - 900
        if self.base_color_node:
            self.base_color_node.location = (self.base_x_position, self.principled_node.location.y)
            self.base_color_node.hide = True

    def _find_principled_node(self):
        """Find the Principled BSDF node in the material."""
        for node in self.material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                return node
        return None
    
    def _find_base_color_node(self):
        base_color_input = self.principled_node.inputs['Base Color']
        if base_color_input.is_linked:
            return base_color_input.links[0].from_node
        else:
            return None

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

    def link_texture_principled_node(self, tex_image_node, input_name):
        if not tex_image_node:
            return
        self.material.node_tree.links.new(tex_image_node.outputs['Color'], self.principled_node.inputs[input_name])

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

    def import_tcl(self):
        # Get the current connection to Base Color
        base_color_input = self.principled_node.inputs['Base Color']
        original_color_node = base_color_input.links[0].from_node if base_color_input.is_linked else None

        # Handle _tcl texture
        tcl_node = self.import_texture('_tcl', non_color=True, location_y=self.principled_node.location.y + 100)
        if tcl_node:
            # Create mix node for TCL
            mix_color_node = self.material.node_tree.nodes.new('ShaderNodeMixRGB')
            mix_color_node.label = 'Tcl Mix'
            mix_color_node.blend_type = 'MIX'
            mix_color_node.inputs[2].default_value = (1, 1, 1, 1)
            mix_color_node.location = (tcl_node.location.x + 300, tcl_node.location.y)

            # Connect nodes
            if original_color_node:
                self.material.node_tree.links.new(original_color_node.outputs['Color'], mix_color_node.inputs[1])
            self.material.node_tree.links.new(tcl_node.outputs['Color'], mix_color_node.inputs[0])  # Factor
            self.material.node_tree.links.new(mix_color_node.outputs['Color'], self.principled_node.inputs['Base Color'])

    def import_second_color(self):
        base_color_input = self.principled_node.inputs['Base Color']
        alb_node = base_color_input.links[0].from_node if base_color_input.is_linked else None
        trm_node = self.import_texture('_trm', location_y=self.principled_node.location.y + 300)

        if not (alb_node and trm_node):
            return
        
        nodes = self.material.node_tree.nodes
        links = self.material.node_tree.links
        
        # Create and setup screen node
        screen_node = nodes.new('ShaderNodeMixRGB')
        screen_node.blend_type = 'SCREEN'
        screen_node.inputs['Fac'].default_value = 1.0
        screen_node.hide = True
        screen_node.location = (self.principled_node.location.x - 200, self.principled_node.location.y)
        
        # alb process
        alb_multiple_node = nodes.new('ShaderNodeMixRGB')
        alb_multiple_node.label = 'Alb Multiply'
        alb_multiple_node.blend_type = 'MULTIPLY'
        alb_multiple_node.inputs['Fac'].default_value = 1.0
        alb_multiple_node.inputs[2].default_value = (1, 1, 1, 1)
        alb_multiple_node.location = (self.base_color_node.location.x + 500, self.base_color_node.location.y)
        links.new(alb_node.outputs['Color'], alb_multiple_node.inputs[1])
        links.new(alb_multiple_node.outputs['Color'], screen_node.inputs[1])

        # trm process
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

        # mai process (optional)
        mai_node = self.import_texture('_mai', non_color=True, location_y=self.principled_node.location.y + 500)
        if mai_node:
            second_texture_node = nodes.new('ShaderNodeMixRGB')
            second_texture_node.blend_type = 'MULTIPLY'
            second_texture_node.hide = True
            second_texture_node.location = (mai_node.location.x + 300, mai_node.location.y)
            second_texture_node.inputs['Fac'].default_value = 1.0
            links.new(mai_node.outputs['Color'], second_texture_node.inputs[2])
            links.new(trm_second_screen_node.outputs['Color'], second_texture_node.inputs[1])

        # connect trm
        links.new(second_texture_node.outputs['Color'], screen_node.inputs[2])

        # thc process (optional)
        thc_node = self.import_texture('_thc', non_color=True, location_y=self.principled_node.location.y + 600)
        if thc_node:
            invert_node = nodes.new('ShaderNodeInvert')
            invert_node.hide = True
            invert_node.location = (thc_node.location.x + 300, thc_node.location.y)
            links.new(thc_node.outputs['Color'], invert_node.inputs['Color'])
            links.new(invert_node.outputs['Color'], screen_node.inputs[0])

        # final connect base color
        links.new(screen_node.outputs['Color'], base_color_input)

    def import_second_shader(self):
        """
        Import and setup shader-related textures (_trm and _thc).
        Sets up complex shader mixing with translucent BSDF when _trm exists,
        and optionally connects _thc as a factor if present.
        """
        trm_node = self.import_texture('_trm')
        thc_node = self.import_texture('_thc', non_color=True)

        if trm_node:
            nodes = self.material.node_tree.nodes
            links = self.material.node_tree.links

            # Create and setup multiply mix node
            mix_color_node = nodes.new('ShaderNodeMixRGB')
            mix_color_node.label = 'Trm Multiply'
            mix_color_node.blend_type = 'MULTIPLY'
            mix_color_node.inputs['Fac'].default_value = 1.0
            mix_color_node.inputs[2].default_value = (1, 1, 1, 1)
            mix_color_node.location = (self.principled_node.location.x + 200, self.principled_node.location.y + 200)

            # Connect _trm to mix color
            links.new(trm_node.outputs['Color'], mix_color_node.inputs[1])  # A input

            # Create and setup translucent BSDF
            translucent_node = nodes.new('ShaderNodeBsdfTranslucent')
            links.new(mix_color_node.outputs['Color'], translucent_node.inputs['Color'])

            # Connect normal if exists
            normal_map_node = None
            for link in links:
                if (link.to_node == self.principled_node and
                    link.to_socket.name == 'Normal' and
                    link.from_node.type == 'NORMAL_MAP'):
                    normal_map_node = link.from_node
                    break

            if normal_map_node:
                links.new(normal_map_node.outputs['Normal'], translucent_node.inputs['Normal'])

            # Create and setup mix shader
            mix_shader_node = nodes.new('ShaderNodeMixShader')
            mix_shader_node.inputs['Fac'].default_value = 1.0
            links.new(translucent_node.outputs['BSDF'], mix_shader_node.inputs[1])

            # Create and setup add shader
            add_shader_node = nodes.new('ShaderNodeAddShader')
            links.new(self.principled_node.outputs['BSDF'], add_shader_node.inputs[0])
            links.new(mix_shader_node.outputs['Shader'], add_shader_node.inputs[1])

            # Connect to material output
            output_node = None
            for node in nodes:
                if node.type == 'OUTPUT_MATERIAL':
                    output_node = node
                    break

            if not output_node:
                output_node = nodes.new('ShaderNodeOutputMaterial')

            links.new(add_shader_node.outputs['Shader'], output_node.inputs['Surface'])

            if thc_node:
                links.new(thc_node.outputs['Color'], mix_shader_node.inputs['Fac'])

    def _is_grayscale_image(self, image):
        """흑백 이미지 여부 확인"""
        pixels = image.pixels[:]
        for i in range(0, len(pixels), 4):  # RGBA -> 4개씩 묶음
            r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
            if r != g or g != b or b != r:
                return False  # 색상이 다르면 컬러
        return True  # 모두 동일하면 흑백

    def import_emission(self):
        if not self.principled_node:
            return

        # Emission 노드의 Color 출력이 Principled BSDF의 Emission 입력에 연결되어 있는지 확인
        emission_node = None
        for link in self.material.node_tree.links:
            if (link.to_node == self.principled_node and link.to_socket.name == 'Emission Color'):
                if link.from_node.type == 'TEX_IMAGE':
                    emission_node = link.from_node
                    break

        # if none node, try import _emm
        if not emission_node:
            emission_node = self.import_texture('_emm')

        if not emission_node:
            emission_node = self.import_texture('_emi')

        if emission_node and emission_node.image:
            emission_node.location = (self.base_x_position, self.principled_node.location.y - 250)
            mix_node = self.material.node_tree.nodes.new('ShaderNodeMixRGB')
            mix_node.blend_type = 'MULTIPLY'
            mix_node.inputs['Fac'].default_value = 1.0
            mix_node.location = (emission_node.location.x + 300, emission_node.location.y)
            mix_node.hide = True

            base_color_input = self.principled_node.inputs['Base Color']
            if base_color_input.is_linked:
                self.material.node_tree.links.new(base_color_input.links[0].from_node.outputs['Color'], mix_node.inputs[1])
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

import os
import bpy
import re

class MaterialProcessor:
    def __init__(self, material):
        self.material = material
        self.principled_node = self._find_principled_node()
        
    def _find_principled_node(self):
        """Find the Principled BSDF node in the material."""
        for node in self.material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                return node
        return None

    def set_metallic_value(self, value):
        """Set the metallic value for the material."""
        if self.principled_node:
            self.principled_node.inputs['Metallic'].default_value = value

    def link_texture(self, texture_dir, base_name, suffix, input_name, non_color=False, is_normal_map=False):
        """
        Link a texture to a material input.
        
        Args:
            texture_dir: Directory containing textures
            base_name: Base name of the texture
            suffix: Texture suffix (in lowercase)
            input_name: Name of the input to connect to
            non_color: Whether to set colorspace to Non-Color
            is_normal_map: Whether this is a normal map
        """
        if not self.principled_node:
            return
            
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

        texture_path = find_texture_file(texture_dir, base_name, suffix)
        if not texture_path:
            return

        # Create a new image texture node
        tex_image_node = self.material.node_tree.nodes.new('ShaderNodeTexImage')
        tex_image_node.image = bpy.data.images.load(texture_path)
        if non_color:
            tex_image_node.image.colorspace_settings.name = 'Non-Color'

        if is_normal_map:
            # Create and connect a normal map node
            normal_map_node = self.material.node_tree.nodes.new('ShaderNodeNormalMap')
            self.material.node_tree.links.new(tex_image_node.outputs['Color'], normal_map_node.inputs['Color'])
            self.material.node_tree.links.new(normal_map_node.outputs['Normal'], self.principled_node.inputs[input_name])
        else:
            # Directly connect the texture to the specified input
            self.material.node_tree.links.new(tex_image_node.outputs['Color'], self.principled_node.inputs[input_name])

    def _is_grayscale_image(self, image):
        """흑백 이미지 여부 확인"""
        pixels = image.pixels[:]
        for i in range(0, len(pixels), 4):  # RGBA -> 4개씩 묶음
            r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
            if r != g or g != b or b != r:
                return False  # 색상이 다르면 컬러
        return True  # 모두 동일하면 흑백

    def handle_emission(self):
        if not self.principled_node:
            return

        # Emission 노드의 Color 출력이 Principled BSDF의 Emission 입력에 연결되어 있는지 확인
        emission_node = None
        for link in self.material.node_tree.links:
            if (link.to_node == self.principled_node and link.to_socket.name == 'Emission Color'):
                if link.from_node.type == 'TEX_IMAGE':
                    emission_node = link.from_node
                    break

        if emission_node and emission_node.image:
            if self._is_grayscale_image(emission_node.image):
                emission_node.image.colorspace_settings.name = 'Non-Color'
            
            mix_node = self.material.node_tree.nodes.new('ShaderNodeMixRGB')
            mix_node.blend_type = 'MULTIPLY'
            mix_node.inputs['Fac'].default_value = 1.0

            base_color_input = self.principled_node.inputs['Base Color']
            if base_color_input.is_linked:
                self.material.node_tree.links.new(base_color_input.links[0].from_node.outputs['Color'], mix_node.inputs[1])
            self.material.node_tree.links.new(emission_node.outputs['Color'], mix_node.inputs[2])
            self.material.node_tree.links.new(mix_node.outputs['Color'], self.principled_node.inputs['Emission Color'])

    def handle_alpha_connection(self, texture_dir, base_name):
        """Handle the alpha connection, removing existing links and connecting _Opa."""
        if not self.principled_node:
            return

        # Remove existing alpha links unconditionally
        for link in self.material.node_tree.links:
            if link.to_node == self.principled_node and link.to_socket.name == "Alpha":
                self.material.node_tree.links.remove(link)

        # Check for _Opa texture and connect if available
        alpha_path = os.path.join(texture_dir, f"{base_name}_Opa.png")
        if os.path.exists(alpha_path):
            tex_image_node = self.material.node_tree.nodes.new('ShaderNodeTexImage')
            tex_image_node.image = bpy.data.images.load(alpha_path)
            tex_image_node.image.colorspace_settings.name = 'Non-Color'
            self.material.node_tree.links.new(tex_image_node.outputs['Color'], self.principled_node.inputs['Alpha'])

    def find_base_texture(nodes):        
        # Define base suffixes
        suffixes = ['_Alb', '_Emm', '_Emi']
        
        # 각 suffix를 정규표현식 패턴으로 변환
        # re.escape()를 사용하여 특수문자가 있을 경우 처리
        patterns = [re.compile(re.escape(suffix), re.IGNORECASE) for suffix in suffixes]
        
        for node in nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                image_path = bpy.path.abspath(node.image.filepath)
                basename = os.path.basename(image_path)
                
                # 각 패턴에 대해 검사
                for pattern, original_suffix in zip(patterns, suffixes):
                    match = pattern.search(basename)
                    if match:
                        # 실제 찾은 suffix를 사용
                        found_suffix = basename[match.start():match.end()]
                        base_name = basename[:match.start()]
                        return base_name
                        
        return None

    def find_base_from_material(material):
        """Extract base_name from the material name."""
        if not material:
            return None  # If no material is provided, return None

        # Remove suffixes like '.001', '.002', etc.
        return material.name.split('.')[0]


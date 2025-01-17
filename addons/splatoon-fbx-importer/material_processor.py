import os
import bpy
import re

class MaterialProcessor:
    def __init__(self, material, file_path):
        self.material = material
        self.file_path = file_path
        self.base_name = self._find_base_texture() or self._find_base_from_material()
        self.principled_node = self._find_principled_node()

    def _find_principled_node(self):
        """Find the Principled BSDF node in the material."""
        for node in self.material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                return node
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

    def import_texture(self, suffix, non_color=False):
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

        self.material.node_tree.links.new(tex_image_node.outputs['Color'], normal_map_node.inputs['Color'])
        self.material.node_tree.links.new(normal_map_node.outputs['Normal'], self.principled_node.inputs['Normal'])

    # TODO tcl과 alb 을 mix하고 이후 mai를 multiple해야할듯, alb관련 텍스쳐니까 걍 한함수로 컨트롤해야하나?
    def import_team_color(self):
        pass

    def import_mai(self):
        pass

    # TODO 쉐이더로 관리하는건 기정사실인데, 이둘도 한한함수로 처리해야 순서가 안꼬일듯. 아마 trm은 무조건있고 thc는 있을때도있고 없을때도있고 그랬떤걸로
    # 쉐이더말고 image로 관리하게하는 bool을 주긴해야할듯 머리카락말고는 대체로 쉐이더필요없음
    def import_trm(self):
        pass

    def import_thc(self):
        pass

    # 기타 예약 텍스처는 우선 import를 해줄지 말지 고민해야겠다. import unlink texture 이런거..?

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

bl_info = {
    "name": "Splatoon FBX Importer",
    "author": "blancgoat",
    "version": (1, 5),
    "blender": (4, 0, 0),
    "location": "File > Import > Splatoon FBX (.fbx)",
    "description": "Enhanced FBX importer for Splatoon models with automatic texture linking.",
    "category": "Import-Export",
}

import bpy
import os
from collections import deque

processing_queue = deque()
imported_objects = []

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

    def is_grayscale_image(self, image):
        """흑백 이미지 여부 확인"""
        if not image or not image.has_data:
            return True  # 데이터가 없으면 흑백으로 간주
        pixels = image.pixels[:]
        for i in range(0, len(pixels), 4):  # RGBA -> 4개씩 묶음
            r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
            if r != g or g != b or b != r:
                return False  # 색상이 다르면 컬러
        return True  # 모두 동일하면 흑백

    def handle_emission(self):
        """emission파일이 흑백일경우 적절히 조치"""
        if not self.principled_node:
            return

        # Emission 노드의 Color 출력이 Principled BSDF의 Emission 입력에 연결되어 있는지 확인
        emission_node = None
        for link in self.material.node_tree.links:
            if (link.to_node == self.principled_node and link.to_socket.name == 'Emission Color'):
                if link.from_node.type == 'TEX_IMAGE':
                    emission_node = link.from_node
                    break

        if emission_node:
            # 컬러면 진행하지않음
            if not (emission_node.image and self.is_grayscale_image(emission_node.image)):
                return
            
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

class IMPORT_OT_splatoon_fbx(bpy.types.Operator):
    """Custom Splatoon FBX Importer with batch support"""
    bl_idname = "import_scene.splatoon_fbx"
    bl_label = "Splatoon FBX (.fbx)"
    bl_options = {'REGISTER', 'UNDO'}
    
    files: bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    directory: bpy.props.StringProperty(
        subtype='DIR_PATH',
        options={'HIDDEN'},
    )

    def execute(self, context):
        global processing_queue, imported_objects
        processing_queue.clear()
        imported_objects.clear()
        
        # 먼저 모든 파일 정보를 대기열에 추가
        for file_elem in self.files:
            filepath = os.path.join(self.directory, file_elem.name)
            file_path = os.path.dirname(filepath)
            file_name = os.path.splitext(file_elem.name)[0]
            processing_queue.append((filepath, file_path, file_name))
        
        # 첫 번째 파일 처리 시작
        if processing_queue:
            filepath, file_path, file_name = processing_queue.popleft()
            
            # 현재 선택된 오브젝트 저장
            prev_selected = set(obj.name for obj in bpy.context.selected_objects)
            
            # FBX 임포트
            bpy.ops.import_scene.fbx(filepath=filepath)
            
            # 새로 임포트된 오브젝트 찾기
            new_objects = [obj for obj in bpy.context.selected_objects if obj.name not in prev_selected]
            imported_objects.append((file_name, new_objects))
            
            # 후처리를 위한 타이머 등록
            bpy.app.timers.register(
                lambda: process_imported_fbx_after_delay(file_path, file_name)
            )
        
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
def find_base_texture(nodes):
    import re
    
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

def process_imported_fbx_after_delay(file_path, file_name):
    """Wait until FBX import finishes before processing meshes."""
    global imported_objects
    
    if not imported_objects:
        return 0.1  # 임포트된 오브젝트가 없으면 재시도
    
    current_file_name, current_objects = imported_objects[0]
    
    # 현재 파일의 오브젝트만 처리
    for obj in current_objects:
        if obj.type == 'ARMATURE':
            obj.scale = (1.0, 1.0, 1.0)
            obj.name = current_file_name  # 현재 파일 이름으로 설정
        elif obj.type == 'MESH':
            for mat_slot in obj.material_slots:
                if mat_slot.material and mat_slot.material.use_nodes:
                    material_processor = MaterialProcessor(mat_slot.material)
                    material_processor.set_metallic_value(0.0)
                    
                    for link in material_processor.material.node_tree.links:
                        if (link.to_node == material_processor.principled_node and 
                            link.to_socket.name == "Alpha"):
                            material_processor.material.node_tree.links.remove(link)
                    
                    base_name = find_base_texture(mat_slot.material.node_tree.nodes) or find_base_from_material(mat_slot.material)

                    material_processor.link_texture(file_path, base_name, "_mtl", "Metallic", non_color=True)
                    material_processor.link_texture(file_path, base_name, "_rgh", "Roughness", non_color=True)
                    material_processor.link_texture(file_path, base_name, "_opa", "Alpha", non_color=True)
                    material_processor.link_texture(file_path, base_name, "_nrm", "Normal", non_color=True, is_normal_map=True)

                    material_processor.handle_emission()
    
    # 현재 파일 처리 완료
    imported_objects.pop(0)
    
    # 모든 객체 선택 해제
    bpy.ops.object.select_all(action='DESELECT')
    
    # 대기열에 다음 파일이 있으면 처리 시작
    if processing_queue:
        filepath, file_path, file_name = processing_queue.popleft()
        
        # 현재 선택된 오브젝트 저장
        prev_selected = set(obj.name for obj in bpy.context.selected_objects)
        
        # 다음 FBX 임포트
        bpy.ops.import_scene.fbx(filepath=filepath)
        
        # 새로 임포트된 오브젝트 찾기
        new_objects = [obj for obj in bpy.context.selected_objects if obj.name not in prev_selected]
        imported_objects.append((file_name, new_objects))
        
        return 0.1  # 다음 파일의 후처리를 위해 타이머 유지
    
    return None  # 모든 처리 완료

def menu_func_import(self, context):
    self.layout.operator(IMPORT_OT_splatoon_fbx.bl_idname, text="Splatoon FBX (.fbx)")

def register():
    bpy.utils.register_class(IMPORT_OT_splatoon_fbx)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(IMPORT_OT_splatoon_fbx)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
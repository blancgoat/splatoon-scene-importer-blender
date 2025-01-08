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
        """Link a texture to a material input."""
        if not self.principled_node:
            return

        texture_path = os.path.join(texture_dir, f"{base_name}{suffix}.png")
        if not os.path.exists(texture_path):
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

def find_base_from_material(material):
    """Extract base_name from the material name."""
    if not material:
        return None  # If no material is provided, return None

    # Remove suffixes like '.001', '.002', etc.
    base_name = material.name.split('.')[0]
    base_name = base_name.split('_')[0]
    return base_name

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
                    
                    base_name = find_base_from_material(mat_slot.material)
                    material_processor.link_texture(file_path, base_name, "_Mtl", "Metallic", non_color=True)
                    material_processor.link_texture(file_path, base_name, "_Rgh", "Roughness", non_color=True)
                    material_processor.link_texture(file_path, base_name, "_Opa", "Alpha", non_color=True)
                    material_processor.link_texture(file_path, base_name, "_Nrm", "Normal", non_color=True, is_normal_map=True)
    
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